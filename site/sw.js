/* 나침반 서비스워커 — 앱처럼 설치되고, 오프라인에서도 마지막 브리핑을 볼 수 있게. */
const CACHE = 'nachimban-v2';
// 스크립트도 미리 담아둔다 — 이게 없으면 알림 칸이 통째로 사라진다
const CORE = ['/', '/index.html', '/thanks.html', '/manifest.json', '/icon-192.png',
              '/push.js', '/sw-register.js'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

/* 페이지가 '바로 교체하라'고 하면 대기하지 않는다 */
self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/* 네트워크 우선 — 항상 최신 뉴스를 보되, 오프라인이면 캐시로 대체 */
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      })
      .catch(() => caches.match(req).then((r) => {
        if (r) return r;
        // HTML 폴백은 '화면 이동' 요청에만. 스크립트 자리에 HTML을 돌려주면
        // 파싱이 깨져 push.js 가 통째로 죽는다(알림 칸이 안 보이던 원인).
        if (req.mode === 'navigate') return caches.match('/index.html');
        return Response.error();
      }))
  );
});

/* 푸시 알림 수신 (푸시 서버 연결 후 동작) */
self.addEventListener('push', (e) => {
  let data = { title: '나침반', body: '오늘의 브리핑이 도착했습니다.' };
  try { if (e.data) data = Object.assign(data, e.data.json()); } catch (_) {}
  e.waitUntil(self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    data: { url: data.url || '/' },
  }));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/';
  e.waitUntil(clients.matchAll({ type: 'window' }).then((list) => {
    for (const c of list) if (c.url.includes(url) && 'focus' in c) return c.focus();
    return clients.openWindow(url);
  }));
});
