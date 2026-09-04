"""발행 전 자동 정리 — 지시만으로는 반복해서 새는 것을 코드로 막는다.

한자(신문식 약칭)는 SKILL 에서 금지했는데도 여러 호에서 다시 나타났다
(제5호 獨·美·檢, 제27호 美, 제32호 美·發·差). 그래서 발행 파이프라인에서
기계적으로 치환한다. 매핑에 없는 한자가 남으면 호출측이 알 수 있게 함께 반환한다.
"""
from __future__ import annotations
import re

# 신문식 한 글자 약칭 → 평범한 한글
HANJA = {
    # 나라·지역
    "美": "미국", "獨": "독일", "中": "중국", "日": "일본", "韓": "한국",
    "北": "북한", "英": "영국", "佛": "프랑스", "露": "러시아", "伊": "이탈리아",
    "濠": "호주", "印": "인도", "蘭": "네덜란드", "墺": "오스트리아", "瑞": "스위스",
    "波": "폴란드", "越": "베트남", "泰": "태국", "比": "필리핀", "加": "캐나다",
    "歐": "유럽", "亞": "아시아", "臺": "대만", "濠洲": "호주",
    # 정치·기관
    "與": "여당", "野": "야당", "靑": "대통령실", "檢": "검찰", "警": "경찰",
    "軍": "군", "政": "정부", "靑瓦臺": "대통령실", "與野": "여야",
    # 경제
    "銀": "은행", "株": "주식", "證": "증권", "弗": "달러", "元": "위안",
    # 접미·접두로 붙는 것
    "發": "발", "差": "차이", "增": "증가", "減": "감소", "級": "급",
    "前": "전", "後": "후", "新": "신", "舊": "구", "行": "행",
}

# 한글(AC00-D7A3)은 제외하고 CJK 표의문자만
_HAN_RE = re.compile("[㐀-䶿一-鿿豈-﫿]")
_FIELDS = ("head", "desc", "interp", "source")


def clean_text(s: str) -> str:
    if not s:
        return s
    for k in sorted(HANJA, key=len, reverse=True):   # 긴 것부터
        if k in s:
            s = s.replace(k, HANJA[k])
    return s


def find_hanja(s: str) -> list:
    return _HAN_RE.findall(s or "")


def clean_items(items: list) -> tuple:
    """items(dict 리스트)의 텍스트에서 한자를 치환한다.
    반환: (치환한 개수, 매핑에 없어 남은 한자 목록)"""
    replaced, leftover = 0, []
    for idx, it in enumerate(items):
        for f in _FIELDS:
            v = it.get(f)
            if not isinstance(v, str) or not v:
                continue
            if find_hanja(v):
                new = clean_text(v)
                if new != v:
                    replaced += 1
                    it[f] = new
                rest = find_hanja(it[f])
                if rest:
                    leftover.append({"index": idx, "field": f,
                                     "chars": "".join(sorted(set(rest))),
                                     "text": it[f][:60]})
        for t in it.get("terms") or []:
            for tf in ("term", "explain"):
                if isinstance(t.get(tf), str) and find_hanja(t[tf]):
                    t[tf] = clean_text(t[tf])
                    replaced += 1
    return replaced, leftover


# ── 중복(연속 게재) 감지 ────────────────────────────────────────────────────
# 같은 사안이 며칠씩 이어지는 문제가 반복됐다(2026-09-04 지적: 작센안할트 선거
# 4개 호, 경산 유학생 살해 5개 호). SKILL 에 규칙을 넣어도 새므로, 발행 때
# 기계적으로 세어 로그에 남긴다. 발행을 막지는 않는다(오탐으로 결호 나면 더 나쁨).

_STOP = {"오늘", "내일", "올해", "내년", "이번", "관련", "정부", "발표", "확대", "추진",
         "검토", "시행", "인상", "하락", "상승", "논의", "예상", "전망", "위해", "대한"}


def _keywords(text: str) -> set:
    """제목에서 의미 있는 낱말만 뽑는다(2글자 이상 한글/영문/숫자)."""
    words = re.findall(r"[가-힣A-Za-z][가-힣A-Za-z0-9]{1,}", text or "")
    return {w for w in words if len(w) >= 2 and w not in _STOP}


def find_repeats(items: list, past_issues: list, min_overlap: int = 2) -> list:
    """past_issues(최근 호들의 published 목록)와 겹치는 항목을 찾는다.
    반환: [{'head', 'seen_in': [(호수, 날짜, 옛제목), ...]}, ...]"""
    out = []
    for it in items:
        kws = _keywords(it.get("head", ""))
        if len(kws) < 2:
            continue
        seen = []
        for num, date, heads in past_issues:
            for h in heads:
                if len(kws & _keywords(h)) >= min_overlap:
                    seen.append((num, date, h))
                    break
        if len(seen) >= 2:            # 2개 호 이상에서 반복 → 3번째이므로 경고
            out.append({"head": it.get("head", ""), "seen_in": seen})
    return out
