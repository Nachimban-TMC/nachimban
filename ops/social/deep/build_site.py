#!/usr/bin/env python3
"""심층 캐러셀을 사이트에 올리는 페이지로 만든다 (무료, 로컬).
  python3 ops/social/deep/build_site.py
→ site/social/deep/index.html            : 심층 모아보기 (최신순)
→ site/social/deep/<슬러그>/index.html   : 이미지 저장 + 인스타 캡션·스레드 문구 복사
→ site/social/deep/<슬러그>/img/deep-NN.jpg

새 심층을 만들면 아래 DEEPS 맨 위에 한 줄 추가하고 다시 실행한다.
각 심층은 이 폴더의 out-<슬러그>/deep-NN.jpg, <슬러그>-caption-ig.txt, <슬러그>-threads.txt 를 쓴다.
매일 자동 생성(make_social.build_all)은 site/social/ 최상위만 덮어쓰므로 이 폴더는 유지된다."""
import glob, html, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.dirname(HERE))
import make_social as ms

SITE = os.path.join(REPO, "site", "social", "deep")

# 최신순. (슬러그, 제목, 날짜 표기, 지역)
DEEPS = [
    ("2026-09-26-vw-recall", "폭스바겐 조향 리콜, 내 차도?", "2026. 09. 26", "독일"),
    ("2026-09-24-sozialbetrug", "독일 복지 부정수급 대책 10가지", "2026. 09. 24", "독일"),
]

EXTRA_CSS = """
.back{display:inline-block;font-size:13px;color:var(--soft);margin-bottom:14px;text-decoration:none}
.list a{display:flex;gap:14px;align-items:center;padding:14px 0;border-bottom:1px solid var(--line);
 color:inherit;text-decoration:none}
.list img{width:84px;border:1px solid var(--line);border-radius:6px;flex:none}
.list .t{font-size:16px;font-weight:800;line-height:1.35}
.list .m{font-size:12px;color:var(--faint);margin-top:4px}
"""


def _read(path):
    return open(path, encoding="utf-8").read().strip() if os.path.exists(path) else ""


def build_one(slug, title, date, region):
    src = os.path.join(HERE, "out-" + slug)
    imgs = sorted(glob.glob(os.path.join(src, "deep-*.jpg")))
    if not imgs:
        raise SystemExit(f"이미지 없음: {src} — 먼저 {slug}.py 를 실행하세요")
    dst = os.path.join(SITE, slug)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(os.path.join(dst, "img"))
    for p in imgs:
        shutil.copy2(p, os.path.join(dst, "img", os.path.basename(p)))
    ig = _read(os.path.join(HERE, f"{slug}-caption-ig.txt")) or _read(os.path.join(HERE, f"{slug}-caption.txt"))
    th = _read(os.path.join(HERE, f"{slug}-threads.txt"))
    n = len(imgs)
    thumbs = "".join(
        f'<a href="img/deep-{i:02d}.jpg" download="nachimban-deep-{slug}-{i:02d}.jpg">'
        f'<span class="i">{i:02d}</span><img src="img/deep-{i:02d}.jpg" alt="{i}장" loading="lazy"></a>'
        for i in range(1, n + 1))
    t = html.escape(title)
    page = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>나침반 심층 · {t}</title>
<style>{ms.VIEWER_CSS}{EXTRA_CSS}</style></head><body>
<a class="back" href="../">← 심층 모아보기</a>
<div class="hd"><h1>{t}</h1>
<div class="rom">{date} · {region} · 심층 캐러셀 {n}장</div></div>

<h2>🖼 캐러셀용 · 4:5 ({n}장)</h2>
<div class="note">길게 눌러 저장하거나 번호를 눌러 내려받으세요. 인스타에는 순서대로 올리세요.</div>
<div class="grid">{thumbs}</div>

<h2>📝 인스타그램 캡션</h2>
<div class="cap" id="ig"></div>
<button onclick="cp(IG,this)">캡션 복사</button>

<h2>🧵 스레드 문구</h2>
<div class="cap" id="th"></div>
<button onclick="cp(TH,this)">스레드 문구 복사</button>

<p class="tip">이 페이지는 매일 자동 갱신되지 않습니다. 오늘의 소셜 자료는 <a href="/social/">/social</a> 에 있습니다.</p>
<script>
var IG={json.dumps(ig, ensure_ascii=False)}, TH={json.dumps(th, ensure_ascii=False)};
document.getElementById('ig').textContent=IG||'(캡션 파일 없음)';
document.getElementById('th').textContent=TH||'(스레드 파일 없음)';
function cp(t,b){{navigator.clipboard.writeText(t).then(function(){{
 var o=b.textContent;b.textContent='복사됨 ✓';setTimeout(function(){{b.textContent=o}},1500);}});}}
</script></body></html>"""
    open(os.path.join(dst, "index.html"), "w", encoding="utf-8").write(page)
    return n


def build_index():
    rows = "".join(
        f'<a href="{slug}/"><img src="{slug}/img/deep-01.jpg" alt="" loading="lazy">'
        f'<div><div class="t">{html.escape(title)}</div><div class="m">{date} · {region}</div></div></a>'
        for slug, title, date, region in DEEPS)
    page = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>나침반 심층 모아보기</title>
<style>{ms.VIEWER_CSS}{EXTRA_CSS}</style></head><body>
<a class="back" href="/social/">← 오늘의 소셜 자료</a>
<div class="hd"><h1>나침반 심층 모아보기</h1>
<div class="rom">기사 하나를 골라 깊게 푼 캐러셀 · 최신순</div></div>
<div class="list">{rows}</div>
</body></html>"""
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(page)


def main():
    os.makedirs(SITE, exist_ok=True)
    for slug, title, date, region in DEEPS:
        print(slug, build_one(slug, title, date, region), "장")
    build_index()
    print("→ site/social/deep/")


if __name__ == "__main__":
    main()
