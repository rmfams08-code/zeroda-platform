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
    from services.settlement_helpers import (
        get_customer_match, build_price_map, correct_row_prices, build_biz_info
    )

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

    # ── 거래처 구분 필터 + 하위 거래처 선택 ──
    _custs = load_customers_from_db(vendor)
    _cust_type_options = ["학교", "기업", "관공서", "일반업장"]
    col_t, col_s = st.columns(2)
    with col_t:
        _sel_type = st.selectbox("거래처 구분", _cust_type_options, key="send_cust_type")
    with col_s:
        # 선택한 구분에 해당하는 거래처 목록
        _type_custs = [
            name for name, info in _custs.items()
            if str(info.get('구분', '학교')) == _sel_type
        ]
        if _sel_type == '학교':
            # 학교: 수거 데이터에서 추출한 학교도 합산
            _data_schools = list(set(r.get('school_name', '') for r in rows if r.get('school_name')))
            _type_custs = sorted(set(_type_custs + _data_schools))
        else:
            _type_custs = sorted(_type_custs)

        if not _type_custs:
            st.warning(f"'{_sel_type}' 구분의 등록된 거래처가 없습니다.")
            return
        _send_choices = ['전체'] + _type_custs
        school = st.selectbox("거래처 선택", _send_choices, key=f"send_cust_{_sel_type}")

    if school != '전체':
        rows = filter_rows_by_school(rows, school)

    # 거래처 정보 조회 + 단가 보정 (공통 헬퍼 사용)
    _cust_info = get_customer_match(vendor, school, _custs) if school != '전체' else {}
    _ct = _sel_type  # 필터에서 선택한 구분 사용
    _price_map = build_price_map(_cust_info)
    if _price_map:
        rows = correct_row_prices(rows, _price_map)
    _biz_info = build_biz_info(_cust_info, school) if school != '전체' else {}

    # 면세/과세 판별 — 학교=면세, 그 외=부가세 10%
    _is_school = (_sel_type == '학교')

    # 데이터 표시
    st.markdown(f"### {year}년 {month}월 · {school if school != '전체' else '전체'}")
    df = pd.DataFrame(rows)
    show = [c for c in ['collect_date','school_name','item_type','weight','unit_price','amount','driver','status'] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    total_weight = sum(float(r.get('weight', 0)) for r in rows)
    total_amount = sum(float(r.get('amount', 0)) for r in rows)

    if _is_school:
        c1, c2 = st.columns(2)
        with c1:
            st.metric("총 수거량", f"{total_weight:,.1f} kg")
        with c2:
            st.metric("공급가액 (면세)", f"{total_amount:,.0f} 원")
    else:
        _vat = round(total_amount * 0.1)
        _total_with_vat = round(total_amount + _vat)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("총 수거량", f"{total_weight:,.1f} kg")
        with c2:
            st.metric("공급가액", f"{total_amount:,.0f} 원")
        with c3:
            st.metric("부가세 (10%)", f"{_vat:,.0f} 원")
        with c4:
            st.metric("합계 (VAT포함)", f"{_total_with_vat:,.0f} 원")

    st.divider()

    # ── 수급자(거래처) 정보 ────────────────
    _type_label = "학교" if _is_school else _sel_type
    st.markdown(f"#### 수급자 정보 ({_type_label})")
    _skp = school.replace(" ", "_")  # key prefix — 거래처 변경 시 위젯 자동 초기화
    _bi_col1, _bi_col2 = st.columns(2)
    with _bi_col1:
        to_email = st.text_input("수신 이메일",
                                  value=_biz_info.get('이메일', ''), key=f"send_email_{_skp}")
        _rep     = st.text_input("대표자", value=_biz_info.get('대표자', ''), key=f"send_rep_{_skp}")
        _biz_no  = st.text_input("사업자번호", value=_biz_info.get('사업자번호', ''), key=f"send_bizno_{_skp}")
    with _bi_col2:
        to_phone  = st.text_input("수신 전화번호 (문자 발송용)",
                                   value=_biz_info.get('전화번호', ''), key=f"send_phone_{_skp}",
                                   placeholder="010-0000-0000")
        _addr     = st.text_input("주소", value=_biz_info.get('주소', ''), key=f"send_addr_{_skp}")
        _biz_type = st.text_input("업태", value=_biz_info.get('업태', ''), key=f"send_btype_{_skp}")
        _biz_item = st.text_input("종목", value=_biz_info.get('종목', ''), key=f"send_bitem_{_skp}")

    # ── 미납 정보 표시 ──
    _overdue_amt = float(_biz_info.get('미납금액', 0) or 0)
    _overdue_mon = _biz_info.get('미납개월', '') or ''
    _overdue_note = _biz_info.get('미납비고', '') or ''
    if _overdue_amt > 0:
        st.error(f"⚠️ **미납 안내** — 미납금액: {_overdue_amt:,.0f}원 | 미납개월: {_overdue_mon or '미입력'}"
                 + (f" | 비고: {_overdue_note}" if _overdue_note else ""))

    # 입력값 반영
    _biz_info.update({
        '상호': school if school != '전체' else '전체', '이메일': to_email,
        '전화번호': to_phone,
        '대표자': _rep, '사업자번호': _biz_no, '주소': _addr,
        '업태': _biz_type, '종목': _biz_item, '구분': _ct
    })

    st.divider()

    # ── 공급자(업체) 정보 ────────────────
    st.markdown("#### 공급자 정보 (업체)")
    vendor_rows = db_get('vendor_info', {'vendor': vendor})
    vinfo = vendor_rows[0] if vendor_rows else {}

    _vi_col1, _vi_col2 = st.columns(2)
    with _vi_col1:
        _v_rep   = st.text_input("대표자", value=vinfo.get('rep', ''), key="send_vrep")
        _v_bizno = st.text_input("사업자번호", value=vinfo.get('biz_no', ''), key="send_vbizno")
    with _vi_col2:
        _v_addr    = st.text_input("주소", value=vinfo.get('address', ''), key="send_vaddr")
        _v_contact = st.text_input("연락처", value=vinfo.get('contact', ''), key="send_vcontact")

    vinfo.update({
        'biz_name': vinfo.get('biz_name', vendor),
        'rep': _v_rep, 'biz_no': _v_bizno,
        'address': _v_addr, 'contact': _v_contact
    })

    st.divider()

    # ── 이메일 내용 ────────────────
    st.markdown("#### 이메일 내용")
    _school_label = school if school != '전체' else '전체'
    subject = st.text_input("제목",
                             value=f"[{vinfo.get('biz_name', vendor)}] {year}년 {month}월 거래명세서 - {_school_label}",
                             key="send_subject")
    # 미납 안내 문구 자동 생성
    _overdue_body = ""
    if _overdue_amt > 0:
        _overdue_body = f"""
※ 미납 안내
미납금액: {_overdue_amt:,.0f}원
미납개월: {_overdue_mon or '확인 필요'}"""
        if _overdue_note:
            _overdue_body += f"\n비고: {_overdue_note}"
        _overdue_body += "\n조속한 납부 부탁드립니다.\n"

    body = st.text_area("본문",
                         value=f"""{_school_label} 담당자님께,

안녕하세요. {vinfo.get('biz_name', vendor)} 입니다.

{year}년 {month}월 거래명세서를 첨부하여 발송드립니다.
확인 후 문의사항이 있으시면 연락 주시기 바랍니다.
{_overdue_body}
감사합니다.
{vinfo.get('biz_name', vendor)} 드림
연락처: {_v_contact}""",
                         height=180, key="send_body")

    st.divider()

    _pdf_filename = f"거래명세서_{_school_label}_{year}{month_str}.pdf"

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("📥 PDF 다운로드", use_container_width=True, key="dl_pdf"):
            try:
                from services.pdf_generator import generate_statement_pdf
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

    with col4:
        if st.button("📱 요약문자", use_container_width=True, key="send_sms_summary"):
            if not to_phone:
                st.error("수신 전화번호를 입력하세요.")
            else:
                try:
                    from services.sms_service import send_statement_sms, build_summary_sms_text
                    _total_w = sum(float(r.get('weight', 0)) for r in rows)
                    _total_a = sum(float(r.get('amount', 0)) for r in rows)
                    sms_text = build_summary_sms_text(
                        vinfo.get('biz_name', vendor), _school_label,
                        year, month, _total_w, _total_a,
                        overdue_amount=_overdue_amt,
                        overdue_months=_overdue_mon
                    )
                    with st.spinner("문자 발송 중..."):
                        success, msg = send_statement_sms(
                            to_phone, sms_text,
                            vendor_name=vinfo.get('biz_name', vendor),
                            vendor_contact=_v_contact
                        )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"문자 발송 실패: {e}")

    with col5:
        if st.button("📋 상세문자", use_container_width=True, key="send_sms_detail"):
            if not to_phone:
                st.error("수신 전화번호를 입력하세요.")
            else:
                try:
                    from services.sms_service import send_statement_sms, build_detail_sms_text
                    _total_w = sum(float(r.get('weight', 0)) for r in rows)
                    _total_a = sum(float(r.get('amount', 0)) for r in rows)
                    sms_text = build_detail_sms_text(
                        vinfo.get('biz_name', vendor), _school_label,
                        year, month, rows, _total_w, _total_a,
                        overdue_amount=_overdue_amt,
                        overdue_months=_overdue_mon
                    )
                    with st.spinner("상세 문자 발송 중..."):
                        success, msg = send_statement_sms(
                            to_phone, sms_text,
                            vendor_name=vinfo.get('biz_name', vendor),
                            vendor_contact=_v_contact
                        )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"문자 발송 실패: {e}")
