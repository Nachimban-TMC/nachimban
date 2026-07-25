"""① 수집 + ② 선별 — 📰 취재 기자 (AI + 웹 검색).

지역별로 실제 웹을 검색해 재외한인에게 중요한 뉴스 후보를 발굴하고,
관련성 상위 N개를 골라 출처와 함께 돌려준다.
"""
from __future__ import annotations
from typing import List

import config
from schema import Candidate
from pipeline import llm

_SYSTEM = (
    "당신은 재외한인(해외 거주 한국인)을 위한 뉴스 서비스의 취재 기자입니다. "
    "법률 개정·복지·비자·세금·투자 등 '해외에 사는 한국인에게 실제로 영향이 있는' "
    "뉴스만 발굴합니다. 반드시 web_search/web_fetch 로 1차 출처(관보·부처 고시·"
    "공관 공지·신뢰 매체)를 확인하고, 확인되지 않은 것은 버립니다. 과장·추측 금지."
)


def collect_region(region: str, date: str) -> List[Candidate]:
    meta = config.REGIONS[region]
    hint = config.REGION_TOPIC_HINTS.get(region, "")
    cats = ", ".join(config.CATEGORIES.keys())
    user = f"""오늘은 {date} 입니다. '{meta['k']}({meta['en']})' 관련해서
재외한인에게 중요한 최신 뉴스를 웹에서 조사하세요.

우선 주제 힌트: {hint}

요구사항:
- 관련성 높은 순으로 정확히 {meta['count']}건 선정
- 각 건마다 출처 URL을 최소 {config.MIN_SOURCES}개 확보(1차 출처 우선)
- category 는 다음 중 하나: {cats}
- effective_date 에 시행/개정 핵심 날짜를 적기

마지막에 아래 형식의 ```json 블록으로만 결과를 출력:
```json
{{"items": [
  {{"region": "{region}", "category": "...", "headline": "...",
    "summary": "...", "effective_date": "...", "source_name": "...",
    "source_urls": ["https://...", "https://..."]}}
]}}
```"""
    data = llm.research(_SYSTEM, user, model=config.MODEL_JOURNALIST)
    items = [Candidate(**it) for it in data.get("items", [])]
    return items[: meta["count"]]


def collect(date: str, regions: List[str] | None = None) -> List[Candidate]:
    regions = regions or config.REGION_ORDER
    out: List[Candidate] = []
    for r in regions:
        print(f"  📰 수집: {r} …")
        out.extend(collect_region(r, date))
    return out
