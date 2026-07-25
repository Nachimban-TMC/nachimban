"""오전 7시 이메일 발송 — Resend API (표준 라이브러리만 사용).

- 발행된 issue 를 이메일용 HTML 다이제스트로 만들고
- data/subscribers.txt 의 구독자에게 Resend 로 발송한다.

필요한 환경변수:
  RESEND_API_KEY   Resend 대시보드에서 발급 (필수)
  NB_FROM          발신자, 예: "나침반 <brief@your-domain.com>" (Resend 인증 도메인)
구독자: data/subscribers.txt (한 줄에 이메일 하나). 없으면 발송 건너뜀.
"""
from __future__ import annotations
import json
import os
import urllib.request

import config
from schema import Issue, NewsItem

_RG = {"de": "🇩🇪 독일", "kr": "🇰🇷 한국", "eu": "🇪🇺 EU", "us": "🇺🇸 미국", "fr": "🇫🇷 프랑스"}


def _item_html(it: NewsItem) -> str:
    kr, en, _ = config.CATEGORIES.get(it.category, (it.category, "", ""))
    return f"""
      <tr><td style="padding:16px 0;border-bottom:1px solid #eee;">
        <div style="font:700 11px/1 Arial;letter-spacing:1px;color:#888;text-transform:uppercase;">{kr} · {en}</div>
        <div style="font:800 17px/1.35 Arial;color:#111;margin:6px 0 6px;">{it.head}</div>
        <div style="font:400 13px/1.6 Arial;color:#555;">{it.desc}</div>
        <div style="font:400 13px/1.55 Arial;color:#111;border-left:3px solid #111;padding:4px 0 4px 10px;margin:8px 0;">
          <b>쉬운 해석</b> — {it.interp}</div>
        <a href="{it.url}" style="font:700 12px Arial;color:#111;">원문 읽기 →</a>
      </td></tr>"""


def build_email_html(issue: Issue) -> str:
    date_dot = issue.date.replace("-", ". ")
    body = []
    for r in config.REGION_ORDER:
        items = [it for it in issue.published if it.region == r]
        if not items:
            continue
        body.append(f'<tr><td style="padding:22px 0 4px;font:800 14px Arial;color:#111;">{_RG[r]}</td></tr>')
        body.extend(_item_html(it) for it in items)
    rows = "".join(body)
    return f"""<!doctype html><html><body style="margin:0;background:#f6f6f4;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f6f4;">
      <tr><td align="center" style="padding:28px 12px;">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #e2e1dd;">
          <tr><td style="padding:26px 26px 8px;border-bottom:2px solid #111;">
            <div style="font:800 30px/1 Arial;letter-spacing:6px;color:#111;">나침반</div>
            <div style="font:400 12px Arial;color:#888;margin-top:6px;">재외한인 아침 브리핑 · 제 {issue.number} 호 · {date_dot} · 오전 7:00</div>
          </td></tr>
          <tr><td style="padding:4px 26px 20px;">
            <table width="100%" cellpadding="0" cellspacing="0">{rows}</table>
          </td></tr>
          <tr><td style="padding:18px 26px;border-top:1px solid #eee;font:400 11px Arial;color:#999;">
            나침반 · 재외한인을 위한 매일 아침 뉴스 · 수신거부는 회신 주세요.
          </td></tr>
        </table>
      </td></tr>
    </table></body></html>"""


def _subscribers() -> list[str]:
    path = os.path.join(config.DATA_DIR, "subscribers.txt")
    if not os.path.exists(path):
        return []
    return [ln.strip() for ln in open(path, encoding="utf-8") if ln.strip() and not ln.startswith("#")]


def send(issue: Issue) -> int:
    """구독자에게 발송. 발송 건수 반환. 키/구독자 없으면 0(건너뜀)."""
    key = os.getenv("RESEND_API_KEY")
    subs = _subscribers()
    if not key:
        print("   ✉️  RESEND_API_KEY 없음 → 발송 건너뜀(코드는 준비됨)")
        return 0
    if not subs:
        print("   ✉️  data/subscribers.txt 비어있음 → 발송 건너뜀")
        return 0
    frm = os.getenv("NB_FROM", "나침반 <onboarding@resend.dev>")
    subject = f"[나침반] 제{issue.number}호 · {issue.date} 아침 브리핑"
    html = build_email_html(issue)
    sent = 0
    for to in subs:
        payload = json.dumps({"from": frm, "to": [to], "subject": subject, "html": html}).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails", data=payload, method="POST",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=20)
            sent += 1
        except Exception as e:  # noqa: BLE001
            print(f"   ✉️  발송 실패 {to}: {e}")
    print(f"   ✉️  발송 완료 {sent}/{len(subs)}건")
    return sent
