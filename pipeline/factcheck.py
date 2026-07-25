"""④⑤ 이중 팩트체크 — 🔎 팩트체커 A & 🔎 팩트체커 B (독립).

두 검증자가 '서로 다른 모델'로 독립 검증한다. 각자 원문(source_urls)을
web_fetch 로 대조하고, 필요하면 web_search 로 추가 확인해 수치·날짜·시행일이
맞는지 본다. 사용자 요청("한 명 더 두더라도 확실하게")을 반영한 핵심 단계.
"""
from __future__ import annotations
import json

import config
from schema import NewsItem, FactVerdict
from pipeline import llm

_SYSTEM = (
    "당신은 재외한인 뉴스의 팩트체커입니다. 주어진 뉴스 카드의 사실 주장"
    "(수치·금액·시행일·요건·기관명)을 원문 출처와 1:1로 대조합니다. "
    "web_fetch 로 출처를 열고, 필요하면 web_search 로 교차 확인하세요. "
    "요약 전체가 아니라 '조각(개별 주장)' 단위로 검증합니다. "
    "하나라도 출처와 어긋나거나 확인 불가면 HOLD. 확신이 서야만 PASS."
)


def _check(item: NewsItem, model: str) -> FactVerdict:
    user = f"""다음 카드의 사실을 검증하세요.

제목: {item.head}
요약: {item.desc}
쉬운 해석: {item.interp}
출처: {', '.join(item.source_urls) or '(없음)'}

절차:
1) 각 출처를 web_fetch 로 열어 본문 확인
2) 카드의 수치·날짜·시행일·요건·기관명을 원문과 대조
3) 출처가 {config.MIN_SOURCES}개 미만이거나 하나라도 불일치면 HOLD

마지막에 ```json 으로만:
```json
{{"verdict": "PASS 또는 HOLD",
  "confidence": 0.0~1.0,
  "sources_count": 확인한 출처 수(정수),
  "issues": ["불일치/의심 항목", "..."]}}
```"""
    data = llm.research(_SYSTEM, user, model=model)
    # research 는 dict 를 돌려줌 → FactVerdict 로 검증
    return FactVerdict(**{
        "verdict": data.get("verdict", "HOLD"),
        "confidence": float(data.get("confidence", 0.0)),
        "sources_count": int(data.get("sources_count", 0)),
        "issues": data.get("issues", []) or [],
    })


def check_a(item: NewsItem) -> FactVerdict:
    return _check(item, model=config.MODEL_FACTCHECK_A)


def check_b(item: NewsItem) -> FactVerdict:
    # 독립성: A와 다른 모델
    return _check(item, model=config.MODEL_FACTCHECK_B)
