"""프로젝트 루트의 .env 를 읽어 환경변수로 올린다 (외부 패키지 없이).

이렇게 하면 예약작업이 자동 실행될 때도 키를 찾을 수 있다.
이미 환경변수로 지정된 값은 덮어쓰지 않는다(명령줄 우선).
"""
from __future__ import annotations
import os

_LOADED = False


def load() -> None:
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(path):
        return
    try:
        for raw in open(path, encoding="utf-8"):
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            # 따옴표로 감싼 값 허용
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            if k and k not in os.environ:      # 이미 있으면 유지
                os.environ[k] = v
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠️  .env 읽기 실패: {e}")
