#!/usr/bin/env python3
"""오늘자 호에서 인스타/스레드용 자료를 만든다.
- site/social/img/slide-NN.jpg : 1080x1350 캐러셀 이미지 (Chrome 렌더 → JPG)
- site/social/index.html       : 폰에서 열어 이미지 저장·캡션 복사하는 뷰어
브랜드 톤(신문식 흑백 에디토리얼)을 사이트와 맞춘다. 유료 생성 안 씀.

단독 실행:  python3 ops/social/make_social.py
자동 발행에서: import 해서 build_all() 호출 (실패해도 예외를 밖으로 안 던짐).
"""
import json, os, glob, html, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
SOCIAL = os.path.join(SITE, "social")
IMG = os.path.join(SOCIAL, "img")

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

RG = {"de": ("독일", "GERMANY"), "kr": ("한국", "KOREA"), "eu": ("EU", "EUROPE"),
      "us": ("미국", "USA"), "wo": ("세계", "WORLD")}
RGE = {"de": "🇩🇪", "kr": "🇰🇷", "eu": "🇪🇺", "us": "🇺🇸", "wo": "🌍"}


def latest_issue():
    files = sorted(glob.glob(os.path.join(DATA, "issue-*.json")))
    if not files:
        raise FileNotFoundError("발행된 호가 없습니다")
    return json.load(open(files[-1], encoding="utf-8"))


def pick(items, n=7):
    order = ["de", "kr", "eu", "us", "wo"]
    by = {r: [it for it in items if it["region"] == r] for r in order}
    out, i = [], 0
    while len(out) < min(n, len(items)) and i < 200:
        r = order[i % len(order)]
        if by[r]:
            out.append(by[r].pop(0))
        i += 1
    return out


def fmt_date(d):
    return d.replace("-", ". ")


def esc(s):
    return html.escape(s, quote=False)


CSS = """
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased;}
:root{--paper:#FFFFFF;--panel:#F4F3F1;--ink:#0A0A0A;--soft:#4B4B4B;--faint:#8C8C8C;
 --line:#E2E1DD;--band:#0A0A0A;--bandink:#FFFFFF;
 --disp:"Helvetica Neue","Pretendard","Apple SD Gothic Neo",Arial,sans-serif;
 --kr:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
 --serif:Georgia,"Times New Roman",serif;}
body{background:#fff;font-family:var(--kr);}
.slide{width:1080px;height:1350px;background:var(--paper);color:var(--ink);
 position:relative;overflow:hidden;display:flex;flex-direction:column;
 padding:86px 84px;margin:0;}
.top{display:flex;justify-content:space-between;align-items:flex-start;}
.pill{display:inline-flex;gap:12px;align-items:baseline;background:var(--band);
 color:var(--bandink);padding:14px 26px;border-radius:999px;}
.pill .ko{font-family:var(--disp);font-weight:800;font-size:30px;}
.pill .en{font-family:var(--disp);font-weight:700;font-size:18px;letter-spacing:.22em;opacity:.7;}
.pg{font-family:var(--serif);font-style:italic;font-size:26px;color:var(--faint);}
.mid{flex:1;display:flex;flex-direction:column;justify-content:center;}
.head{font-family:var(--disp);font-weight:800;line-height:1.12;letter-spacing:-.01em;
 font-size:82px;margin:0 0 40px;}
.desc{font-size:40px;line-height:1.55;color:var(--soft);font-weight:500;}
.interp{margin-top:44px;background:var(--panel);border-left:8px solid var(--ink);
 padding:34px 36px;border-radius:4px;}
.interp .lb{font-family:var(--disp);font-weight:800;font-size:20px;letter-spacing:.18em;
 text-transform:uppercase;color:var(--faint);margin-bottom:14px;}
.interp p{font-size:36px;line-height:1.5;color:var(--ink);font-weight:500;}
.interp b{font-weight:800;}
.foot{display:flex;justify-content:space-between;align-items:center;
 border-top:2px solid var(--ink);padding-top:26px;}
.foot .bn{font-family:var(--disp);font-weight:800;font-size:26px;letter-spacing:.02em;}
.foot .u{font-family:var(--serif);font-size:24px;color:var(--faint);}
.cover{align-items:center;text-align:center;justify-content:center;}
.cover .kr{font-family:var(--disp);font-weight:800;font-size:300px;line-height:.9;letter-spacing:-.02em;}
.cover .rom{font-family:var(--serif);font-style:italic;font-size:40px;color:var(--soft);margin-top:26px;}
.cover .rule{width:120px;height:3px;background:var(--ink);margin:52px 0;}
.cover .meta{font-family:var(--disp);font-weight:700;font-size:34px;letter-spacing:.04em;}
.cover .lead{font-size:34px;color:var(--soft);margin-top:20px;line-height:1.5;}
.cover .band{position:absolute;left:0;right:0;bottom:0;background:var(--band);color:var(--bandink);
 font-family:var(--disp);font-weight:800;font-size:28px;letter-spacing:.06em;padding:34px;text-align:center;}
.outro{background:var(--band);color:var(--bandink);align-items:center;text-align:center;justify-content:center;}
.outro .s{font-size:38px;color:#B9B9B4;line-height:1.5;}
.outro .big{font-family:var(--disp);font-weight:800;font-size:104px;line-height:1.08;margin:30px 0 44px;}
.outro .u{font-family:var(--serif);font-style:italic;font-size:40px;}
.outro .hint{margin-top:60px;border:2px solid #4A4A48;border-radius:999px;padding:22px 40px;font-size:30px;color:#DcDcD8;}
"""


