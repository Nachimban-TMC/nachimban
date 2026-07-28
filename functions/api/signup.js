/* 이메일 구독 접수 (Netlify Forms 대체).
   폼 전송을 받아 KV 에 저장하고 완료 페이지로 보냅니다. */

export async function onRequestPost({ request, env }) {
  const ct = request.headers.get('content-type') || '';
  let email = '';
  try {
    if (ct.includes('application/json')) {
      email = ((await request.json()).email || '').trim();
    } else {
      const form = await request.formData();
      if ((form.get('bot-field') || '').toString().trim()) {   // 스팸 봇 차단
        return Response.redirect(new URL('/thanks', request.url), 303);
      }
      email = (form.get('email') || '').toString().trim();
    }
  } catch {
    return new Response('bad request', { status: 400 });
  }

  if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return new Response('invalid email', { status: 400 });
  }
  if (env.NB_KV) {
    await env.NB_KV.put('email:' + email.toLowerCase(), JSON.stringify({
      email, created_at: new Date().toISOString(),
    }));
  }
  // 폼 전송이면 완료 페이지로, fetch 면 JSON 으로
  if (ct.includes('application/json')) {
    return new Response(JSON.stringify({ ok: true }), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  return Response.redirect(new URL('/thanks', request.url), 303);
}
