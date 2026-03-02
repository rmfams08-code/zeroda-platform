# zeroda_platform/modules/vendor_admin/customer_tab.py
# ==========================================
# 외주업체 관리자 - 거래처(학교) 관리 탭
# ==========================================

import streamlit as st
from database.db_manager import (
    load_customers_from_db, save_customer_to_db,
    delete_customer_from_db, db_get
)


def render_customer_tab(vendor: str):
    st.markdown("## 🏫 거래처 관리")

    tab_list, tab_add, tab_sync = st.tabs(["거래처 목록", "거래처 등록", "학교 동기화"])

    with tab_list:
        _render_list(vendor)
    with tab_add:
        _render_add(vendor)
    with tab_sync:
        _render_sync(vendor)


def _render_list(vendor: str):
    st.markdown("### 거래처 목록")

    customers = load_customers_from_db(vendor)
    if not customers:
        st.info("등록된 거래처가 없습니다.")
        return

    for name, info in customers.items():
        with st.expander(f"🏫 {name}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**사업자번호:** {info.get('사업자번호', '-')}")
                st.markdown(f"**대표자:** {info.get('대표자', '-')}")
                st.markdown(f"**이메일:** {info.get('이메일', '-')}")
            with col2:
                st.markdown(f"**업태:** {info.get('업태', '-')}")
                st.markdown(f"**종목:** {info.get('종목', '-')}")
                st.markdown(f"**구분:** {info.get('구분', '-')}")
            st.markdown(f"**주소:** {info.get('주소', '-')}")

            if st.button("🗑️ 삭제", key=f"del_cust_{name}"):
                delete_customer_from_db(vendor, name)
                st.success(f"{name} 삭제 완료")
                st.rerun()


def _render_add(vendor: str):
    st.markdown("### 거래처 등록/수정")

    col1, col2 = st.columns(2)
    with col1:
        name    = st.text_input("상호(학교명) *", key="cust_name")
        biz_no  = st.text_input("사업자번호",     key="cust_biz_no")
        rep     = st.text_input("대표자",         key="cust_rep")
        email   = st.text_input("이메일",         key="cust_email")
    with col2:
        addr     = st.text_input("주소",    key="cust_addr")
        biz_type = st.text_input("업태",    key="cust_biz_type",
                                 placeholder="예: 교육서비스업")
        biz_item = st.text_input("종목",    key="cust_biz_item",
                                 placeholder="예: 초등학교")
        cust_type = st.selectbox("구분",
                                 ['학교', '기관', '사업장', '기타'],
                                 key="cust_type")

    if st.button("💾 저장", type="primary", key="btn_cust_save"):
        if not name:
            st.error("상호(학교명)는 필수입니다.")
            return
        ok = save_customer_to_db(vendor, name, {
            '사업자번호': biz_no, '대표자': rep, '주소': addr,
            '업태': biz_type, '종목': biz_item,
            '이메일': email, '구분': cust_type
        })
        if ok:
            st.success(f"'{name}' 저장 완료")
        else:
            st.error("저장 실패")


def _render_sync(vendor: str):
    """
    학교 마스터 → 거래처 자동 동기화
    school_master에 있는 이 업체 담당 학교를
    customer_info에 자동 등록
    """
    st.markdown("### 학교 마스터 동기화")
    st.info("학교 마스터에 배정된 학교를 거래처에 자동 등록합니다.")

    from database.db_manager import get_schools_by_vendor
    schools  = get_schools_by_vendor(vendor)
    existing = load_customers_from_db(vendor)

    new_schools = [s for s in schools if s not in existing]

    if not new_schools:
        st.success("모든 담당 학교가 거래처에 등록되어 있습니다.")
        return

    st.warning(f"미등록 학교 {len(new_schools)}개 발견")
    for s in new_schools:
        st.markdown(f"• {s}")

    if st.button("🔄 일괄 등록", type="primary", key="btn_sync"):
        count = 0
        for s in new_schools:
            ok = save_customer_to_db(vendor, s, {
                '사업자번호': '', '대표자': '', '주소': '',
                '업태': '교육서비스업', '종목': '학교',
                '이메일': '', '구분': '학교'
            })
            if ok:
                count += 1
        st.success(f"{count}개 학교 거래처 등록 완료")
        st.rerun()