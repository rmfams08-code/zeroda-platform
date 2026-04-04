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


# ── AI 일별 특이사항 프롬프트 템플릿 (AI월말명세서용) ──
AI_DAILY_REMARK_PROMPT = """당신은 학교급식 잔반 분석 전문가입니다.
아래 일별 데이터를 보고, **각 날짜마다 한 줄(40자 이내)** AI 코멘트를 생성하세요.

## 분석 기준
- 학교급식법 시행규칙 [별표 3] 공식기준 참조
- 잔반 등급: A(<150g 우수), B(150~245g 양호), C(245~300g 주의), D(300g+ 경보)
- 메뉴 유형별 잔반 순위: 채소·나물(57.4%) > 국·찌개(22.7%) > 생선(13.5%)
- 전일 대비 증감, 요일 패턴, 메뉴 조합 효과를 분석

## 코멘트 작성 규칙
- 전일 대비 증감률이 20% 이상이면 반드시 언급
- 같은 요일의 평균과 비교
- 메뉴 조합이 잔반에 미친 영향 분석
- 긍정적 변화(감소)도 언급
- 숫자·근거 중심으로 간결하게

## 기관: {site_name}
## 기간: {year_month}
{school_standard_text}

## 일별 데이터
{daily_data_text}

## 출력 형식
반드시 아래 JSON 형식으로만 출력하세요. 다른 텍스트 없이 JSON만 출력:
{{"remarks": {{"YYYY-MM-DD": "AI 코멘트", ...}}}}
"""


# ── 일일 안전보건 점검표 (산업안전보건법 제36조 근거) ──
# 4개 카테고리 27항목 — 폐기물수집운반업 특화
DAILY_SAFETY_CHECKLIST = {
    '1인작업안전': {
        'label': '1인 작업 안전',
        'icon': '🚨',
        'items': [
            {'id': 'solo_01', 'text': '작업 시작 전 관리감독자에게 작업 일정 및 위치를 사전 통보하였는가?'},
            {'id': 'solo_02', 'text': '수거 앱(ZERODA) 로그인 및 데이터 연결 상태를 확인하였는가?'},
            {'id': 'solo_03', 'text': '각 거래처 수거 완료 시 수거량을 즉시 입력하였는가? (본사 이상유무 모니터링 연동)'},
            {'id': 'solo_04', 'text': '작업 현장 반경 내 낙하·협착 위험 구역을 확인하고 안전 구역을 설정하였는가?'},
            {'id': 'solo_05', 'text': '작업 종료 후 관리감독자에게 작업 완료를 보고하였는가?'},
        ],
    },
    '보호구위생': {
        'label': '보호구 및 위생',
        'icon': '🦺',
        'items': [
            {'id': 'ppe_01', 'text': '안전화(안전 인증품) 착용 상태를 확인하였는가?'},
            {'id': 'ppe_02', 'text': '방수·방오 처리된 장갑(안전 장갑) 착용 상태를 확인하였는가?'},
            {'id': 'ppe_03', 'text': '방진 마스크(KF94 이상 또는 방취 기능 포함) 착용 상태를 확인하였는가?'},
            {'id': 'ppe_04', 'text': '방수 앞치마(에이프런) 또는 방오 작업복 착용 상태를 확인하였는가?'},
            {'id': 'ppe_05', 'text': '안전모 착용 상태를 확인하였는가? (리프트 적재함 하부 접근 시 필수)'},
            {'id': 'ppe_06', 'text': '작업 후 손 씻기 및 위생 처리(손 소독제 비치 여부)를 확인하였는가?'},
            {'id': 'ppe_07', 'text': '기타 필요한 개인보호구(눈 보호대, 무릎 보호대 등) 지참 여부를 확인하였는가?'},
        ],
    },
    '차량장비점검': {
        'label': '차량 및 장비 점검',
        'icon': '🚛',
        'items': [
            {'id': 'veh_01', 'text': '차량 외관(타이어 마모·공기압, 제동장치, 오일류 누유) 이상 여부를 점검하였는가?'},
            {'id': 'veh_02', 'text': '리프트(승강장치) 유압 호스 및 연결부위 누유·균열 여부를 육안으로 점검하였는가?'},
            {'id': 'veh_03', 'text': '리프트 작동 시 비상정지 스위치(인터록 장치) 정상 작동 여부를 확인하였는가?'},
            {'id': 'veh_04', 'text': '리프트 승강 구간 내 이물질(수거통 잔재, 이물) 및 장애물을 제거하였는가?'},
            {'id': 'veh_05', 'text': '리프트 체인·와이어로프의 이완·마모·손상 여부를 점검하였는가?'},
            {'id': 'veh_06', 'text': '적재함 도어 개폐 잠금 장치(안전핀, 래치) 정상 작동 여부를 확인하였는가?'},
            {'id': 'veh_07', 'text': '차량 경보음(후진 경보) 및 작업 표시등(황색 경광등) 정상 작동 여부를 확인하였는가?'},
            {'id': 'veh_08', 'text': '차량이 평탄한 지면에 고정(사이드 브레이크 체결, 고임목 설치)되어 있는가?'},
        ],
    },
    '중량물상하차': {
        'label': '중량물 상하차',
        'icon': '📦',
        'items': [
            {'id': 'load_01', 'text': '수거통(200kg 잔반통, 120L 전용통) 이동 전 바퀴(캐스터) 상태 및 잠금장치를 점검하였는가?'},
            {'id': 'load_02', 'text': '수거통을 리프트 걸이에 체결 시 후크·고리의 정위치 체결 여부를 확인하였는가?'},
            {'id': 'load_03', 'text': '리프트 작동 중 수거통 하부 및 승강 경로에 신체 일부가 위치하지 않도록 조치하였는가?'},
            {'id': 'load_04', 'text': '리프트 작동은 수거통이 완전히 고정된 것을 확인한 후 실시하였는가?'},
            {'id': 'load_05', 'text': '중량물 이동 시 무릎을 굽히고 척추를 직립한 올바른 자세로 작업하였는가? (허리 비틀기 금지)'},
            {'id': 'load_06', 'text': '경사면·우천 시 등 미끄러운 바닥 조건에서는 작업을 중단하고 안전 조치를 취하였는가?'},
            {'id': 'load_07', 'text': '수거통 적재 후 적재함 내부 고정(로프·결박장치) 이상 여부를 확인하였는가?'},
        ],
    },
}

# 기사 활동 모니터링 설정 (수거 입력 기반 이상 감지)
DRIVER_MONITORING_CONFIG = {
    'alert_threshold_min': 50,     # 마지막 수거 입력 후 N분 초과 시 주의
    'warning_threshold_min': 80,   # N분 초과 시 경고
    'emergency_threshold_min': 120, # N분 초과 시 긴급
    'work_hours': {'start': 7, 'end': 18},  # 근무시간 (시간 외는 모니터링 제외)
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
