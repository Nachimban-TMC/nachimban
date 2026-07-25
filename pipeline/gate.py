"""⑥ 게이트 — 두 팩트체커 결과를 합쳐 발행/보류 결정.

규칙(사용자 요청 "확실하게" 반영):
- A와 B가 모두 PASS 여야 하고
- 두 검증자 모두 확신도 >= MIN_CONFIDENCE, 출처 >= MIN_SOURCES 여야 발행.
- 하나라도 어긋나면 HOLD → 사람(편집장) 검토 큐로.
"""
from __future__ import annotations
from typing import List, Tuple

import config
from schema import NewsItem
from pipeline import factcheck


def evaluate(item: NewsItem) -> NewsItem:
    a = factcheck.check_a(item)
    b = factcheck.check_b(item)
    item.check_a, item.check_b = a, b

    notes: List[str] = []
    ok = True
    for name, v in (("A", a), ("B", b)):
        if v.verdict != "PASS":
            ok = False; notes.append(f"팩트체커 {name}: HOLD ({'; '.join(v.issues) or '사유 미기재'})")
        if v.confidence < config.MIN_CONFIDENCE:
            ok = False; notes.append(f"팩트체커 {name}: 확신도 낮음 {v.confidence:.2f}")
        if v.sources_count < config.MIN_SOURCES:
            ok = False; notes.append(f"팩트체커 {name}: 출처 부족 {v.sources_count} < {config.MIN_SOURCES}")

    item.verdict = "PASS" if ok else "HOLD"
    item.check_notes = notes
    return item


def split(items: List[NewsItem]) -> Tuple[List[NewsItem], List[NewsItem]]:
    """(발행, 보류) 로 분리."""
    published, held = [], []
    for it in items:
        (published if it.verdict == "PASS" else held).append(it)
    return published, held
