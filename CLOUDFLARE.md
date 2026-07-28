# Cloudflare Pages 이전 안내

Netlify 무료 배포 한도가 소진되어 Cloudflare Pages 로 옮깁니다.
(Cloudflare Pages: 월 500회 배포 · Functions · KV 모두 무료)

## 1) KV 저장소 만들기
Cloudflare 대시보드 → **Storage & Databases → KV → Create instance**
- 이름: `nachimban`

## 2) Pages 프로젝트 만들기
**Compute (Workers) → Pages → Connect to Git** → `Nachimban-TMC/nachimban` 선택
- Framework preset: **None**
- Build command: **비움**
- Build output directory: **`site`**
- **Save and Deploy**

## 3) 바인딩·변수 설정 (중요)
프로젝트 → **Settings**
- **Bindings → Add → KV namespace**
  - Variable name: `NB_KV`  ← 이 이름이어야 합니다
  - KV namespace: `nachimban`
- **Environment variables → Add**
  - `PUSH_ADMIN_TOKEN` = (Netlify 에 쓰던 값과 동일하게)

설정 후 **Deployments → Retry deployment** 한 번 실행.

## 4) 주소 확인 후 알려주기
`https://<프로젝트명>.pages.dev` 가 발급됩니다.
주소가 `nachimban.pages.dev` 가 아니면 `.env` 에 아래를 추가하세요:

```
NB_SITE_URL=https://실제주소.pages.dev
```

## 5) 푸시 알림 다시 켜기
도메인이 바뀌면 기존 푸시 구독은 무효가 됩니다.
새 주소에서 **홈 화면에 추가 → SUBSCRIBE → 알림 받기** 를 다시 눌러주세요.

## 받은 것 확인하기
```bash
python3 -m pipeline.inbox      # 이메일 구독자 + 편집팀에 온 의견
```

## 참고: 배포 습관
한도를 아끼기 위해 **수정은 모아서 하루 1회** 배포합니다.
