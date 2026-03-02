# zeroda_platform/modules/vendor_admin/collection_tab.py
# ==========================================
# 외주업체 관리자 - 수거 데이터 탭
# ==========================================

import streamlit as st
import pandas as pd
from config.settings import CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import db_get, db_upsert, get_schools_by_vendor


def render_collection_tab(vendor: str):
    st.markdown("## 📋 수거 데이터")

    tab_view, tab_input, tab_pdf = st.tabs(["수거 조회", "수거 입력", "수거일보 PDF"])

    with tab_view:
        _render_view(vendor)
    with tab_input:
        _render_input(vendor)
    with tab_pdf:
        _render_pdf(vendor)


def _render_view(vendor: str):
    st.markdown("### 수거 데이터 조회")

    col1, col2 = st.columns(2)
    with col1:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=2, key="vc_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="vc_month")

    rows = db_get('real_collection')
    rows = [r for r in rows
            if r.get('수거업체') == vendor
            and int(r.get('월', 0) or 0) == month
            and str(r.get('년도', '')) == str(year)]

    if not rows:
        st.info("조건에 맞는 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    display_cols = ['날짜', '학교명', '음식물(kg)', '단가(원)', '공급가', '수거기사']
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    total_kg  = df['음식물(kg)'].astype(float).sum() if '음식물(kg)' in df.columns else 0
    total_amt = df['공급가'].astype(float).sum()     if '공급가'    in df.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("총 수거량",  f"{total_kg:,.1f} kg")
    c2.metric("총 공급가액", f"{total_amt:,.0f} 원")
    c3.metric("수거 건수",  f"{len(rows)} 건")


def _render_input(vendor: str):
    st.markdown("### 수거 실적 입력")
    st.info("기사 앱에서 입력된 데이터가 자동 반영됩니다. 누락 건은 여기서 직접 입력하세요.")

    schools = get_schools_by_vendor(vendor)
    if not schools:
        st.warning("배정된 학교가 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        school = st.selectbox("학교명", schools, key="ci_school")
        date_v = st.date_input("수거 날짜", key="ci_date")
        kg     = st.number_input("음식물 수거량 (kg)", min_value=0.0,
                                  step=0.1, key="ci_kg")
    with col2:
        price  = st.number_input("단가 (원/kg)", min_value=0,
                                  value=162, step=1, key="ci_price")
        driver = st.text_input("수거 기사", key="ci_driver")
        time_v = st.text_input("수거 시간", placeholder="09:30", key="ci_time")

    supply = int(kg * price / 1.1)
    vat    = int(kg * price) - supply
    st.markdown(f"**공급가액:** {supply:,}원  |  **부가세:** {vat:,}원  |  **합계:** {int(kg*price):,}원")

    if st.button("💾 저장", type="primary", key="btn_ci_save"):
        if kg <= 0:
            st.error("수거량을 입력하세요.")
            return
        date_str = str(date_v)
        ok = db_upsert('real_collection', {
            '날짜':      date_str,
            '학교명':    school,
            '음식물(kg)': kg,
            '단가(원)':   price,
            '공급가':     supply,
            '월':         date_v.month,
            '년도':       str(date_v.year),
            '수거업체':   vendor,
            '수거기사':   driver,
            '수거시간':   time_v,
        })
        if ok:
            st.success(f"{school} {date_str} 수거 실적 저장 완료")
        else:
            st.error("저장 실패")


def _render_pdf(vendor: str):
    st.markdown("### 수거일보 PDF 생성")

    col1, col2, col3 = st.columns(3)
    with col1:
        year   = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                              index=2, key="vpdf_year")
    with col2:
        month  = st.selectbox("월", list(range(1, 13)),
                              index=CURRENT_MONTH - 1, key="vpdf_month")
    with col3:
        schools = get_schools_by_vendor(vendor)
        school  = st.selectbox("학교", schools, key="vpdf_school") if schools else None

    if not school:
        st.info("배정된 학교가 없습니다.")
        return

    if st.button("📄 PDF 생성", type="primary", key="btn_vpdf"):
        rows = db_get('real_collection')
        rows = [r for r in rows
                if r.get('학교명') == school
                and r.get('수거업체') == vendor
                and int(r.get('월', 0) or 0) == month
                and str(r.get('년도', '')) == str(year)]

        if not rows:
            st.warning("해당 조건의 수거 데이터가 없습니다.")
            return

        # 계약 단가
        price_rows = db_get('contract_data', {'vendor': vendor})
        price_dict = {r['item']: r['price'] for r in price_rows}
        contract_price = int(price_dict.get('음식물', 162))

        from services.pdf_generator import generate_collection_report_pdf
        pdf = generate_collection_report_pdf(school, year, month,
                                             rows, contract_price)
        if pdf:
            st.download_button("💾 PDF 저장", pdf,
                file_name=f"{year}{month:02d}_{school}_수거일보.pdf",
                mime="application/pdf")
        else:
            st.error("PDF 생성 실패 (reportlab 설치 확인)")