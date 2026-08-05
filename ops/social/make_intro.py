#!/usr/bin/env python3
"""계정 소개(고정 게시물)용 인트로 캐러셀 5장 → 1080x1350 PNG.
새 방문자에게 '나침반이 뭐 하는 곳인지'를 한눈에. 브랜드 톤(신문식 흑백)."""
import os, glob, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "intro")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

COMPASS = """<svg width="{s}" height="{s}" viewBox="0 0 100 100">
 <circle cx="50" cy="50" r="46" fill="none" stroke="{c}" stroke-width="1.6"/>
 <g fill="{c}"><rect x="49.2" y="6" width="1.6" height="8"/><rect x="49.2" y="86" width="1.6" height="8"/>
 <rect x="6" y="49.2" width="8" height="1.6"/><rect x="86" y="49.2" width="8" height="1.6"/></g>
 <polygon points="50,16 41,52 59,52" fill="{n}"/><polygon points="50,84 41,52 59,52" fill="{s2}"/>
 <circle cx="50" cy="52" r="3.4" fill="{c}"/></svg>"""

CSS = """
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
:root{--paper:#FFFFFF;--panel:#F4F3F1;--ink:#0A0A0A;--soft:#4B4B4B;--faint:#8C8C8C;
 --line:#E2E1DD;--band:#0A0A0A;--bandink:#FFFFFF;
 --disp:"Helvetica Neue","Pretendard","Apple SD Gothic Neo",Arial,sans-serif;
 --kr:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
 --serif:Georgia,"Times New Roman",serif}
body{background:#fff;font-family:var(--kr)}
.slide{width:1080px;height:1350px;background:var(--paper);color:var(--ink);
 position:relative;overflow:hidden;display:flex;flex-direction:column;padding:96px 88px}
.kick{font-family:var(--disp);font-weight:800;font-size:24px;letter-spacing:.26em;
 text-transform:uppercase;color:var(--faint)}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center}
.big{font-family:var(--disp);font-weight:800;line-height:1.14;letter-spacing:-.01em;font-size:92px}
.body{font-size:42px;line-height:1.55;color:var(--soft);font-weight:500;margin-top:38px}
.list{margin-top:20px}
.row{display:flex;align-items:baseline;gap:24px;padding:24px 0;border-bottom:1px solid var(--line);font-size:46px;font-weight:700}
.row .num{font-family:var(--serif);font-style:italic;font-size:34px;color:var(--faint);min-width:52px}
.row small{display:block;font-size:28px;font-weight:500;color:var(--faint);margin-top:6px}
.tagline{font-size:34px;color:var(--soft);line-height:1.5}
.foot{display:flex;justify-content:space-between;align-items:center;border-top:2px solid var(--ink);padding-top:26px}
.foot .bn{font-family:var(--disp);font-weight:800;font-size:26px}
.foot .u{font-family:var(--serif);font-size:24px;color:var(--faint)}
.pgnum{position:absolute;top:96px;right:88px;font-family:var(--serif);font-style:italic;font-size:26px;color:var(--faint)}
/* 표지/CTA (검정) */
.dark{background:var(--band);color:var(--bandink)}
.center{align-items:center;text-align:center;justify-content:center}
.cover .kr{font-family:var(--disp);font-weight:800;font-size:150px;letter-spacing:-.01em;margin-top:44px}
.cover .rom{font-family:var(--serif);font-style:italic;font-size:38px;color:#B9B9B4;margin-top:20px}
.cover .sub{font-size:34px;color:#DcDcD8;margin-top:40px;letter-spacing:.02em}
.cover .swipe{position:absolute;bottom:70px;right:88px;font-size:30px;color:#8C8C8C}
.cta .s{font-size:38px;color:#B9B9B4}
.cta .big{font-family:var(--disp);font-weight:800;font-size:104px;line-height:1.08;margin:26px 0 40px;color:#fff}
.cta .u{font-family:var(--serif);font-style:italic;font-size:40px}
.cta .hint{margin-top:56px;border:2px solid #4A4A48;border-radius:999px;padding:22px 40px;font-size:30px;color:#DcDcD8}
.cta .h{margin-top:34px;font-family:var(--disp);font-weight:800;font-size:30px;letter-spacing:.04em;color:#fff}
"""

