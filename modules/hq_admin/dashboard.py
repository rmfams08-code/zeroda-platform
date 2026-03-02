# zeroda_platform/modules/hq_admin/dashboard.py
# ==========================================
# 본사 관리자 메인 대시보드
# ==========================================

import streamlit as st
from datetime import datetime
from config.settings import COMMON_CSS, CO2_FACTOR, TREE_FACTOR, CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import db_get, get_all_vendors, get_all_schools


def render_dashboard():
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.markdown("## 🏢 본사 관리자 대시보드")

    year  = st.session_state.get('selected_year',  CURRENT_YEAR)
    month = st.session_state.get('selected_month', CURRENT_MONTH)

    col_y, col_m, _ = st.columns([1, 1, 4])
    with col_y:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=list(range(2023, CURRENT_YEAR + 1)).index(year),
                             key="dash_year")
    with col_m:
        month = st.selectbox("월", list(range(1, 13)), index=month - 1, key="dash_month")

    st.session_state['selected_year']  = year
    st.session_state['selected_month'] = month

    # ── 수거 데이터 집계 ──
    rows = db_get('real_collection')
    df_month = [r for r in rows
                if int(r.get('월', 0) or 0) == month
                and str(r.get('년도', '')) == str(year)]

    total_food    = sum(float(r.get('음식물(kg)', 0) or 0) for r in df_month)
    total_recycle = sum(float(r.get('재활용(kg)', 0) or 0) for r in df_month)
    total_biz     = sum(float(r.get('사업장(kg)', 0) or 0) for r in df_month)
    total_all     = total_food + total_recycle + total_biz
    co2_saved     = round(total_all * CO2_FACTOR, 1)
    trees         = round(co2_saved / TREE_FACTOR, 1)

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

    # ── 업체별 수거 현황 ──
    st.markdown("### 📊 업체별 수거 현황")
    vendors = get_all_vendors()
    if vendors and df_month:
        cols = st.columns(min(len(vendors), 4))
        for i, vendor in enumerate(vendors):
            v_rows = [r for r in df_month if r.get('수거업체') == vendor]
            v_kg   = sum(float(r.get('음식물(kg)', 0) or 0) for r in v_rows)
            with cols[i % 4]:
                st.metric(label=vendor, value=f"{v_kg:,.1f} kg",
                          delta=f"{len(v_rows)}건")
    else:
        st.info(f"{year}년 {month}월 수거 데이터가 없습니다.")

    # ── 학교별 수거량 TOP 5 ──
    st.markdown("### 🏫 학교별 수거량 TOP 5")
    if df_month:
        school_kg = {}
        for r in df_month:
            s  = r.get('학교명', '미상')
            kg = float(r.get('음식물(kg)', 0) or 0)
            school_kg[s] = school_kg.get(s, 0) + kg

        top5 = sorted(school_kg.items(), key=lambda x: x[1], reverse=True)[:5]
        for rank, (school, kg) in enumerate(top5, 1):
            pct = (kg / total_food * 100) if total_food > 0 else 0
            st.markdown(f"**{rank}위 {school}** — {kg:,.1f} kg ({pct:.1f}%)")
            st.progress(pct / 100)
    else:
        st.info("데이터가 없습니다.")

    # ── 환경 기여 요약 ──
    st.markdown("### 🌱 환경 기여 현황")
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        st.metric("총 수거량", f"{total_all:,.1f} kg")
    with ec2:
        st.metric("CO₂ 감축량", f"{co2_saved:,} kg")
    with ec3:
        st.metric("소나무 동등 효과", f"{trees:,} 그루")