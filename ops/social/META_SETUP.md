# 인스타·스레드 자동 게시 — Meta 설정 (한 번만)

자동 게시 코드는 준비됨. 아래를 채우면 매일 발행과 함께 자동으로 올라간다.
토큰은 `data/social_tokens.json` 에 넣는다(gitignore 처리됨 — 커밋 안 됨).

## A. 인스타그램 준비
1. 인스타 앱 → 설정 → **프로페셔널 계정(비즈니스/크리에이터)** 으로 전환
2. **페이스북 페이지** 하나 만들고 그 인스타 계정과 연결 (Meta Business Suite)

## B. Meta 개발자 앱
1. https://developers.facebook.com → **앱 만들기** (유형: 비즈니스)
2. 제품 추가: **Instagram** (Graph API) + **Threads API**
3. 권한(스코프):
   - 인스타: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `business_management`
   - 스레드: `threads_basic`, `threads_content_publish`
   - ⚠️ 본인 계정에 올리는 용도면 **앱을 개발 모드로 두고 본인을 역할(테스터/관리자)로 추가**하면 앱 심사 없이 사용 가능
4. **장기(long-lived) 액세스 토큰** 발급 (Graph API Explorer → 토큰을 장기로 교환)
5. **ID 확인**: 인스타 비즈니스 계정 ID, 스레드 사용자 ID

## C. 토큰 파일 작성
`~/nachimban/data/social_tokens.json` 을 아래 형식으로:
```json
{
  "instagram": {
    "user_id": "인스타_비즈니스_계정_ID",
    "access_token": "장기_토큰",
    "app_id": "앱ID",
    "app_secret": "앱시크릿"
  },
  "threads": {
    "user_id": "스레드_사용자_ID",
    "access_token": "스레드_장기_토큰"
  }
}
```
- `app_id`/`app_secret` 을 넣으면 인스타 토큰도 45일마다 **자동 갱신**된다(안 넣으면 갱신 안 됨).
- 스레드 토큰은 app_secret 없이도 자동 갱신된다.

## D. 테스트
```
cd ~/nachimban
python3 ops/social/post_social.py --dry     # 실제 게시 없이 점검
python3 ops/social/post_social.py            # 실제로 한 번 올려보기
python3 ops/social/post_social.py --refresh  # 토큰 수동 갱신
```
성공하면 이후 매일 발행 때 자동으로 올라간다. 실패 시 관리자에게만 알림.

## 참고
- 이미지는 이미 공개 URL(`nachimban.pages.dev/social/img/...`)에 있어 API가 바로 가져간다.
- 하루 한 번, 날짜별로 플랫폼마다 한 번만 게시(중복 방지: `data/social_posted.json`).
- 인스타=캐러셀 9장, 스레드=대표 이미지 1장+텍스트. (스레드도 캐러셀로 바꿀 수 있음)
