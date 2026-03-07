# modules/hq_admin/dashboard.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, get_all_schools, get_all_vendors
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_dashboard():
    st.markdown("## 대시보드 - 본사 관리자")

    # 새로고침 버튼
    col_r, _ = st.columns([1, 5])
    with col_r:
        if st.button("🔄 새로고침", key="hq_dash_refresh"):
            try:
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
            except Exception:
                pass
            st.rerun()

    # 연도/월 필터
    col1, col2 = st.columns(2)
    with col1:
        year  = st.selectbox("연도", [2024, 2025, 2026],
                              index=[2024,2025,2026].index(CURRENT_YEAR)
                              if CURRENT_YEAR in [2024,2025,2026] else 2,
                              key="hq_dash_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                              index=CURRENT_MONTH - 1, key="hq_dash_month")

    month_str = f"{year}-{str(month).zfill(2)}"

    # 통계 카드
    schools  = get_all_schools()
    vendors  = get_all_vendors()
    col_data = db_get('real_collection')
    users    = db_get('users')

    # 이번 달 필터
    month_data = [r for r in col_data
                  if str(r.get('collect_date', '')).startswith(month_str)]

    food_kg    = sum(float(r.get('weight', 0)) for r in month_data
                     if '음식물' in str(r.get('item_type', '')))
    recycle_kg = sum(float(r.get('weight', 0)) for r in month_data
                     if '재활용' in str(r.get('item_type', '')))
    general_kg = sum(float(r.get('weight', 0)) for r in month_data
                     if '일반' in str(r.get('item_type', ''))
                     or ('음식물' not in str(r.get('item_type', ''))
                         and '재활용' not in str(r.get('item_type', ''))))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🍱 음식물 수거량", f"{food_kg:,.1f} kg")
    with c2:
        st.metric("♻️ 재활용 수거량", f"{recycle_kg:,.1f} kg")
    with c3:
        st.metric("🏭 사업장 수거량", f"{general_kg:,.1f} kg")
    with c4:
        try:
            from services.carbon_calculator import calculate_carbon_reduction
            carbon, _ = calculate_carbon_reduction(food_kg, recycle_kg, general_kg)
        except Exception:
            carbon = 0.0
        st.metric("🌿 CO₂ 감축", f"{carbon:,.1f} kg")

    st.divider()

    # 업체별 수거 현황
    st.markdown("### 🏢 업체별 수거 현황")
    if month_data:
        df = pd.DataFrame(month_data)
        if 'vendor' in df.columns and 'weight' in df.columns:
            summary = df.groupby('vendor')['weight'].sum().reset_index()
            summary.columns = ['업체', '수거량(kg)']
            st.dataframe(summary, use_container_width=True, hide_index=True)
        else:
            st.info(f"{year}년 {month}월 수거 데이터가 없습니다.")
    else:
        st.info(f"{year}년 {month}월 수거 데이터가 없습니다.")

    st.divider()

    # 학교별 수거량 TOP 5
    st.markdown("### 🏫 학교별 수거량 TOP 5")
    if month_data:
        df = pd.DataFrame(month_data)
        if 'school_name' in df.columns and 'weight' in df.columns:
            top5 = df.groupby('school_name')['weight'].sum().nlargest(5).reset_index()
            top5.columns = ['학교명', '수거량(kg)']
            st.dataframe(top5, use_container_width=True, hide_index=True)
        else:
            st.info("데이터가 없습니다.")
    else:
        st.info("데이터가 없습니다.")

    st.divider()

    # 환경 기여 현황
    st.markdown("### 🌱 환경 기여 현황")
    total_weight = sum(float(r.get('weight', 0)) for r in month_data)
    try:
        from services.carbon_calculator import calculate_carbon_reduction, calculate_from_rows
        result = calculate_from_rows(month_data)
        carbon_total = result.get('carbon_reduced', 0)
        trees        = result.get('tree_equivalent', 0)
    except Exception:
        carbon_total = 0.0
        trees        = 0.0

    e1, e2, e3 = st.columns(3)
    with e1:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with e2:
        st.metric("CO₂ 감축량", f"{carbon_total:,.1f} kg")
    with e3:
        st.metric("소나무 동등 효과", f"{trees:,.1f} 그루")
