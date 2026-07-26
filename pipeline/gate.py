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
    """A급(중요·수치·고위험)은 2인 이중 검증, B급은 1인 + 출처 2개.

    사용자 요청으로 토큰을 아끼되, 오보 피해가 큰 뉴스는 이중 검증을 유지한다.
    """
    a = factcheck.check_a(item)
    item.check_a = a

    double = factcheck.needs_double_check(item)
    # B급이라도 1차에서 걸리면 이중 검증으로 승격해 확실히 판단
    if double or a.verdict != "PASS":
        b = factcheck.check_b(item)
        item.check_b = b
        checks = (("A", a), ("B", b))
    else:
        item.check_b = None
        checks = (("A", a),)

    notes: List[str] = []
    if not double:
        notes.append("B급(단일 검증 + 출처 2개)")
    ok = True
    for name, v in checks:
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
