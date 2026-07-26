"""⑦ 발행 — 사이트 생성 + 아카이브 적재.

- data/issue-NNNN.json : 그 호의 전체 데이터(발행분 + 보류분 + 검증 로그)
- data/index.json      : 아카이브용 호 목록(누적)
- site/index.html      : template.html 의 <!--FEED--> / <!--ARCHIVE--> 를
                         실제 카드/아카이브로 치환한 정적 페이지(자체 완결)
"""
from __future__ import annotations
import json
import os
from typing import List

import config
from schema import Issue, NewsItem

_RG_SHORT = {"de": "독일", "kr": "한국", "eu": "EU", "us": "USA", "fr": "프랑스"}
_AD = """  <div class="adslot">
    <span class="lbl">Advertisement · 광고</span>
    <div class="body"><b>이 자리에 광고가 노출됩니다.</b> 재외한인 대상 서비스 — 국제 송금·환전, 법률·세무 상담, 유학·보험, 항공 등</div>
    <div class="meta">광고 문의 · ads@nachimban.co</div>
  </div>"""


# ── 카드/섹션 렌더 (template.html 의 CSS 클래스와 일치) ──────────────
def _card(it: NewsItem, date_dot: str) -> str:
    kr, en, img = config.CATEGORIES.get(it.category, (it.category, "", "g1"))
    hotcls = " hot" if it.hot else ""
    hl = f'\n        <div class="hot-line">{it.hotflag}</div>' if it.hotflag else ""
    return f"""      <article class="card">
        <div class="m-top"><span class="date">{date_dot}</span><span class="tag{hotcls}">{kr} <em>{en}</em></span></div>
        <div class="thumb {img}"><span class="ph">Sample</span></div>{hl}
        <h3>{it.head}</h3>
        <p class="desc">{it.desc}</p>
        <div class="interp"><span class="il">쉬운 해석 — 법률 해설가</span><p>{it.interp}</p></div>
        <div class="m-bot"><span><span class="lb">Source</span>{it.source}</span><span><span class="lb">Read</span>{it.read} min</span><a class="readmore" href="{it.url}"><span class="arrow">↗</span>read more</a></div>
      </article>"""


def _section(region: str, items: List[NewsItem], date_dot: str) -> str:
    meta = config.REGIONS[region]
    cards = "\n\n".join(_card(it, date_dot) for it in items)
    return f"""  <section data-region="{region}">
    <div class="sec-hd"><span class="k">{meta['k']}</span><span class="en">{meta['en']}</span><span class="rule"></span></div>
    <div class="grid">

{cards}

    </div>
  </section>"""


def _build_search_index() -> str:
    """모든 호의 뉴스를 검색용 JSON 으로. (n=호수, d=날짜, r=지역, c=카테고리, h=제목)"""
    import glob
    rows = []
    for path in sorted(glob.glob(os.path.join(config.DATA_DIR, "issue-*.json")), reverse=True):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for it in d.get("published", []):
            kr, _, _ = config.CATEGORIES.get(it.get("category", ""), (it.get("category", ""), "", ""))
            rows.append({
                "n": d.get("number"),
                "d": d.get("date"),
                "r": it.get("region"),
                "c": kr,
                "h": it.get("head", ""),
            })
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def _render_filter(issue: Issue) -> str:
    """지역 인덱스 — config.REGION_ORDER 를 따라 자동 생성(그 호에 기사가 있는 지역만)."""
    have = {it.region for it in issue.published}
    out = ['<button class="fpill on" data-r="all" onclick="showRegion(\'all\')">All</button>']
    for r in config.REGION_ORDER:
        if r in have:
            meta = config.REGIONS[r]
            out.append(f'<button class="fpill" data-r="{r}" '
                       f'onclick="showRegion(\'{r}\')">{meta.get("s", meta["k"])}</button>')
    return "\n      ".join(out)


def _render_feed(issue: Issue) -> str:
    date_dot = issue.date.replace("-", ".")
    by_region = {r: [it for it in issue.published if it.region == r] for r in config.REGION_ORDER}
    blocks = []
    for r in config.REGION_ORDER:
        if not by_region[r]:
            continue
        blocks.append(_section(r, by_region[r], date_dot))
        if config.AD_AFTER and r == config.AD_AFTER:   # None 이면 광고 숨김
            blocks.append(_AD)
    return "\n\n".join(blocks)


