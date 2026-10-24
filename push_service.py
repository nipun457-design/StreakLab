"""
=============================================================================
StreakLab — Real Mobile Web Push Notification Service (push_service.py)
Implements standards-based Web Push with VAPID credentials, subscription management,
expired endpoint pruning, and serverless cron-compatible reminder scheduling.
=============================================================================
"""

import os
import re
import json
import base64
import logging
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
import pywebpush
from pywebpush import webpush, WebPushException
from py_vapid import Vapid
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("streaklab.push_service")

# Default claim email if not provided in environment
DEFAULT_CLAIM_EMAIL = "mailto:admin@streaklab.app"


def get_vapid_config():
    """
    Reads VAPID credentials and cron secrets from environment variables.
    """
    pub = os.environ.get("VAPID_PUBLIC_KEY", "").strip()
    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    email = os.environ.get("VAPID_CLAIM_EMAIL", "").strip() or DEFAULT_CLAIM_EMAIL
    if not email.startswith("mailto:"):
        email = f"mailto:{email}"

    cron_secret = os.environ.get("CRON_SECRET", "").strip()
    return {
        "public_key": pub,
        "private_key": priv,
        "claim_email": email,
        "cron_secret": cron_secret,
        "is_configured": bool(pub and priv)
    }


def is_vapid_configured():
    """Returns True if VAPID credentials are set in environment variables."""
    cfg = get_vapid_config()
    return cfg["is_configured"]


def get_vapid_public_key():
    """Returns the VAPID public key string, or None if unconfigured."""
    cfg = get_vapid_config()
    return cfg["public_key"] if cfg["is_configured"] else None


def generate_vapid_keypair():
    """
    Generates a new P-256 VAPID keypair suitable for Web Push notifications.
    Returns a dictionary with base64url-encoded public and private keys and PEM private key.
    """
    v = Vapid()
    v.generate_keys()

    raw_pub = v.public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint
    )
    b64_pub = base64.urlsafe_b64encode(raw_pub).rstrip(b'=').decode('utf-8')

    pem_priv = v.private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    ).decode('utf-8')

    raw_priv = v.private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    )
    b64_priv = base64.urlsafe_b64encode(raw_priv).rstrip(b'=').decode('utf-8')

    return {
        "public_key": b64_pub,
        "private_key": b64_priv,
        "private_key_pem": pem_priv
    }


