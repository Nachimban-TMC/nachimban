/* 푸시 구독 저장/해제 — Cloudflare Pages Functions + KV
   (기존 Netlify Functions + Blobs 를 대체) */

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { ...cors, 'Content-Type': 'application/json' },
  });

export async function onRequestOptions() {
  return new Response('', { headers: cors });
}

export async function onRequestPost({ request, env }) {
  return save(request, env, false);
}

export async function onRequestDelete({ request, env }) {
  return save(request, env, true);
}

async function save(request, env, remove) {
  if (!env.NB_KV) return json({ error: 'KV not bound' }, 500);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: 'invalid json' }, 400);
  }
  const sub = body && body.subscription;
  if (!sub || !sub.endpoint) return json({ error: 'subscription required' }, 400);

  // endpoint 를 키로 (같은 기기 중복 저장 방지)
  const key = 'push:' + btoa(sub.endpoint).replace(/[^A-Za-z0-9]/g, '').slice(0, 180);

  if (remove) {
    await env.NB_KV.delete(key);
    return json({ ok: true, removed: true });
  }
  // 같은 기기가 다시 등록할 때 기존 기록을 덮어쓰면 안 된다. 앱을 열 때마다
  // push.js 가 자동으로 재등록하므로, 그때마다 '언제 처음 구독했는지'와
  // '실제로 알림을 받았는지'(last_seen·seen_count)가 지워진다. 그러면 살아 있는
  // 기기와 죽은 기기를 구분할 근거가 사라진다. 그래서 기존 값을 살려서 합친다.
  let prev = null;
  try {
    prev = await env.NB_KV.get(key, 'json');
  } catch { /* 기록이 없거나 깨졌으면 새로 만든다 */ }
  const rec = { subscription: sub, created_at: (prev && prev.created_at) || new Date().toISOString() };
  if (prev && prev.last_seen) rec.last_seen = prev.last_seen;
  if (prev && prev.seen_count) rec.seen_count = prev.seen_count;
  await env.NB_KV.put(key, JSON.stringify(rec));
  return json({ ok: true });
}
