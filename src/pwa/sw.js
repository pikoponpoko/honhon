// HonHon service worker: 本体は常にネットワーク優先（公開の更新をすぐ反映）、オフライン時はキャッシュを使う
const CACHE = 'honhon-__BUILD__';
// フォントは公開のたびに取り直さないよう、本体とは別の消さないキャッシュに入れる
const FONTS = 'honhon-fonts';
const CORE = ['/', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png', '/boards.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k.startsWith('honhon-') && k !== CACHE && k !== FONTS).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  const font = u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com';
  if (u.origin !== self.location.origin && !font) return;
  // Dropbox のサインインから戻るページはキャッシュしない（本体の代わりに保存されないように）
  if (u.pathname.startsWith('/tehon-auth')) return;
  if (font) {
    // フォントはキャッシュ優先
    e.respondWith(caches.match(r).then(hit => hit || fetch(r).then(res => {
      if (res.ok || res.type === 'opaque') { const cp = res.clone(); caches.open(FONTS).then(c => c.put(r, cp)); }
      return res;
    })));
    return;
  }
  e.respondWith(fetch(r).then(res => {
    if (res.ok) { const cp = res.clone(); caches.open(CACHE).then(c => c.put(r.mode === 'navigate' ? '/' : r, cp)); }
    return res;
  }).catch(() => caches.match(r.mode === 'navigate' ? '/' : r)));
});
