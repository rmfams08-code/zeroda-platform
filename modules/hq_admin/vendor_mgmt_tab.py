# zeroda_platform/modules/hq_admin/vendor_mgmt_tab.py
# ==========================================
# 본사 관리자 - 외주업체 관리 탭
# ==========================================

import streamlit as st
from database.db_manager import (
    db_get, db_upsert, db_delete,
    get_all_vendors, get_schools_by_vendor,
    assign_school_to_vendor, update_vendor_name,
    get_all_schools
)


def render_vendor_mgmt_tab():
    st.markdown("## 🤝 외주업체 관리")

    tab_info, tab_school, tab_contract = st.tabs(
        ["사업자정보", "학교 배정", "계약 관리"])

    with tab_info:
        _render_vendor_info()
    with tab_school:
        _render_school_assign()
    with tab_contract:
        _render_contract_mgmt()


def _render_vendor_info():
    """
    외주업체 사업자정보 관리
    ★ 업체명 수정 + CASCADE 업데이트 포함
    """
    st.markdown("### 사업자정보 관리")

    vendor_rows = db_get('vendor_info')
    if not vendor_rows:
        st.info("등록된 업체가 없습니다.")
        _render_vendor_add()
        return

    # 업체 선택
    vendor_options = {
        f"{r.get('biz_name') or r['vendor']} ({r['vendor']})": r['vendor']
        for r in vendor_rows
    }
    selected_label  = st.selectbox("업체 선택", list(vendor_options.keys()),
                                   key="vinfo_sel")
    selected_vendor = vendor_options[selected_label]

    rows = db_get('vendor_info', {'vendor': selected_vendor})
    if not rows:
        st.warning("업체 정보를 불러올 수 없습니다.")
        return

    info = rows[0]

    col1, col2 = st.columns(2)
    with col1:
        # ★ 업체명 수정 가능 (CASCADE 업데이트)
        new_biz_name = st.text_input("업체명 ★",
                                     value=info.get('biz_name', ''),
                                     key="vinfo_biz_name",
                                     help="변경 시 관련 모든 테이블에 자동 반영됩니다")
        biz_no  = st.text_input("사업자번호", value=info.get('biz_no', ''),  key="vinfo_biz_no")
        rep     = st.text_input("대표자",    value=info.get('rep', ''),     key="vinfo_rep")
        contact = st.text_input("연락처",    value=info.get('contact', ''), key="vinfo_contact")
    with col2:
        email    = st.text_input("이메일",  value=info.get('email', ''),    key="vinfo_email")
        addr     = st.text_input("주소",    value=info.get('addr', ''),     key="vinfo_addr")
        biz_type = st.text_input("업태",    value=info.get('biz_type', ''), key="vinfo_biz_type")
        biz_item = st.text_input("종목",    value=info.get('biz_item', ''), key="vinfo_biz_item")

    if st.button("💾 저장", type="primary", key="btn_vinfo_save"):
        original_biz_name = info.get('biz_name', '')

        # ★ 업체명 변경 시 CASCADE 처리
        if new_biz_name and new_biz_name != original_biz_name:
            ok = update_vendor_name(selected_vendor, new_biz_name)
            if ok:
                st.success(f"업체명 변경: '{original_biz_name}' → '{new_biz_name}' (전체 반영 완료)")
            else:
                st.error("업체명 CASCADE 업데이트 실패")
                return

        # 나머지 정보 저장
        ok = db_upsert('vendor_info', {
            'vendor':   selected_vendor,
            'biz_name': new_biz_name,
            'biz_no':   biz_no,
            'rep':      rep,
            'contact':  contact,
            'email':    email,
            'addr':     addr,
            'biz_type': biz_type,
            'biz_item': biz_item,
        })
        if ok:
            st.success("사업자정보 저장 완료")
            st.rerun()
        else:
            st.error("저장 실패")

    st.divider()
    _render_vendor_add()


