/* 나침반 서비스워커 — 앱처럼 설치되고, 오프라인에서도 마지막 브리핑을 볼 수 있게. */
const CACHE = 'nachimban-v3';
// '.html' 주소는 넣지 않는다. Cloudflare Pages 가 확장자 없는 주소로
// 308 리다이렉트하는데, 리다이렉트된 응답은 캐시에 넣을 수 없다.
const CORE = ['/', '/thanks', '/manifest.json', '/icon-192.png', '/sw-register.js',
              '/style.css'];   // CSS 가 없으면 오프라인에서 화면이 깨진다

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) =>
      // addAll 은 하나만 실패해도 전부 실패하고, install 이 실패하면
      // 서비스워커가 영영 활성화되지 않는다(푸시도 영영 불가능해진다).
      // 캐시는 '있으면 좋은 것'일 뿐이므로 실패는 넘기고 설치를 마친다.
      Promise.all(CORE.map((u) =>
        fetch(u).then((r) => (r.ok && !r.redirected ? c.put(u, r) : null))
                .catch(() => null)
      ))
    ).catch(() => null).then(() => self.skipWaiting())
  );
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
        // 리다이렉트·에러 응답은 캐시에 넣을 수 없다(넣으려 하면 예외).
        if (res.ok && !res.redirected) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
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
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      const target = new URL(url, self.location.origin);
      for (const c of list) {
        let same = false;
        try { same = new URL(c.url).origin === target.origin; } catch (_) {}
        if (!same) continue;
        // 이미 열려 있는 창은 '새 주소로 이동'시킨다. focus 만 하면 어제 화면이
        // 그대로 남아, 사용자가 앱을 껐다 다시 켜야 오늘 뉴스를 보게 된다.
        if ('navigate' in c) {
          return c.navigate(target.href).then((cl) => (cl || c).focus()).catch(() => c.focus());
        }
        return c.focus();
      }
      return clients.openWindow(target.href);
    })
  );
});
