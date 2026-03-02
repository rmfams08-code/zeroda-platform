# zeroda_platform/modules/vendor_admin/dashboard.py
# ==========================================
# 외주업체 관리자 대시보드
# ==========================================

import streamlit as st
from datetime import datetime, date
from config.settings import COMMON_CSS, CO2_FACTOR, TREE_FACTOR, CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import (
    db_get, get_schools_by_vendor, load_schedule, get_vendor_display_name
)


def render_dashboard(vendor: str):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    biz_name = get_vendor_display_name(vendor)
    st.markdown(f"## 🤝 {biz_name} 관리자 대시보드")

    year  = st.session_state.get('v_year',  CURRENT_YEAR)
    month = st.session_state.get('v_month', CURRENT_MONTH)

    col_y, col_m, _ = st.columns([1, 1, 4])
    with col_y:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=list(range(2023, CURRENT_YEAR + 1)).index(year),
                             key="v_dash_year")
    with col_m:
        month = st.selectbox("월", list(range(1, 13)),
                             index=month - 1, key="v_dash_month")

    st.session_state['v_year']  = year
    st.session_state['v_month'] = month

    # ── 수거 데이터 집계 ──
    rows = db_get('real_collection')
    rows = [r for r in rows
            if r.get('수거업체') == vendor
            and int(r.get('월', 0) or 0) == month
            and str(r.get('년도', '')) == str(year)]

    total_food    = sum(float(r.get('음식물(kg)', 0) or 0) for r in rows)
    total_recycle = sum(float(r.get('재활용(kg)', 0) or 0) for r in rows)
    total_biz     = sum(float(r.get('사업장(kg)', 0) or 0) for r in rows)
    co2_saved     = round((total_food + total_recycle + total_biz) * CO2_FACTOR, 1)

    # ── KPI 카드 ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="custom-card">
            <div class="metric-title">🍱 음식물 수거량</div>
            <div class="metric-value-food">{total_food:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="custom-card custom-card-green">
            <div class="metric-title">♻️ 재활용 수거량</div>
            <div class="metric-value-recycle">{total_recycle:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="custom-card custom-card-purple">
            <div class="metric-title">🏭 사업장 수거량</div>
            <div class="metric-value-biz">{total_biz:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="custom-card custom-card-orange">
            <div class="metric-title">🌿 CO₂ 감축</div>
            <div class="metric-value-total">{co2_saved:,} kg</div>
        </div>""", unsafe_allow_html=True)

    # ── 담당 학교 현황 ──
    st.markdown("### 🏫 담당 학교 수거 현황")
    schools = get_schools_by_vendor(vendor)
    if not schools:
        st.info("배정된 학교가 없습니다.")
        return

    school_data = {}
    for r in rows:
        s  = r.get('학교명', '')
        kg = float(r.get('음식물(kg)', 0) or 0)
        school_data[s] = school_data.get(s, 0) + kg

    cols = st.columns(min(len(schools), 4))
    for i, school in enumerate(schools):
        kg = school_data.get(school, 0)
        with cols[i % 4]:
            color = '#34a853' if kg > 0 else '#ea4335'
            st.markdown(f"""
            <div style="background:#f8f9fa;border-radius:8px;padding:12px;
                        margin-bottom:8px;border-left:4px solid {color};">
                <div style="font-weight:700;font-size:13px;">{school}</div>
                <div style="font-size:18px;font-weight:900;color:{color};">
                    {kg:,.1f} kg</div>
            </div>""", unsafe_allow_html=True)

    # ── 오늘 수거 일정 미리보기 ──
    st.markdown("### 📅 오늘 수거 일정")
    today = date.today()
    weekday_map = {0:'월',1:'화',2:'수',3:'목',4:'금',5:'토',6:'일'}
    today_wd = weekday_map[today.weekday()]

    sched = load_schedule(vendor, today.month)
    if sched and today_wd in sched.get('요일', []):
        today_schools = sched.get('학교', [])
        st.success(f"오늘({today_wd}요일) 수거 학교: {len(today_schools)}개")
        for s in today_schools:
            st.markdown(f"• {s}")
    else:
        st.info(f"오늘({today_wd}요일)은 수거 일정이 없습니다.")