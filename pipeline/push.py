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
from pipeline import env
from schema import Issue

_VAPID_PATH = os.path.join(config.DATA_DIR, "vapid.json")


def _vapid() -> dict | None:
    if not os.path.exists(_VAPID_PATH):
        return None
    return json.load(open(_VAPID_PATH, encoding="utf-8"))


def _fetch_subscriptions() -> list[dict] | None:
    """구독 목록. 토큰이 없으면 None(=푸시 시도 자체를 건너뜀)."""
    token = os.getenv("PUSH_ADMIN_TOKEN")
    if not token:
        print("   🔔 PUSH_ADMIN_TOKEN 없음 → 푸시 건너뜀")
        print('       👉 발송하려면: PUSH_ADMIN_TOKEN="정한값" python3 -m pipeline.run --send-latest')
        return None
    url = config.SITE_URL.rstrip("/") + "/api/subscribers"
    req = urllib.request.Request(url, headers={
        "x-admin-token": token,
        "User-Agent": "nachimban/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        subs = data.get("subscriptions", [])
        print(f"   🔔 알림 켠 기기: {len(subs)}대")
        return subs
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:200]
        except Exception:  # noqa: BLE001
            pass
        print(f"   🔔 구독자 목록 조회 실패 — HTTP {e.code}")
        if e.code == 401:
            print("       👉 PUSH_ADMIN_TOKEN 이 Netlify 환경변수와 다릅니다. 값을 확인하세요.")
        elif e.code == 404:
            print("       👉 /api/subscribers 함수가 아직 배포되지 않았습니다.")
            print("          Netlify → Deploys → Trigger deploy 로 재배포하세요.")
        elif body:
            print(f"       사유: {body}")
        return []
    except Exception as e:  # noqa: BLE001
        print(f"   🔔 구독자 목록 조회 실패: {type(e).__name__}: {e}")
        return []


def send(issue: Issue) -> int:
    """오늘 호 알림을 모든 구독 기기에 발송. 보낸 수를 반환."""
    env.load()
    keys = _vapid()
    if not keys:
        print("   🔔 data/vapid.json 없음 → 푸시 건너뜀")
        return 0
    subs = _fetch_subscriptions()
    if subs is None:          # 토큰 없음 — 위에서 이미 안내함
        return 0
    if not subs:
        print("   🔔 아직 알림을 켠 기기가 없습니다.")
        print("       👉 휴대폰에서 사이트 → SUBSCRIBE → '알림 받기' 를 눌러주세요.")
        print("          (아이폰은 먼저 '홈 화면에 추가' 후 그 앱에서 열어야 합니다)")
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
