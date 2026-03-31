# modules/vendor_admin/statement_tab.py
# 거래명세서 생성 및 이메일 발송
import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_manager import db_get, get_schools_by_vendor, load_customers_from_db, filter_rows_by_school, get_unit_price
from services.pdf_generator import generate_statement_pdf
from services.excel_generator import generate_collection_excel
from services.email_service import send_statement_email
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_statement_tab(vendor):
    st.markdown("## 정산 관리")

    stab1, stab2 = st.tabs(["📊 정산 현황", "📧 거래명세서 발송"])

    with stab1:
        _render_vendor_summary(vendor)

    with stab2:
        _render_vendor_send(vendor)


def _render_vendor_summary(vendor):
    """외주업체 정산 현황 요약 (본사와 동일 패턴)"""
    col1, col2 = st.columns(2)
    with col1:
        _sy = st.selectbox("연도", [2024, 2025, 2026],
                           index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                           key="vstmt_sum_year")
    with col2:
        _sm = st.selectbox("월", list(range(1, 13)),
                           index=CURRENT_MONTH - 1, key="vstmt_sum_month")

    _month_str = str(_sm).zfill(2)
    rows = [r for r in db_get('real_collection')
            if r.get('vendor') == vendor
            and str(r.get('collect_date', '')).startswith(f"{_sy}-{_month_str}")]

    if not rows:
        st.info("해당 기간 수거 데이터가 없습니다.")
        return

    st.markdown(f"### {_sy}년 {_sm}월 정산 현황")

    df = pd.DataFrame(rows)
    total_weight = df['weight'].sum() if 'weight' in df.columns else 0
    total_amount = (df['weight'] * df['unit_price']).sum() \
        if ('weight' in df.columns and 'unit_price' in df.columns) else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with c2:
        st.metric("공급가액", f"{total_amount:,.0f} 원")
    with c3:
        st.metric("총 건수", f"{len(rows)}건")

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


