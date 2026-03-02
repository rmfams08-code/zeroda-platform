# zeroda_platform/modules/hq_admin/settlement_tab.py
# ==========================================
# 본사 관리자 - 정산 탭
# ==========================================

import streamlit as st
import pandas as pd
from config.settings import CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import db_get, get_all_vendors, get_all_schools


def render_settlement_tab():
    st.markdown("## 💰 정산 관리")

    tab_month, tab_school, tab_send = st.tabs(
        ["월별 정산", "학교별 정산", "정산서 발송"])

    with tab_month:
        _render_monthly_settlement()
    with tab_school:
        _render_school_settlement()
    with tab_send:
        _render_send_settlement()


def _get_settlement_data(year, month, vendor=None):
    """정산 데이터 집계"""
    rows = db_get('real_collection')
    rows = [r for r in rows
            if int(r.get('월', 0) or 0) == month
            and str(r.get('년도', '')) == str(year)]
    if vendor and vendor != '전체':
        rows = [r for r in rows if r.get('수거업체') == vendor]

    school_data = {}
    for r in rows:
        school = r.get('학교명', '미상')
        kg     = float(r.get('음식물(kg)', 0) or 0)
        price  = float(r.get('단가(원)', 162) or 162)
        amt    = int(kg * price)
        vendor_name = r.get('수거업체', '')

        if school not in school_data:
            school_data[school] = {
                '학교명': school, '수거량': 0,
                '단가': int(price), '금액': 0, '업체': vendor_name
            }
        school_data[school]['수거량'] += kg
        school_data[school]['금액']   += amt

    return list(school_data.values())


def _render_monthly_settlement():
    st.markdown("### 월별 정산 현황")

    col1, col2, col3 = st.columns(3)
    with col1:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=2, key="sett_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="sett_month")
    with col3:
        vendors = ['전체'] + get_all_vendors()
        vendor  = st.selectbox("업체", vendors, key="sett_vendor")

    data = _get_settlement_data(year, month, vendor)
    if not data:
        st.info("정산 데이터가 없습니다.")
        return

    df = pd.DataFrame(data)
    df['공급가액'] = (df['금액'] / 1.1).astype(int)
    df['부가세']   = df['금액'] - df['공급가액']

    st.dataframe(
        df[['학교명', '수거량', '단가', '공급가액', '부가세', '금액', '업체']],
        use_container_width=True
    )

    total_amt = df['금액'].sum()
    total_sup = df['공급가액'].sum()
    total_vat = df['부가세'].sum()
    total_kg  = df['수거량'].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 수거량",  f"{total_kg:,.1f} kg")
    c2.metric("공급가액 합계", f"{total_sup:,} 원")
    c3.metric("부가세 합계",  f"{total_vat:,} 원")
    c4.metric("합계금액",    f"{total_amt:,} 원")

    # 엑셀/홈택스 다운로드
    col_xl, col_ht = st.columns(2)
    with col_xl:
        if st.button("📥 정산 엑셀", key="dl_sett_xl"):
            from services.excel_generator import generate_settlement_excel
            xl = generate_settlement_excel(vendor, year, month, data)
            if xl:
                st.download_button("💾 저장", xl,
                    file_name=f"{year}{month:02d}_정산서.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_ht:
        if st.button("📥 홈택스 양식", key="dl_hometax"):
            from services.excel_generator import generate_hometax_excel
            xl = generate_hometax_excel(vendor, year, month, data)
            if xl:
                st.download_button("💾 저장", xl,
                    file_name=f"{year}{month:02d}_홈택스.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _render_school_settlement():
    st.markdown("### 학교별 정산서")

    col1, col2, col3 = st.columns(3)
    with col1:
        year   = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                              index=2, key="sch_sett_year")
    with col2:
        month  = st.selectbox("월", list(range(1, 13)),
                              index=CURRENT_MONTH - 1, key="sch_sett_month")
    with col3:
        schools = get_all_schools()
        school  = st.selectbox("학교", schools, key="sch_sett_school") if schools else None

    if not school:
        st.info("학교 마스터 데이터가 없습니다.")
        return

    rows = db_get('real_collection')
    rows = [r for r in rows
            if r.get('학교명') == school
            and int(r.get('월', 0) or 0) == month
            and str(r.get('년도', '')) == str(year)]

    if not rows:
        st.info(f"{school} {year}년 {month}월 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    display_cols = ['날짜', '음식물(kg)', '단가(원)', '공급가', '수거업체']
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    total_kg  = df['음식물(kg)'].astype(float).sum() if '음식물(kg)' in df.columns else 0
    total_amt = df['공급가'].astype(float).sum()     if '공급가'    in df.columns else 0

    c1, c2 = st.columns(2)
    c1.metric("총 수거량", f"{total_kg:,.1f} kg")
    c2.metric("총 금액",   f"{total_amt:,.0f} 원")

    if st.button("📄 PDF 정산서 생성", key="gen_pdf"):
        from services.pdf_generator import generate_collection_report_pdf
        pdf = generate_collection_report_pdf(school, year, month, rows)
        if pdf:
            st.download_button("💾 PDF 저장", pdf,
                file_name=f"{year}{month:02d}_{school}_정산서.pdf",
                mime="application/pdf")
        else:
            st.error("PDF 생성 실패 (reportlab 설치 확인)")


def _render_send_settlement():
    st.markdown("### 📧 정산서 이메일 발송")

    col1, col2 = st.columns(2)
    with col1:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=2, key="send_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="send_month")

    # 학교별 이메일 목록
    customer_rows = db_get('customer_info')
    school_emails = {
        r['name']: r.get('email', '')
        for r in customer_rows if r.get('email')
    }

    if not school_emails:
        st.warning("등록된 학교 이메일이 없습니다. 거래처 관리에서 이메일을 등록하세요.")
        return

    st.markdown(f"이메일 등록 학교: **{len(school_emails)}개**")

    if st.button("📨 전체 일괄 발송", type="primary", key="send_all"):
        from services.pdf_generator   import generate_collection_report_pdf
        from services.excel_generator import generate_settlement_excel
        from services.email_service   import send_bulk_settlement_emails

        recipients = []
        data_all = _get_settlement_data(year, month)

        for school, email in school_emails.items():
            s_rows = db_get('real_collection')
            s_rows = [r for r in s_rows
                      if r.get('학교명') == school
                      and int(r.get('월', 0) or 0) == month
                      and str(r.get('년도', '')) == str(year)]
            if not s_rows:
                continue

            s_data = [d for d in data_all if d['학교명'] == school]
            pdf    = generate_collection_report_pdf(school, year, month, s_rows)
            xl     = generate_settlement_excel(school, year, month, s_data)

            recipients.append({
                'email': email, 'school': school,
                'year': year, 'month': month,
                'pdf': pdf, 'excel': xl
            })

        if recipients:
            with st.spinner(f"{len(recipients)}개 학교 발송 중..."):
                result = send_bulk_settlement_emails(recipients)
            st.success(f"✅ 성공: {len(result['성공'])}건")
            if result['실패']:
                st.error(f"❌ 실패: {len(result['실패'])}건")
                for f in result['실패']:
                    st.caption(f"  • {f['school']}: {f['error']}")
        else:
            st.warning("발송 대상 데이터가 없습니다.")