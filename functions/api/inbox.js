/* 관리자용 — 이메일 구독자와 받은 의견을 한 번에 조회.
   PUSH_ADMIN_TOKEN 으로 보호. 발송 스크립트와 사장님 확인용. */

export async function onRequestGet({ request, env }) {
  const token = request.headers.get('x-admin-token');
  if (!env.PUSH_ADMIN_TOKEN || token !== env.PUSH_ADMIN_TOKEN) {
    return new Response(JSON.stringify({ error: 'unauthorized' }), {
      status: 401, headers: { 'Content-Type': 'application/json' },
    });
  }
  if (!env.NB_KV) {
    return new Response(JSON.stringify({ error: 'KV not bound' }), {
      status: 500, headers: { 'Content-Type': 'application/json' },
    });
  }

  async function collect(prefix) {
    const out = [];
    let cursor;
    do {
      const list = await env.NB_KV.list({ prefix, cursor });
      for (const k of list.keys) {
        const v = await env.NB_KV.get(k.name, { type: 'json' });
        if (v) out.push(v);
      }
      cursor = list.list_complete ? null : list.cursor;
    } while (cursor);
    return out;
  }

  const [emails, feedback] = await Promise.all([collect('email:'), collect('fb:')]);
  feedback.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

  return new Response(JSON.stringify({
    subscribers: emails.map((e) => e.email),
    subscriber_count: emails.length,
    feedback,
    feedback_count: feedback.length,
  }, null, 2), { headers: { 'Content-Type': 'application/json' } });
}
