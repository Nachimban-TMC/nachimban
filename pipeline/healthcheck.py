"""사이트가 오늘자로 갱신됐는지 밖에서 확인한다.

파이프라인 안에 알림을 넣어도, 파이프라인이 '아예 실행되지 않으면'
그 알림도 울리지 않는다. 그래서 발행보다 늦은 시각에 이것만 따로 돌려
사이트를 직접 열어보고 확인한다.

사용:  python3 -m pipeline.healthcheck            # 오늘 기준
       python3 -m pipeline.healthcheck --quiet    # 정상이면 조용히
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import re
import sys
import urllib.request

import config
from pipeline import alert, env


def _fetch_latest_date() -> str | None:
    """배포된 사이트가 말하는 '최신 호 날짜'. 못 읽으면 None."""
    url = config.SITE_URL.rstrip("/") + "/archive-data.json"
    req = urllib.request.Request(url, headers={
        "User-Agent": "nachimban-healthcheck/1.0", "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode())
        issues = d.get("issues") or []
        return issues[0].get("d") if issues else None
    except Exception:  # noqa: BLE001
        pass
    # 데이터 파일을 못 읽으면 대문 HTML 에서 날짜를 찾아본다
    try:
        req = urllib.request.Request(config.SITE_URL,
                                     headers={"User-Agent": "nachimban-healthcheck/1.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            html = r.read().decode("utf-8", "replace")
        m = re.search(r"(\d{4})\.\s*(\d{2})\.\s*(\d{2})\s*·\s*AM", html)
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="발행 여부 확인")
    ap.add_argument("--date", default=None, help="기대 날짜(기본: 오늘)")
    ap.add_argument("--quiet", action="store_true", help="정상이면 출력하지 않음")
    ap.add_argument("--no-alert", action="store_true", help="확인만, 알림 없음")
    args = ap.parse_args()
    env.load()

    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    # 주말은 발행하지 않는다(예약 작업이 평일만 돈다)
    if today.weekday() >= 5:
        if not args.quiet:
            print(f"✅ {today} 는 주말 — 발행 대상 아님")
        return 0

    expected = today.isoformat()
    latest = _fetch_latest_date()

    if latest == expected:
        if not args.quiet:
            print(f"✅ 정상 — 사이트 최신 호가 {latest} 입니다")
        return 0

    print(f"🚨 오늘자 브리핑이 확인되지 않습니다")
    print(f"   기대: {expected}   사이트: {latest or '읽지 못함'}")
    if not args.no_alert:
        alert.stale(latest or "", expected)
    return 1


if __name__ == "__main__":
    sys.exit(main())
