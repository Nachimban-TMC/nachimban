"""오케스트레이터 — 매일 새벽 도는 파이프라인의 진입점.

실행:
  python -m pipeline.run --mock            # API 없이 샘플로 전체 흐름 재현(사이트 생성)
  python -m pipeline.run                    # 실제: 수집→요약→이중 팩트체크→발행
  python -m pipeline.run --regions de kr    # 특정 지역만
옵션:
  --date 2026-07-25  --number 5

단계: ① 수집+선별(기자) → ③ 요약·해석(법률해설가) → ④⑤ 이중 팩트체크
      → ⑥ 게이트(발행/보류) → ⑦ 발행(사이트+아카이브). 보류분은 사람 검토 큐로.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from typing import List

import config
from schema import Candidate, NewsItem, FactVerdict, Issue


def _next_number() -> int:
    path = os.path.join(config.DATA_DIR, "index.json")
    if os.path.exists(path):
        idx = json.load(open(path, encoding="utf-8"))
        if idx:
            return max(e["number"] for e in idx) + 1
    return 5  # 데모 기본(제5호)


def run_real(date: str, number: int, regions: List[str]) -> Issue:
    from pipeline import collect, draft, gate
    print("① 수집 + ② 선별 (취재 기자)…")
    candidates: List[Candidate] = collect.collect(date, regions)
    print(f"   후보 {len(candidates)}건")

    print("③ 요약·해석 (법률 해설가)…")
    items: List[NewsItem] = [draft.draft_item(c) for c in candidates]

    print("④⑤ 이중 팩트체크 (팩트체커 A + B, 독립)…")
    items = [gate.evaluate(it) for it in items]

    published, held = gate.split(items)
    print(f"⑥ 게이트: 발행 {len(published)} · 보류 {len(held)}")
    return Issue(number=number, date=date, published=published, held=held)


def run_mock(date: str, number: int, regions: List[str]) -> Issue:
    """API 없이: 미리 준비한 뉴스로 발행 흐름만 재현."""
    raw = json.load(open(os.path.join(config.DATA_DIR, "sample_raw.json"), encoding="utf-8"))
    items: List[NewsItem] = []
    for d in raw:
        if regions and d["region"] not in regions:
            continue
        it = NewsItem(**d)
        # 합성 검증 로그(실서비스에선 팩트체커 A/B가 채움)
        v = FactVerdict(verdict="PASS", confidence=0.95, sources_count=2)
        it.check_a, it.check_b, it.verdict = v, v, "PASS"
        items.append(it)
    print(f"⑥ (mock) 발행 {len(items)}건 · 이중 팩트체크는 합성 통과")
    return Issue(number=number, date=date, published=items, held=[])


def _latest_number() -> int:
    idx = os.path.join(config.DATA_DIR, "index.json")
    if os.path.exists(idx):
        data = json.load(open(idx, encoding="utf-8"))
        if data:
            return max(e["number"] for e in data)
    raise SystemExit("발송할 호가 없습니다(index.json 비어있음)")


def _load_issue(number: int) -> Issue:
    path = os.path.join(config.DATA_DIR, f"issue-{number:04d}.json")
    return Issue(**json.load(open(path, encoding="utf-8")))


def main():
    ap = argparse.ArgumentParser(description="나침반 데일리 파이프라인")
    ap.add_argument("--mock", action="store_true", help="API 없이 샘플로 사이트 생성")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--number", type=int, default=None, help="발행 호수")
    ap.add_argument("--regions", nargs="*", default=None)
    ap.add_argument("--send", action="store_true", help="발행 후 이메일도 발송")
    ap.add_argument("--send-only", type=int, metavar="N",
                    help="빌드 없이 저장된 제N호를 이메일로만 발송(07:00 발송 잡용)")
    ap.add_argument("--send-latest", action="store_true",
                    help="빌드 없이 가장 최근 호를 이메일로만 발송")
    args = ap.parse_args()

    from pipeline import publish, notify

    # 07:00 발송 전용: 이미 만들어둔 호를 메일로만
    if args.send_only or args.send_latest:
        num = args.send_only or _latest_number()
        issue = _load_issue(num)
        print(f"=== 발송: 제{issue.number}호 · {issue.date} ===")
        notify.send(issue)
        return

    number = args.number or _next_number()
    regions = args.regions or config.REGION_ORDER

    print(f"=== 나침반 제{number}호 · {args.date} ({'mock' if args.mock else 'live'}) ===")
    issue = (run_mock if args.mock else run_real)(args.date, number, regions)
    out = publish.publish(issue)
    print(f"⑦ 발행 완료 → {out}")
    if issue.held:
        print(f"⚠️  보류 {len(issue.held)}건 → 편집장 검토 필요:")
        for it in issue.held:
            print(f"    - [{it.region}] {it.head} :: {'; '.join(it.check_notes)}")
    if args.send:
        notify.send(issue)


if __name__ == "__main__":
    main()
