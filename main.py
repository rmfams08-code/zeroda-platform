# zeroda_platform/main.py
# ==========================================
# 제로다(ZERODA) 플랫폼 - 메인 진입점
# ==========================================

import sys
import os

# Streamlit Cloud 경로 문제 해결
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from config.settings import PLATFORM_FULL_NAME, COMMON_CSS, ROLES, ROLE_ICONS
from database.db_init import init_db, migrate_csv_to_db
from auth.login import render_login_page, is_logged_in, logout, get_current_user


# ------------------------------------------
# 페이지 설정 (최초 1회)
# ------------------------------------------

st.set_page_config(
    page_title="ZERODA",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ------------------------------------------
# DB 초기화 (앱 시작 시 자동)
# ------------------------------------------

@st.cache_resource
def startup():
    init_db()
    migrate_csv_to_db()
    return True

startup()


# ------------------------------------------
# 로그인 체크
# ------------------------------------------

if not is_logged_in():
    render_login_page()
    st.stop()


# ------------------------------------------
# 로그인 이후 - 유저 정보
# ------------------------------------------

user   = get_current_user()
role   = user.get('role', '')
vendor = user.get('vendor', '')
name   = user.get('name', '')


# ------------------------------------------
# 사이드바
# ------------------------------------------

def render_sidebar(menu_items: list) -> str:
    with st.sidebar:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a73e8,#34a853);
                    padding:20px;border-radius:10px;margin-bottom:20px;text-align:center;">
            <div style="font-size:28px;"></div>
            <div style="color:white;font-weight:900;font-size:18px;">ZERODA</div>
            <div style="color:rgba(255,255,255,0.8);font-size:12px;">제로다 폐기물데이터플랫폼</div>
        </div>
        """, unsafe_allow_html=True)

        role_label = ROLES.get(role, role)
        role_icon  = ROLE_ICONS.get(role, '')
        st.markdown(f"""
        <div style="background:#f8f9fa;border-radius:8px;padding:12px;margin-bottom:16px;">
            <div style="font-size:11px;color:#5f6368;">로그인</div>
            <div style="font-weight:700;">{role_icon} {name}</div>
            <div style="font-size:12px;color:#5f6368;">{role_label}</div>
        </div>
        """, unsafe_allow_html=True)

        selected = st.session_state.get('current_menu', menu_items[0][1])

        for label, key in menu_items:
            if st.button(label, key=f"menu_{key}", use_container_width=True):
                st.session_state['current_menu'] = key
                selected = key

        st.divider()
        if st.button("로그아웃", use_container_width=True, key="logout_btn"):
            logout()

    return st.session_state.get('current_menu', menu_items[0][1])


# ------------------------------------------
# 역할별 라우팅
# ------------------------------------------

# 본사 관리자
if role == 'admin':
    menu = [
        ("대시보드",    "dashboard"),
        ("수거 데이터",  "data"),
        ("정산 관리",    "settlement"),
        ("수거일정",     "schedule"),
        ("외주업체 관리", "vendor"),
        ("계정 관리",    "account"),
    ]
    page = render_sidebar(menu)

    if page == "dashboard":
        from modules.hq_admin.dashboard import render_dashboard
        render_dashboard()
    elif page == "data":
        from modules.hq_admin.data_tab import render_data_tab
        render_data_tab()
    elif page == "settlement":
        from modules.hq_admin.settlement_tab import render_settlement_tab
        render_settlement_tab()
    elif page == "schedule":
        from modules.hq_admin.schedule_tab import render_schedule_tab
        render_schedule_tab()
    elif page == "vendor":
        from modules.hq_admin.vendor_mgmt_tab import render_vendor_mgmt_tab
        render_vendor_mgmt_tab()
    elif page == "account":
        from modules.hq_admin.account_mgmt_tab import render_account_mgmt_tab
        render_account_mgmt_tab()


# 외주업체 관리자
elif role == 'vendor_admin':
    menu = [
        ("대시보드",   "dashboard"),
        ("수거 데이터", "collection"),
        ("수거일정",    "schedule"),
        ("거래처 관리", "customer"),
        ("일반업장",    "biz"),
    ]
    page = render_sidebar(menu)

    if page == "dashboard":
        from modules.vendor_admin.dashboard import render_dashboard
        render_dashboard(vendor)
    elif page == "collection":
        from modules.vendor_admin.collection_tab import render_collection_tab
        render_collection_tab(vendor)
    elif page == "schedule":
        from modules.vendor_admin.schedule_tab import render_schedule_tab
        render_schedule_tab(vendor)
    elif page == "customer":
        from modules.vendor_admin.customer_tab import render_customer_tab
        render_customer_tab(vendor)
    elif page == "biz":
        from modules.vendor_admin.biz_tab import render_biz_tab
        render_biz_tab(vendor)


# 수거기사
elif role == 'driver':
    menu = [
        ("오늘 일정",  "dashboard"),
        ("수거 입력",  "input"),
    ]
    page = render_sidebar(menu)

    if page == "dashboard":
        from modules.driver.dashboard import render_dashboard
        render_dashboard(user)
    elif page == "input":
        from modules.driver.collection_input import render_collection_input
        render_collection_input(user)


# 학교 (행정실 + 영양사)
elif role in ('school_admin', 'school_nutrition'):
    if role == 'school_admin':
        menu = [
            ("대시보드",      "dashboard"),
            ("수거 내역",      "collection"),
            ("정산서 다운로드", "settlement"),
        ]
    else:
        menu = [
            ("대시보드",  "dashboard"),
            ("수거일정",  "schedule"),
            ("수거 조회", "collection"),
        ]

    page = render_sidebar(menu)
    from modules.school.dashboard import render_dashboard
    render_dashboard(user)


# 교육청
elif role == 'edu_office':
    menu = [
        ("대시보드",      "dashboard"),
        ("학교별 현황",   "schools"),
        ("통계 차트",     "chart"),
        ("데이터 다운로드", "download"),
    ]
    page = render_sidebar(menu)
    from modules.edu_office.dashboard import render_dashboard
    render_dashboard(user)


# 알 수 없는 역할
else:
    st.error(f"알 수 없는 역할입니다: {role}")
    st.info("관리자에게 문의하세요.")
    if st.button("로그아웃"):
        logout()
