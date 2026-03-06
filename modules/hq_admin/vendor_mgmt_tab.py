# modules/hq_admin/vendor_mgmt_tab.py
import streamlit as st
from database.db_manager import db_get, db_upsert, db_delete, get_all_schools


def render_vendor_mgmt_tab():
    st.markdown("## 외주업체 관리")

    tab1, tab2, tab3 = st.tabs(["업체 목록", "업체 등록", "학교 별칭 관리"])

    with tab1:
        vendors = db_get('vendor_info')
        if not vendors:
            st.info("등록된 업체가 없습니다.")
        else:
            import pandas as pd
            df = pd.DataFrame(vendors)
            st.dataframe(df, use_container_width=True)

    with tab2:
        st.markdown("### 신규 업체 등록")
        col1, col2 = st.columns(2)
        with col1:
            vendor_id  = st.text_input("업체 ID (영문)", key="new_vid")
            biz_name   = st.text_input("상호명", key="new_vname")
            rep        = st.text_input("대표자", key="new_vrep")
        with col2:
            biz_no     = st.text_input("사업자번호", key="new_vbizno")
            address    = st.text_input("주소", key="new_vaddr")
            contact    = st.text_input("연락처", key="new_vcontact")
            email      = st.text_input("이메일", key="new_vemail")

        # 담당 학교 배정
        schools = get_all_schools()
        assigned = st.multiselect("담당 학교", schools, key="new_vschools")

        if st.button("업체 등록", type="primary"):
            if not vendor_id or not biz_name:
                st.error("업체 ID와 상호명은 필수입니다.")
            else:
                ok = db_upsert('vendor_info', {
                    'vendor': vendor_id, 'biz_name': biz_name,
                    'rep': rep, 'biz_no': biz_no,
                    'address': address, 'contact': contact,
                    'email': email
                })
                if ok:
                    for s in assigned:
                        db_upsert('school_master', {'school_name': s, 'vendor': vendor_id})
                    st.success(f"업체 '{biz_name}' 등록 완료!")
                else:
                    st.error("등록 실패")

    with tab3:
        st.markdown("### 학교 별칭 관리")
        st.caption("수거 데이터의 학교명과 계정의 담당학교명이 다를 때 별칭을 등록하세요. 예) 서초고등학교 → 별칭: 서초고,서초고교")

        schools_all = db_get('school_master')
        if not schools_all:
            st.info("등록된 학교가 없습니다.")
        else:
            school_names = sorted([r['school_name'] for r in schools_all])
            sel_school = st.selectbox("학교 선택", school_names, key="alias_school_sel")

            # 현재 별칭 조회
            cur_rows = db_get('school_master', {'school_name': sel_school})
            cur_alias = cur_rows[0].get('alias', '') if cur_rows else ''

            new_alias = st.text_input(
                "별칭 목록 (쉼표로 구분)",
                value=cur_alias,
                key="alias_input",
                help="예: 서초고,서초고교,서초고등"
            )
            st.caption(f"현재 정식명: **{sel_school}** | 현재 별칭: `{cur_alias or '없음'}`")

            if st.button("별칭 저장", key="alias_save"):
                cleaned = ','.join([a.strip() for a in new_alias.split(',') if a.strip()])
                ok = db_upsert('school_master', {'school_name': sel_school, 'alias': cleaned})
                if ok:
                    st.success(f"'{sel_school}' 별칭 저장 완료: {cleaned or '(없음)'}")
                    st.rerun()
                else:
                    st.error("저장 실패")
