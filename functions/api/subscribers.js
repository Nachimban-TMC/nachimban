/* 푸시 구독자 목록 — 발송 스크립트 전용. PUSH_ADMIN_TOKEN 으로 보호. */

export async function onRequestGet({ request, env }) {
  const token = request.headers.get('x-admin-token');
  if (!env.PUSH_ADMIN_TOKEN || token !== env.PUSH_ADMIN_TOKEN) {
    return new Response(JSON.stringify({ error: 'unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!env.NB_KV) {
    return new Response(JSON.stringify({ error: 'KV not bound' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const subs = [];
  let cursor;
  do {
    const list = await env.NB_KV.list({ prefix: 'push:', cursor });
    for (const k of list.keys) {
      const v = await env.NB_KV.get(k.name, { type: 'json' });
      if (v && v.subscription) subs.push(v.subscription);
    }
    cursor = list.list_complete ? null : list.cursor;
  } while (cursor);

  return new Response(JSON.stringify({ count: subs.length, subscriptions: subs }), {
    headers: { 'Content-Type': 'application/json' },
  });
}
