<?php
/* Фоновый помощник браузера (service worker) Rai: показывает push-уведомления, даже когда сайт закрыт.
   Страницы не перехватывает (нет обработчика fetch) — сайт, нейросеть и модели грузятся как обычно. */
header('Content-Type: application/javascript; charset=utf-8');
header('Cache-Control: no-cache');
header('X-Content-Type-Options: nosniff');
?>
"use strict";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let d = {};
  try { d = event.data ? event.data.json() : {}; } catch (e) { d = {body: event.data ? event.data.text() : ""}; }
  const options = {
    body: d.body || "",
    icon: d.icon || "icon.php?s=192",
    badge: "icon.php?s=96",
    data: {url: d.url || "chat.html"},
    lang: "ru"
  };
  if (d.tag) { options.tag = d.tag; options.renotify = true; }
  event.waitUntil(self.registration.showNotification(d.title || "Rai", options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL((event.notification.data && event.notification.data.url) || "chat.html", self.registration.scope).href;
  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then((list) => {
    for (const c of list) if (c.url.split("#")[0] === url.split("#")[0] && "focus" in c) return c.focus();
    return self.clients.openWindow ? self.clients.openWindow(url) : null;
  }));
});

// браузер сменил подписку (например, после обновления) — сообщаем сайту новую
self.addEventListener("pushsubscriptionchange", (event) => {
  event.waitUntil((async () => {
    const r = await fetch("push_api.php", {cache: "no-store"});
    const info = await r.json();
    if (!info.key) return;
    const raw = atob(info.key.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((info.key.length + 3) % 4));
    const key = Uint8Array.from(raw, (c) => c.charCodeAt(0));
    const sub = await self.registration.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: key});
    if (event.oldSubscription) {
      await fetch("push_api.php", {method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({action: "unsubscribe", endpoint: event.oldSubscription.endpoint})});
    }
    // новую подписку страница сохранит сама при следующем открытии (нужен токен входа)
    const all = await self.clients.matchAll({type: "window", includeUncontrolled: true});
    for (const c of all) c.postMessage({type: "rai-push-resubscribed", endpoint: sub.endpoint});
  })());
});