def _render_vendor_send(vendor):
    """외주업체 거래명세서 발송 (기존 기능 유지)"""
    # ── 필터 ──────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                            key="stmt_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="stmt_month")
    with col3:
        schools = get_schools_by_vendor(vendor)
        if not schools:
            st.warning("담당 학교가 없습니다.")
            return
        school = st.selectbox("학교 선택", schools, key="stmt_school")

    # ── 수거 데이터 조회 + 단가 보정 (공통 헬퍼 사용) ──
    from services.settlement_helpers import (
        get_customer_match, build_price_map, correct_row_prices
    )
    month_str = str(month).zfill(2)
    all_rows = db_get('real_collection')
    rows = [r for r in filter_rows_by_school(all_rows, school)
            if r.get('vendor') == vendor
            and str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    _all_customers = load_customers_from_db(vendor)
    _cust_info = get_customer_match(vendor, school, _all_customers)
    _price_map = build_price_map(_cust_info)
    if _price_map:
        rows = correct_row_prices(rows, _price_map)

    st.markdown(f"### {year}년 {month}월 · {school}")

    if rows:
        df = pd.DataFrame(rows)
        show_cols = [c for c in ['collect_date', 'item_type', 'weight', 'unit_price', 'amount', 'driver', 'memo'] if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True)
        total_weight = sum(float(r.get('weight', 0)) for r in rows)
        total_amount = sum(
            float(r.get('weight', 0)) *
            (float(r.get('unit_price', 0)) or get_unit_price(vendor, school, r.get('item_type', '')))
            for r in rows
        )
        c1, c2 = st.columns(2)
        with c1:
            st.metric("총 수거량", f"{total_weight:,.1f} kg")
        with c2:
            st.metric("공급가액", f"{total_amount:,.0f} 원")
    else:
        st.warning("해당 기간 수거 데이터가 없습니다. 데이터 입력 후 발송하세요.")

    st.divider()

    # ── 수급자(학교) 정보 ─────────────────
    customers = load_customers_from_db(vendor)
    # customer_info 테이블 key가 'name' 컬럼 기준
    biz_info = customers.get(school, {})
    if not biz_info:
        # school_name으로도 시도
        for k, v in customers.items():
            if k == school or v.get('상호') == school:
                biz_info = v
                break

    st.markdown("#### 수급자 정보 (학교)")
    _skp = school.replace(" ", "_")  # key prefix — 학교 변경 시 위젯 자동 초기화
    col1, col2 = st.columns(2)
    with col1:
        to_email = st.text_input("수신 이메일",
                                  value=biz_info.get('이메일', ''), key=f"stmt_email_{_skp}")
        rep      = st.text_input("대표자", value=biz_info.get('대표자', ''), key=f"stmt_rep_{_skp}")
        biz_no   = st.text_input("사업자번호", value=biz_info.get('사업자번호', ''), key=f"stmt_bizno_{_skp}")
    with col2:
        to_phone = st.text_input("수신 전화번호 (문자 발송용)",
                                  value=biz_info.get('전화번호', ''), key=f"stmt_phone_{_skp}",
                                  placeholder="010-0000-0000")
        addr     = st.text_input("주소", value=biz_info.get('주소', ''), key=f"stmt_addr_{_skp}")
        biz_type = st.text_input("업태", value=biz_info.get('업태', ''), key=f"stmt_btype_{_skp}")
        biz_item = st.text_input("종목", value=biz_info.get('종목', ''), key=f"stmt_bitem_{_skp}")

    # 거래처 구분 (면세/과세 판단용)
    _cust_type = _cust_info.get('구분', '학교')

    # 수급자 정보 업데이트
    biz_info.update({
        '상호': school, '이메일': to_email, '전화번호': to_phone,
        '대표자': rep, '사업자번호': biz_no, '주소': addr,
        '업태': biz_type, '종목': biz_item, '구분': _cust_type
    })

    st.divider()

    # ── 공급자(업체) 정보 ────────────────
    st.markdown("#### 공급자 정보 (우리 업체)")
    vendor_rows = db_get('vendor_info', {'vendor': vendor})
    vinfo = vendor_rows[0] if vendor_rows else {}

    col1, col2 = st.columns(2)
    with col1:
        v_rep    = st.text_input("대표자", value=vinfo.get('rep', ''), key="stmt_vrep")
        v_bizno  = st.text_input("사업자번호", value=vinfo.get('biz_no', ''), key="stmt_vbizno")
    with col2:
        v_addr   = st.text_input("주소", value=vinfo.get('address', ''), key="stmt_vaddr")
        v_contact= st.text_input("연락처", value=vinfo.get('contact', ''), key="stmt_vcontact")

    vinfo.update({
        'biz_name': vinfo.get('biz_name', vendor),
        'rep': v_rep, 'biz_no': v_bizno,
        'address': v_addr, 'contact': v_contact
    })

    st.divider()

    # ── 이메일 내용 ───────────────────────
    st.markdown("#### 이메일 내용")
    subject = st.text_input(
        "제목",
        value=f"[{vendor}] {year}년 {month}월 거래명세서 - {school}",
        key=f"stmt_subject_{school}_{year}_{month}"
    )
    body = st.text_area(
        "본문",
        value=f"""{school} 담당자님께,

안녕하세요. {vinfo.get('biz_name', vendor)} 입니다.

{year}년 {month}월 거래명세서를 첨부하여 발송드립니다.
확인 후 문의사항이 있으시면 연락 주시기 바랍니다.

감사합니다.
{vinfo.get('biz_name', vendor)} 드림
연락처: {v_contact}""",
        height=150,
        key=f"stmt_body_{school}_{year}_{month}"
    )

    st.divider()

    # ── 버튼 영역 ─────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        # PDF 미리보기/다운로드
        if st.button("PDF 생성 및 다운로드", use_container_width=True):
            if not rows:
                st.error("수거 데이터가 없어 PDF를 생성할 수 없습니다.")
            else:
                try:
                    pdf_bytes = generate_statement_pdf(
                        vendor, school, year, month, rows, biz_info, vinfo,
                        cust_type=_cust_type
                    )
                    filename = f"거래명세서_{school}_{year}{month_str}.pdf"
                    st.download_button(
                        label="PDF 다운로드",
                        data=pdf_bytes,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True
                    )
                    st.success("PDF 생성 완료!")
                except Exception as e:
                    st.error(f"PDF 생성 실패: {e}")

    with col2:
        # 엑셀 다운로드
        if st.button("엑셀 다운로드", use_container_width=True):
            if not rows:
                st.error("수거 데이터가 없습니다.")
            else:
                try:
                    excel_bytes = generate_collection_excel(vendor, school, year, month, rows)
                    filename = f"수거내역_{school}_{year}{month_str}.xlsx"
                    st.download_button(
                        label="엑셀 다운로드",
                        data=excel_bytes,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    st.success("엑셀 생성 완료!")
                except Exception as e:
                    st.error(f"엑셀 생성 실패: {e}")

    with col3:
        # 이메일 발송
        if st.button("📧 이메일 발송", type="primary", use_container_width=True):
            if not to_email:
                st.error("수신 이메일을 입력하세요.")
            else:
                with st.spinner("PDF 생성 및 발송 중..."):
                    try:
                        pdf_bytes = generate_statement_pdf(
                            vendor, school, year, month, rows or [], biz_info, vinfo,
                            cust_type=_cust_type
                        )
                        filename = f"거래명세서_{school}_{year}{month_str}.pdf"
                        success, msg = send_statement_email(
                            to_email, subject, body, pdf_bytes, filename
                        )
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)
                            if "SMTP 설정" in msg or "인증" in msg:
                                st.info("💡 Streamlit Cloud → Manage App → Secrets 에서\n"
                                        "NAVER_SMTP_USER, NAVER_SMTP_APP_PW 를 등록하세요.")
                    except Exception as e:
                        st.error(f"발송 중 오류: {e}")
                        st.info("💡 Streamlit Cloud Secrets에 SMTP 설정이 필요합니다.")

    with col4:
        # 요약 문자 발송 (SMS 단문)
        if st.button("📱 요약문자", use_container_width=True):
            if not to_phone:
                st.error("수신 전화번호를 입력하세요.")
            else:
                try:
                    from services.sms_service import send_statement_sms, build_summary_sms_text
                    _total_w = sum(float(r.get('weight', 0)) for r in rows)
                    _total_a = sum(
                        float(r.get('weight', 0)) *
                        (float(r.get('unit_price', 0)) or get_unit_price(vendor, school, r.get('item_type', '')))
                        for r in rows
                    )
                    sms_text = build_summary_sms_text(
                        vinfo.get('biz_name', vendor), school,
                        year, month, _total_w, _total_a
                    )
                    with st.spinner("문자 발송 중..."):
                        success, msg = send_statement_sms(
                            to_phone, sms_text,
                            vendor_name=vinfo.get('biz_name', vendor),
                            vendor_contact=v_contact
                        )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"문자 발송 실패: {e}")

    with col5:
        # 상세 문자 발송 (LMS 장문, 일별 수거 내역)
        if st.button("📋 상세문자", use_container_width=True):
            if not to_phone:
                st.error("수신 전화번호를 입력하세요.")
            else:
                try:
                    from services.sms_service import send_statement_sms, build_detail_sms_text
                    _total_w = sum(float(r.get('weight', 0)) for r in rows)
                    _total_a = sum(
                        float(r.get('weight', 0)) *
                        (float(r.get('unit_price', 0)) or get_unit_price(vendor, school, r.get('item_type', '')))
                        for r in rows
                    )
                    sms_text = build_detail_sms_text(
                        vinfo.get('biz_name', vendor), school,
                        year, month, rows, _total_w, _total_a
                    )
                    with st.spinner("상세 문자 발송 중..."):
                        success, msg = send_statement_sms(
                            to_phone, sms_text,
                            vendor_name=vinfo.get('biz_name', vendor),
                            vendor_contact=v_contact
                        )
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                except Exception as e:
                    st.error(f"문자 발송 실패: {e}")
