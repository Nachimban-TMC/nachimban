"""⑦ 발행 — 사이트 생성 + 아카이브 적재.

- data/issue-NNNN.json : 그 호의 전체 데이터(발행분 + 보류분 + 검증 로그)
- data/index.json      : 아카이브용 호 목록(누적)
- site/index.html      : template.html 의 <!--FEED--> 를
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


def _esc_attr(s: str) -> str:
    return (s.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;"))


def _interp_label(it: NewsItem) -> str:
    """사건·사고 카드에 '법률 해설가'를 붙이면 어색하다."""
    return "현지 한인에게" if it.category == "general" else "쉬운 해석 — 법률 해설가"


def _share_btn(it: NewsItem) -> str:
    """카드 공유 버튼. 원문이 아니라 '나침반'을 공유한다(서비스를 알리는 게 목적)."""
    return (f'<button class="shr" type="button" aria-label="이 소식 공유하기" '
            f'title="공유하기" onclick="nbShare(this)" data-h="{_esc_attr(it.head)}">'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>'
            '<circle cx="18" cy="19" r="3"/>'
            '<path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg></button>')


# 주제군마다 준비된 사진 장수 (site/img/gN-1.jpg …)
_IMG_VARIANTS = {"g1": 6, "g2": 4, "g3": 4, "g4": 6, "g5": 4,
                 "g6": 4, "g7": 4, "g8": 4, "g9": 4, "g10": 4}


class _ImgRotator:
    """한 호 안에서 사진이 겹치지 않게 골라준다.

    예전에는 카테고리 하나에 사진 하나여서, 지역마다 들어가는 1면 뉴스 4건이
    한 화면에 똑같은 사진 4장으로 나왔다. '호수 + 그 주제군을 이미 몇 번 썼는지'로
    고르면 같은 호 안에서는 반드시 다른 사진이 나오고(주제군 사진 수 이내),
    호가 바뀌면 시작점도 달라져 날마다 다르게 보인다.
    """

    def __init__(self, issue_no: int = 0) -> None:
        self.issue_no = issue_no
        self._used: dict[str, int] = {}

    def pick(self, group: str) -> str:
        n = _IMG_VARIANTS.get(group, 1)
        if n <= 1:
            return group
        k = self._used.get(group, 0)
        self._used[group] = k + 1
        return f"{group}-{(self.issue_no + k) % n + 1}"


# ── 카드/섹션 렌더 (template.html 의 CSS 클래스와 일치) ──────────────
def _card(it: NewsItem, date_dot: str, rot: "_ImgRotator | None" = None) -> str:
    kr, en, group = config.CATEGORIES.get(it.category, (it.category, "", "g1"))
    img = (rot or _ImgRotator()).pick(group)
    hotcls = " hot" if it.hot else ""
    hl = f'\n        <div class="hot-line">{it.hotflag}</div>' if it.hotflag else ""
    return f"""      <article class="card">
        <div class="m-top"><span class="date">{date_dot}</span><span class="tag{hotcls}">{kr} <em>{en}</em></span></div>
        <div class="thumb {img}"><span class="ph">Sample</span></div>{hl}
        <h3>{it.head}</h3>
        <p class="desc">{it.desc}</p>
        <div class="interp"><span class="il">{_interp_label(it)}</span><p>{it.interp}</p></div>
        <div class="m-bot"><span><span class="lb">Source</span>{it.source}</span><span><span class="lb">Read</span>{it.read} min</span>{_share_btn(it)}<a class="readmore" href="{it.url}" target="_blank" rel="noopener noreferrer"><span class="arrow">↗</span>read more</a></div>
      </article>"""


def _section(region: str, items: List[NewsItem], date_dot: str,
             rot: "_ImgRotator | None" = None) -> str:
    meta = config.REGIONS[region]
    cards = "\n\n".join(_card(it, date_dot, rot) for it in items)
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


def _archive_info(index: List[dict]) -> str:
    """아카이브 안내에 들어갈 현재 현황 (하드코딩 대신 자동 갱신)."""
    if not index:
        return ""
    issues = len(index)
    total = sum(e.get("total", 0) for e in index)
    return f"지금까지 <b>{issues}호</b>, 모두 <b>{total}건</b>을 전해드렸습니다."


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
    rot = _ImgRotator(issue.number)   # 호 전체가 하나의 회전판을 공유한다
    for r in config.REGION_ORDER:
        if not by_region[r]:
            continue
        blocks.append(_section(r, by_region[r], date_dot, rot))
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


def _write_archive_data(index: List[dict]) -> None:
    """아카이브 목록과 검색 인덱스를 파일 하나로 뺀다.

    예전에는 이 둘을 '모든 호 페이지 안에' 통째로 넣었다. 호가 쌓일수록
    페이지마다 같은 데이터가 무거워지고, 새 호가 나올 때마다 지난 호를
    전부 다시 만들어야 목록이 최신이 됐다. 파일 하나로 빼면 페이지 크기는
    호 수와 무관하게 고정되고, 지난 호는 다시 만들 필요가 없다.
    """
    issues = []
    for i, iss in enumerate(index):
        cnt = " · ".join(f"{_RG_SHORT[r]} {n}" for r, n in iss.get("region_counts", {}).items())
        issues.append({
            "n": iss["number"],
            "d": iss["date"],
            "label": f"{cnt} — {iss['total']}건" if cnt else f"{iss['total']}건 발행",
            "sample": iss.get("sample", []) if i == 0 else [],
        })
    data = {
        "info": {"issues": len(index), "total": sum(e.get("total", 0) for e in index)},
        "issues": issues,
        "search": json.loads(_build_search_index()),
    }
    out = os.path.join(config.SITE_DIR, "archive-data.json")
    json.dump(data, open(out, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))


def _write_sitemap(index: List[dict]) -> None:
    """검색엔진에 어떤 페이지가 있는지 알린다. 호가 늘 때마다 다시 쓴다."""
    base = config.SITE_URL.rstrip("/")
    latest = index[0]["date"] if index else ""
    rows = [f"  <url><loc>{base}/</loc><lastmod>{latest}</lastmod>"
            f"<changefreq>daily</changefreq><priority>1.0</priority></url>"]
    for it in index:
        rows.append(f"  <url><loc>{base}/archive/{it['number']}</loc>"
                    f"<lastmod>{it['date']}</lastmod>"
                    f"<changefreq>never</changefreq><priority>0.7</priority></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    open(os.path.join(config.SITE_DIR, "sitemap.xml"), "w", encoding="utf-8").write(xml)


def _og(html: str, *, url: str = "", title: str = "", desc: str = "") -> str:
    """공유 카드(og) 채우기. 절대주소가 필요해 여기서 넣는다."""
    base = config.SITE_URL.rstrip("/")
    html = html.replace("<!--SITEURL-->", (url or base))
    # og:image 는 항상 사이트 루트 기준 절대주소여야 한다
    html = html.replace(f'content="{url}/og.png"', f'content="{base}/og.png"') if url else html
    if title:
        html = html.replace('property="og:title" content="나침반 — 재외한인 아침 브리핑"',
                            f'property="og:title" content="{title}"')
        html = html.replace('name="twitter:title" content="나침반 — 재외한인 아침 브리핑"',
                            f'name="twitter:title" content="{title}"')
    if desc:
        old = ('content="해외에 사는 우리에게 꼭 필요한 법률·복지·비자·세금 소식만 매일 아침 7시."')
        html = html.replace(old, f'content="{desc}"')
    return html


def _inline_push(html: str) -> str:
    """푸시 스크립트를 HTML 안에 직접 넣는다.

    외부 파일로 두면 네트워크가 한 번만 흔들려도(또는 서비스워커가 엉뚱한
    응답을 돌려줘도) 알림 칸이 통째로 사라진다. 실제로 그렇게 사라졌다.
    """
    src = open(os.path.join(config.SITE_DIR, "push.js"), encoding="utf-8").read()
    src = src.replace("</script>", "<\\/script>")   # 조기 종료 방지
    return html.replace("/*<!--PUSHJS-->*/", src)


# ── 공개 API ─────────────────────────────────────────────────────
def _render_issue_page(tpl: str, issue: Issue, index: List[dict]) -> str:
    """지난 호를 그대로 다시 볼 수 있는 개별 페이지."""
    html = tpl.replace("<!--FILTER-->", _render_filter(issue))
    html = html.replace("<!--FEED-->", _render_feed(issue))
    html = _inline_push(html)
    html = html.replace("<!--ISSUEDATE-->", "")
    # 지난 호는 그 호의 제목·헤드라인으로 공유되게 한다
    heads = " · ".join(it.head for it in issue.published[:3])
    html = _og(html,
               url=f"{config.SITE_URL.rstrip('/')}/archive/{issue.number}",
               title=f"나침반 제{issue.number}호 · {issue.date.replace('-', '. ')}",
               desc=(heads[:150] or "재외한인을 위한 아침 브리핑"))
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
    _write_archive_data(index)
    _write_sitemap(index)
    # 3) 사이트 렌더
    tpl = open(os.path.join(config.SITE_DIR, "template.html"), encoding="utf-8").read()
    tpl = tpl.replace("<!--FILTER-->", _render_filter(issue))
    tpl = tpl.replace("<!--FEED-->", _render_feed(issue))
    tpl = _inline_push(tpl)
    tpl = _og(tpl)          # 대문은 브랜드 기본 문구 그대로
    tpl = tpl.replace("<!--ISSUEDATE-->", issue.date)
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
