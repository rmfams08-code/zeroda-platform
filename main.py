# zeroda_platform/main.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from config.settings import ROLES, ROLE_ICONS
from database.db_init import (init_db, migrate_csv_to_db, migrate_vendor_names,
                               migrate_school_alias, migrate_customer_price,
                               migrate_safety_tables, migrate_schedules_unique,
                               migrate_biz_to_customer, migrate_customer_recycler,
                               migrate_customer_gps, migrate_expenses_table,
                               migrate_meal_tables, migrate_school_nutrition_to_meal,
                               migrate_processing_confirm_table,
                               migrate_meal_analysis_remark,
                               migrate_customer_fixed_fee,
                               migrate_neis_school_code,
                               migrate_meal_schedules_table,
                               migrate_user_approval_status)
from auth.login import render_login_page, is_logged_in, logout, get_current_user

st.set_page_config(
    page_title="ZERODA",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def startup():
    init_db()
    migrate_schedules_unique()  # schedules 테이블 vendor+month UNIQUE 제약 추가
    migrate_csv_to_db()
    migrate_vendor_names()  # vendor 필드 업체명→ID 자동 교정
    migrate_school_alias()  # school_master alias 컬럼 자동 추가
    migrate_customer_price()  # customer_info 단가 컬럼 자동 추가
    migrate_safety_tables()   # 안전관리 평가 테이블 자동 생성 (FEAT-02)
    migrate_biz_to_customer()  # 일반업장 → 거래처 통합 마이그레이션
    migrate_customer_recycler()  # customer_info recycler(재활용자) 컬럼 자동 추가
    migrate_customer_gps()       # customer_info GPS 좌표 컬럼 자동 추가
    migrate_expenses_table()     # 월말정산 지출내역 테이블 자동 생성
    migrate_meal_tables()        # 단체급식 관리 테이블 자동 생성
    migrate_school_nutrition_to_meal()  # school_nutrition → meal_manager 역할 전환
    migrate_processing_confirm_table()   # 처리확인(계근표) 테이블 자동 생성
    migrate_meal_analysis_remark()       # meal_analysis remark 컬럼 추가 (잔반 특이사항)
    migrate_customer_fixed_fee()         # customer_info 월 고정비용 컬럼 추가 (기타 구분)
    migrate_neis_school_code()           # customer_info NEIS 학교코드 컬럼 추가
    migrate_meal_schedules_table()       # 식단기반 수거일정 테이블 자동 생성
    migrate_user_approval_status()       # users 테이블 승인상태 컬럼 추가
    return True

startup()

# 공통 CSS 적용
from config.components import apply_css
apply_css()

if not is_logged_in():
    render_login_page()
    st.stop()

user   = get_current_user()
role   = user.get('role', '')
vendor = user.get('vendor', '')
name   = user.get('name', '')


def render_sidebar(menu_items):
    with st.sidebar:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a73e8,#34a853);
                    padding:20px;border-radius:10px;margin-bottom:20px;text-align:center;">
            <div style="color:white;font-weight:900;font-size:22px;">ZERODA</div>
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

        if 'current_menu' not in st.session_state:
            st.session_state['current_menu'] = menu_items[0][1]

        for label, key in menu_items:
            if st.button(label, key=f"menu_{key}", use_container_width=True):
                st.session_state['current_menu'] = key

        st.divider()
        if st.button("로그아웃", use_container_width=True, key="logout_btn"):
            logout()

    return st.session_state.get('current_menu', menu_items[0][1])


if role == 'admin':
    menu = [
        ("대시보드",     "dashboard"),
        ("수거 데이터",   "data"),
        ("정산 관리",     "settlement"),
        ("수거일정",      "schedule"),
        ("거래처 관리",   "customer"),
        ("외주업체 관리", "vendor"),
        ("계정 관리",     "account"),
        ("안전관리",      "safety"),
        ("탄소감축 현황", "carbon"),
        ("폐기물 분석",   "analytics"),
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
    elif page == "customer":
        import streamlit as st
        from modules.vendor_admin.customer_tab import render_customer_tab
        from database.db_manager import db_get
        vendors = db_get('vendor_info')
        if vendors:
            vendor_opts = {v.get('biz_name', v['vendor']): v['vendor'] for v in vendors}
            sel_label = st.selectbox("업체 선택", list(vendor_opts.keys()), key="hq_cust_vendor")
            render_customer_tab(vendor=vendor_opts[sel_label])
        else:
            import streamlit as st
            st.info("등록된 업체가 없습니다.")
    elif page == "vendor":
        from modules.hq_admin.vendor_mgmt_tab import render_vendor_mgmt_tab
        render_vendor_mgmt_tab()
    elif page == "account":
        from modules.hq_admin.account_mgmt_tab import render_account_mgmt_tab
        render_account_mgmt_tab()
    elif page == "safety":
        from modules.hq_admin.safety_tab import render_safety_tab
        render_safety_tab()
    elif page == "carbon":
        from modules.hq_admin.carbon_tab import render_carbon_tab
        render_carbon_tab()
    elif page == "analytics":
        from modules.hq_admin.analytics_tab import render_analytics_tab
        render_analytics_tab()

elif role == 'vendor_admin':
    menu = [
        ("대시보드",    "dashboard"),
        ("수거 데이터",  "collection"),
        ("수거일정",     "schedule"),
        ("거래처 관리",  "customer"),
        ("거래명세서 발송", "statement"),
        ("안전관리",     "safety"),
        ("수거 분석",    "analytics"),
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
    elif page == "statement":
        from modules.vendor_admin.statement_tab import render_statement_tab
        render_statement_tab(vendor)
    elif page == "safety":
        from modules.vendor_admin.safety_tab import render_safety_tab
        render_safety_tab(vendor)
    elif page == "analytics":
        from modules.vendor_admin.analytics_tab import render_analytics_tab
        render_analytics_tab()

elif role == 'driver':
    # 기사 앱은 탭 통합 단일 페이지
    from modules.driver.dashboard import render_dashboard
    render_dashboard(user)

elif role == 'school_admin':
    menu = [("대시보드", "dashboard")]
    page = render_sidebar(menu)
    from modules.school.dashboard import render_dashboard
    render_dashboard(user)

elif role == 'edu_office':
    menu = [("대시보드", "dashboard")]
    page = render_sidebar(menu)
    from modules.edu_office.dashboard import render_dashboard
    render_dashboard(user)

elif role in ('meal_manager', 'school_nutrition'):
    menu = [
        ("식단 등록",       "menu_register"),
        ("스마트잔반분석",   "smart_waste"),
        ("AI잔반분석",      "ai_waste"),
        ("수거 현황",       "collection"),
        ("정산 확인",       "settlement"),
        ("ESG 보고서",      "esg"),
    ]
    page = render_sidebar(menu)

    if page == "menu_register":
        from modules.meal_manager.menu_register import render_menu_register
        render_menu_register(user)
    elif page == "smart_waste":
        from modules.meal_manager.smart_waste_tab import render_smart_waste_tab
        render_smart_waste_tab(user)
    elif page == "ai_waste":
        from modules.meal_manager.ai_waste_tab import render_ai_waste_tab
        render_ai_waste_tab(user)
    elif page == "collection":
        from modules.meal_manager.school_view import render_school_collection
        render_school_collection(user)
    elif page == "settlement":
        from modules.meal_manager.school_view import render_school_settlement
        render_school_settlement(user)
    elif page == "esg":
        from modules.meal_manager.school_view import render_school_esg
        render_school_esg(user)

else:
    st.error(f"알 수 없는 역할: {role}")
    if st.button("로그아웃"):
        logout()