def cover_slide(iss):
    regs = " · ".join(RG[r][0] for r in ["de", "kr", "eu", "us", "wo"])
    n = len(iss["published"])
    return f"""<section class="slide cover">
  <div class="kr">나침반</div>
  <div class="rom">Nachimban — The Morning Compass</div>
  <div class="rule"></div>
  <div class="meta">{fmt_date(iss['date'])} · 제{iss['number']}호</div>
  <div class="lead">해외에 살면 놓치기 쉬운<br>오늘의 뉴스 {n}건</div>
  <div class="band">{regs}</div>
</section>"""


def news_slide(it, idx, total, date):
    ko, en = RG.get(it["region"], (it["region"], ""))
    interp = it.get("interp", "").strip()
    interp_html = f'<div class="interp"><div class="lb">쉬운 해석</div><p>{interp}</p></div>' if interp else ""
    return f"""<section class="slide">
  <div class="top">
    <span class="pill"><span class="ko">{esc(ko)}</span><span class="en">{en}</span></span>
    <span class="pg">{idx:02d} / {total:02d}</span>
  </div>
  <div class="mid">
    <h2 class="head">{esc(it['head'])}</h2>
    <p class="desc">{esc(it['desc'])}</p>
    {interp_html}
  </div>
  <div class="foot"><span class="bn">나침반</span><span class="u">{fmt_date(date)}</span></div>
</section>"""


def outro_slide():
    return """<section class="slide outro">
  <div class="s">매일 아침 7시, 놓치기 쉬운 소식을</div>
  <div class="big">앱으로<br>받아보세요</div>
  <div class="u">nachimban.pages.dev</div>
  <div class="hint">공유 → 홈 화면에 추가</div>
</section>"""


