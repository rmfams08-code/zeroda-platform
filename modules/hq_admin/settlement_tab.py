# modules/hq_admin/settlement_tab.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, get_all_vendors, get_all_schools, filter_rows_by_school, load_customers_from_db
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_settlement_tab():
    st.markdown("## 정산 관리")

    tab1, tab2 = st.tabs(["📊 정산 현황", "📧 정산서 발송"])

    with tab1:
        _render_summary()

    with tab2:
        _render_send_settlement()


def _render_summary():
    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                            key="set_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="set_month")
    with col3:
        vendors = ['전체'] + get_all_vendors()
        vendor = st.selectbox("업체", vendors, key="set_vendor")

    rows = db_get('real_collection')
    if not rows:
        st.info("수거 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)

    # 필터
    if 'collect_date' in df.columns:
        df['collect_date'] = pd.to_datetime(df['collect_date'], errors='coerce')
        df = df[df['collect_date'].dt.year == year]
        df = df[df['collect_date'].dt.month == month]
    if vendor != '전체' and 'vendor' in df.columns:
        df = df[df['vendor'] == vendor]

    if df.empty:
        st.info("해당 기간 데이터가 없습니다.")
        return

    st.markdown(f"### {year}년 {month}월 정산")

    # 요약 메트릭
    total_weight = df['weight'].sum() if 'weight' in df.columns else 0
    total_amount = (df['weight'] * df['unit_price']).sum() \
        if ('weight' in df.columns and 'unit_price' in df.columns) else 0
    vat = total_amount * 0.1

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with c2:
        st.metric("공급가액", f"{total_amount:,.0f} 원")
    with c3:
        st.metric("합계(VAT포함)", f"{total_amount + vat:,.0f} 원")

    # 학교별 집계
    if 'school_name' in df.columns and 'weight' in df.columns:
        st.markdown("#### 학교별 수거 현황")
        summary = df.groupby('school_name').agg(
            수거량=('weight', 'sum'),
            수거횟수=('weight', 'count')
        ).reset_index()
        summary.columns = ['학교명', '수거량(kg)', '수거횟수']
        summary = summary.sort_values('수거량(kg)', ascending=False)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    # 상태별 현황
    if 'status' in df.columns:
        st.markdown("#### 수거 상태 현황")
        status_map = {
            'draft':     '📋 임시저장',
            'submitted': '📤 전송완료',
            'confirmed': '✅ 확인완료',
            'rejected':  '❌ 반려',
        }
        df['status_label'] = df['status'].map(status_map).fillna(df['status'])
        status_counts = df['status_label'].value_counts().reset_index()
        status_counts.columns = ['상태', '건수']
        st.dataframe(status_counts, use_container_width=True, hide_index=True)


def _render_send_settlement():
    st.markdown("### 정산서 이메일 발송")

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                            key="send_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="send_month")
    with col3:
        vendors = get_all_vendors()
        if not vendors:
            st.warning("등록된 업체가 없습니다.")
            return
        vendor = st.selectbox("업체 선택", vendors, key="send_vendor")

    month_str = str(month).zfill(2)
    rows = [r for r in db_get('real_collection')
            if r.get('vendor') == vendor
            and str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    if not rows:
        st.warning("해당 기간 수거 데이터가 없습니다.")
        return

    # 학교 선택
    schools = list(set(r.get('school_name', '') for r in rows if r.get('school_name')))
    school = st.selectbox("학교 선택", ['전체'] + sorted(schools), key="send_school")

    if school != '전체':
        rows = filter_rows_by_school(rows, school)

    df = pd.DataFrame(rows)
    show = [c for c in ['collect_date','school_name','item_type','weight','status'] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    total_weight = sum(float(r.get('weight', 0)) for r in rows)
    total_amount = sum(float(r.get('weight', 0)) * float(r.get('unit_price', 0)) for r in rows)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with c2:
        st.metric("공급가액", f"{total_amount:,.0f} 원")

    st.divider()

    # 수신처 이메일
    to_email = st.text_input("수신 이메일", key="send_email",
                              placeholder="school@email.com")
    subject = st.text_input("제목",
                             value=f"[하영자원] {year}년 {month}월 정산서 - {school if school != '전체' else '전체'}",
                             key="send_subject")
    body = st.text_area("본문",
                         value=f"안녕하세요.\n\n{year}년 {month}월 정산서를 첨부하여 발송드립니다.\n\n감사합니다.",
                         height=120, key="send_body")

    # 거래처 구분 조회 (면세/과세 판단용)
    _custs = load_customers_from_db(vendor)
    if school != '전체':
        _cust_match = _custs.get(school, {})
        if not _cust_match:
            for _ck, _cv in _custs.items():
                if _cv.get('상호') == school:
                    _cust_match = _cv
                    break
        _ct = _cust_match.get('구분', '학교')
    else:
        _ct = '학교'

    # 거래처 정보 (biz_info) 조회 — PDF에 실제 데이터 전달 (외주업체와 동일)
    _biz_info = {}
    if school != '전체':
        _cust_match2 = _custs.get(school, {})
        if not _cust_match2:
            for _ck2, _cv2 in _custs.items():
                if _cv2.get('상호') == school:
                    _cust_match2 = _cv2
                    break
        if _cust_match2:
            _biz_info = {
                '상호': _cust_match2.get('상호', school),
                '사업자번호': _cust_match2.get('사업자번호', ''),
                '대표자': _cust_match2.get('대표자', ''),
                '주소': _cust_match2.get('주소', ''),
                '업태': _cust_match2.get('업태', ''),
                '종목': _cust_match2.get('종목', ''),
                '이메일': _cust_match2.get('이메일', ''),
                '구분': _cust_match2.get('구분', '학교'),
            }

    _school_label = school if school != '전체' else '전체'
    _pdf_filename = f"거래명세서_{_school_label}_{year}{month_str}.pdf"

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📥 PDF 다운로드", use_container_width=True, key="dl_pdf"):
            try:
                from services.pdf_generator import generate_statement_pdf
                vendor_rows = db_get('vendor_info', {'vendor': vendor})
                vinfo = vendor_rows[0] if vendor_rows else {}
                pdf = generate_statement_pdf(
                    vendor, _school_label,
                    year, month, rows, _biz_info, vinfo, cust_type=_ct
                )
                st.download_button("PDF 다운로드", data=pdf,
                                   file_name=_pdf_filename, mime="application/pdf",
                                   use_container_width=True)
                st.success("PDF 생성 완료!")
            except Exception as e:
                st.error(f"PDF 생성 실패: {e}")

    with col2:
        if st.button("📥 엑셀 다운로드", use_container_width=True, key="dl_excel"):
            try:
                from services.excel_generator import generate_collection_excel
                excel_bytes = generate_collection_excel(rows)
                _xls_filename = f"수거내역_{_school_label}_{year}{month_str}.xlsx"
                st.download_button("엑셀 다운로드", data=excel_bytes,
                                   file_name=_xls_filename,
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
                st.success("엑셀 생성 완료!")
            except Exception as e:
                st.error(f"엑셀 생성 실패: {e}")

    with col3:
        if st.button("📧 이메일 발송", type="primary", use_container_width=True, key="send_btn"):
            if not to_email:
                st.error("수신 이메일을 입력하세요.")
            else:
                try:
                    from services.pdf_generator import generate_statement_pdf
                    from services.email_service import send_statement_email
                    vendor_rows = db_get('vendor_info', {'vendor': vendor})
                    vinfo = vendor_rows[0] if vendor_rows else {}
                    pdf = generate_statement_pdf(
                        vendor, _school_label,
                        year, month, rows, _biz_info, vinfo, cust_type=_ct
                    )
                    with st.spinner("발송 중..."):
                        success, msg = send_statement_email(
                            to_email, subject, body, pdf, _pdf_filename
                        )
                    if success:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"발송 실패: {e}")
