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

    from config.dashboard_helpers import render_weight_metrics, render_env_contribution
    render_weight_metrics(month_data, show_carbon=True)

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

    # 환경 기여 현황 (공통 헬퍼)
    render_env_contribution(month_data)