def _render_vendor_add():
    """신규 업체 등록"""
    with st.expander("➕ 신규 업체 등록"):
        col1, col2 = st.columns(2)
        with col1:
            new_vid      = st.text_input("업체 ID (영문)", key="new_vid",
                                         placeholder="예: vendor_a")
            new_biz_name = st.text_input("업체명",        key="new_vbiz_name")
            new_biz_no   = st.text_input("사업자번호",    key="new_vbiz_no")
        with col2:
            new_rep      = st.text_input("대표자",        key="new_vrep")
            new_contact  = st.text_input("연락처",        key="new_vcontact")
            new_email    = st.text_input("이메일",        key="new_vemail")

        if st.button("등록", key="btn_vendor_add"):
            if not new_vid or not new_biz_name:
                st.error("업체 ID와 업체명은 필수입니다.")
            else:
                existing = db_get('vendor_info', {'vendor': new_vid})
                if existing:
                    st.error("이미 존재하는 업체 ID입니다.")
                else:
                    ok = db_upsert('vendor_info', {
                        'vendor':   new_vid,
                        'biz_name': new_biz_name,
                        'biz_no':   new_biz_no,
                        'rep':      new_rep,
                        'contact':  new_contact,
                        'email':    new_email,
                    })
                    if ok:
                        st.success(f"업체 '{new_biz_name}' 등록 완료")
                        st.rerun()
                    else:
                        st.error("등록 실패")


def _render_school_assign():
    """학교 배정 관리 (★ DB 반영 버그 수정)"""
    st.markdown("### 학교 배정 관리")

    vendors = get_all_vendors()
    schools = get_all_schools()

    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return
    if not schools:
        st.info("등록된 학교가 없습니다.")
        return

    vendor = st.selectbox("업체 선택", vendors, key="assign_vendor")

    current_schools = get_schools_by_vendor(vendor)
    remaining       = [s for s in schools if s not in current_schools]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**현재 배정 학교 ({len(current_schools)}개)**")
        for s in current_schools:
            c_s, c_btn = st.columns([4, 1])
            c_s.write(s)
            if c_btn.button("해제", key=f"unassign_{s}"):
                # ★ 버그 수정: DB 직접 업데이트
                from database.db_manager import db_execute
                db_execute(
                    "UPDATE school_master SET vendor='' WHERE school_name=?", [s])
                st.success(f"{s} 배정 해제")
                st.rerun()

    with col2:
        st.markdown(f"**미배정 학교 ({len(remaining)}개)**")
        if remaining:
            to_add = st.multiselect("배정할 학교", remaining, key="assign_add")
            if st.button("배정 추가", type="primary", key="btn_assign"):
                for s in to_add:
                    assign_school_to_vendor(s, vendor)  # ★ DB 반영
                if to_add:
                    st.success(f"{len(to_add)}개 학교 배정 완료")
                    st.rerun()
        else:
            st.info("모든 학교가 배정되었습니다.")


def _render_contract_mgmt():
    """계약 관리"""
    st.markdown("### 계약 관리")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return

    vendor = st.selectbox("업체 선택", vendors, key="contract_vendor")

    # 계약 정보
    contract_rows = db_get('contract_info', {'vendor': vendor})
    contract = contract_rows[0] if contract_rows else {}

    col1, col2 = st.columns(2)
    with col1:
        rep        = st.text_input("대표자",   value=contract.get('rep', ''),        key="ct_rep")
        biz_no     = st.text_input("사업자번호", value=contract.get('biz_no', ''),   key="ct_biz_no")
        start_date = st.text_input("계약 시작일", value=contract.get('start_date', ''), key="ct_start",
                                   placeholder="2025-01-01")
    with col2:
        end_date = st.text_input("계약 종료일", value=contract.get('end_date', ''), key="ct_end",
                                 placeholder="2025-12-31")
        status   = st.selectbox("계약 상태",
                                ['진행중', '만료', '해지'],
                                index=['진행중','만료','해지'].index(
                                    contract.get('status', '진행중'))
                                if contract.get('status') in ['진행중','만료','해지'] else 0,
                                key="ct_status")

    # 품목별 단가
    st.markdown("**품목별 수거 단가**")
    price_rows = db_get('contract_data', {'vendor': vendor})
    price_dict = {r['item']: r['price'] for r in price_rows}

    items = ['음식물', '재활용', '일반쓰레기', '사업장']
    new_prices = {}
    cols = st.columns(len(items))
    for i, item in enumerate(items):
        with cols[i]:
            new_prices[item] = st.number_input(
                f"{item} (원/kg)",
                value=int(price_dict.get(item, 162)),
                min_value=0, step=1,
                key=f"price_{vendor}_{item}"
            )

    if st.button("💾 계약 저장", type="primary", key="btn_contract_save"):
        db_upsert('contract_info', {
            'vendor': vendor, 'rep': rep, 'biz_no': biz_no,
            'start_date': start_date, 'end_date': end_date, 'status': status
        })
        for item, price in new_prices.items():
            db_upsert('contract_data', {
                'vendor': vendor, 'item': item, 'price': price
            })
        st.success("계약 정보 저장 완료")