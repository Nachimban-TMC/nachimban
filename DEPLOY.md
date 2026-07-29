# 나침반 — 배포와 자동 운영

## 전체 그림

```
Mac Studio (독일 자택, 24시간 가동)
  └ Claude 앱 예약 작업
      06:00  취재 → 팩트체크 → site/ 갱신 → git push
      07:00  구독자에게 앱 푸시(+메일)
  └ launchd / pmset
      05:50  맥 자동 기상 (잠자기·전원꺼짐 모두 복구)
      06:30  발행 확인 — 실패 시 관리자에게만 알림 (토큰 안 듦)
      5분마다 Claude 앱 생존 확인, 죽으면 재실행

GitHub (Nachimban-TMC/nachimban)
  └(push)─▶ Cloudflare Pages ─▶ https://nachimban.pages.dev
```

**호스팅은 Cloudflare Pages입니다.** 예전에 Netlify를 썼지만 무료 배포 한도가
나흘 만에 소진돼 옮겼습니다(2026-07-28). 배포는 하루 한 번으로 모읍니다.

**취재는 Claude 구독으로 돌아갑니다 — API 종량 과금이 아닙니다.**
`.github/workflows/` 의 GitHub Actions 는 비활성 상태로 남겨둔 것이며,
클라우드로 옮길 때만 쓰입니다(그때는 `ANTHROPIC_API_KEY` 과금이 발생).

---

## 구성 요소

| 위치 | 역할 |
|---|---|
| `pipeline/` | 취재·초안·팩트체크·발행·발송·헬스체크 코드 |
| `site/` | 배포되는 정적 사이트 (Pages 의 publish directory) |
| `functions/api/*.js` | Cloudflare Pages Functions — 구독·피드백·푸시 저장(KV) |
| `data/` | 호별 데이터와 아카이브 인덱스 |
| `ops/` | 무인 운영 스크립트 + 발행 지시서 사본 |

---

## 키와 비밀값

**절대 커밋하지 않습니다** (`.gitignore` 로 제외):

| 파일 | 내용 |
|---|---|
| `.env` | `PUSH_ADMIN_TOKEN`, `RESEND_API_KEY`, `NB_ADMIN_PUSH` |
| `data/vapid.json` | 웹 푸시 개인키 |
| `data/subscribers.txt` | 구독자 이메일 |

Cloudflare 쪽은 **Pages 프로젝트 → Settings** 에서 환경변수 `PUSH_ADMIN_TOKEN`
과 KV 바인딩 `NB_KV` 를 등록합니다.

> 키는 직접 입력하세요. 채팅에 붙여넣지 마세요.
> `NB_ADMIN_PUSH` 는 사고 알림을 받을 **관리자 기기**의 푸시 엔드포인트 일부입니다.
> 비어 있으면 푸시를 보내지 않고 메일로만 알립니다(구독자 오발송 방지).

---

## 자주 쓰는 명령

```bash
# 발행 여부 확인 (토큰 안 듦)
cd ~/nachimban && python3 -m pipeline.healthcheck

# 이미 만든 최신 호를 다시 발송 (푸시 + 메일)
cd ~/nachimban && python3 -m pipeline.run --send-latest

# 구독자·받은 의견 확인
cd ~/nachimban && python3 -m pipeline.inbox
```

`git push` 하면 Cloudflare Pages 가 1~2분 내 자동 반영합니다.

---

## 무인 운영 설정 (2026-07-28 적용)

```bash
sudo pmset repeat wakeorpoweron MTWRF 05:50:00   # 평일 자동 기상
sudo pmset -a autorestart 1                       # 정전 복구
```

- Claude.app 을 **로그인 항목**에 등록 (재부팅 후 자동 실행)
- `com.nachimban.claude-keeper` — 앱 감시, 죽으면 재실행
- `com.nachimban.healthcheck` — 평일 06:30 발행 확인

**잠자기에서 깨어나는 것은 세션이 유지되므로 암호가 걸려 있어도 동작합니다.**
자동 로그인이 필요한 경우는 재부팅이 일어났을 때뿐입니다.

### 2026년 10월 한국 체류 대비

맥을 모니터 없이 켜둔 채로 갑니다. 떠나기 전에:

1. **FileVault 해제** — 켜져 있으면 자동 로그인이 불가능하고, 재부팅 시 암호
   화면에서 영구 정지됩니다(그 화면에는 네트워크가 없어 원격 복구 불가)
2. 자동 로그인 켜기 (1번 완료 후에야 가능)
3. 자동 업데이트 끄기 — 재부팅을 유발하는 가장 큰 요인
4. Tailscale 설치(맥+아이폰) — 원격 복구 수단
5. `.env`, `data/vapid.json` 을 비밀번호 관리자에 백업
6. 귀국 후 1~3번 원상복구

전기세는 월 약 7유로. 클라우드 이전 시 API 비용은 월 약 $63 로 8배입니다.
실제 금액은 발행 로그의 "API 종량제 환산" 값을 보고 판단하세요.

---

## 발행 지시서 — 중요

매일 아침 실제로 실행되는 것은 파이프라인 스크립트가 아니라
`~/.claude/scheduled-tasks/nachimban-daily-brief/SKILL.md` 를 따르는 Claude 세션입니다.
이 세션이 WebSearch 로 직접 취재한 뒤 `publish.publish()` 만 호출합니다.

**`config.py` 나 `collect.py` 를 고쳐도 발행 결과는 바뀌지 않습니다.**
편집 규칙을 바꿀 때는 지시서를 반드시 함께 고치세요.
사본: `ops/daily-brief-SKILL.md`
