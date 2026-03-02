# zeroda_platform/modules/edu_office/dashboard.py
# ==========================================
# 교육청/교육지원청 대시보드
# ★ df_edu_real 미정의 버그 수정
# ==========================================

import streamlit as st
import pandas as pd
from config.settings import COMMON_CSS, CO2_FACTOR, TREE_FACTOR, CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import db_get, get_schools_by_edu_office


def render_dashboard(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    edu_office = user.get('edu_office', '')
    name       = user.get('name', '')

    st.markdown(f"## 🎓 {edu_office or name} 현황")

    year  = st.session_state.get('edu_year',  CURRENT_YEAR)
    month = st.session_state.get('edu_month', CURRENT_MONTH)

    col_y, col_m, _ = st.columns([1, 1, 4])
    with col_y:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=list(range(2023, CURRENT_YEAR + 1)).index(year),
                             key="edu_year_sel")
    with col_m:
        month = st.selectbox("월", list(range(1, 13)),
                             index=month - 1, key="edu_month_sel")

    st.session_state['edu_year']  = year
    st.session_state['edu_month'] = month

    # ── 관할 학교 목록 ──
    schools = get_schools_by_edu_office(edu_office) if edu_office else []

    # ── ★ 버그 수정: df_edu_real 안전하게 생성 ──
    all_rows = db_get('real_collection')
    edu_rows = [r for r in all_rows
                if r.get('학교명') in schools
                and int(r.get('월', 0) or 0) == month
                and str(r.get('년도', '')) == str(year)]

    # ★ 핵심: df_edu_real 항상 정의 (비어있어도 빈 DataFrame)
    df_edu_real = pd.DataFrame(edu_rows) if edu_rows else pd.DataFrame()

    if not schools:
        st.warning("관할 학교 정보가 없습니다. 관리자에게 문의하세요.")
        _render_empty_state()
        return

    # ── KPI ──
    total_food    = float(df_edu_real['음식물(kg)'].sum()) if '음식물(kg)' in df_edu_real.columns else 0
    total_recycle = float(df_edu_real['재활용(kg)'].sum()) if '재활용(kg)' in df_edu_real.columns else 0
    co2_saved     = round(total_food * CO2_FACTOR, 1)
    trees         = round(co2_saved / TREE_FACTOR, 1)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="custom-card">
            <div class="metric-title">🏫 관할 학교</div>
            <div class="metric-value-total">{len(schools)} 개교</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="custom-card">
            <div class="metric-title">🍱 음식물 수거량</div>
            <div class="metric-value-food">{total_food:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="custom-card custom-card-green">
            <div class="metric-title">♻️ 재활용 수거량</div>
            <div class="metric-value-recycle">{total_recycle:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="custom-card custom-card-orange">
            <div class="metric-title">🌿 CO₂ 감축</div>
            <div class="metric-value-total">{co2_saved:,} kg</div>
        </div>""", unsafe_allow_html=True)

    tab_school, tab_chart, tab_download = st.tabs(
        ["학교별 현황", "차트", "데이터 다운로드"])

    with tab_school:
        _render_school_table(schools, df_edu_real)
    with tab_chart:
        _render_chart(schools, df_edu_real)
    with tab_download:
        _render_download(edu_office, year, month, df_edu_real)


def _render_school_table(schools: list, df: pd.DataFrame):
    st.markdown("### 학교별 수거 현황")

    if df.empty:
        st.info("해당 기간 수거 데이터가 없습니다.")
        # 학교 목록만 표시
        for s in schools:
            st.markdown(f"• {s} — 데이터 없음")
        return

    school_summary = []
    for s in schools:
        s_df = df[df['학교명'] == s] if '학교명' in df.columns else pd.DataFrame()
        food_kg = float(s_df['음식물(kg)'].sum()) if not s_df.empty and '음식물(kg)' in s_df.columns else 0
        days    = len(s_df) if not s_df.empty else 0
        school_summary.append({
            '학교명':      s,
            '수거량(kg)': round(food_kg, 1),
            '수거 횟수':   days,
            '상태':        '✅ 정상' if food_kg > 0 else '⚠️ 미수거',
        })

    summary_df = pd.DataFrame(school_summary)
    st.dataframe(summary_df, use_container_width=True)

    no_data = [r['학교명'] for r in school_summary if r['수거량(kg)'] == 0]
    if no_data:
        st.warning(f"미수거 학교 {len(no_data)}개: {', '.join(no_data)}")


def _render_chart(schools: list, df: pd.DataFrame):
    st.markdown("### 학교별 수거량 차트")

    if df.empty or '음식물(kg)' not in df.columns:
        st.info("차트를 표시할 데이터가 없습니다.")
        return

    chart_data = (
        df.groupby('학교명')['음식물(kg)']
          .sum()
          .reset_index()
          .sort_values('음식물(kg)', ascending=False)
    ) if '학교명' in df.columns else pd.DataFrame()

    if chart_data.empty:
        st.info("데이터가 없습니다.")
        return

    st.bar_chart(chart_data.set_index('학교명'))


def _render_download(edu_office: str, year: int, month: int, df: pd.DataFrame):
    st.markdown("### 데이터 다운로드")

    if df.empty:
        st.info("다운로드할 데이터가 없습니다.")
        return

    # CSV
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        "📥 CSV 다운로드", csv,
        file_name=f"{year}{month:02d}_{edu_office}_수거현황.csv",
        mime="text/csv"
    )

    # 엑셀
    if st.button("📥 엑셀 다운로드", key="edu_xl"):
        from services.excel_generator import generate_collection_excel
        data = df.to_dict('records')
        xl = generate_collection_excel(edu_office, year, month, data)
        if xl:
            st.download_button("💾 엑셀 저장", xl,
                file_name=f"{year}{month:02d}_{edu_office}_수거현황.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # 알바로 다운로드 버튼 (기존 기능 유지)
    st.divider()
    st.markdown("### 올바로 연계 다운로드")
    st.info("올바로 시스템 연계용 데이터 형식으로 다운로드합니다.")
    if st.button("📥 올바로 양식", key="edu_allbaro"):
        _generate_allbaro(edu_office, year, month, df)


def _generate_allbaro(edu_office: str, year: int, month: int, df: pd.DataFrame):
    """★ 버그 수정: df_edu_real 대신 매개변수 df 사용"""
    if df.empty:
        st.warning("데이터가 없습니다.")
        return

    try:
        allbaro_cols = {
            '배출자명':   '학교명',
            '폐기물종류': '재활용방법',
            '수거량(kg)': '음식물(kg)',
            '수거일자':   '날짜',
            '수거업체':   '수거업체',
        }
        result = pd.DataFrame()
        for out_col, in_col in allbaro_cols.items():
            if in_col in df.columns:
                result[out_col] = df[in_col]
            else:
                result[out_col] = ''

        csv = result.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "💾 올바로 CSV 저장", csv,
            file_name=f"{year}{month:02d}_{edu_office}_올바로.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"올바로 양식 생성 실패: {e}")


def _render_empty_state():
    st.markdown("""
    <div style="text-align:center;padding:40px;color:#5f6368;">
        <div style="font-size:48px;">🎓</div>
        <div style="font-size:18px;margin-top:10px;">관할 학교 데이터가 없습니다</div>
        <div style="font-size:14px;margin-top:8px;">
            본사 관리자에게 학교 배정을 요청하세요
        </div>
    </div>""", unsafe_allow_html=True)