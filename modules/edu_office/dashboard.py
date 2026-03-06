# modules/edu_office/dashboard.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, get_all_schools, get_all_vendors
from services.carbon_calculator import calculate_from_rows
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_dashboard(user):
    st.markdown("## 교육청 - 학교 수거 현황")

    # 새로고침 버튼
    col_r, _ = st.columns([1, 5])
    with col_r:
        if st.button("🔄 새로고침", key="edu_dash_refresh"):
            try:
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
            except Exception:
                pass
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["전체 현황", "학교별 조회", "업체별 현황", "🌿 탄소감축 현황"])

    with tab1:
        _render_overview()

    with tab2:
        _render_by_school()

    with tab3:
        _render_by_vendor()

    with tab4:
        _render_carbon()


def _render_overview():
    schools  = get_all_schools()
    all_rows = db_get('real_collection')

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("관할 학교 수", f"{len(schools)}개")
    with c2:
        total = sum(float(r.get('weight', 0)) for r in all_rows)
        st.metric("누적 수거량", f"{total:,.0f} kg")
    with c3:
        this = [r for r in all_rows if f"-{str(CURRENT_MONTH).zfill(2)}-" in str(r.get('collect_date', ''))]
        st.metric(f"{CURRENT_MONTH}월 수거량", f"{sum(float(r.get('weight',0)) for r in this):,.0f} kg")
    with c4:
        vendors = get_all_vendors()
        st.metric("등록 업체 수", f"{len(vendors)}개")

    st.divider()
    st.markdown("### 학교별 수거 현황")

    if not all_rows:
        st.info("수거 데이터가 없습니다.")
        return

    df = pd.DataFrame(all_rows)
    if 'school_name' in df.columns and 'weight' in df.columns:
        summary = df.groupby('school_name')['weight'].agg(['sum','count']).reset_index()
        summary.columns = ['학교명', '총수거량(kg)', '수거횟수']
        summary = summary.sort_values('총수거량(kg)', ascending=False)
        st.dataframe(summary, use_container_width=True, hide_index=True)


def _render_by_school():
    schools = get_all_schools()
    if not schools:
        st.info("등록된 학교가 없습니다.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        school = st.selectbox("학교 선택", schools, key="edu_school")
    with col2:
        year = st.selectbox("연도", [2024, 2025, 2026], key="edu_year")
    with col3:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="edu_month")

    rows = [r for r in db_get('real_collection') if r.get('school_name') == school]

    if month != '전체':
        month_str = str(month).zfill(2)
        rows = [r for r in rows if str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    if not rows:
        st.info("해당 조건의 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    show = [c for c in ['collect_date','vendor','item_type','weight','driver'] if c in df.columns]
    st.dataframe(df[show].sort_values('collect_date', ascending=False) if 'collect_date' in df.columns else df[show],
                 use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")
    with c2:
        st.metric("수거 횟수", f"{len(df)}회")


def _render_by_vendor():
    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        vendor = st.selectbox("업체 선택", vendors, key="edu_vendor")
    with col2:
        year = st.selectbox("연도", [2024, 2025, 2026], key="edu_vendor_year")

    rows = [r for r in db_get('real_collection')
            if r.get('vendor') == vendor
            and str(r.get('collect_date', '')).startswith(str(year))]

    if not rows:
        st.info("해당 업체의 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")

    if 'school_name' in df.columns:
        by_school = df.groupby('school_name')['weight'].sum().reset_index()
        by_school.columns = ['학교명', '수거량(kg)']
        by_school = by_school.sort_values('수거량(kg)', ascending=False)
        st.dataframe(by_school, use_container_width=True, hide_index=True)


def _render_carbon():
    st.markdown("### 탄소배출 감축 현황")

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                            key="edu_cb_year")
    with col2:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="edu_cb_month")

    rows = [r for r in db_get('real_collection')
            if str(r.get('collect_date', '')).startswith(str(year))]
    if month != '전체':
        m = str(month).zfill(2)
        rows = [r for r in rows if f"-{m}-" in str(r.get('collect_date', ''))]

    if not rows:
        st.info("해당 기간 데이터가 없습니다.")
        return

    result = calculate_from_rows(rows)

    # 핵심 메트릭
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total_kg = result['food_kg'] + result['recycle_kg'] + result['general_kg']
        st.metric("총 수거량", f"{total_kg:,.0f} kg")
    with c2:
        st.metric("탄소 감축량", f"{result['carbon_reduced']:,.1f} kg CO₂")
    with c3:
        st.metric("나무 식재 환산", f"{result['tree_equivalent']:,.0f} 그루")
    with c4:
        st.metric("CO₂ 톤 환산", f"{result['carbon_reduced']/1000:,.2f} tCO₂")

    st.divider()

    # 학교별 탄소감축 순위
    st.markdown("#### 학교별 탄소감축 순위")
    from collections import defaultdict
    by_school = defaultdict(list)
    for r in rows:
        sn = r.get('school_name', '')
        if sn:
            by_school[sn].append(r)

    ranking = []
    for school, school_rows in by_school.items():
        res = calculate_from_rows(school_rows)
        ranking.append({
            '학교명': school,
            '탄소감축(kg CO₂)': res['carbon_reduced'],
            '나무환산(그루)': res['tree_equivalent'],
        })

    if ranking:
        import pandas as pd
        df = pd.DataFrame(ranking).sort_values('탄소감축(kg CO₂)', ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index('학교명')['탄소감축(kg CO₂)'])
