"""초안 점검 — 발행 세션이 저장 직후 스스로 돌려보는 검사기(읽기 전용).

왜 만들었나:
  SKILL 에 규칙을 적어도 중복·재탕이 계속 샜다(2026-09-15 확인: 금리 7개 호 연속,
  브리 치즈 리콜 제37→42호 재탕 등). 원인은 두 가지였다.
    1) 세션이 최근 4개 호만 봤다 → 5~6일 뒤 같은 기사가 돌아왔다.
    2) 예전 감지기는 초안이 다 쓰인 뒤 로그에만 남겼다 → 쓰는 쪽은 경고를 못 봤다.
  그래서 '쓰는 단계'에서 세션이 직접 돌리고, 걸리면 고쳐서 다시 저장하게 한다.

사용:
  python3 -m pipeline.draft_check recent        # 조사 시작 전: 최근 10개 호 + 이미 반복된 주제
  python3 -m pipeline.draft_check               # 저장 후: data/today-draft.json 점검
  python3 -m pipeline.draft_check --issue 43    # 과거 호를 초안처럼 점검(기준값 검증용)

파일을 쓰지 않는다. 무인 세션의 Bash 승인 대기를 피하기 위해서다.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import config  # noqa: E402
from pipeline import sanitize  # noqa: E402

LOOKBACK = 10          # 재탕 비교 범위(호). 4개 호로는 5~6일 뒤 재탕을 못 막았다.
SERIES_WINDOW = 7      # 연속 게재를 세는 범위(호)
DUP = 0.35             # 이 이상이면 같은 기사일 가능성이 높다
RELATED = 0.25         # 이 이상이면 같은 주제로 센다
# 기준값 근거(2026-09-16, 제35~44호 실측): 실제 재탕 쌍은 0.35~1.06점
# (107조 1.06, FBAR 0.62, H-1B·L-1 0.56, 브리 치즈 0.53, 독감 0.39, 유학비자 0.37),
# 서로 다른 기사끼리는 대부분 0.25 아래였다. 0.40 으로 두면 독감(0.39)을 놓쳤다.
# 못 잡는 경우: 제목 표현이 크게 다른 같은 사안(연방강제 제40·41호, 0.2 미만).

# ── 유사도 ────────────────────────────────────────────────
# 낱말 비교는 '브리치즈'/'브리 치즈'처럼 띄어쓰기·조사가 바뀌면 놓친다.
# 글자 두 개씩 끊은 조각(bigram)으로 비교해 표기 차이를 흡수한다.
_ENDINGS = {"습니", "니다", "합니", "됩니", "입니", "했습", "있습", "였습", "었습",
            "았습", "겠습", "봅니", "옵니", "집니"}
_NUM_RE = re.compile(r"\d[\d,.]*")


def _norm(s: str) -> str:
    return re.sub(r"[^가-힣A-Za-z0-9]", "", s or "")


def _bigrams(s: str) -> set:
    t = _norm(s)
    return {t[i:i + 2] for i in range(len(t) - 1)} - _ENDINGS


def _nums(s: str) -> set:
    """107, 4500, 3.3 처럼 기사를 특정하는 수치. 연도·한두 자리 수는 흔해서 뺀다."""
    out = set()
    for m in _NUM_RE.findall(s or ""):
        v = m.replace(",", "").rstrip(".")
        if v in {"2025", "2026", "2027"}:
            continue
        if len(v.replace(".", "")) >= 3 or "." in v:
            out.add(v)
    return out


def _jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def similarity(a: dict, b: dict) -> float:
    """두 기사가 같은 사안일 가능성(대략 0~1.3)."""
    h = _jac(_bigrams(a.get("head", "")), _bigrams(b.get("head", "")))
    d = _jac(_bigrams(a.get("desc", "")), _bigrams(b.get("desc", "")))
    n = len(_nums(a.get("head", "") + " " + a.get("desc", ""))
            & _nums(b.get("head", "") + " " + b.get("desc", "")))
    return max(h, d) + 0.1 * min(n, 3)


# ── 데이터 ────────────────────────────────────────────────
def load_issues() -> dict:
    out = {}
    for f in glob.glob(os.path.join(REPO, "data", "issue-*.json")):
        d = json.load(open(f, encoding="utf-8"))
        out[d["number"]] = d
    return out


def _past(issues: dict, before: int, n: int) -> list:
    nums = sorted(k for k in issues if k < before)[-n:]
    return [issues[k] for k in nums]


# ── 규칙 ──────────────────────────────────────────────────
_MARKET = re.compile(r"코스피|코스닥|환율|증시|뉴욕증시|다우|나스닥|금리|FOMC|ECB|연준|국채|유가")
_SPORTS = re.compile(r"우승|결승|리그|월드컵|올림픽|US오픈|그랜드슬램|국가대표|감독 선임")
_INCIDENT = re.compile(r"전복|추락|사망|실종|화재|총격|흉기|살해|체포|구속|송치|뇌물|폭발|붕괴 사고")
_FEUD = re.compile(r"사퇴|후보자|청문회|원내대표|탄핵|공천|대정부질문|개헌")
_PRACTICAL = {"life", "health", "housing", "travel", "tax", "welfare", "labor",
              "education", "study", "visa", "immigration", "pension", "citizenship"}


def review(items: list, past: list) -> tuple[list, list]:
    """(고쳐야 할 것, 판단이 필요한 것) 두 목록을 돌려준다."""
    errors, warns = [], []

    # 1) 카드 규격 — 넘으면 화면에서 잘린다
    for it in items:
        tag = "[%s] %s" % (it.get("region"), it.get("head"))
        for f in ("head", "desc", "interp", "source"):
            h = sanitize.find_hanja(it.get(f) or "")
            if h:
                errors.append("%s — 한자 %s (%s)" % (tag, "".join(h), f))
        if len(it.get("head", "")) > 25:
            errors.append("%s — 제목 %d자(25자 이내)" % (tag, len(it["head"])))
        L = len(it.get("desc", ""))
        if L > 100:
            errors.append("%s — desc %d자(100자 넘으면 잘림)" % (tag, L))
        elif L < 85:
            warns.append("%s — desc %d자로 짧음(90~100자 권장)" % (tag, L))
        P = len(re.sub(r"</?b>", "", it.get("interp", "")))
        if P > 78:
            errors.append("%s — interp %d자(78자 이내)" % (tag, P))
        for f in ("desc", "interp"):
            txt = (it.get(f) or "").strip()
            if not txt.endswith("."):
                errors.append("%s — %s 문장이 끝맺어지지 않음" % (tag, f))
            for sent in re.split(r"(?<=\.)\s*", txt):
                s = sent.rstrip(". ")
                if s.endswith("다") and not s.endswith("니다"):
                    errors.append("%s — %s 기사체 문장: …%s" % (tag, f, s[-12:]))
                    break
        for t in it.get("terms") or []:
            if t.get("term", "") not in it.get("desc", ""):
                errors.append("%s — 용어 '%s' 가 desc 에 없음" % (tag, t.get("term")))
            if re.search(r"(니다|습니다)\.?$", t.get("explain", "")):
                errors.append("%s — 용어 풀이 '%s' 는 명사로 끝내기" % (tag, t.get("term")))

    # 2) 재탕 · 연속 게재 — 최근 10개 호와 비교
    for it in items:
        tag = "[%s] %s" % (it.get("region"), it.get("head"))
        best = None
        for iss in past:
            for old in iss["published"]:
                s = similarity(it, old)
                if not best or s > best[0]:
                    best = (s, iss["number"], old["head"])
        if best and best[0] >= DUP:
            warns.append("%s — 재탕 의심: 제%d호 '%s' (유사도 %.2f). 새 진전이 없으면 빼세요"
                         % (tag, best[1], best[2], best[0]))
        series = [iss["number"] for iss in past[-SERIES_WINDOW:]
                  if any(similarity(it, old) >= RELATED for old in iss["published"])]
        if len(series) >= 2:
            warns.append("%s — 최근 %d개 호 중 %d개 호에 같은 주제(제%s호). 3번째는 결정적 전환일 때만"
                         % (tag, SERIES_WINDOW, len(series), "·".join(map(str, series))))

    # 3) 한 주제는 한 호에 한 장
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            # 0.30 이면 '규정, 15일 시행'처럼 틀만 같은 다른 기사까지 묶였다(제37호)
            if similarity(a, b) >= 0.35:
                warns.append("한 호에 같은 주제 두 장: '%s' / '%s'" % (a["head"], b["head"]))
    market = [it for it in items if _MARKET.search(it.get("head", ""))]
    # 시황 카드끼리는 문장 틀이 비슷해 기준을 낮춰 본다(제44호 한국·미국 '국채금리' 두 장)
    for i, a in enumerate(market):
        for b in market[i + 1:]:
            if a["region"] != b["region"] and 0.25 <= similarity(a, b) < 0.35:
                warns.append("같은 시황 흐름 두 장: '%s' / '%s' — 한 섹션에만" % (a["head"], b["head"]))
    if len({it["region"] for it in market}) >= 3:
        warns.append("금리·증시·유가 카드가 %d개 섹션에 흩어짐: %s — 같은 날 같은 흐름이면 한 장으로"
                     % (len({it['region'] for it in market}), ", ".join(it["head"] for it in market)))
    for it in market:
        if it.get("region") == "kr":
            warns.append("[kr] %s — 한국 시황은 큰 변동(지수 ±2%%·환율 연중 최고/최저)일 때만" % it["head"])

    # 4) 금지 항목이 새지 않았나
    for it in items:
        tag = "[%s] %s" % (it.get("region"), it.get("head"))
        text = it.get("head", "") + " " + it.get("desc", "")
        if _SPORTS.search(text):
            warns.append("%s — 스포츠로 보임. 재외한인에게 의미가 있는지 확인" % tag)
        if _INCIDENT.search(it.get("head", "")):
            warns.append("%s — 사건·사고로 보임. 1면급이거나 독자 행동 지침이 있을 때만" % tag)
        if _FEUD.search(it.get("head", "")):
            warns.append("%s — 정쟁으로 보임. 해외 거주자에게 할 일이 없으면 빼세요" % tag)

    # 5) 구성
    for r, meta in config.REGIONS.items():
        mine = [it for it in items if it.get("region") == r]
        if len(mine) < meta.get("count", 0):
            warns.append("%s %d건 (기준 %d건) — 실생활 뉴스로 더 채울 수 있는지 확인"
                         % (meta["short"], len(mine), meta["count"]))
        if mine and not any(it.get("category") == "general" for it in mine):
            errors.append("%s 에 주요뉴스(general)가 없음" % meta["short"])
        if mine and sum(1 for it in mine if it.get("hot")) != 1:
            errors.append("%s 의 hot 이 %d건(지역당 1건)" % (meta["short"], sum(1 for it in mine if it.get("hot"))))
    de_prac = [it for it in items if it.get("region") == "de" and it.get("category") in _PRACTICAL]
    if len(de_prac) < 3:
        warns.append("독일 실생활 후보 %d건(3건 필요)" % len(de_prac))
    fin = [it for it in items if it.get("region") in ("eu", "us") and it.get("category") in ("stocks", "invest", "crypto")]
    if not any(it["region"] == "eu" for it in fin):
        warns.append("EU 주식·투자 카드가 없음(상돈님 요청: EU·미국 주식 1~2꼭지)")
    if not any(it["region"] == "us" for it in fin):
        warns.append("미국 주식·투자 카드가 없음(상돈님 요청: EU·미국 주식 1~2꼭지)")

    return errors, warns


# ── 출력 ──────────────────────────────────────────────────
def print_recent(issues: dict) -> None:
    last = max(issues)
    past = _past(issues, last + 1, LOOKBACK)
    for iss in past:
        print("제%d호 %s" % (iss["number"], iss["date"]))
        for it in iss["published"]:
            print("  [%s] %s" % (it["region"], it["head"]))
    # 이미 두 개 호 이상 실린 주제 — 오늘 새 진전이 없으면 싣지 않는다
    items = [(iss["number"], it) for iss in past[-SERIES_WINDOW:] for it in iss["published"]]
    groups: list[list] = []
    for num, it in items:
        for g in groups:
            if any(n != num and similarity(it, o) >= 0.35 for n, o in g):
                g.append((num, it))
                break
        else:
            groups.append([(num, it)])
    repeated = [g for g in groups if len({n for n, _ in g}) >= 2]
    print("\n⛔ 최근 %d개 호에 이미 2번 이상 실린 주제 — 오늘 결정적 전환이 없으면 싣지 마세요" % SERIES_WINDOW)
    for g in sorted(repeated, key=lambda g: -len({n for n, _ in g})):
        nums = sorted({n for n, _ in g})
        print("  · %s  (제%s호)" % (g[-1][1]["head"], "·".join(map(str, nums))))


def main(argv: list) -> int:
    issues = load_issues()
    if argv and argv[0] == "recent":
        print_recent(issues)
        return 0
    if len(argv) >= 2 and argv[0] == "--issue":
        n = int(argv[1])
        items, past = issues[n]["published"], _past(issues, n, LOOKBACK)
        print("제%d호를 초안처럼 점검 (비교: 제%d~%d호)" % (n, past[0]["number"], past[-1]["number"]))
    else:
        path = os.path.join(REPO, "data", "today-draft.json")
        if not os.path.exists(path):
            print("초안(data/today-draft.json)이 없습니다.")
            return 1
        items = json.load(open(path, encoding="utf-8")).get("items") or []
        past = _past(issues, max(issues) + 1, LOOKBACK)
    errors, warns = review(items, past)
    print("총 %d건" % len(items))
    print("\n❌ 고쳐야 할 것 %d건" % len(errors))
    for e in errors:
        print("  - " + e)
    print("\n⚠️ 판단이 필요한 것 %d건" % len(warns))
    for w in warns:
        print("  - " + w)
    print("\n" + ("✅ 규격 통과 — 경고 항목은 하나씩 판단해 고치거나 유지 사유를 보고에 적으세요"
                  if not errors else "❌ 고친 뒤 Write 로 다시 저장하고 이 점검을 다시 돌리세요"))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
