# zeroda_platform/config/settings.py
import os
from datetime import datetime

# DB 경로
DB_PATH = os.environ.get("ZERODA_DB_PATH", "zeroda.db")

# 플랫폼 정보
PLATFORM_NAME = "ZERODA"
PLATFORM_FULL_NAME = "제로다 폐기물데이터플랫폼"
COMPANY_NAME = "하영자원"
COMPANY_REGION = "경기도 화성시"
COMPANY_BIZ_NO = "603-17-01234"

# 동적 날짜
CURRENT_YEAR  = datetime.now().year
CURRENT_MONTH = datetime.now().month
CURRENT_DATE  = datetime.now().strftime("%Y-%m-%d")

# 탄소감축 계수
CO2_FACTOR  = 0.587
TREE_FACTOR = 6.6

# 보안 설정
EXCEL_PASSWORD = os.environ.get("ZERODA_EXCEL_PW", "change_me_in_env")
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        if "ZERODA_EXCEL_PW" in st.secrets:
            EXCEL_PASSWORD = st.secrets["ZERODA_EXCEL_PW"]
        elif "HAYOUNG_EXCEL_PW" in st.secrets:
            EXCEL_PASSWORD = st.secrets["HAYOUNG_EXCEL_PW"]
except Exception:
    pass

# SMTP 설정
SMTP_HOST = "smtp.worksmobile.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("NAVER_SMTP_USER", "")
SMTP_PW   = os.environ.get("NAVER_SMTP_APP_PW", "")
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        SMTP_USER = st.secrets.get("NAVER_SMTP_USER", SMTP_USER)
        SMTP_PW   = st.secrets.get("NAVER_SMTP_APP_PW", SMTP_PW)
except Exception:
    pass

# 사용자 역할 정의
ROLES = {
    "admin":            "본사 관리자",
    "vendor_admin":     "외주업체 관리자",
    "driver":           "수거기사",
    "school_admin":     "학교 행정실",
    "school_nutrition": "급식 담당(영양사)",
    "edu_office":       "교육청/교육지원청",
    "meal_manager":     "단체급식 담당",
}

ROLE_GROUPS = {
    "admin":            "admin",
    "vendor_admin":     "vendor_admin",
    "driver":           "driver",
    "school_admin":     "edu_school",
    "school_nutrition": "meal",
    "edu_office":       "edu_school",
    "meal_manager":     "meal",
}

# 이모지 제거 - 텍스트로 대체
ROLE_ICONS = {
    "admin":            "[본사]",
    "vendor_admin":     "[업체]",
    "driver":           "[기사]",
    "school_admin":     "[학교]",
    "school_nutrition": "[급식]",
    "edu_office":       "[교육청]",
    "meal_manager":     "[급식]",
}

# DB 허용 테이블
ALLOWED_TABLES = {
    'price_data', 'contract_info', 'contract_data',
    'schedule_data', 'today_schedule', 'customer_info',
    'biz_customers', 'vendor_info', 'users',
    'real_collection', 'sim_collection', 'school_master', 'schedules',
    'meal_menus', 'meal_analysis',
}