def save_subscription(db, sub_data, user_agent="", timezone="UTC"):
    """
    Saves or reactivates a browser push subscription in the database.
    """
    if not sub_data or not isinstance(sub_data, dict):
        raise ValueError("Invalid subscription data: must be an object")

    endpoint = sub_data.get("endpoint")
    keys = sub_data.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        raise ValueError("Missing endpoint, p256dh, or auth in push subscription")

    # Validate timezone or fallback to UTC
    tz = str(timezone or "UTC").strip()
    try:
        ZoneInfo(tz)
    except Exception:
        tz = "UTC"

    # Check existing subscription by endpoint
    existing = db.execute("SELECT id FROM push_subscriptions WHERE endpoint = ?", (endpoint,)).fetchone()
    if existing:
        db.execute("""
            UPDATE push_subscriptions
            SET p256dh = ?, auth = ?, user_agent = ?, timezone = ?, active = 1
            WHERE endpoint = ?
        """, (p256dh, auth, user_agent, tz, endpoint))
        sub_id = existing["id"]
    else:
        cur = db.execute("""
            INSERT INTO push_subscriptions (endpoint, p256dh, auth, user_agent, timezone, active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (endpoint, p256dh, auth, user_agent, tz))
        sub_id = cur.lastrowid

    db.commit()
    return {
        "id": sub_id,
        "endpoint": endpoint,
        "timezone": tz,
        "active": 1
    }


def remove_subscription(db, endpoint):
    """
    Deactivates a push subscription when the user turns off push notifications.
    """
    if not endpoint:
        return False
    db.execute("UPDATE push_subscriptions SET active = 0 WHERE endpoint = ?", (endpoint,))
    db.commit()
    return True


def delete_subscription(db, endpoint):
    """
    Completely removes an expired subscription (e.g. HTTP 410 Gone from push service).
    """
    if not endpoint:
        return False
    db.execute("DELETE FROM push_subscriptions WHERE endpoint = ?", (endpoint,))
    db.commit()
    return True


def send_web_push(subscription_dict, payload_dict):
    """
    Dispatches a single Web Push notification through the browser vendor's push service.
    Handles expired subscriptions (HTTP 410 / 404) safely.
    """
    cfg = get_vapid_config()
    if not cfg["is_configured"]:
        return {
            "success": False,
            "error": "VAPID credentials not configured on server",
            "unconfigured": True
        }

    sub_info = {
        "endpoint": subscription_dict.get("endpoint"),
        "keys": {
            "p256dh": subscription_dict.get("p256dh"),
            "auth": subscription_dict.get("auth")
        }
    }

    payload_json = json.dumps(payload_dict)

    try:
        response = webpush(
            subscription_info=sub_info,
            data=payload_json,
            vapid_private_key=cfg["private_key"],
            vapid_claims={"sub": cfg["claim_email"]}
        )
        return {
            "success": True,
            "status_code": getattr(response, "status_code", 200)
        }
    except WebPushException as exc:
        status_code = getattr(exc.response, "status_code", None) if hasattr(exc, "response") and exc.response else None
        is_expired = status_code in (404, 410)
        logger.warning(f"WebPush delivery error: {exc} (HTTP {status_code})")
        return {
            "success": False,
            "status_code": status_code,
            "error": str(exc),
            "expired": is_expired
        }
    except Exception as exc:
        logger.error(f"Unexpected WebPush error: {exc}")
        return {
            "success": False,
            "error": str(exc),
            "expired": False
        }


def send_test_push(db, endpoint=None):
    """
    Sends an immediate test push notification to verify phone and browser integration.
    """
    if not is_vapid_configured():
        return {
            "success": False,
            "error": "VAPID keys not configured. Set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY."
        }

    if endpoint:
        sub = db.execute("SELECT * FROM push_subscriptions WHERE endpoint = ? AND active = 1", (endpoint,)).fetchone()
    else:
        sub = db.execute("SELECT * FROM push_subscriptions WHERE active = 1 ORDER BY id DESC LIMIT 1").fetchone()

    if not sub:
        return {
            "success": False,
            "error": "No active push subscription found on this device. Please enable notifications first."
        }

    payload = {
        "title": "StreakLab Push Connected 🔥",
        "body": "Mobile push notifications are working smoothly on your device!",
        "icon": "/static/icons/icon-192.png",
        "badge": "/static/icons/icon-192.png",
        "tag": "streaklab-test-notification",
        "url": "/#settings",
        "actions": [
            {"action": "open", "title": "Open StreakLab"}
        ]
    }

    res = send_web_push(dict(sub), payload)
    if res.get("expired"):
        delete_subscription(db, sub["endpoint"])
    return res


def check_and_send_due_reminders(db, now_override=None):
    """
    Evaluates all active habits with enabled reminders against current local time per subscriber.
    - Honors completion status: skips habits already completed today.
    - Strictly prevents duplicate notifications: checks habit_notification_logs.
    - Handles expired subscriptions safely.
    - Returns an execution summary dictionary.
    """
    cfg = get_vapid_config()
    if not cfg["is_configured"]:
        return {
            "status": "skipped",
            "message": "VAPID keys not configured on server",
            "processed": 0,
            "sent": 0
        }

    # Fetch all active subscriptions
    subscriptions = db.execute("SELECT * FROM push_subscriptions WHERE active = 1").fetchall()
    if not subscriptions:
        return {
            "status": "ok",
            "message": "No active push subscriptions",
            "processed": 0,
            "sent": 0
        }

    # Fetch all active habits with enabled reminders
    habits = db.execute("""
        SELECT h.id, h.name, h.target_time, h.target_frequency, h.category,
               COALESCE(r.reminder_time, h.reminder_time, '08:00') AS reminder_time,
               COALESCE(r.enabled, h.reminder_enabled, 1) AS reminder_enabled
        FROM habits h
        LEFT JOIN habit_reminders r ON h.id = r.habit_id
        WHERE h.active = 1 AND COALESCE(r.enabled, h.reminder_enabled, 1) = 1
    """).fetchall()

    processed_count = 0
    sent_count = 0
    skipped_completed = 0
    skipped_duplicate = 0
    expired_cleaned = 0

    utc_now = datetime.now(ZoneInfo("UTC"))

    for sub in subscriptions:
        sub_dict = dict(sub)
        tz_name = sub_dict.get("timezone") or "UTC"
        try:
            user_tz = ZoneInfo(tz_name)
        except Exception:
            user_tz = ZoneInfo("UTC")

        # Local time for this subscriber
        local_now = now_override if now_override else utc_now.astimezone(user_tz)
        local_today_str = local_now.date().isoformat()
        current_hm = local_now.strftime("%H:%M")
        weekday_idx = local_now.weekday()  # 0=Mon, 6=Sun
        is_weekend = weekday_idx in (5, 6)

        for habit in habits:
            processed_count += 1
            hid = habit["id"]
            hname = habit["name"]
            rem_time = habit["reminder_time"] or "08:00"
            freq = (habit["target_frequency"] or "daily").strip().lower()

            # Schedule frequency filter
            if freq == "weekdays" and is_weekend:
                continue
            if freq == "weekends" and not is_weekend:
                continue

            # Check if reminder is due in the current minute window
            # (Allows exact minute match or within a 2-minute margin for cron schedules)
            rem_m = re.match(r"^(\d{1,2}):(\d{2})", rem_time)
            if not rem_m:
                continue
            r_hour, r_min = int(rem_m.group(1)), int(rem_m.group(2))

            time_diff_minutes = (local_now.hour * 60 + local_now.minute) - (r_hour * 60 + r_min)
            # Due window: exactly now (0 min) or within the last 5 minutes (tolerates minor cron latency)
            if not (0 <= time_diff_minutes <= 5):
                continue

            # 1. Completion check: skip if habit is already marked completed today
            rec_row = db.execute(
                "SELECT status FROM habit_records WHERE habit_id = ? AND record_date = ?",
                (hid, local_today_str)
            ).fetchone()
            if rec_row and rec_row["status"] == "completed":
                skipped_completed += 1
                continue

            # 2. Duplicate prevention check: skip if already sent today for this habit
            log_row = db.execute(
                "SELECT id FROM habit_notification_logs WHERE habit_id = ? AND notification_date = ?",
                (hid, local_today_str)
            ).fetchone()
            if log_row:
                skipped_duplicate += 1
                continue

            # 3. Dispatch Push Notification
            payload = {
                "title": f"Habit Reminder: {hname} 🔔",
                "body": f"Time for your scheduled {hname}! Tap to log your check-in.",
                "icon": "/static/icons/icon-192.png",
                "badge": "/static/icons/icon-192.png",
                "tag": f"habit-{hid}-{local_today_str}",
                "url": f"/#overview",
                "habitId": hid,
                "actions": [
                    {"action": "completed", "title": "Mark Done"},
                    {"action": "open", "title": "Open StreakLab"}
                ]
            }

            result = send_web_push(sub_dict, payload)
            if result.get("success"):
                sent_count += 1
                # Log successful notification to prevent duplicates today
                try:
                    db.execute("""
                        INSERT INTO habit_notification_logs (habit_id, notification_date, notification_time)
                        VALUES (?, ?, ?)
                    """, (hid, local_today_str, current_hm))
                    db.commit()
                except Exception as log_err:
                    logger.warning(f"Failed to record notification log: {log_err}")
            elif result.get("expired"):
                delete_subscription(db, sub_dict["endpoint"])
                expired_cleaned += 1
                break  # Don't send more to this expired subscription

    return {
        "status": "ok",
        "processed": processed_count,
        "sent": sent_count,
        "skipped_completed": skipped_completed,
        "skipped_duplicate": skipped_duplicate,
        "expired_cleaned": expired_cleaned,
        "timestamp": datetime.now(ZoneInfo("UTC")).isoformat()
    }
