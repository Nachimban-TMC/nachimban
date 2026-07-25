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


def _headline_rows(issue: Issue, limit: int = 5) -> str:
    """중요 뉴스(hot) 우선으로 헤드라인만 간결하게. 본문은 사이트에서."""
    ordered = sorted(issue.published, key=lambda it: (not it.hot,))
    rows = []
    for it in ordered[:limit]:
        kr, _, _ = config.CATEGORIES.get(it.category, (it.category, "", ""))
        star = ' <span style="color:#e0795f;">●</span>' if it.hot else ""
        rows.append(f"""
      <tr><td style="padding:15px 0;border-bottom:1px solid #262628;">
        <div style="font:700 10px/1 -apple-system,Arial;letter-spacing:1.5px;color:#77776f;text-transform:uppercase;">{_RG.get(it.region, it.region)} &nbsp;·&nbsp; {kr}{star}</div>
        <div style="font:700 16px/1.45 -apple-system,Arial;color:#f3f2ef;margin-top:7px;">{it.head}</div>
      </td></tr>""")
    return "".join(rows)


def build_email_html(issue: Issue) -> str:
    """간결한 다이제스트: 헤드라인 몇 개 + 사이트로 보내는 큰 버튼."""
    date_dot = issue.date.replace("-", ". ")
    total = len(issue.published)
    counts = " · ".join(
        f"{_RG[r].split()[-1]} {n}" for r, n in issue.region_counts().items() if r in _RG
    )
    rows = _headline_rows(issue)
    more = total - min(total, 5)
    more_line = f"외 {more}건이 더 있습니다" if more > 0 else "전체 브리핑을 확인하세요"
    url = config.SITE_URL

    # 사이트와 같은 흑백 매거진 톤 (잉크블랙 배경)
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="color-scheme" content="dark"></head>
    <body style="margin:0;padding:0;background:#0b0b0c;">
    <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#0b0b0c;">
      <tr><td align="center" style="padding:30px 12px;">
        <table width="520" cellpadding="0" cellspacing="0" role="presentation" style="background:#111112;border:1px solid #262628;max-width:520px;width:100%;">

          <!-- 마스트헤드 (사이트와 동일한 톤) -->
          <tr><td style="padding:32px 26px 18px;border-bottom:2px solid #f3f2ef;">
            <div style="font:800 38px/1 -apple-system,'Helvetica Neue',Arial;letter-spacing:8px;color:#f3f2ef;">나침반</div>
            <div style="font:italic 400 12px/1 Georgia,serif;color:#77776f;margin-top:10px;letter-spacing:.5px;">Nachimban — The Morning Compass</div>
          </td></tr>

          <!-- 발행 정보 -->
          <tr><td style="padding:18px 26px 2px;">
            <div style="font:700 10px/1 -apple-system,Arial;letter-spacing:1.6px;color:#77776f;text-transform:uppercase;">
              제 {issue.number} 호 &nbsp;·&nbsp; {date_dot} &nbsp;·&nbsp; 오늘 {total}건
            </div>
            <div style="font:400 14px/1.65 -apple-system,Arial;color:#b4b3af;margin-top:12px;">
              오늘 아침, 해외에 사는 우리에게 꼭 필요한 소식입니다.
            </div>
          </td></tr>

          <!-- 헤드라인만 -->
          <tr><td style="padding:12px 26px 4px;">
            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">{rows}</table>
            <div style="font:italic 400 12.5px/1.5 Georgia,serif;color:#77776f;padding-top:15px;">{more_line}</div>
          </td></tr>

          <!-- 사이트로 보내는 버튼 (흰 버튼 = 사이트 다크모드와 동일) -->
          <tr><td style="padding:10px 26px 32px;">
            <table cellpadding="0" cellspacing="0" role="presentation" width="100%">
              <tr><td align="center" bgcolor="#f3f2ef" style="background:#f3f2ef;">
                <a href="{url}" style="display:block;padding:17px 20px;font:800 12px/1 -apple-system,Arial;letter-spacing:1.8px;color:#0b0b0c;text-decoration:none;text-transform:uppercase;">
                  오늘의 브리핑 전체 보기 &nbsp;&#8599;
                </a>
              </td></tr>
            </table>
            <div style="font:400 11.5px/1.6 -apple-system,Arial;color:#77776f;text-align:center;padding-top:13px;">
              각 소식마다 <b style="color:#b4b3af;">쉬운 해석</b>과 원문 링크가 함께 있습니다.
            </div>
          </td></tr>

          <!-- 푸터 -->
          <tr><td style="padding:17px 26px 22px;border-top:1px solid #262628;background:#0e0e0f;">
            <div style="font:400 11px/1.65 -apple-system,Arial;color:#6a6a63;">
              {counts}<br>
              나침반 · 재외한인을 위한 매일 아침 뉴스<br>
              <a href="{url}" style="color:#8a8a82;text-decoration:none;">{url.replace('https://', '')}</a> &nbsp;·&nbsp; 수신거부는 회신 주세요.
            </div>
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
    print(f"   ✉️  발신자: {frm}")
    for to in subs:
        payload = json.dumps({"from": frm, "to": [to], "subject": subject, "html": html}).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails", data=payload, method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                # User-Agent 를 명시하지 않으면 Python 기본값이 봇으로 차단됨
                # (Cloudflare error 1010 → HTTP 403)
                "User-Agent": "nachimban/1.0 (+https://nachimban.netlify.app)",
                "Accept": "application/json",
            })
        try:
            urllib.request.urlopen(req, timeout=20)
            sent += 1
            print(f"   ✉️  발송 성공 → {to}")
        except urllib.error.HTTPError as e:
            # Resend 가 알려주는 실제 실패 사유를 그대로 보여준다
            try:
                detail = e.read().decode("utf-8", "replace")[:400]
            except Exception:  # noqa: BLE001
                detail = "(응답 본문 없음)"
            print(f"   ✉️  발송 실패 {to}")
            print(f"       HTTP {e.code} {e.reason}")
            print(f"       사유: {detail}")
            _hint(e.code, detail)
        except Exception as e:  # noqa: BLE001
            print(f"   ✉️  발송 실패 {to}: {type(e).__name__}: {e}")
    print(f"   ✉️  발송 완료 {sent}/{len(subs)}건")
    return sent


def _hint(code: int, detail: str) -> None:
    """자주 나오는 실패 원인에 대한 한글 안내."""
    d = detail.lower()
    if "1010" in d or "cloudflare" in d:
        print("       👉 Cloudflare 봇 차단입니다. User-Agent 헤더가 빠졌을 때 발생합니다.")
        print("          pipeline/notify.py 가 최신인지 확인하세요(이미 수정됨).")
    elif code in (401, 403) and "api" in d and "key" in d:
        print("       👉 API 키가 잘못됐거나 권한이 없습니다. Resend에서 키를 다시 확인하세요.")
    elif "testing emails" in d or "own email" in d or "verify a domain" in d:
        print("       👉 Resend 테스트 모드입니다. onboarding@resend.dev 로는")
        print("          '가입한 계정의 이메일 주소'로만 보낼 수 있습니다.")
        print("          data/subscribers.txt 의 주소가 Resend 가입 이메일과 같은지 확인하세요.")
    elif "domain" in d and ("not verified" in d or "verify" in d):
        print("       👉 발신 도메인이 인증되지 않았습니다. NB_FROM 을")
        print("          '나침반 <onboarding@resend.dev>' 로 두거나, 도메인을 인증하세요.")
    elif code == 422:
        print("       👉 요청 형식 문제입니다. NB_FROM 형식이 '이름 <메일주소>' 인지 확인하세요.")
