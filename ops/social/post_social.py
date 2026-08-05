#!/usr/bin/env python3
"""인스타그램(캐러셀) + 스레드 자동 게시.

- site/social/manifest.json (make_social 이 만든 이미지 공개 URL·캡션)을 읽어 올린다.
- 토큰은 data/social_tokens.json 에서 읽는다(절대 커밋 금지). 없거나 비면 조용히 건너뛴다.
- 같은 날짜는 플랫폼별로 한 번만 올린다(data/social_posted.json 로 중복 방지).
- 실패는 예외로 올려 호출측(auto_publish)이 관리자에게만 알리게 한다.

수동:  python3 ops/social/post_social.py            # 오늘자 게시
       python3 ops/social/post_social.py --dry      # 실제 게시 없이 점검
       python3 ops/social/post_social.py --refresh  # 토큰만 갱신
"""
from __future__ import annotations
import json, os, sys, time, urllib.parse, urllib.request, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MANIFEST = os.path.join(ROOT, "site", "social", "manifest.json")
TOKENS = os.path.join(ROOT, "data", "social_tokens.json")
POSTED = os.path.join(ROOT, "data", "social_posted.json")

IG_API = "https://graph.facebook.com/v21.0"
TH_API = "https://graph.threads.net/v1.0"
TH_ROOT = "https://graph.threads.net"


def _req(url, params, method="POST"):
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        url = url + "?" + data.decode()
        req = urllib.request.Request(url, method="GET")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"{method} {url.split('?')[0]} → HTTP {e.code}: {body}") from None


def load(path, default):
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def _have(cfg, *keys):
    return cfg and all(cfg.get(k) for k in keys)


# ---------- 인스타그램 ----------
def ig_post(ig, image_urls, caption, dry=False):
    uid, tok = ig["user_id"], ig["access_token"]
    if dry:
        return f"[dry] IG 캐러셀 {len(image_urls)}장 게시 예정"
    children = []
    for u in image_urls[:10]:  # 캐러셀 최대 10장
        r = _req(f"{IG_API}/{uid}/media",
                 {"image_url": u, "is_carousel_item": "true", "access_token": tok})
        children.append(r["id"])
    car = _req(f"{IG_API}/{uid}/media",
               {"media_type": "CAROUSEL", "children": ",".join(children),
                "caption": caption, "access_token": tok})
    cid = car["id"]
    # 컨테이너가 준비될 때까지 잠깐 대기
    for _ in range(20):
        st = _req(f"{IG_API}/{cid}", {"fields": "status_code", "access_token": tok}, method="GET")
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            raise RuntimeError(f"IG 컨테이너 처리 오류: {st}")
        time.sleep(3)
    pub = _req(f"{IG_API}/{uid}/media_publish",
               {"creation_id": cid, "access_token": tok})
    return f"IG 게시 완료 id={pub.get('id')}"


# ---------- 스레드 ----------
def threads_post(th, image_url, text, dry=False):
    uid, tok = th["user_id"], th["access_token"]
    if dry:
        return "[dry] 스레드 이미지+텍스트 게시 예정"
    r = _req(f"{TH_API}/{uid}/threads",
             {"media_type": "IMAGE", "image_url": image_url, "text": text, "access_token": tok})
    cid = r["id"]
    time.sleep(10)  # 스레드는 게시 전 미디어 처리 시간이 필요
    pub = _req(f"{TH_API}/{uid}/threads_publish",
               {"creation_id": cid, "access_token": tok})
    return f"스레드 게시 완료 id={pub.get('id')}"


# ---------- 토큰 갱신 ----------
def refresh_tokens(log=print):
    cfg = load(TOKENS, {})
    changed = False
    th = cfg.get("threads")
    if _have(th, "access_token"):
        try:
            r = _req(f"{TH_ROOT}/refresh_access_token",
                     {"grant_type": "th_refresh_token", "access_token": th["access_token"]},
                     method="GET")
            if r.get("access_token"):
                th["access_token"] = r["access_token"]; changed = True
                log(f"스레드 토큰 갱신됨(만료 {r.get('expires_in','?')}초)")
        except Exception as e:
            log(f"스레드 토큰 갱신 실패: {e}")
    ig = cfg.get("instagram")
    if _have(ig, "access_token", "app_id", "app_secret"):
        try:
            r = _req(f"{IG_API}/oauth/access_token",
                     {"grant_type": "fb_exchange_token", "client_id": ig["app_id"],
                      "client_secret": ig["app_secret"], "fb_exchange_token": ig["access_token"]},
                     method="GET")
            if r.get("access_token"):
                ig["access_token"] = r["access_token"]; changed = True
                log("인스타 장기 토큰 갱신됨")
        except Exception as e:
            log(f"인스타 토큰 갱신 실패: {e}")
    if changed:
        cfg["_refreshed"] = dt.date.today().isoformat()
        json.dump(cfg, open(TOKENS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return changed


def _maybe_refresh(cfg, log):
    """마지막 갱신이 45일 넘었으면 갱신(토큰 만료 전 자동 연장)."""
    last = cfg.get("_refreshed")
    try:
        old = last and (dt.date.today() - dt.date.fromisoformat(last)).days >= 45
    except Exception:
        old = True
    if old:
        refresh_tokens(log)
        return load(TOKENS, cfg)
    return cfg


def run(dry=False, log=print):
    cfg = load(TOKENS, {})
    ig, th = cfg.get("instagram"), cfg.get("threads")
    if not (_have(ig, "user_id", "access_token") or _have(th, "user_id", "access_token")):
        log("소셜 토큰 없음 — 자동 게시 건너뜀(설정 전)")
        return
    if not os.path.exists(MANIFEST):
        raise RuntimeError("manifest.json 없음 — make_social 먼저 실행 필요")
    m = load(MANIFEST, {})
    date = m.get("date")
    posted = load(POSTED, {})
    day = posted.get(date, {})

    if not dry:
        cfg = _maybe_refresh(cfg, log)
        ig, th = cfg.get("instagram"), cfg.get("threads")

    results = []
    if _have(ig, "user_id", "access_token") and not day.get("instagram"):
        results.append(ig_post(ig, m["image_urls"], m["ig_caption"], dry))
        day["instagram"] = True
    elif day.get("instagram"):
        results.append("IG 이미 게시됨(건너뜀)")

    if _have(th, "user_id", "access_token") and not day.get("threads"):
        results.append(threads_post(th, m["image_urls"][0], m["threads_text"], dry))
        day["threads"] = True
    elif day.get("threads"):
        results.append("스레드 이미 게시됨(건너뜀)")

    if not dry:
        posted[date] = day
        json.dump(posted, open(POSTED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for r in results:
        log("  · " + r)


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh_tokens()
    else:
        run(dry="--dry" in sys.argv)