def _slide_doc(inner):
    return (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>{inner}</body></html>')


def render_images(slides):
    """각 슬라이드를 Chrome 헤드리스로 1080x1350 렌더 후 JPG 로 저장. 실패 개수 반환.
    Chrome 은 PNG 만 출력하므로 임시 PNG → sips(맥 기본)로 JPG 변환한다.
    인스타/스레드는 JPG 가 표준이라 폰에서 바로 업로드된다(IG 게시 API 도 JPEG 요구)."""
    if not os.path.exists(CHROME):
        raise RuntimeError(f"Chrome 없음: {CHROME}")
    os.makedirs(IMG, exist_ok=True)
    for old in glob.glob(os.path.join(IMG, "slide-*.png")) + glob.glob(os.path.join(IMG, "slide-*.jpg")):
        os.remove(old)
    fail = 0
    with tempfile.TemporaryDirectory() as td:
        for n, s in enumerate(slides, start=1):
            hp = os.path.join(td, f"s{n:02d}.html")
            open(hp, "w", encoding="utf-8").write(_slide_doc(s))
            png = os.path.join(td, f"s{n:02d}.png")   # 임시 PNG
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            "--no-first-run", "--no-default-browser-check",
                            "--force-device-scale-factor=1", "--window-size=1080,1350",
                            "--default-background-color=FFFFFFFF",
                            f"--screenshot={png}", f"file://{hp}"],
                           check=False, capture_output=True, text=True, timeout=60)
            jpg = os.path.join(IMG, f"slide-{n:02d}.jpg")
            ok = os.path.exists(png) and os.path.getsize(png) > 2000
            if ok:
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
                                png, "--out", jpg], check=False, capture_output=True, text=True)
                ok = os.path.exists(jpg) and os.path.getsize(jpg) > 2000
            if not ok:
                fail += 1
    return fail


def captions(iss, picks):
    lines = "\n".join(f"{RGE.get(it['region'],'•')} {it['head']}" for it in picks)
    d = fmt_date(iss["date"])
    ig = (f"📮 나침반 · {d} · 제{iss['number']}호\n\n"
          f"해외에 살면 놓치기 쉬운 오늘의 소식, 핵심만 골라 쉽게 풀었습니다.\n\n"
          f"{lines}\n\n"
          f"전체 {len(iss['published'])}건은 앱에서 👉 nachimban.pages.dev\n"
          f"(공유 → 홈 화면에 추가하면 매일 아침 받아볼 수 있어요)\n\n"
          f"#재외한인 #재외국민 #해외거주 #교민 #유학생 #워홀 #독일교민 #미국교민 "
          f"#유럽교민 #나침반 #오늘의뉴스 #해외생활 #비자 #여권 #ETIAS")
    th = (f"나침반 · {d} 오늘의 재외한인 브리핑 🧭\n\n{lines}\n\n"
          f"전체는 앱에서 → nachimban.pages.dev")
    return ig, th


VIEWER_CSS = """
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
:root{--kr:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
 --serif:Georgia,serif;--ink:#0A0A0A;--soft:#4B4B4B;--faint:#8C8C8C;--line:#E2E1DD;--panel:#F4F3F1}
body{font-family:var(--kr);color:var(--ink);background:#fff;line-height:1.6;
 max-width:640px;margin:0 auto;padding:22px 18px 60px}
.hd{border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:8px}
.hd h1{font-size:22px;font-weight:800;letter-spacing:-.01em}
.hd .rom{font-family:var(--serif);font-style:italic;color:var(--faint);font-size:14px;margin-top:2px}
h2{font-size:15px;font-weight:800;letter-spacing:.02em;margin:30px 0 6px}
.note{font-size:13px;color:var(--faint);margin-bottom:12px}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.grid a{display:block;position:relative}
.grid img{width:100%;border:1px solid var(--line);border-radius:6px;display:block}
.grid .i{position:absolute;top:5px;left:5px;background:rgba(10,10,10,.82);color:#fff;
 font-size:11px;font-weight:700;padding:2px 7px;border-radius:99px}
.cap{background:var(--panel);border:1px solid var(--line);border-radius:8px;
 padding:14px;font-size:14px;white-space:pre-wrap;word-break:break-word;margin-top:8px}
button{font-family:inherit;font-size:14px;font-weight:700;border:0;border-radius:99px;
 background:var(--ink);color:#fff;padding:11px 18px;margin-top:10px;cursor:pointer}
button:active{opacity:.7}
.tip{font-size:12px;color:var(--faint);margin-top:8px}
a.dl{display:inline-block;margin-top:12px;font-size:13px;color:var(--soft)}
@media(prefers-color-scheme:dark){
 body{background:#0d0d0e;color:#f2f1ee}
 :root{--panel:#1b1b1c;--line:#2a2a2c;--ink:#f2f1ee}
 button{background:#f2f1ee;color:#0d0d0e}
 .grid img{border-color:#2a2a2c}}
"""


