# zeroda_platform/modules/hq_admin/data_tab.py
# ==========================================
# 본사 관리자 - 수거 데이터 탭
# ==========================================

import streamlit as st
import pandas as pd
from config.settings import CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import db_get, db_upsert, db_delete, get_all_schools, get_all_vendors


def render_data_tab():
    st.markdown("## 📋 수거 데이터 관리")

    tab_real, tab_sim, tab_upload = st.tabs(["실제 수거", "시뮬레이션", "데이터 업로드"])

    # ── 실제 수거 데이터 ──────────────────────
    with tab_real:
        _render_real_data()

    # ── 시뮬레이션 데이터 ────────────────────
    with tab_sim:
        _render_sim_data()

    # ── 데이터 업로드 ────────────────────────
    with tab_upload:
        _render_upload()


def _render_real_data():
    st.markdown("### 실제 수거 데이터")

    col1, col2, col3 = st.columns(3)
    with col1:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=2, key="real_year")
    with col2:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="real_month")
    with col3:
        vendors = ['전체'] + get_all_vendors()
        vendor  = st.selectbox("업체", vendors, key="real_vendor")

    rows = db_get('real_collection')

    # 필터
    if month != '전체':
        rows = [r for r in rows if int(r.get('월', 0) or 0) == int(month)]
    if vendor != '전체':
        rows = [r for r in rows if r.get('수거업체') == vendor]
    rows = [r for r in rows if str(r.get('년도', '')) == str(year)]

    if not rows:
        st.info("조건에 맞는 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    display_cols = ['날짜', '학교명', '음식물(kg)', '단가(원)', '공급가',
                    '수거업체', '수거기사', '수거시간']
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    # 집계
    total_kg  = df['음식물(kg)'].astype(float).sum() if '음식물(kg)' in df.columns else 0
    total_amt = df['공급가'].astype(float).sum()     if '공급가'    in df.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("총 수거량",  f"{total_kg:,.1f} kg")
    c2.metric("총 공급가액", f"{total_amt:,.0f} 원")
    c3.metric("수거 건수",  f"{len(rows):,} 건")

    # 엑셀 다운로드
    try:
        from services.excel_generator import generate_collection_excel
        if st.button("📥 엑셀 다운로드", key="dl_real"):
            data = df[display_cols].to_dict('records')
            xl = generate_collection_excel('전체', year,
                                           month if month != '전체' else 0, data)
            if xl:
                st.download_button("💾 저장", xl,
                    file_name=f"{year}_{month}_수거일보.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception:
        pass


def _render_sim_data():
    st.markdown("### 시뮬레이션 데이터")

    rows = db_get('sim_collection')
    if not rows:
        st.info("시뮬레이션 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)
    st.caption(f"총 {len(rows)}행")


def _render_upload():
    st.markdown("### 📤 수거 데이터 업로드")
    st.info("CSV 또는 엑셀 파일을 업로드하면 DB에 자동 저장됩니다.")

    uploaded = st.file_uploader("파일 선택 (.csv, .xlsx)",
                                type=['csv', 'xlsx'], key="upload_file")
    if not uploaded:
        return

    try:
        if uploaded.name.endswith('.csv'):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)

        st.dataframe(df.head(10))
        st.caption(f"미리보기: 상위 10행 / 전체 {len(df)}행")

        target = st.selectbox("저장 테이블",
                              ['real_collection', 'sim_collection'],
                              key="upload_target")

        if st.button("DB에 저장", type="primary", key="btn_upload"):
            import sqlite3
            from config.settings import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            try:
                df.to_sql(target, conn, if_exists='append', index=False)
                conn.commit()
                st.success(f"{len(df)}행 저장 완료")
            except Exception as e:
                st.error(f"저장 실패: {e}")
            finally:
                conn.close()
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")