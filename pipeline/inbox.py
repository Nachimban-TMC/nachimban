"""받은 것 확인 — 이메일 구독자와 편집팀에 온 의견.

사용:  python3 -m pipeline.inbox
키는 .env 의 PUSH_ADMIN_TOKEN 을 씁니다.
"""
from __future__ import annotations
import json
import os
import urllib.request

import config
from pipeline import env


def fetch() -> dict:
    env.load()
    token = os.getenv("PUSH_ADMIN_TOKEN")
    if not token:
        print("PUSH_ADMIN_TOKEN 이 없습니다 (.env 확인)")
        return {}
    url = config.SITE_URL.rstrip("/") + "/api/inbox"
    req = urllib.request.Request(url, headers={
        "x-admin-token": token, "User-Agent": "nachimban/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"조회 실패: {type(e).__name__}: {e}")
        return {}


def main() -> None:
    d = fetch()
    if not d:
        return
    print(f"\n📧 이메일 구독자 {d.get('subscriber_count', 0)}명")
    for e in d.get("subscribers", []):
        print(f"   · {e}")

    fb = d.get("feedback", [])
    print(f"\n💬 받은 의견 {len(fb)}건")
    for f in fb:
        when = (f.get("created_at") or "")[:16].replace("T", " ")
        print(f"\n   [{when}] {f.get('type', '')}")
        print(f"   {f.get('message', '')}")
        if f.get("email"):
            print(f"   ↩︎ 회신: {f['email']}")
    print()


if __name__ == "__main__":
    main()
