/* 편집팀에 의견 보내기 접수 (Netlify Forms 대체). */

export async function onRequestPost({ request, env }) {
  let type = '', message = '', email = '';
  try {
    const form = await request.formData();
    if ((form.get('bot-field') || '').toString().trim()) {     // 스팸 봇 차단
      return Response.redirect(new URL('/thanks-feedback', request.url), 303);
    }
    type = (form.get('type') || '').toString().trim();
    message = (form.get('message') || '').toString().trim();
    email = (form.get('email') || '').toString().trim();
  } catch {
    return new Response('bad request', { status: 400 });
  }

  if (!message) return new Response('message required', { status: 400 });

  if (env.NB_KV) {
    const key = 'fb:' + new Date().toISOString() + ':' + Math.random().toString(36).slice(2, 7);
    await env.NB_KV.put(key, JSON.stringify({
      type, message: message.slice(0, 4000), email,
      created_at: new Date().toISOString(),
    }));
  }
  return Response.redirect(new URL('/thanks-feedback', request.url), 303);
}
