/**
 * StreakLab — Mobile Push Notification Service Worker (sw.js)
 * Handles background Web Push events, notifications when the browser/PWA is closed,
 * and user interactions when tapping notifications.
 */

const SW_VERSION = 'streaklab-v2.1';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('push', (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = {
        title: 'StreakLab Reminder',
        body: event.data.text() || 'Time to check in on your habits!'
      };
    }
  } else {
    data = {
      title: 'StreakLab Reminder',
      body: 'Time to check in on your habits!'
    };
  }

  const title = data.title || 'StreakLab Reminder 🔔';
  const options = {
    body: data.body || 'Keep your streak alive today!',
    icon: data.icon || '/static/icons/icon-192.png',
    badge: data.badge || '/static/icons/icon-192.png',
    tag: data.tag || 'streaklab-habit-reminder',
    renotify: true,
    vibrate: [120, 60, 120],
    data: {
      url: data.url || '/',
      habitId: data.habitId || null,
      timestamp: Date.now()
    },
    actions: data.actions || [
      { action: 'open', title: 'Open StreakLab' },
      { action: 'dismiss', title: 'Dismiss' }
    ]
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const notifData = event.notification.data || {};
  let targetUrl = notifData.url || '/';

  // If user clicked the "dismiss" action, take no further action
  if (event.action === 'dismiss') {
    return;
  }

  // If user clicked "completed" action with a habitId, navigate to habit overview
  if (event.action === 'completed' && notifData.habitId) {
    targetUrl = `/#overview?focusHabit=${encodeURIComponent(notifData.habitId)}`;
  }

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // If a StreakLab window is already open, focus it and navigate
      for (const client of clientList) {
        if ('focus' in client) {
          if ('navigate' in client && targetUrl !== '/') {
            client.navigate(targetUrl);
          }
          return client.focus();
        }
      }
      // Otherwise open a new window
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
    })
  );
});
