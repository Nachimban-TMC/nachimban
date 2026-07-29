"""발행 사고 알림 — 관리자(운영자)에게만 간다.

두 겹으로 막는다.
  1) 파이프라인 안에서 터진 경우  → run.py 가 이 모듈로 알린다
  2) 파이프라인이 아예 안 돈 경우 → healthcheck.py 가 밖에서 확인해 알린다

2)가 핵심이다. 스크립트가 실행조차 안 되면 스크립트 안의 알림도 울리지 않는다.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request

import config
from pipeline import env


def _admin_email() -> str:
    return os.getenv("NB_ADMIN_EMAIL", "zookzlue@gmail.com")


def _mail(subject: str, body_html: str) -> bool:
    key = os.getenv("RESEND_API_KEY")
    if not key:
        print("   🚨 RESEND_API_KEY 없음 → 관리자 메일 건너뜀")
        return False
    frm = os.getenv("NB_FROM", "나침반 <onboarding@resend.dev>")
    payload = json.dumps({
        "from": frm, "to": [_admin_email()],
        "subject": subject, "html": body_html,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "nachimban/1.0",     # 없으면 봇으로 차단된다
            "Accept": "application/json",
        })
    try:
        urllib.request.urlopen(req, timeout=20)
        print(f"   🚨 관리자 메일 발송 → {_admin_email()}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"   🚨 관리자 메일 실패: {type(e).__name__}: {e}")
        return False


def _push(title: str, body: str) -> int:
    """관리자 기기로만 푸시.

    사고 알림은 운영자가 볼 것이지 구독자가 볼 것이 아니다. 구독자 폰에
    '발행 실패'가 뜨면 서비스 신뢰만 깎인다. 그래서 전체 구독자에게 보내지
    않고, .env 의 NB_ADMIN_PUSH 에 적힌 기기에만 보낸다.

    NB_ADMIN_PUSH 에는 관리자 기기 엔드포인트의 '일부 문자열'을 쉼표로
    구분해 넣는다(전체 URL을 적을 필요 없음). 비어 있으면 푸시를 보내지
    않고 메일로만 알린다 — 잘못 보내느니 안 보내는 쪽이 낫다.
    """
    marks = [m.strip() for m in os.getenv("NB_ADMIN_PUSH", "").split(",") if m.strip()]
    if not marks:
        print("   🚨 NB_ADMIN_PUSH 미설정 → 푸시 건너뜀(메일로만 알림)")
        return 0
    try:
        from pipeline import push as _p
        keys = _p._vapid()
        subs = _p._fetch_subscriptions()
        if not keys or not subs:
            return 0
        from pywebpush import webpush
    except Exception:  # noqa: BLE001
        return 0

    admin = [s for s in subs
             if any(m in (s.get("endpoint") or "") for m in marks)]
    if not admin:
        print("   🚨 관리자 기기를 찾지 못함 → 푸시 건너뜀(메일로만 알림)")
        return 0

    data = json.dumps({"title": title, "body": body,
                       "url": config.SITE_URL}, ensure_ascii=False)
    sent = 0
    for sub in admin:
        try:
            webpush(subscription_info=sub, data=data,
                    vapid_private_key=keys["private"],
                    vapid_claims={"sub": "mailto:" + _admin_email()})
            sent += 1
        except Exception:  # noqa: BLE001
            pass
    print(f"   🚨 관리자 푸시 {sent}/{len(admin)}건 (전체 구독자 {len(subs)}명 중)")
    return sent


def failure(stage: str, err: BaseException, *, number: int | None = None,
            date: str = "", push_too: bool = False) -> None:
    """발행이 실패했을 때. 조용히 지나가지 않게 하는 것이 목적이다."""
    env.load()
    what = f"제{number}호 · {date}" if number else (date or "오늘자")
    subject = f"🚨 [나침반] 발행 실패 — {stage}"
    body = f"""
    <div style="font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;
                max-width:620px;line-height:1.7;color:#0A0A0A">
      <p style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;
                color:#8C8C8C;margin:0 0 6px">Nachimban · System Alert</p>
      <h2 style="margin:0 0 14px;font-size:22px">발행이 실패했습니다</h2>
      <table style="border-collapse:collapse;font-size:14px">
        <tr><td style="padding:4px 14px 4px 0;color:#8C8C8C">대상</td><td><b>{what}</b></td></tr>
        <tr><td style="padding:4px 14px 4px 0;color:#8C8C8C">단계</td><td><b>{stage}</b></td></tr>
        <tr><td style="padding:4px 14px 4px 0;color:#8C8C8C">오류</td>
            <td><b>{type(err).__name__}</b></td></tr>
      </table>
      <pre style="background:#F4F3F1;padding:14px;border-radius:6px;font-size:12px;
                  white-space:pre-wrap;word-break:break-all">{str(err)[:1200]}</pre>
      <p style="font-size:13px;color:#4B4B4B">
        오늘 아침 브리핑은 <b>나가지 않았습니다.</b> 구독자에게는 알림도 가지 않습니다.
      </p>
      <p style="font-size:13px">
        <a href="{config.SITE_URL}" style="color:#0A0A0A">사이트 확인 →</a>
      </p>
    </div>"""
    _mail(subject, body)
    if push_too:
        _push("🚨 나침반 발행 실패", f"{stage} 단계에서 멈췄습니다")


def stale(latest_date: str, expected: str) -> None:
    """파이프라인이 아예 돌지 않아 사이트가 낡았을 때."""
    env.load()
    subject = f"🚨 [나침반] {expected} 브리핑이 올라오지 않았습니다"
    body = f"""
    <div style="font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;
                max-width:620px;line-height:1.7;color:#0A0A0A">
      <p style="font-size:11px;letter-spacing:.16em;text-transform:uppercase;
                color:#8C8C8C;margin:0 0 6px">Nachimban · System Alert</p>
      <h2 style="margin:0 0 14px;font-size:22px">오늘 브리핑이 없습니다</h2>
      <table style="border-collapse:collapse;font-size:14px">
        <tr><td style="padding:4px 14px 4px 0;color:#8C8C8C">기대한 날짜</td><td><b>{expected}</b></td></tr>
        <tr><td style="padding:4px 14px 4px 0;color:#8C8C8C">사이트 최신</td><td><b>{latest_date or '알 수 없음'}</b></td></tr>
      </table>
      <p style="font-size:13px;color:#4B4B4B">
        예약 작업이 실행되지 않았거나, 실행 도중 멈췄을 수 있습니다.
      </p>
      <p style="font-size:13px">
        <a href="{config.SITE_URL}" style="color:#0A0A0A">사이트 확인 →</a>
      </p>
    </div>"""
    _mail(subject, body)
    _push("🚨 나침반 오늘 브리핑 없음", f"{expected} 발행이 확인되지 않습니다")
