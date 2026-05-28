/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope;

declare const __WB_MANIFEST: Array<{ url: string; revision: string | null }>;

import { precacheAndRoute } from "workbox-precaching";

precacheAndRoute(self.__WB_MANIFEST);

self.addEventListener("push", (event) => {
  const data = event.data?.json() ?? {};
  const title = data.title || "Howlify";
  const options: NotificationOptions = {
    body: data.body || "",
    icon: "/pwa-192x192.svg",
    badge: "/pwa-192x192.svg",
    data: { url: data.url || "/" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const c of clients) {
        if (c.url === url && "focus" in c) return c.focus();
      }
      return self.clients.openWindow(url);
    }),
  );
});
