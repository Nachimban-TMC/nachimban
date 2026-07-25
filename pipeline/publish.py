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


def _render_feed(issue: Issue) -> str:
    date_dot = issue.date.replace("-", ".")
    by_region = {r: [it for it in issue.published if it.region == r] for r in config.REGION_ORDER}
    blocks = []
    for r in config.REGION_ORDER:
        if not by_region[r]:
            continue
        blocks.append(_section(r, by_region[r], date_dot))
        if r == config.AD_AFTER:
            blocks.append(_AD)
    return "\n\n".join(blocks)


def _render_archive(index: List[dict]) -> str:
    """index[0] = 최신 호(펼침), 나머지는 요약 행."""
    if not index:
        return ""
    latest = index[0]
    items = "\n".join(
        f'        <div class="arch-item"><span class="rg">{s["rg"]}</span>'
        f'<span class="ttl">{s["title"]}</span></div>'
        for s in latest.get("sample", [])
    )
    dt = latest["date"].replace("-", " · ")
    cnt = " · ".join(f"{_RG_SHORT[r]} {n}" for r, n in latest["region_counts"].items())
    out = [f"""    <div class="issue">
      <div class="issue-hd"><span class="no">{latest['number']:02d}</span><span class="dt">{dt} · 오늘</span><span class="cnt">{cnt} — {latest['total']}건</span></div>
      <div class="arch-list">
{items}
      </div>
    </div>"""]
    for iss in index[1:]:
        dt = iss["date"].replace("-", " · ")
        out.append(f"""    <div class="issue">
      <div class="issue-hd"><span class="no">{iss['number']:02d}</span><span class="dt">{dt}</span><span class="cnt">{iss['total']}건 발행</span></div>
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
    tpl = tpl.replace("<!--FEED-->", _render_feed(issue))
    tpl = tpl.replace("<!--ARCHIVE-->", _render_archive(index))
    tpl = tpl.replace("2026. 07. 25 · AM 7:00", f"{issue.date.replace('-', '. ')} · AM 7:00")
    out = os.path.join(config.SITE_DIR, "index.html")
    open(out, "w", encoding="utf-8").write(tpl)
    return out
