/*
  朝刊テック - Service Worker（ステップ8: PWA）

  役割:
   1. アプリの土台（HTML/アイコン/マニフェスト）をキャッシュし、オフラインでも起動できるようにする
   2. データ(/api/* ・ ./data/*.json)は「ネット優先・失敗時キャッシュ」で、最新を出しつつ圏外でも前回分を表示
   3. 将来のWeb Push通知の受け口（push / notificationclick）を用意しておく

  iOSのPWAでは、ホーム画面に追加したアプリからの起動時に Service Worker が有効になる。
*/

const CACHE = 'morning-tech-v1';

// オフラインでも起動できるよう最初にキャッシュしておく土台ファイル
const APP_SHELL = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const isData = url.pathname.startsWith('/api/') || url.pathname.includes('/data/');

  if (isData) {
    // データはネット優先（最新を出す）。失敗したらキャッシュにフォールバック。
    event.respondWith(
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => caches.match(req))
    );
  } else {
    // 土台ファイルはキャッシュ優先（高速・オフライン対応）。
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req))
    );
  }
});

// ===== Web Push の受け口（ステップ8の発展。送信側を作れば有効になる） =====
self.addEventListener('push', (event) => {
  let data = { title: '朝刊テック', body: '今朝のまとめができました。' };
  try { if (event.data) data = event.data.json(); } catch (e) { /* テキストpushはデフォルト文言 */ }
  event.waitUntil(
    self.registration.showNotification(data.title || '朝刊テック', {
      body: data.body || '',
      icon: './icons/icon-192.png',
      badge: './icons/icon-192.png',
      data: { url: data.url || './' },
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || './';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) { if ('focus' in c) return c.focus(); }
      if (clients.openWindow) return clients.openWindow(target);
    })
  );
});
