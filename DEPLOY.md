# 배포 & 매일 7시 발송 세팅 가이드

전체 그림:

```
GitHub 저장소  ──(push)──▶  Netlify  ──▶  실제 사이트 URL(무료·자동 재배포)
     ▲                                         
     │ 매일 커밋                                
GitHub Actions cron
  · 06:00 KST  build   : 파이프라인 실행 → site/ 갱신 → 커밋(→Netlify 재배포)
  · 07:00 KST  notify  : 최신 호를 Resend 로 구독자에게 이메일 발송
```

사장님이 하실 일은 **① 저장소 올리기 ② Netlify 연결 ③ 키 3개 등록 ④ Resend 도메인 인증**
네 가지뿐입니다. 코드·스케줄·발송 로직은 다 붙어 있습니다.

---

## 1) GitHub 저장소에 올리기

```bash
cd ~/nachimban
git init && git add . && git commit -m "나침반 초기 세팅"
# GitHub 에서 빈 저장소 생성 후:
git remote add origin https://github.com/<사용자명>/nachimban.git
git push -u origin main
```

> `data/subscribers.txt` 와 `.env` 는 `.gitignore` 로 자동 제외됩니다(개인정보/키 보호).

## 2) Netlify 연결 (무료)

1. netlify.com 로그인 → **Add new site → Import an existing project → GitHub**
2. `nachimban` 저장소 선택
3. **Publish directory** 를 `site` 로 설정, Build command 는 비움 (`netlify.toml` 에 이미 지정됨)
4. Deploy → 바로 `https://<이름>.netlify.app` URL 발급 ✅
5. (선택) **Domain settings** 에서 커스텀 도메인 연결 — 예: `nachimban.co`

> **지금 당장 한 번 보고 싶다면**: netlify.com/drop 에 `site/` 폴더를 드래그하면
> 즉시 임시 URL 이 뜹니다(계정 연결 없이 미리보기용).
>
> Vercel 을 쓰신다면 `vercel.json` 이 준비돼 있어 저장소 Import 만 하면 됩니다.

## 3) GitHub 시크릿 등록

저장소 → **Settings → Secrets and variables → Actions → New repository secret** 로 3개:

| 이름 | 값 | 용도 |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | 매일 수집·요약·이중 팩트체크 실행 |
| `RESEND_API_KEY` | `re_...` | 이메일 발송 |
| `NB_FROM` | `나침반 <brief@nachimban.co>` | 발신자(아래 4번에서 인증한 도메인) |

## 4) Resend 이메일 세팅

1. resend.com 가입 → **API Keys** 에서 키 발급 → 위 `RESEND_API_KEY` 에 등록
2. **Domains** 에서 발송 도메인(예: `nachimban.co`) 추가 후 DNS 인증
   (인증 전에는 `onboarding@resend.dev` 로만 테스트 발송 가능)
3. 인증된 주소를 `NB_FROM` 에 넣기
4. 구독자: `data/subscribers.txt` 파일에 이메일을 한 줄에 하나씩
   (개인정보라 저장소에는 안 올라가니, 서버/Actions에서 관리하거나
   추후 커뮤니티 '구독' 폼과 DB로 연동)

## 5) 동작 확인

- GitHub → **Actions** 탭 → `daily-build` → **Run workflow** (수동 실행)로 즉시 테스트
- 그 다음 `daily-notify` 도 수동 실행해 메일이 오는지 확인
- 이상 없으면 매일 06:00 / 07:00 (KST) 자동 실행됩니다

---

## 시간대 메모

cron 은 UTC 기준입니다. 한국(KST=UTC+9):
- `0 21 * * *` → **06:00 KST** (사이트 생성)
- `0 22 * * *` → **07:00 KST** (이메일 발송)

다른 나라 기준으로 바꾸려면 `.github/workflows/*.yml` 의 cron 만 수정하세요.

## 로컬에서 미리 돌려보기

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # 실제 수집·팩트체크
export RESEND_API_KEY=re_...             # 실제 발송
python -m pipeline.run --send            # 발행 + 즉시 발송
python -m pipeline.run --mock            # 키 없이 사이트만 생성(오프라인)
```
