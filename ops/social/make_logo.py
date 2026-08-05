#!/usr/bin/env python3
"""프로필 로고 시안 3종을 1080x1080 PNG로 렌더(원형 크롭 대비 안전영역 중앙 배치)."""
import os, glob, tempfile, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "logo")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

BASE = """
*{margin:0;padding:0;box-sizing:border-box;-webkit-font-smoothing:antialiased}
:root{--disp:"Helvetica Neue","Pretendard","Apple SD Gothic Neo",Arial,sans-serif;
 --serif:Georgia,"Times New Roman",serif}
.c{width:1080px;height:1080px;display:flex;flex-direction:column;align-items:center;
 justify-content:center;position:relative;overflow:hidden}
.needle{display:block}
"""

# 나침반 바늘(북=흰색, 남=회색) + 링 + N
COMPASS = """<svg class="needle" width="{s}" height="{s}" viewBox="0 0 100 100">
 <circle cx="50" cy="50" r="46" fill="none" stroke="{stroke}" stroke-width="1.6"/>
 <g fill="{stroke}"><rect x="49.2" y="6" width="1.6" height="8"/><rect x="49.2" y="86" width="1.6" height="8"/>
 <rect x="6" y="49.2" width="8" height="1.6"/><rect x="86" y="49.2" width="8" height="1.6"/></g>
 <polygon points="50,16 41,52 59,52" fill="{north}"/>
 <polygon points="50,84 41,52 59,52" fill="{south}"/>
 <circle cx="50" cy="52" r="3.4" fill="{stroke}"/>
</svg>"""

def variant_A():  # 검정 원판 + 흰 워드마크
    return f"""<div class="c" style="background:#0A0A0A;color:#fff">
      <div style="font-family:var(--disp);font-weight:800;font-size:250px;letter-spacing:-.02em">나침반</div>
      <div style="font-family:var(--serif);font-style:italic;font-size:44px;color:#B9B9B4;margin-top:26px;letter-spacing:.02em">The Morning Compass</div>
    </div>"""

def variant_B():  # 검정 원판 + 나침반 마크 + 워드마크
    comp = COMPASS.format(s=360, stroke="#FFFFFF", north="#FFFFFF", south="#6E6E6E")
    return f"""<div class="c" style="background:#0A0A0A;color:#fff">
      {comp}
      <div style="font-family:var(--disp);font-weight:800;font-size:150px;letter-spacing:-.01em;margin-top:40px">나침반</div>
    </div>"""

def variant_C():  # 밝은 바탕 + 검정 나침반 마크 + 워드마크(원형 크롭 최적화)
    comp = COMPASS.format(s=470, stroke="#0A0A0A", north="#0A0A0A", south="#C9C7C2")
    return f"""<div class="c" style="background:#F4F3F1;color:#0A0A0A">
      {comp}
      <div style="font-family:var(--disp);font-weight:800;font-size:104px;letter-spacing:.02em;margin-top:30px">나침반</div>
    </div>"""

def circle_preview(inner):
    """실제 프로필처럼 원형으로 잘린 모습(체크무늬 배경 위)."""
    return f"""<div style="width:1080px;height:1080px;background:
      repeating-conic-gradient(#d8d8d8 0% 25%, #eee 0% 50%) 0/120px 120px;
      display:flex;align-items:center;justify-content:center">
      <div style="width:960px;height:960px;border-radius:50%;overflow:hidden;
        box-shadow:0 8px 40px rgba(0,0,0,.25)">
        <div style="transform:scale(.8889);transform-origin:top left">{inner}</div>
      </div></div>"""

def doc(inner):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{BASE}</style></head><body>{inner}</body></html>'

def render(name, inner):
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, name + ".html")
        open(hp, "w", encoding="utf-8").write(doc(inner))
        png = os.path.join(OUT, name + ".png")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--no-first-run", "--no-default-browser-check", "--force-device-scale-factor=1",
                        "--window-size=1080,1080", f"--screenshot={png}", f"file://{hp}"],
                       check=False, capture_output=True, text=True, timeout=60)
        ok = os.path.exists(png) and os.path.getsize(png) > 2000
        print(("OK  " if ok else "FAIL ") + png)

if __name__ == "__main__":
    for old in glob.glob(os.path.join(OUT, "*.png")):
        os.remove(old)
    render("logo-A-wordmark", variant_A())
    render("logo-B-compass-word", variant_B())
    render("logo-C-icon", variant_C())
    render("logo-C-circle-preview", circle_preview(variant_C()))
