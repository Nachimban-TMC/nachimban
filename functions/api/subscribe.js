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
  await env.NB_KV.put(key, JSON.stringify({ subscription: sub, created_at: new Date().toISOString() }));
  return json({ ok: true });
}
