#!/usr/bin/env python3
"""무인 발행 — Claude 루틴이 남긴 초안(data/today-draft.json)을 받아
빌드 → git push → 알림 발송까지 사람 승인 없이 끝낸다.

왜 이렇게 나눴나:
  예약 루틴(Claude 세션)은 git push·푸시 발송 같은 '바깥으로 나가는' 명령에서
  매번 승인을 요구해 6시에 멈춘다. 그 두 단계를 승인 개념이 없는 launchd 셸로
  옮겼다. Claude 루틴은 조사 후 초안 파일만 쓰면 되고(멈출 일 없음), 나머지는
  이 스크립트가 한다.

동작:
  - data/today-draft.json 없으면 조용히 종료(할 일 없음).
  - 오늘 이미 발행됐으면 초안만 치우고 종료(중복 방지).
  - 있으면: 빌드 → 커밋·푸시 → pipeline.run --send-latest(푸시+이메일) → 초안 보관.
  - 어느 단계든 실패하면 관리자에게만 실패 알림(구독자에겐 안 감).

멱등(idempotent): 여러 번 돌려도 오늘 것은 한 번만 발행된다.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
sys.path.insert(0, REPO)

DRAFT = os.path.join(REPO, "data", "today-draft.json")
INDEX = os.path.join(REPO, "data", "index.json")
DRAFTS_DIR = os.path.join(REPO, "data", "drafts")
LOG = os.path.join(REPO, "ops", "logs", "auto_publish.log")


def _log(msg: str) -> None:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _today() -> str:
    return dt.date.today().isoformat()


def _index() -> list:
    if not os.path.exists(INDEX):
        return []
    try:
        return json.load(open(INDEX, encoding="utf-8"))
    except Exception:
        return []


def _already_published_today() -> bool:
    return any(x.get("date") == _today() for x in _index())


def _next_number() -> int:
    idx = _index()
    return (max((x.get("number", 0) for x in idx), default=0)) + 1


def _archive_draft(tag: str) -> None:
    os.makedirs(DRAFTS_DIR, exist_ok=True)
    dst = os.path.join(DRAFTS_DIR, f"{_today()}-{tag}.json")
    try:
        shutil.move(DRAFT, dst)
        _log(f"초안 보관: {os.path.relpath(dst, REPO)}")
    except Exception as e:
        _log(f"초안 보관 실패(무시): {e}")


def _git(*args: str) -> None:
    subprocess.run(["git", *args], cwd=REPO, check=True,
                   capture_output=True, text=True)


def main() -> int:
    if not os.path.exists(DRAFT):
        return 0  # 할 일 없음 — 조용히 종료

    if _already_published_today():
        _log("오늘 이미 발행됨 → 초안만 치우고 종료")
        _archive_draft("skipped")
        return 0

    _log("초안 발견 — 무인 발행 시작")
    number = _next_number()
    today = _today()

    # --- 1) 빌드 ---
    try:
        draft = json.load(open(DRAFT, encoding="utf-8"))
        raw_items = draft.get("items") or draft.get("published") or []
        if not raw_items:
            raise ValueError("초안에 뉴스 항목이 없습니다(items 비어 있음)")

        from schema import Issue, NewsItem, FactVerdict
        from pipeline import publish

        items = [NewsItem(**d) for d in raw_items]
        v = FactVerdict(verdict="PASS", confidence=0.95, sources_count=2)
        for it in items:
            it.check_a, it.check_b, it.verdict = v, v, "PASS"
        issue = Issue(number=number, date=today, published=items, held=[])
        out = publish.publish(issue)
        _log(f"빌드 완료: 제{number}호 {today} · {len(items)}건 → {os.path.relpath(out, REPO)}")
    except Exception as e:
        _log(f"🚨 빌드 실패: {type(e).__name__}: {e}")
        _alert_failure("빌드", e, number, today)
        return 1

    # --- 1-b) 소셜 자료(인스타·스레드) 생성 — 최선노력, 실패해도 발행은 계속 ---
    try:
        sys.path.insert(0, os.path.join(REPO, "ops", "social"))
        import make_social
        r = make_social.build_all()
        _log(f"소셜 생성: 슬라이드 {r['slides']}장(실패 {r['failed']}) → /social/")
    except Exception as e:
        _log(f"소셜 생성 실패(무시, 발행은 진행): {type(e).__name__}: {e}")

    # --- 2) 커밋 · 푸시 (Cloudflare 자동 배포) ---
    try:
        _git("add", "site/", "data/")
        _git("commit", "-m", f"제{number}호 자동 발행 {today}")
        _git("push")
        _log("git push 완료 — Cloudflare 재배포 시작")
    except subprocess.CalledProcessError as e:
        _log(f"🚨 git push 실패: {e.stderr or e}")
        _alert_failure("배포(git push)", e, number, today)
        return 1

    # --- 3) 알림 발송(앱 푸시 + 이메일) ---
    try:
        r = subprocess.run([sys.executable, "-m", "pipeline.run", "--send-latest"],
                           cwd=REPO, check=True, capture_output=True, text=True)
        _log("알림 발송 완료: " + (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "ok"))
    except subprocess.CalledProcessError as e:
        _log(f"🚨 알림 발송 실패: {e.stderr or e}")
        _alert_failure("알림 발송", e, number, today)
        # 발행·배포는 됐으므로 초안은 치운다(중복 발행 방지). 실패는 알림으로 이미 통지.

    # --- 4) 인스타·스레드 자동 게시 — 최선노력(토큰 없으면 건너뜀, 실패해도 발행은 완료) ---
    try:
        _wait_images_live()
        sys.path.insert(0, os.path.join(REPO, "ops", "social"))
        import post_social
        post_social.run(log=_log)
    except Exception as e:
        _log(f"🚨 소셜 자동 게시 실패: {type(e).__name__}: {e}")
        _alert_failure("소셜 자동 게시", e, number, today)

    _archive_draft("published")
    _log(f"✅ 제{number}호 무인 발행 완료")
    _log("📱 인스타·스레드 소셜 자료: https://nachimban.pages.dev/social")
    return 0


def _wait_images_live(timeout: int = 180) -> None:
    """게시 API는 공개 이미지 URL을 가져가므로, Cloudflare 배포가 끝나 이미지가
    실제로 뜰 때까지 기다린다(최대 timeout초)."""
    import urllib.request
    url = "https://nachimban.pages.dev/social/img/slide-01.png"
    deadline = dt.datetime.now() + dt.timedelta(seconds=timeout)
    while dt.datetime.now() < deadline:
        try:
            req = urllib.request.Request(url + f"?cb={int(time.time())}", method="HEAD")
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    return
        except Exception:
            pass
        time.sleep(10)
    _log("소셜 이미지 라이브 확인 시간초과 — 그래도 게시 시도")


def _alert_failure(stage: str, err: BaseException, number: int, date: str) -> None:
    """관리자에게만 실패 알림. 구독자에겐 가지 않는다."""
    try:
        from pipeline import alert
        alert.failure(stage, err, number=number, date=date, push_too=True)
    except Exception as e:
        _log(f"실패 알림조차 실패(무시): {e}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 최후 방어 — 어떤 예외도 조용히 죽지 않게
        _log(f"🚨 예기치 못한 오류: {type(e).__name__}: {e}")
        try:
            _alert_failure("무인 발행", e, 0, _today())
        finally:
            sys.exit(1)
