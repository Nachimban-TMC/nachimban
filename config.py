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
REGION_ORDER = ["de", "kr", "eu", "us"]
REGIONS = {
    # k=섹션 제목(정식명), s=필터 라벨(짧게), en=한글
    "de": {"k": "Germany",        "s": "Germany", "en": "독일",       "count": 5},
    "kr": {"k": "Korea",          "s": "Korea",   "en": "한국 · 국내", "count": 5},
    "eu": {"k": "European Union",  "s": "EU",      "en": "EU 공통",     "count": 3},  # 투자 1건 포함
    "us": {"k": "United States",   "s": "USA",     "en": "미국",        "count": 4},  # 주식 2건 포함
    # 프랑스는 사용자 요청으로 잠시 제외 (나중에 되살리려면 아래 두 줄 복구)
    # "fr": {"k": "France",        "en": "프랑스",      "count": 2},
}
# 광고 슬롯: 지금은 숨김. 다시 켜려면 "de" 등 지역 코드를 넣으세요.
AD_AFTER = None

# ── 카테고리 → (한글, 영어, 이미지클래스) ─────────────────────────
# 이미지 클래스는 얼굴 없는 재사용 흑백 이미지(template.html에 내장).
CATEGORIES = {
    # 그날 법률·복지 뉴스가 적을 수 있어, 지역마다 '주요뉴스' 한 꼭지를 함께 싣는다
    "general":     ("주요뉴스",   "TOP STORY",   "g4"),
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
}

# 각 지역마다 'general'(주요뉴스) 1건을 반드시 포함한다.
# 법률·복지 뉴스가 그날 적더라도 브리핑이 비지 않도록 하는 장치.
REQUIRE_GENERAL_PER_REGION = True
GENERAL_HINT = (
    "그날 그 나라 주요 언론이 '1면·톱뉴스'로 다룬 소식 1건. "
    "정책 발표가 아니라, 그날 그곳 사람들이 실제로 가장 많이 이야기한 뉴스여야 합니다 "
    "(대형 사건·사고, 재난, 치안, 교통 마비, 파업, 선거·정국, 큰 경제 충격 등). "
    "법률/복지 뉴스가 아니어도 됩니다. 판단 기준: 그 도시에 사는 한국인이 "
    "'이건 당연히 알아야지'라고 여길 만한 뉴스인가."
)

# 정원과 무관하게 반드시 실어야 하는 중대 사안.
# 이런 날 '비자 수수료 인상'만 싣고 큰 사고를 빠뜨리면 브리핑 전체를 못 믿게 된다.
BREAKING_HINT = (
    "아래에 해당하는 일이 최근 24~48시간 안에 그 지역에서 있었다면, "
    "정원을 넘겨서라도 반드시 1건 포함하세요(category 는 general, hot 표시):\n"
    "  · 사망자·다수 부상자가 발생한 사건이나 사고\n"
    "  · 테러·총격·흉기 난동 등 치안 사건\n"
    "  · 지진·홍수·폭염·대형 화재 등 재난\n"
    "  · 공항·철도·대중교통 마비, 대규모 파업\n"
    "  · 전국적 정전·통신 장애, 감염병 경보\n"
    "  · 정권 붕괴·조기 총선 등 급격한 정국 변화\n"
    "해당 사항이 없으면 억지로 만들지 마세요. 없으면 없는 대로 둡니다."
)

# 사이트 주소 (이메일의 '전체 보기' 링크에 사용)
# 호스팅 이전: Netlify → Cloudflare Pages (배포 한도 때문)
SITE_URL = os.getenv("NB_SITE_URL", "https://nachimban.pages.dev")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SITE_DIR = os.path.join(os.path.dirname(__file__), "site")