# 한글 폰트 후보
FONT_CANDIDATES = [
    ('NanumGothic.ttf', None),
    ('fonts/NanumGothic.ttf', None),
    ('C:/Windows/Fonts/malgun.ttf', None),
    ('C:/Windows/Fonts/malgunbd.ttf', None),
    ('C:/Windows/Fonts/NanumGothic.ttf', None),
    ('C:/Windows/Fonts/batang.ttc', 0),
    ('C:/Windows/Fonts/gulim.ttc', 0),
    ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', None),
    ('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 0),
    ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 0),
    ('/System/Library/Fonts/AppleSDGothicNeo.ttc', 0),
    ('/Library/Fonts/NanumGothic.ttf', None),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 학교급식 공식기준 (학교급식법 시행규칙 [별표 3] + 발주량 공식)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 학교급 자동 판별 ──
def detect_school_level(school_name: str) -> str:
    """학교명에서 학교급(초등/중학/고등) 자동 추출.
    예: '서초고등학교' → '고등', '화성중학교' → '중학', '오산초등학교' → '초등'
    판별 실패 시 '혼합평균' 반환.
    """
    name = str(school_name or '')
    if '고등' in name or '고교' in name:
        return '고등'
    if '중학' in name or '중교' in name:
        return '중학'
    if '초등' in name or '초교' in name:
        return '초등'
    return '혼합평균'


# ── 1끼 영양기준 [별표 3] (교육부, 2021.01.29 개정) ──
# 에너지 ±10% 허용, 탄수화물:단백질:지방 = 55~70%:7~20%:15~30%
SCHOOL_NUTRITION_STANDARD = {
    '초등': {
        'label': '초등학교 (4~6학년 평균)',
        'energy_kcal':  600,     # 남 634 + 여 567 평균
        'protein_g':    11.7,
        'vitA_RE':      130,
        'thiamin_mg':   0.22,
        'riboflavin_mg': 0.24,
        'vitC_mg':      17,
        'calcium_mg':   200,
        'iron_mg':      3.0,
    },
    '중학': {
        'label': '중학교',
        'energy_kcal':  750,     # 남 850 + 여 650 평균
        'protein_g':    15.0,
        'vitA_RE':      170,
        'thiamin_mg':   0.27,
        'riboflavin_mg': 0.33,
        'vitC_mg':      23,
        'calcium_mg':   267,
        'iron_mg':      4.0,
    },
    '고등': {
        'label': '고등학교',
        'energy_kcal':  785,     # 남 900 + 여 670 평균
        'protein_g':    16.7,
        'vitA_RE':      200,
        'thiamin_mg':   0.30,
        'riboflavin_mg': 0.37,
        'vitC_mg':      27,
        'calcium_mg':   267,
        'iron_mg':      4.0,
    },
    '혼합평균': {
        'label': '혼합평균 (학교급 미상)',
        'energy_kcal':  700,
        'protein_g':    14.0,
        'vitA_RE':      170,
        'thiamin_mg':   0.26,
        'riboflavin_mg': 0.31,
        'vitC_mg':      22,
        'calcium_mg':   245,
        'iron_mg':      3.7,
    },
}

# ── 1끼 구성별 제공량 기준 [별표 3] (고등학교 남 900kcal 기준) ──
MEAL_COMPOSITION_STANDARD = {
    '초등': {
        '밥':       {'supply_g': 180, 'kcal': 270},
        '국':       {'supply_g': 200, 'kcal':  40},
        '주반찬':   {'supply_g':  60, 'kcal': 100},
        '부반찬':   {'supply_g':  50, 'kcal':  25},
        '김치':     {'supply_g':  40, 'kcal':  15},
        'total_g': 530, 'total_kcal': 600,
    },
    '중학': {
        '밥':       {'supply_g': 210, 'kcal': 315},
        '국':       {'supply_g': 230, 'kcal':  46},
        '주반찬':   {'supply_g':  70, 'kcal': 115},
        '부반찬':   {'supply_g':  55, 'kcal':  28},
        '김치':     {'supply_g':  50, 'kcal':  18},
        'total_g': 615, 'total_kcal': 750,
    },
    '고등': {
        '밥':       {'supply_g': 220, 'kcal': 330},
        '국':       {'supply_g': 250, 'kcal':  50},
        '주반찬':   {'supply_g':  80, 'kcal': 130},
        '부반찬':   {'supply_g':  60, 'kcal':  30},
        '김치':     {'supply_g':  60, 'kcal':  20},
        'total_g': 670, 'total_kcal': 785,
    },
    '혼합평균': {
        '밥':       {'supply_g': 200, 'kcal': 300},
        '국':       {'supply_g': 230, 'kcal':  46},
        '주반찬':   {'supply_g':  70, 'kcal': 115},
        '부반찬':   {'supply_g':  55, 'kcal':  28},
        '김치':     {'supply_g':  50, 'kcal':  18},
        'total_g': 605, 'total_kcal': 700,
    },
}

# ── 잔반 등급 기준 — 1인당 g [별표3 + 논문 종합] ──
WASTE_GRADE_STANDARD = {
    'A': {'min': 0,   'max': 150, 'label': '우수', 'desc': '잔반 최소화 달성'},
    'B': {'min': 150, 'max': 245, 'label': '양호', 'desc': '혼합평균(245g) 이하'},
    'C': {'min': 245, 'max': 300, 'label': '주의', 'desc': '표준 초과, 메뉴 조정 권장'},
    'D': {'min': 300, 'max': 9999,'label': '경보', 'desc': '고잔반, 메뉴 구성 재검토 필요'},
}

# ── 메뉴 유형별 잔반 발생 순위 [논문 종합: KCI, RISS, 한국식품영양과학회] ──
MENU_WASTE_RANK_STANDARD = {
    '채소·나물': {'rank': 1, 'waste_pct': 57.4, 'note': '편식 최다 요인'},
    '국·찌개류': {'rank': 2, 'waste_pct': 22.7, 'note': '국물 잔반, 학교급 높을수록 감소'},
    '생선류':    {'rank': 3, 'waste_pct': 13.5, 'note': '뼈·가시 전처리 발생'},
    '밥류':      {'rank': 4, 'waste_pct': 10.3, 'note': '상대적 저잔반'},
    '육류':      {'rank': 5, 'waste_pct':  5.0, 'note': '잔반 매우 적음'},
    '과일':      {'rank': 6, 'waste_pct':  2.0, 'note': '껍질·씨 전처리 잔여물만'},
}

# ── 발주량 산출 공식 (식약처 집단급식소 급식안전관리 기준) ──
# 발주량 = 1인 순사용량 × 출고계수 × 예정식수
# 출고계수 = 100 ÷ (100 - 폐기율)
# → 실제 조리량은 1인 제공량보다 약 10~25% 더 많음
PROCUREMENT_FORMULA = {
    'desc': '발주량 = 1인 순사용량 × 출고계수 × 예정식수',
    'waste_factor_desc': '출고계수 = 100 ÷ (100 - 폐기율)',
    'typical_waste_rates': {
        '채소류': 20,   # 폐기율 20% → 출고계수 1.25
        '육류':   10,   # 폐기율 10% → 출고계수 1.11
        '생선류': 35,   # 폐기율 35% → 출고계수 1.54
        '과일류': 15,   # 폐기율 15% → 출고계수 1.18
        '곡류':    5,   # 폐기율  5% → 출고계수 1.05
    },
    'cooking_loss_pct': 10,  # 조리손실 약 10% (수분 증발, 기름 흡수 등)
    'total_overhead_pct': 20,  # 폐기율 + 조리손실 종합 → 제공량 대비 약 20% 추가
}

# ── 공식기준 분석 근거 출처 ──
OFFICIAL_REFERENCES = [
    "[1] 학교급식법 시행규칙 [별표 3] (교육부, 2021.01.29 개정) — law.go.kr",
    "[2] 경기도교육청, 「2023학년도 학교급식 정책추진 기본계획」, 2023.02 — goe.go.kr",
    "[3] 한국식품영양과학회 (2019), 경기도 학교급식 음식물쓰레기 발생 실태 — JAKO201908662572910",
    "[4] 한국식품영양학회지 KCI, 고등학생 학교급식 만족도와 메뉴 선호도 — ART001424254",
    "[5] 중학생 편식·급식 식단기호도 조사, RISS 학위논문 — 서울 광진구 중학생 300명",
    "[6] 환경부/한국폐기물협회, 2023년 전국폐기물 발생 및 처리현황 — kwaste.or.kr",
    "[7] 식약처, 「집단급식소 급식안전관리 기준」 — 발주량 산출 공식",
    "[8] 한국인 영양소 섭취기준(KDRIs), 한국영양학회 — kns.or.kr",
]


def get_school_standard(school_name: str) -> dict:
    """학교명 기반으로 해당 학교급의 전체 공식기준을 반환"""
    level = detect_school_level(school_name)
    return {
        'level': level,
        'nutrition': SCHOOL_NUTRITION_STANDARD.get(level, SCHOOL_NUTRITION_STANDARD['혼합평균']),
        'composition': MEAL_COMPOSITION_STANDARD.get(level, MEAL_COMPOSITION_STANDARD['혼합평균']),
        'waste_grade': WASTE_GRADE_STANDARD,
        'menu_rank': MENU_WASTE_RANK_STANDARD,
        'procurement': PROCUREMENT_FORMULA,
        'references': OFFICIAL_REFERENCES,
    }


# 공통 CSS
COMMON_CSS = """
<style>
.custom-card { background-color: #ffffff !important; color: #202124 !important; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-top: 5px solid #1a73e8; }
.custom-card-green  { border-top: 5px solid #34a853; }
.custom-card-orange { border-top: 5px solid #fbbc05; }
.custom-card-red    { border-top: 5px solid #ea4335; }
.custom-card-purple { border-top: 5px solid #9b59b6; }
.metric-title        { font-size: 14px; color: #5f6368 !important; font-weight: bold; margin-bottom: 5px; }
.metric-value-food   { font-size: 26px; font-weight: 900; color: #ea4335 !important; }
.metric-value-recycle{ font-size: 26px; font-weight: 900; color: #34a853 !important; }
.metric-value-biz    { font-size: 26px; font-weight: 900; color: #9b59b6 !important; }
.metric-value-total  { font-size: 26px; font-weight: 900; color: #1a73e8 !important; }
.mobile-app-header  { background-color: #202124; color: #ffffff !important; padding: 15px; border-radius: 10px 10px 0 0; text-align: center; margin-bottom: 15px; }
.safety-box  { background-color: #e8f5e9; border: 1px solid #c8e6c9; padding: 15px; border-radius: 8px; color: #2e7d32; font-weight: bold; margin-bottom:15px; }
.alert-box   { background-color: #ffebee; border: 1px solid #ffcdd2; padding: 15px; border-radius: 8px; color: #c62828; margin-bottom: 15px; }
.role-card { background: #fff; border: 2px solid #e8eaed; border-radius: 16px; padding: 35px 20px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06); min-height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
.role-card .icon  { font-size: 64px; margin-bottom: 15px; }
.role-card .title { font-size: 22px; font-weight: 800; color: #202124; margin-bottom: 8px; }
.role-card .desc  { font-size: 14px; color: #5f6368; line-height: 1.5; }
.role-card .arrow { font-size: 24px; color: #1a73e8; margin-top: 12px; }
.footer-info { text-align: center; padding: 20px; color: #777; font-size: 13px; margin-top: 30px; border-top: 1px solid #e8eaed; }
</style>
"""
