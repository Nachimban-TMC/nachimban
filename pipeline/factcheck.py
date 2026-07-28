"""④⑤ 이중 팩트체크 — 🔎 팩트체커 A & 🔎 팩트체커 B (독립).

두 검증자가 '서로 다른 모델'로 독립 검증한다. 각자 원문(source_urls)을
web_fetch 로 대조하고, 필요하면 web_search 로 추가 확인해 수치·날짜·시행일이
맞는지 본다. 사용자 요청("한 명 더 두더라도 확실하게")을 반영한 핵심 단계.
"""
from __future__ import annotations
import json

import config
from schema import NewsItem, FactVerdict

_SYSTEM = (
    "당신은 재외한인 뉴스의 팩트체커입니다. 주어진 뉴스 카드의 사실 주장"
    "(수치·금액·시행일·요건·기관명)을 출처와 1:1로 대조합니다. "
    "요약 전체가 아니라 '조각(개별 주장)' 단위로 검증합니다.\n"
    "토큰 효율 원칙: 원문을 통째로 읽지 마세요. 검색 결과 요약(스니펫)으로 "
    "확인되는 사실은 그것으로 충분합니다. web_fetch 는 수치·날짜가 스니펫만으로 "
    "확정되지 않을 때만 쓰고, 같은 출처를 두 번 열지 마세요.\n"
    "하나라도 출처와 어긋나거나 확인 불가면 HOLD. 확신이 서야만 PASS."
)

# 위험도가 높아 이중 검증이 필요한 카테고리
_HIGH_RISK = {"visa", "immigration", "citizenship", "tax", "welfare", "pension",
              "health", "invest", "stocks", "crypto"}   # 돈·자격과 직결 → 이중 검증


def _check(item: NewsItem, model: str) -> FactVerdict:
    from pipeline import llm   # SDK는 실제 검증할 때만 필요
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
    data = llm.research(_SYSTEM, user, model=model, stage="팩트체크")
    # research 는 dict 를 돌려줌 → FactVerdict 로 검증
    return FactVerdict(**{
        "verdict": data.get("verdict", "HOLD"),
        "confidence": float(data.get("confidence", 0.0)),
        "sources_count": int(data.get("sources_count", 0)),
        "issues": data.get("issues", []) or [],
    })


import re

# '틀리면 피해가 큰 수치'만 잡는다. 연도(2026년)는 제외 — 거의 모든 기사에 있어 의미가 없음.
_NUM = re.compile(
    r"[€$₩]\s*[\d,]"                       # €259, $250
    r"|[\d.,]+\s*(?:%|퍼센트)"              # 7.19%
    r"|[\d,]+\s*(?:억|천만|만\s*원|원|유로|달러)"   # 5억, 1,091원
    r"|\d{1,2}\s*월\s*\d{1,2}\s*일"         # 3월 31일 (기한)
)


def needs_double_check(item: NewsItem) -> bool:
    """A급(이중 검증) 대상인지. hot / 수치 포함 / 고위험 카테고리."""
    if item.hot:
        return True
    if item.category in _HIGH_RISK:
        return True
    return bool(_NUM.search(item.head + " " + item.desc))


def check_a(item: NewsItem) -> FactVerdict:
    return _check(item, model=config.MODEL_FACTCHECK_A)


def check_b(item: NewsItem) -> FactVerdict:
    # 독립성: A와 다른 모델
    return _check(item, model=config.MODEL_FACTCHECK_B)
