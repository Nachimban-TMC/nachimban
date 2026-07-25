"""나침반 파이프라인 설정.

여기 한 곳에서 지역/카테고리/모델을 관리합니다. 카테고리 키는
site/template.html 의 CSS 이미지 클래스(g1..g10)와 1:1로 연결됩니다.
"""
from __future__ import annotations
import os

# ── 모델 ─────────────────────────────────────────────────────────
# 기본은 claude-opus-4-8. 2차 팩트체커(B)는 "독립성"을 위해 일부러
# 다른 모델을 씁니다(같은 실수를 공유하지 않게 하려는 설계). 비용 절감이
# 아니라 교차검증 목적입니다. 환경변수로 덮어쓸 수 있습니다.
MODEL_JOURNALIST = os.getenv("NB_MODEL_JOURNALIST", "claude-opus-4-8")   # 취재 기자
MODEL_LEGAL      = os.getenv("NB_MODEL_LEGAL",      "claude-opus-4-8")   # 법률 해설가
MODEL_FACTCHECK_A = os.getenv("NB_MODEL_FACTCHECK_A", "claude-opus-4-8") # 팩트체커 A
MODEL_FACTCHECK_B = os.getenv("NB_MODEL_FACTCHECK_B", "claude-sonnet-5") # 팩트체커 B (독립)

# ── 발행 규칙 ────────────────────────────────────────────────────
MIN_SOURCES = 2          # 출처 2개 미만이면 자동 보류(HOLD)
MIN_CONFIDENCE = 0.7     # 팩트체커 확신도 하한
PUBLISH_HOUR = 7         # 발행/발송 시각(오전 7시)

# ── 지역 ─────────────────────────────────────────────────────────
# 순서 = 사용자 지정(독일 → 한국 → EU → USA → 프랑스). 광고는 첫 섹션 뒤.
REGION_ORDER = ["de", "kr", "eu", "us", "fr"]
REGIONS = {
    "de": {"k": "Germany",        "en": "독일",       "count": 5},
    "kr": {"k": "Korea",          "en": "한국 · 국내", "count": 5},
    "eu": {"k": "European Union",  "en": "EU 공통",     "count": 3},  # 투자 1건 포함
    "us": {"k": "United States",   "en": "미국",        "count": 4},  # 주식 2건 포함
    "fr": {"k": "France",          "en": "프랑스",      "count": 2},
}
AD_AFTER = "de"  # 이 섹션 뒤에 인피드 광고 슬롯

# ── 카테고리 → (한글, 영어, 이미지클래스) ─────────────────────────
# 이미지 클래스는 얼굴 없는 재사용 흑백 이미지(template.html에 내장).
CATEGORIES = {
    "visa":        ("비자",       "VISA",        "g1"),
    "immigration": ("이민",       "IMMIGRATION", "g1"),
    "citizenship": ("국적·병역",  "CITIZEN",     "g1"),
    "welfare":     ("복지",       "WELFARE",     "g2"),
    "tax":         ("세금",       "TAX",         "g3"),
    "labor":       ("노동",       "LABOR",       "g3"),
    "policy":      ("법·제도",    "POLICY",      "g4"),
    "life":        ("생활",       "LIFE",        "g5"),
    "housing":     ("주거",       "HOUSING",     "g6"),
    "pension":     ("연금",       "PENSION",     "g7"),
    "health":      ("건강보험",   "HEALTH",      "g7"),
    "study":       ("유학",       "STUDY",       "g8"),
    "education":   ("교육",       "EDU",         "g8"),
    "travel":      ("여행",       "TRAVEL",      "g9"),
    "invest":      ("투자",       "INVEST",      "g10"),
    "stocks":      ("주식",       "STOCKS",      "g10"),
    "crypto":      ("가상자산",   "CRYPTO",      "g10"),
}

# 각 지역에서 "이런 주제를 우선 발굴하라"고 취재 기자에게 주는 힌트.
REGION_TOPIC_HINTS = {
    "de": "체류허가/비자, 자녀수당·복지, 대중교통·생활비, 최저임금·노동, 유학생 제도",
    "kr": "재외국민 신원확인·행정, 건강보험·연금, 국적·병역, 해외금융계좌·세금, 재외동포청·교육",
    "eu": "EES/ETIAS 입국제도, EU 공통 소비자·투자자 보호(주식/투자 1건 이상 포함)",
    "us": "비자·이민 수수료, FBAR·세금, 미국 주식 양도세·투자 제도(주식 관련 1~2건 포함)",
    "fr": "체류증(ANEF), 주거보조금(CAF/APL) 등 프랑스 거주 한인 실생활",
}

# 사이트 주소 (이메일의 '전체 보기' 링크에 사용)
SITE_URL = os.getenv("NB_SITE_URL", "https://nachimban.netlify.app")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SITE_DIR = os.path.join(os.path.dirname(__file__), "site")
