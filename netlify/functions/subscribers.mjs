/* 구독자 목록 조회 — 발송 스크립트만 쓸 수 있게 토큰으로 보호.
   Netlify 환경변수 PUSH_ADMIN_TOKEN 과 일치해야 응답합니다. */
import { getStore } from '@netlify/blobs';

export default async (req) => {
  const token = req.headers.get('x-admin-token');
  const expected = Netlify.env.get('PUSH_ADMIN_TOKEN');
  if (!expected || token !== expected) {
    return new Response(JSON.stringify({ error: 'unauthorized' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } });
  }

  const store = getStore('push-subs');
  const { blobs } = await store.list();
  const subs = [];
  for (const b of blobs) {
    const v = await store.get(b.key, { type: 'json' });
    if (v && v.subscription) subs.push(v.subscription);
  }
  return new Response(JSON.stringify({ count: subs.length, subscriptions: subs }),
    { headers: { 'Content-Type': 'application/json' } });
};

export const config = { path: '/api/subscribers' };
