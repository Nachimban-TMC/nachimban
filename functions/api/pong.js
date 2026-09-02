/* 배달 확인(pong) — 기기가 푸시를 '실제로 받았을 때' 서비스워커가 호출한다.

   왜 필요한가: 애플 푸시 서버는 이미 죽은 구독에도 2xx(접수)를 돌려주는 경우가
   있어, 발송 로그만으로는 어느 구독이 살아있는지 알 수 없다(2026-09-02 확인).
   기기가 직접 "받았다"고 알려주면 살아있는 구독을 확실히 구분할 수 있고,
   구독자는 아무 조작도 할 필요가 없다. */

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export async function onRequestOptions() {
  return new Response('', { headers: cors });
}

export async function onRequestPost({ request, env }) {
  if (!env.NB_KV) return new Response('', { status: 204, headers: cors });
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response('', { status: 204, headers: cors });
  }
  const endpoint = body && body.endpoint;
  if (!endpoint) return new Response('', { status: 204, headers: cors });

  // subscribe.js 와 동일한 키 규칙
  const key = 'push:' + btoa(endpoint).replace(/[^A-Za-z0-9]/g, '').slice(0, 180);
  const cur = await env.NB_KV.get(key, { type: 'json' });
  if (!cur) return new Response('', { status: 204, headers: cors });  // 모르는 구독은 무시

  cur.last_seen = new Date().toISOString();
  cur.seen_count = (cur.seen_count || 0) + 1;
  await env.NB_KV.put(key, JSON.stringify(cur));
  return new Response('', { status: 204, headers: cors });
}
