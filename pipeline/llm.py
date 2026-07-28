"""Claude 호출 헬퍼 (Anthropic 공식 SDK).

- structured(): 웹 검색이 필요 없는 단계 → messages.parse 로 스키마 강제
- research(): 웹 검색이 필요한 단계 → web_search/web_fetch 서버툴 사용 후 JSON 추출

기본 모델은 claude-opus-4-8. 팩트체커 B만 독립성을 위해 다른 모델(sonnet-5)을 씀.
자세한 SDK 사용법은 /claude-api 스킬 기준.
"""
from __future__ import annotations
import json
import re
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

_client = None
T = TypeVar("T", bound=BaseModel)

# ── 사용량 측정 ──────────────────────────────────────────────────
# 클라우드로 옮기면 이 호출들이 API 종량 과금이 된다. 옮길지 결정하려면
# 추정이 아니라 실측이 필요해서, 호출마다 토큰을 기록해 둔다.
# 2026-06-24 기준 단가($/백만 토큰). 캐시 읽기는 입력가의 약 1/10.
PRICES = {
    "claude-opus-5":    (5.0, 25.0),
    "claude-opus-4-8":  (5.0, 25.0),
    "claude-sonnet-5":  (3.0, 15.0),
    "claude-haiku-4-5": (1.0,  5.0),
}
USAGE: list[dict] = []


def _record(stage: str, model: str, usage) -> None:
    if usage is None:
        return
    USAGE.append({
        "stage": stage,
        "model": model,
        "in": getattr(usage, "input_tokens", 0) or 0,
        "out": getattr(usage, "output_tokens", 0) or 0,
        "cache_write": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read": getattr(usage, "cache_read_input_tokens", 0) or 0,
    })


def cost_report() -> str:
    """이번 실행이 API 종량제였다면 얼마였을지."""
    if not USAGE:
        return "   💰 사용량 기록 없음"
    by_stage: dict[str, list[int]] = {}
    total = 0.0
    for u in USAGE:
        pin, pout = PRICES.get(u["model"], (5.0, 25.0))
        c = ((u["in"] + u["cache_write"] * 1.25 + u["cache_read"] * 0.1) * pin
             + u["out"] * pout) / 1_000_000
        total += c
        s = by_stage.setdefault(u["stage"], [0, 0, 0, 0.0])
        s[0] += 1
        s[1] += u["in"] + u["cache_read"] + u["cache_write"]
        s[2] += u["out"]
        s[3] += c
    lines = ["", "   ── API 종량제 환산 (실제로는 구독으로 무료) ──"]
    for st, (n, i, o, c) in sorted(by_stage.items(), key=lambda x: -x[1][3]):
        lines.append(f"   {st:12} {n:3}회  입력 {i/1000:7.1f}K  출력 {o/1000:6.1f}K  ${c:6.3f}")
    lines.append(f"   {'합계':12} {len(USAGE):3}회{'':28}${total:6.3f}")
    lines.append(f"   → 평일만 발행 시 월 예상: 약 ${total*21:.0f}"
                 f"  (웹 검색 요금 별도)")
    return "\n".join(lines)


def client() -> "anthropic.Anthropic":
    """지연 초기화된 싱글턴 클라이언트. ANTHROPIC_API_KEY(또는 ant 프로필) 사용."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def structured(system: str, user: str, schema: Type[T], model: str,
               max_tokens: int = 4000, stage: str = "structured") -> T:
    """스키마에 맞춘 구조화 출력. 웹 검색 없음."""
    resp = client().messages.parse(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=schema,
    )
    _record(stage, model, getattr(resp, "usage", None))
    if resp.parsed_output is None:
        raise RuntimeError(f"구조화 출력 파싱 실패 (stop={resp.stop_reason})")
    return resp.parsed_output


def research(system: str, user: str, model: str, max_tokens: int = 8000,
             stage: str = "research") -> dict:
    """web_search / web_fetch 를 써서 실제로 조사한 뒤, 마지막에 낸
    ```json 블록을 파싱해 dict 로 돌려줌. pause_turn 을 처리하는 수동 루프."""
    tools = [
        {"type": "web_search_20260209", "name": "web_search", "max_uses": 8},
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 8},
    ]
    messages = [{"role": "user", "content": user}]
    for _ in range(12):  # 서버툴 반복/일시정지 대비 상한
        resp = client().messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            system=system,
            tools=tools,
            messages=messages,
        )
        _record(stage, model, getattr(resp, "usage", None))
        if resp.stop_reason == "pause_turn":
            # 서버툴 루프 한도 도달 → 이어서 재요청
            messages.append({"role": "assistant", "content": resp.content})
            continue
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        return _extract_json(text)
    raise RuntimeError("research: 반복 상한 도달")


def _extract_json(text: str) -> dict:
    """텍스트에서 ```json … ``` 또는 첫 번째 JSON 객체를 뽑아 파싱."""
    m = re.search(r"```json\s*(.+?)```", text, re.S)
    if m:
        return json.loads(m.group(1))
    m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
    if m:
        return json.loads(m.group(1))
    raise ValueError("응답에서 JSON 을 찾지 못함:\n" + text[:500])
