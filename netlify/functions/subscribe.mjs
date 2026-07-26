/* 푸시 구독 저장 — 방문자가 '알림 받기'를 누르면 여기로 구독 정보가 옵니다.
   저장소는 Netlify Blobs (무료). 개인정보는 브라우저가 만든 구독 endpoint 뿐입니다. */
import { getStore } from '@netlify/blobs';

export default async (req) => {
  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  if (req.method === 'OPTIONS') return new Response('', { headers: cors });

  const store = getStore('push-subs');

  try {
    const body = await req.json();
    const sub = body && body.subscription;
    if (!sub || !sub.endpoint) {
      return new Response(JSON.stringify({ error: 'subscription required' }),
        { status: 400, headers: { ...cors, 'Content-Type': 'application/json' } });
    }
    // endpoint 를 키로 (중복 구독 방지)
    const key = Buffer.from(sub.endpoint).toString('base64url').slice(0, 200);

    if (req.method === 'DELETE') {
      await store.delete(key);
      return new Response(JSON.stringify({ ok: true, removed: true }),
        { headers: { ...cors, 'Content-Type': 'application/json' } });
    }

    await store.setJSON(key, { subscription: sub, created_at: new Date().toISOString() });
    return new Response(JSON.stringify({ ok: true }),
      { headers: { ...cors, 'Content-Type': 'application/json' } });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }),
      { status: 500, headers: { ...cors, 'Content-Type': 'application/json' } });
  }
};

export const config = { path: '/api/subscribe' };