def cover():
    return f"""<section class="slide dark center cover">
      {COMPASS.format(s=300, c="#fff", n="#fff", s2="#6E6E6E")}
      <div class="kr">나침반</div>
      <div class="rom">Nachimban — The Morning Compass</div>
      <div class="sub">재외한인을 위한 아침 뉴스 브리핑</div>
      <div class="swipe">넘겨보기 →</div>
    </section>"""

def slide_why():
    return f"""<section class="slide"><div class="pgnum">01 / 05</div>
      <div class="kick">왜 나침반</div>
      <div class="mid">
        <div class="big">해외에 살면<br>뉴스 하나<br>놓치기 쉽습니다</div>
        <div class="body">비자 규정이 바뀌고, 복지 신청이 마감되고,<br>세금 기한이 지나가도 — 알기 어렵죠.</div>
      </div>
      <div class="foot"><span class="bn">나침반</span><span class="u">The Morning Compass</span></div>
    </section>"""

def slide_what():
    rows = [("01","비자 · 체류","여권·비자·거주 규정 변화"),
            ("02","복지 · 행정","수당·보험·행정 절차 안내"),
            ("03","세금 · 연금","납부 기한·제도 변경"),
            ("04","안전 · 긴급","여행경보·재난·공항 공지")]
    body = "".join(
        f'<div class="row"><span class="num">{n}</span><span>{t}<small>{d}</small></span></div>'
        for n,t,d in rows)
    return f"""<section class="slide"><div class="pgnum">02 / 05</div>
      <div class="kick">무엇을</div>
      <div class="mid">
        <div class="big" style="font-size:78px">놓치면 안 되는<br>것만, 매일</div>
        <div class="list">{body}</div>
      </div>
      <div class="foot"><span class="bn">독일 · 한국 · EU · 미국 · 세계</span><span class="u">5개 지역</span></div>
    </section>"""

def slide_how():
    rows = [("믿을 수 있게","출처를 교차 확인하는 팩트체크"),
            ("쉽게","어려운 말은 '쉬운 해석'으로 풀이"),
            ("매일 아침","오전 7시 · 완전 무료")]
    body = "".join(
        f'<div class="row"><span>{t}<small>{d}</small></span></div>' for t,d in rows)
    return f"""<section class="slide"><div class="pgnum">03 / 05</div>
      <div class="kick">어떻게</div>
      <div class="mid">
        <div class="big" style="font-size:78px">정확하고,<br>읽기 쉽게</div>
        <div class="list">{body}</div>
      </div>
      <div class="foot"><span class="bn">나침반</span><span class="u">매일 아침 7시</span></div>
    </section>"""

def cta():
    return f"""<section class="slide dark center cta">
      <div class="s">매일 아침, 놓치기 쉬운 소식을</div>
      <div class="big">앱으로<br>받아보세요</div>
      <div class="u">nachimban.pages.dev</div>
      <div class="hint">공유 → 홈 화면에 추가 · 무료</div>
      <div class="h">@nachimbantmc</div>
    </section>"""

def doc(inner):
    return f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{inner}</body></html>'

def render(name, inner):
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, name + ".html")
        open(hp, "w", encoding="utf-8").write(doc(inner))
        png = os.path.join(OUT, name + ".png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--no-first-run", "--no-default-browser-check", "--force-device-scale-factor=1",
                        "--window-size=1080,1350", f"--screenshot={png}", f"file://{hp}"],
                       check=False, capture_output=True, text=True, timeout=60)
        ok = os.path.exists(png) and os.path.getsize(png) > 2000
        print(("OK  " if ok else "FAIL ") + os.path.basename(png))

if __name__ == "__main__":
    for old in glob.glob(os.path.join(OUT, "*.png")):
        os.remove(old)
    for i, fn in enumerate([cover, slide_why, slide_what, slide_how, cta], start=1):
        render(f"intro-{i:02d}", fn())
