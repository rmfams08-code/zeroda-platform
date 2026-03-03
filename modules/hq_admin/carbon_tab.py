# modules/hq_admin/carbon_tab.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, get_all_schools, get_all_vendors
from services.carbon_calculator import calculate_from_rows, CARBON_FACTOR
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_carbon_tab():
    st.markdown("## 탄소배출 감축 현황")

    tab1, tab2, tab3 = st.tabs(["📊 전체 현황", "🏫 학교별 순위", "📥 리포트 다운로드"])

    with tab1:
        _render_overview()
    with tab2:
        _render_by_school()
    with tab3:
        _render_report()


def _render_overview():
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                            key="cb_year")
    with col2:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="cb_month")

    rows = db_get('real_collection')
    if not rows:
        st.info("수거 데이터가 없습니다.")
        return

    # 필터
    filtered = [r for r in rows if str(r.get('collect_date', '')).startswith(str(year))]
    if month != '전체':
        m = str(month).zfill(2)
        filtered = [r for r in filtered if f"-{m}-" in str(r.get('collect_date', ''))]

    if not filtered:
        st.info("해당 기간 데이터가 없습니다.")
        return

    result = calculate_from_rows(filtered)

    # 핵심 메트릭
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 수거량", f"{sum(result[k] for k in ['food_kg','recycle_kg','general_kg']):,.0f} kg")
    with c2:
        st.metric("탄소 감축량", f"{result['carbon_reduced']:,.1f} kg CO₂")
    with c3:
        st.metric("나무 식재 환산", f"{result['tree_equivalent']:,.0f} 그루")
    with c4:
        st.metric("CO₂ 톤 환산", f"{result['carbon_reduced']/1000:,.2f} tCO₂")

    st.divider()

    # 품목별 기여도
    st.markdown("#### 품목별 탄소감축 기여도")
    by_item = result['by_item']
    item_kg_map = {'음식물': result['food_kg'], '재활용': result['recycle_kg'], '일반': result['general_kg']}
    df_item = pd.DataFrame([
        {'품목': k, '탄소감축(kg CO₂)': v, '수거량(kg)': item_kg_map.get(k, 0)}
        for k, v in by_item.items()
    ])
    st.dataframe(df_item, use_container_width=True, hide_index=True)

    # 월별 추이 (전체 기간)
    if month == '전체':
        st.markdown("#### 월별 탄소감축 추이")
        monthly = {}
        for r in filtered:
            cd = str(r.get('collect_date', ''))
            if len(cd) >= 7:
                ym = cd[:7]
                if ym not in monthly:
                    monthly[ym] = []
                monthly[ym].append(r)

        if monthly:
            trend = []
            for ym in sorted(monthly.keys()):
                res = calculate_from_rows(monthly[ym])
                trend.append({'월': ym, '탄소감축(kg CO₂)': res['carbon_reduced']})
            df_trend = pd.DataFrame(trend).set_index('월')
            st.line_chart(df_trend)


def _render_by_school():
    year = st.selectbox("연도", [2024, 2025, 2026],
                        index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                        key="cb_rank_year")

    rows = [r for r in db_get('real_collection')
            if str(r.get('collect_date', '')).startswith(str(year))]

    if not rows:
        st.info("데이터가 없습니다.")
        return

    # 학교별 집계
    from collections import defaultdict
    by_school = defaultdict(list)
    for r in rows:
        sn = r.get('school_name', r.get('학교명', ''))
        if sn:
            by_school[sn].append(r)

    ranking = []
    for school, school_rows in by_school.items():
        res = calculate_from_rows(school_rows)
        ranking.append({
            '학교명':          school,
            '총수거량(kg)':    res['food_kg'] + res['recycle_kg'] + res['general_kg'],
            '탄소감축(kg CO₂)': res['carbon_reduced'],
            '나무환산(그루)':   res['tree_equivalent'],
        })

    df = pd.DataFrame(ranking).sort_values('탄소감축(kg CO₂)', ascending=False).reset_index(drop=True)
    df.index += 1
    st.dataframe(df, use_container_width=True)

    # 차트
    if not df.empty:
        st.bar_chart(df.set_index('학교명')['탄소감축(kg CO₂)'].head(10))


def _render_report():
    st.markdown("### 교육청 제출용 리포트")

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026], key="cb_rep_year")
    with col2:
        fmt = st.selectbox("파일 형식", ["엑셀(XLSX)", "CSV"], key="cb_rep_fmt")

    rows = [r for r in db_get('real_collection')
            if str(r.get('collect_date', '')).startswith(str(year))]

    if not rows:
        st.warning("해당 연도 데이터가 없습니다.")
        return

    from collections import defaultdict
    by_school = defaultdict(list)
    for r in rows:
        sn = r.get('school_name', '')
        if sn:
            by_school[sn].append(r)

    report_rows = []
    for school, school_rows in sorted(by_school.items()):
        res = calculate_from_rows(school_rows)
        report_rows.append({
            '학교명':          school,
            '음식물수거(kg)':  res['food_kg'],
            '재활용수거(kg)':  res['recycle_kg'],
            '일반수거(kg)':    res['general_kg'],
            '탄소감축량(kgCO₂)': res['carbon_reduced'],
            '나무식재환산(그루)': res['tree_equivalent'],
        })

    df = pd.DataFrame(report_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    total = calculate_from_rows(rows)
    st.info(f"전체 합계 | 탄소감축: {total['carbon_reduced']:,.1f} kg CO₂ | 나무환산: {total['tree_equivalent']:,.0f} 그루")

    if fmt == "엑셀(XLSX)":
        from services.excel_generator import generate_monthly_summary_excel
        from io import BytesIO
        import openpyxl
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=f'{year}탄소감축')
        st.download_button("📥 엑셀 다운로드", data=buf.getvalue(),
                           file_name=f"탄소감축리포트_{year}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("📥 CSV 다운로드", data=csv.encode('utf-8-sig'),
                           file_name=f"탄소감축리포트_{year}.csv",
                           mime="text/csv")
