# zeroda_platform/config/settings.py
# ==========================================
# 제로다(ZERODA) 플랫폼 - 전역 설정 파일
# 모든 모듈이 이 파일에서 설정값을 import함
# ==========================================

import os
from datetime import datetime

# ==========================================
# DB 경로 설정
# ==========================================
DB_PATH = os.environ.get("ZERODA_DB_PATH", "zeroda.db")

# ==========================================
# 플랫폼 정보
# ==========================================
PLATFORM_NAME = "ZERODA"
PLATFORM_FULL_NAME = "제로다 폐기물데이터플랫폼"
COMPANY_NAME = "하영자원"
COMPANY_REGION = "경기도 화성시"
COMPANY_BIZ_NO = "603-17-01234"  # 하영자원 사업자번호

# ==========================================
# 동적 날짜 (하드코딩 제거)
# ==========================================
CURRENT_YEAR = datetime.now().year
CURRENT_MONTH = datetime.now().month
CURRENT_DATE = datetime.now().strftime("%Y-%m-%d")

# ==========================================
# 탄소감축 계수 (환경부 기준)
# ==========================================
CO2_FACTOR = 0.587   # kgCO₂eq/kg (음식물폐기물 퇴비화 매립회피)
TREE_FACTOR = 6.6    # kg CO₂/그루/년 (소나무, 산림청)

# ==========================================
# 보안 설정
# ==========================================
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

# SMTP 설정 (네이버웍스)
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

# ==========================================
# 사용자 역할(Role) 정의
# ==========================================
ROLES = {
    "admin":            "본사 관리자",
    "vendor_admin":     "외주업체 관리자",
    "driver":           "수거기사",
    "school_admin":     "학교 행정실",
    "school_nutrition": "학교 영양사",
    "edu_office":       "교육청/교육지원청",
}

# 역할별 랜딩페이지 그룹 매핑
ROLE_GROUPS = {
    "admin":            "admin",
    "vendor_admin":     "vendor_admin",
    "driver":           "driver",
    "school_admin":     "edu_school",
    "school_nutrition": "edu_school",
    "edu_office":       "edu_school",
}

# 역할별 아이콘
ROLE_ICONS = {
    "admin":            "🏢",
    "vendor_admin":     "🤝",
    "driver":           "🚚",
    "school_admin":     "🏫",
    "school_nutrition": "🍱",
    "edu_office":       "🎓",
}

# ==========================================
# DB 허용 테이블 목록 (보안용 화이트리스트)
# ==========================================
ALLOWED_TABLES = {
    'price_data',
    'contract_info',
    'contract_data',
    'schedule_data',
    'today_schedule',
    'customer_info',
    'biz_customers',
    'vendor_info',
    'users',
    'real_collection',
    'sim_collection',
    'school_master',
    'schedules',
}

# ==========================================
# 한글 폰트 후보 경로 (우선순위 순)
# ==========================================
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

# ==========================================
# CSS 스타일 (공통)
# ==========================================
COMMON_CSS = """
<style>
.custom-card { background-color: #ffffff !important; color: #202124 !important; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-top: 5px solid #1a73e8; }
.custom-card-green  { border-top: 5px solid #34a853; }
.custom-card-orange { border-top: 5px solid #fbbc05; }
.custom-card-red    { border-top: 5px solid #ea4335; }
.custom-card-purple { border-top: 5px solid #9b59b6; }
.metric-title       { font-size: 14px; color: #5f6368 !important; font-weight: bold; margin-bottom: 5px; }
.metric-value-food   { font-size: 26px; font-weight: 900; color: #ea4335 !important; }
.metric-value-recycle{ font-size: 26px; font-weight: 900; color: #34a853 !important; }
.metric-value-biz    { font-size: 26px; font-weight: 900; color: #9b59b6 !important; }
.metric-value-total  { font-size: 26px; font-weight: 900; color: #1a73e8 !important; }
.mobile-app-header  { background-color: #202124; color: #ffffff !important; padding: 15px; border-radius: 10px 10px 0 0; text-align: center; margin-bottom: 15px; }
.safety-box  { background-color: #e8f5e9; border: 1px solid #c8e6c9; padding: 15px; border-radius: 8px; color: #2e7d32; font-weight: bold; margin-bottom:15px; }
.alert-box   { background-color: #ffebee; border: 1px solid #ffcdd2; padding: 15px; border-radius: 8px; color: #c62828; margin-bottom: 15px; }
.landing-header { background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf9 50%, #e0f0e3 100%); padding: 50px 20px 30px 20px; text-align: center; border-radius: 0 0 20px 20px; margin: -1rem -1rem 30px -1rem; }
.landing-header h1   { font-size: 36px; font-weight: 900; color: #1a1a2e; margin-bottom: 8px; }
.landing-header .subtitle { font-size: 18px; color: #555; }
.landing-header .brand    { font-size: 28px; font-weight: 800; color: #1a73e8; margin-bottom: 15px; }
.role-card { background: #fff; border: 2px solid #e8eaed; border-radius: 16px; padding: 35px 20px; text-align: center; box-shadow: 0 2px 12px rgba(0,0,0,0.06); min-height: 280px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
.role-card .icon  { font-size: 64px; margin-bottom: 15px; }
.role-card .title { font-size: 22px; font-weight: 800; color: #202124; margin-bottom: 8px; }
.role-card .desc  { font-size: 14px; color: #5f6368; line-height: 1.5; }
.role-card .arrow { font-size: 24px; color: #1a73e8; margin-top: 12px; }
.footer-info { text-align: center; padding: 20px; color: #777; font-size: 13px; margin-top: 30px; border-top: 1px solid #e8eaed; }
</style>
"""
```

