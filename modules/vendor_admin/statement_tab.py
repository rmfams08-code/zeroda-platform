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
    st.markdown("## 거래명세서 발송")

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

    # ── 수거 데이터 조회 ──────────────────
    month_str = str(month).zfill(2)
    all_rows = db_get('real_collection')
    rows = [r for r in filter_rows_by_school(all_rows, school)
            if r.get('vendor') == vendor
            and str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    # rows 단가 보정 (load_customers_from_db 방식 — vendor 전체 조회 후 매칭)
    _all_customers = load_customers_from_db(vendor)
    _cust_info = _all_customers.get(school, {})
    if not _cust_info:
        for _ck, _cv in _all_customers.items():
            if _cv.get('상호') == school:
                _cust_info = _cv
                break
    _price_map = {}
    if _cust_info:
        _price_map = {
            '음식물':       float(_cust_info.get('price_food', 0) or 0),
            '재활용':       float(_cust_info.get('price_recycle', 0) or 0),
            '일반':         float(_cust_info.get('price_general', 0) or 0),
            '사업장폐기물': float(_cust_info.get('price_general', 0) or 0),
            '음식물쓰레기': float(_cust_info.get('price_food', 0) or 0),
        }
    corrected_rows = []
    for r in rows:
        row = dict(r)
        item = str(row.get('item_type', '') or row.get('품목', '')).strip()
        up = _price_map.get(item, 0.0)
        if up == 0.0:
            up = float(row.get('unit_price', 0) or 0)
        w = float(row.get('weight', 0) or row.get('음식물(kg)', 0) or 0)
        row['unit_price'] = up
        row['amount']     = round(w * up, 0)
        corrected_rows.append(row)
    rows = corrected_rows

    # ── 단가 디버그 (문제 확인 후 삭제 예정) ──
    with st.expander("🔍 단가 조회 디버그", expanded=False):
        st.write("vendor:", vendor)
        st.write("school:", school)
        st.write("customer 매칭:", "성공" if _cust_info else "실패")
        st.write("_price_map:", _price_map)
        if rows:
            _sample = rows[0]
            st.write("rows[0] item_type:", _sample.get('item_type', ''))
            st.write("rows[0] unit_price:", _sample.get('unit_price', 0))
            st.write("rows[0] amount:", _sample.get('amount', 0))

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
    col1, col2 = st.columns(2)
    with col1:
        to_email = st.text_input("수신 이메일 *",
                                  value=biz_info.get('이메일', ''), key="stmt_email")
        rep      = st.text_input("대표자", value=biz_info.get('대표자', ''), key="stmt_rep")
        biz_no   = st.text_input("사업자번호", value=biz_info.get('사업자번호', ''), key="stmt_bizno")
    with col2:
        addr     = st.text_input("주소", value=biz_info.get('주소', ''), key="stmt_addr")
        biz_type = st.text_input("업태", value=biz_info.get('업태', ''), key="stmt_btype")
        biz_item = st.text_input("종목", value=biz_info.get('종목', ''), key="stmt_bitem")

    # 수급자 정보 업데이트
    biz_info.update({
        '상호': school, '이메일': to_email, '대표자': rep,
        '사업자번호': biz_no, '주소': addr, '업태': biz_type, '종목': biz_item
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
    col1, col2, col3 = st.columns(3)

    with col1:
        # PDF 미리보기/다운로드
        if st.button("PDF 생성 및 다운로드", use_container_width=True):
            if not rows:
                st.error("수거 데이터가 없어 PDF를 생성할 수 없습니다.")
            else:
                try:
                    pdf_bytes = generate_statement_pdf(
                        vendor, school, year, month, rows, biz_info, vinfo
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
        if st.button("이메일 발송", type="primary", use_container_width=True):
            if not to_email:
                st.error("수신 이메일을 입력하세요.")
            else:
                with st.spinner("PDF 생성 및 발송 중..."):
                    try:
                        pdf_bytes = generate_statement_pdf(
                            vendor, school, year, month, rows or [], biz_info, vinfo
                        )
                        filename = f"거래명세서_{school}_{year}{month_str}.pdf"
                        success, msg = send_statement_email(
                            to_email, subject, body, pdf_bytes, filename
                        )
                        if success:
                            st.success(msg)
                            st.balloons()
                        else:
                            # SMTP 설정 안내 포함
                            st.error(msg)
                            if "SMTP 설정" in msg or "인증" in msg:
                                st.info("💡 Streamlit Cloud → Manage App → Secrets 에서\n"                                        "NAVER_SMTP_USER, NAVER_SMTP_APP_PW 를 등록하세요.")
                    except Exception as e:
                        st.error(f"발송 중 오류: {e}")
                        st.info("💡 Streamlit Cloud Secrets에 SMTP 설정이 필요합니다.")