def _render_archive(index: List[dict]) -> str:
    """모든 호를 '읽기' 링크와 함께. 최신 호는 목차까지 펼쳐서 보여준다."""
    if not index:
        return ""
    out = []
    for i, iss in enumerate(index):
        dt = iss["date"].replace("-", " · ")
        cnt = " · ".join(f"{_RG_SHORT[r]} {n}" for r, n in iss.get("region_counts", {}).items())
        label = f"{cnt} — {iss['total']}건" if cnt else f"{iss['total']}건 발행"
        today = " · 오늘" if i == 0 else ""
        link = f"/archive/{iss['number']}.html"
        items = ""
        if i == 0 and iss.get("sample"):
            rows = "\n".join(
                f'        <a class="arch-item" href="{link}"><span class="rg">{s["rg"]}</span>'
                f'<span class="ttl">{s["title"]}</span></a>'
                for s in iss["sample"]
            )
            items = f'\n      <div class="arch-list">\n{rows}\n      </div>'
        out.append(f"""    <div class="issue">
      <a class="issue-hd" href="{link}"><span class="no">{iss['number']:02d}</span><span class="dt">{dt}{today}</span><span class="cnt">{label}</span><span class="go">읽기 →</span></a>{items}
    </div>""")
    return "\n".join(out)


# ── 아카이브 인덱스 관리 ─────────────────────────────────────────
def _update_index(issue: Issue) -> List[dict]:
    path = os.path.join(config.DATA_DIR, "index.json")
    index = []
    if os.path.exists(path):
        index = json.load(open(path, encoding="utf-8"))
    index = [e for e in index if e["number"] != issue.number]  # 같은 호 갱신
    sample = [{"rg": _RG_SHORT[it.region], "title": it.head}
              for it in issue.published[:6]]
    index.insert(0, {
        "number": issue.number,
        "date": issue.date,
        "total": len(issue.published),
        "region_counts": issue.region_counts(),
        "sample": sample,
    })
    index.sort(key=lambda e: e["number"], reverse=True)
    json.dump(index, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return index


# ── 공개 API ─────────────────────────────────────────────────────
def _render_issue_page(tpl: str, issue: Issue, index: List[dict]) -> str:
    """지난 호를 그대로 다시 볼 수 있는 개별 페이지."""
    html = tpl.replace("<!--FILTER-->", _render_filter(issue))
    html = html.replace("<!--FEED-->", _render_feed(issue))
    html = html.replace("<!--ARCHIVE-->", _render_archive(index))
    html = html.replace("/*<!--SEARCHDATA-->*/[]", _build_search_index())
    html = html.replace("2026. 07. 25 · AM 7:00",
                        f"{issue.date.replace('-', '. ')} · 제{issue.number}호")
    # 지난 호임을 알리는 배너 + 오늘자로 돌아가는 링크
    banner = (f'<div class="pastbar">지난 호를 보고 있습니다 · 제{issue.number}호 '
              f'({issue.date.replace("-", ". ")}) <a href="/">오늘의 브리핑 →</a></div>')
    html = html.replace('<div id="view-today">', banner + '\n  <div id="view-today">')
    # 개별 호 페이지에서는 하위 경로이므로 상대 링크 보정 불필요(모두 절대경로 사용)
    return html


def publish(issue: Issue) -> str:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    # 1) 호 데이터 저장(발행분·보류분·검증로그 포함)
    json.dump(issue.model_dump(),
              open(os.path.join(config.DATA_DIR, f"issue-{issue.number:04d}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    # 2) 아카이브 인덱스 갱신
    index = _update_index(issue)
    # 3) 사이트 렌더
    tpl = open(os.path.join(config.SITE_DIR, "template.html"), encoding="utf-8").read()
    tpl = tpl.replace("<!--FILTER-->", _render_filter(issue))
    tpl = tpl.replace("<!--FEED-->", _render_feed(issue))
    tpl = tpl.replace("<!--ARCHIVE-->", _render_archive(index))
    tpl = tpl.replace("/*<!--SEARCHDATA-->*/[]", _build_search_index())
    tpl = tpl.replace("2026. 07. 25 · AM 7:00", f"{issue.date.replace('-', '. ')} · AM 7:00")
    out = os.path.join(config.SITE_DIR, "index.html")
    open(out, "w", encoding="utf-8").write(tpl)

    # 4) 이 호의 개별 페이지도 생성 (아카이브에서 다시 읽기)
    raw = open(os.path.join(config.SITE_DIR, "template.html"), encoding="utf-8").read()
    arc_dir = os.path.join(config.SITE_DIR, "archive")
    os.makedirs(arc_dir, exist_ok=True)
    open(os.path.join(arc_dir, f"{issue.number}.html"), "w", encoding="utf-8").write(
        _render_issue_page(raw, issue, index))
    return out