def viewer_html(iss, picks, ig, th, nslides):
    thumbs = "".join(
        f'<a href="img/slide-{n:02d}.jpg" download="nachimban-{iss["date"]}-{n:02d}.jpg">'
        f'<span class="i">{n:02d}</span>'
        f'<img src="img/slide-{n:02d}.jpg" alt="slide {n}" loading="lazy"></a>'
        for n in range(1, nslides + 1))
    igj = json.dumps(ig, ensure_ascii=False)
    thj = json.dumps(th, ensure_ascii=False)
    return f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>나침반 소셜 · 제{iss['number']}호</title>
<style>{VIEWER_CSS}</style></head><body>
<div class="hd"><h1>나침반 소셜 · 제{iss['number']}호</h1>
<div class="rom">{fmt_date(iss['date'])} · 인스타·스레드용</div></div>

<h2>📸 캐러셀 이미지 ({nslides}장)</h2>
<div class="note">이미지를 <b>길게 눌러 저장</b>하거나 번호를 눌러 내려받으세요. 순서대로 올리면 됩니다.</div>
<div class="grid">{thumbs}</div>

<h2>📝 인스타그램 캡션</h2>
<div class="cap" id="ig"></div>
<button onclick="cp(IG,this)">캡션 복사</button>

<h2>🧵 스레드 문구</h2>
<div class="cap" id="th"></div>
<button onclick="cp(TH,this)">스레드 문구 복사</button>

<p class="tip">매일 아침 발행과 함께 자동 갱신됩니다.</p>
<script>
var IG={igj}, TH={thj};
document.getElementById('ig').textContent=IG;
document.getElementById('th').textContent=TH;
function cp(t,b){{navigator.clipboard.writeText(t).then(function(){{
 var o=b.textContent;b.textContent='복사됨 ✓';setTimeout(function(){{b.textContent=o}},1500);}});}}
</script></body></html>"""


def build_all(n=7):
    """이미지·캡션·뷰어를 site/social/ 에 만든다. 성공 요약(dict) 반환."""
    iss = latest_issue()
    picks = pick(iss["published"], n=n)
    # 표지 없이 바로 첫 기사부터 — 인스타 첫 장이 뉴스라야 후킹된다. (뉴스 → 앱 안내)
    slides = [news_slide(it, i, len(picks), iss["date"]) for i, it in enumerate(picks, start=1)] + \
             [outro_slide()]
    os.makedirs(SOCIAL, exist_ok=True)
    fail = render_images(slides)
    ig, th = captions(iss, picks)
    open(os.path.join(SOCIAL, "captions.txt"), "w", encoding="utf-8").write(
        f"===== INSTAGRAM =====\n\n{ig}\n\n\n===== THREADS =====\n\n{th}\n")
    open(os.path.join(SOCIAL, "index.html"), "w", encoding="utf-8").write(
        viewer_html(iss, picks, ig, th, len(slides)))
    # 매니페스트 — 자동 게시(post_social.py)가 이걸 읽어 그대로 올린다.
    base = "https://nachimban.pages.dev/social/img"
    manifest = {
        "number": iss["number"], "date": iss["date"], "slides": len(slides),
        "image_urls": [f"{base}/slide-{n:02d}.jpg" for n in range(1, len(slides) + 1)],
        "ig_caption": ig, "threads_text": th,
    }
    open(os.path.join(SOCIAL, "manifest.json"), "w", encoding="utf-8").write(
        json.dumps(manifest, ensure_ascii=False, indent=2))
    return {"number": iss["number"], "date": iss["date"],
            "slides": len(slides), "failed": fail, "picks": len(picks)}


if __name__ == "__main__":
    r = build_all()
    print(f"제{r['number']}호 · 슬라이드 {r['slides']}장(렌더실패 {r['failed']}) → site/social/")
    print("뷰어: /social/  ·  캡션: /social/captions.txt")
