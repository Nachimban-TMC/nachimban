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
    "'해외에 사는 한국인에게 실제로 영향이 있는' 뉴스를 발굴합니다. "
    "두 갈래를 함께 봅니다. (1) 법률 개정·복지·비자·세금·투자 등 제도 뉴스, "
    "(2) 그날 그 나라에서 1면·톱으로 다뤄진 큰 뉴스 — 사건·사고·재난·치안·"
    "교통마비·정국 변화 등. 현지 사람이라면 누구나 아는 큰 뉴스를 빠뜨린 브리핑은 "
    "나머지 기사까지 신뢰를 잃습니다. "
    "반드시 web_search/web_fetch 로 1차 출처(관보·부처 고시·공관 공지·신뢰 매체)를 "
    "확인하고, 확인되지 않은 것은 버립니다. 과장·추측 금지. "
    "사건·사고는 특히 사상자 수와 경위를 단정하지 말고 확인된 사실만 씁니다."
)


def collect_region(region: str, date: str) -> List[Candidate]:
    meta = config.REGIONS[region]
    hint = config.REGION_TOPIC_HINTS.get(region, "")
    cats = ", ".join(config.CATEGORIES.keys())
    general_req = ""
    if config.REQUIRE_GENERAL_PER_REGION:
        general_req = f"""
■ 반드시 포함 ① — 그날의 '1면 뉴스' 1건 (category: general)
{config.GENERAL_HINT}
먼저 '{meta['k']} 오늘의 주요 뉴스'를 현지 언론 기준으로 검색해 무엇이 톱인지
확인한 다음, 나머지 제도 뉴스를 고르세요. 순서를 반대로 하지 마세요.

■ 반드시 포함 ② — 중대 사안이 있었다면
{config.BREAKING_HINT}
"""
    user = f"""오늘은 {date} 입니다. '{meta['k']}({meta['en']})' 관련해서
재외한인에게 중요한 최신 뉴스를 웹에서 조사하세요.
{general_req}
우선 주제 힌트(제도 뉴스): {hint}

요구사항:
- 기본 {meta['count']}건 선정 (위 '중대 사안'이 있으면 정원을 넘겨도 됩니다)
- 그중 최소 1건은 category="general" 인 그날의 1면 뉴스
- 각 건마다 출처 URL을 최소 {config.MIN_SOURCES}개 확보(1차 출처 우선)
- category 는 다음 중 하나: {cats}
- effective_date 에 시행/개정 핵심 날짜를 적기(사건·사고는 발생일)

마지막에 아래 형식의 ```json 블록으로만 결과를 출력:
```json
{{"items": [
  {{"region": "{region}", "category": "...", "headline": "...",
    "summary": "...", "effective_date": "...", "source_name": "...",
    "source_urls": ["https://...", "https://..."]}}
]}}
```"""
    data = llm.research(_SYSTEM, user, model=config.MODEL_JOURNALIST, stage="취재")
    items = [Candidate(**it) for it in data.get("items", [])]
    return _keep(items, meta["count"], region)


def _keep(items: List[Candidate], count: int, region: str) -> List[Candidate]:
    """정원만큼 자르되, 그날의 1면 뉴스는 잘라내지 않는다.

    예전에는 앞에서 count 개를 그냥 잘랐다. 그래서 취재 기자가 큰 사건을
    뒤쪽에 넣어 오면 그대로 사라졌다(베를린 사고가 이렇게 빠졌다).
    """
    kept = items[:count]
    if not config.REQUIRE_GENERAL_PER_REGION:
        return kept
    if any(i.category == "general" for i in kept):
        return kept
    rescued = next((i for i in items[count:] if i.category == "general"), None)
    if rescued:
        kept.append(rescued)      # 정원을 넘겨서라도 싣는다
        print(f"     ↳ {region}: 1면 뉴스를 정원 밖에서 되살림 — {rescued.headline}")
    else:
        print(f"     ⚠️  {region}: 그날의 1면 뉴스(general)를 찾지 못했습니다")
    return kept


def collect(date: str, regions: List[str] | None = None) -> List[Candidate]:
    regions = regions or config.REGION_ORDER
    out: List[Candidate] = []
    for r in regions:
        print(f"  📰 수집: {r} …")
        out.extend(collect_region(r, date))
    return out
