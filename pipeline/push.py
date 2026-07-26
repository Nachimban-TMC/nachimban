"""앱 푸시 발송 — 아침에 알림을 누르면 바로 오늘의 브리핑으로.

구조:
  브라우저에서 '알림 받기' → /api/subscribe (Netlify Function) → Netlify Blobs 저장
  발송 시 → /api/subscribers 로 목록을 받아 → 각 기기에 웹푸시 전송

필요한 것:
  data/vapid.json      VAPID 키쌍 (생성됨, 커밋 제외)
  PUSH_ADMIN_TOKEN     구독자 목록 조회용 토큰 (Netlify 환경변수와 동일하게)
  NB_SITE_URL          사이트 주소 (기본값 config.SITE_URL)
"""
from __future__ import annotations
import json
import os
import urllib.request

import config
from schema import Issue

_VAPID_PATH = os.path.join(config.DATA_DIR, "vapid.json")


def _vapid() -> dict | None:
    if not os.path.exists(_VAPID_PATH):
        return None
    return json.load(open(_VAPID_PATH, encoding="utf-8"))


def _fetch_subscriptions() -> list[dict]:
    token = os.getenv("PUSH_ADMIN_TOKEN")
    if not token:
        print("   🔔 PUSH_ADMIN_TOKEN 없음 → 푸시 건너뜀")
        return []
    url = config.SITE_URL.rstrip("/") + "/api/subscribers"
    req = urllib.request.Request(url, headers={
        "x-admin-token": token,
        "User-Agent": "nachimban/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        return data.get("subscriptions", [])
    except Exception as e:  # noqa: BLE001
        print(f"   🔔 구독자 목록 조회 실패: {e}")
        return []


def send(issue: Issue) -> int:
    """오늘 호 알림을 모든 구독 기기에 발송. 보낸 수를 반환."""
    keys = _vapid()
    if not keys:
        print("   🔔 data/vapid.json 없음 → 푸시 건너뜀")
        return 0
    subs = _fetch_subscriptions()
    if not subs:
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("   🔔 pywebpush 미설치 → `pip install pywebpush`")
        return 0

    # 알림을 누르면 바로 오늘의 브리핑으로 이동
    top = next((it.head for it in issue.published if it.hot), None)
    if not top and issue.published:
        top = issue.published[0].head
    payload = json.dumps({
        "title": f"나침반 · 제{issue.number}호",
        "body": top or "오늘의 브리핑이 도착했습니다.",
        "url": config.SITE_URL,
    }, ensure_ascii=False)

    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=keys["private"],
                vapid_claims={"sub": "mailto:" + os.getenv("NB_CONTACT", "zookzlue@gmail.com")},
                timeout=20,
            )
            sent += 1
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                print("   🔔 만료된 구독 1건 (기기에서 알림 해제됨)")
            else:
                print(f"   🔔 발송 실패: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"   🔔 발송 실패: {type(e).__name__}: {e}")
    print(f"   🔔 푸시 발송 {sent}/{len(subs)}건")
    return sent
