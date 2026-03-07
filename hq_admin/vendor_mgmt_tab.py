# modules/hq_admin/vendor_mgmt_tab.py
import streamlit as st
from database.db_manager import db_get, db_upsert, db_delete, get_all_schools, load_customers_from_db, save_customer_to_db


def render_vendor_mgmt_tab():
    st.markdown("## 외주업체 관리")

    tab1, tab2, tab3, tab4 = st.tabs(["업체 목록", "업체 등록", "학교 별칭 관리", "품목별 단가 관리"])

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
                    try:
                        from services.github_storage import _github_get_cached
                        _github_get_cached.clear()
                    except Exception:
                        pass
                    st.rerun()
                else:
                    st.error("저장 실패")

    with tab4:
        st.markdown("### 📋 품목별 단가 관리")
        st.caption("업체와 거래처(학교)를 선택해 품목별 단가를 등록/수정합니다.")

        vendors = db_get('vendor_info')
        if not vendors:
            st.info("등록된 업체가 없습니다.")
        else:
            vendor_opts = {v.get('biz_name', v['vendor']): v['vendor'] for v in vendors}
            sel_vendor_label = st.selectbox("업체 선택", list(vendor_opts.keys()), key="price_vendor_sel")
            sel_vendor = vendor_opts[sel_vendor_label]

            customers = load_customers_from_db(sel_vendor)
            if not customers:
                st.info("해당 업체에 등록된 거래처가 없습니다. 거래처 관리에서 먼저 등록하세요.")
            else:
                sel_cust = st.selectbox("거래처(학교) 선택", list(customers.keys()), key="price_cust_hq_sel")
                cust_info = customers.get(sel_cust, {})

                col1, col2, col3 = st.columns(3)
                with col1:
                    price_food = st.number_input(
                        "🍱 음식물쓰레기 단가 (원/kg)",
                        min_value=0.0, step=10.0, format="%.0f",
                        value=float(cust_info.get('price_food', 0) or 0),
                        key=f"hq_price_food_{sel_vendor}_{sel_cust}"
                    )
                with col2:
                    price_recycle = st.number_input(
                        "♻️ 재활용 단가 (원/kg)",
                        min_value=0.0, step=10.0, format="%.0f",
                        value=float(cust_info.get('price_recycle', 0) or 0),
                        key=f"hq_price_recycle_{sel_vendor}_{sel_cust}"
                    )
                with col3:
                    price_general = st.number_input(
                        "🗑️ 사업장폐기물 단가 (원/kg)",
                        min_value=0.0, step=10.0, format="%.0f",
                        value=float(cust_info.get('price_general', 0) or 0),
                        key=f"hq_price_general_{sel_vendor}_{sel_cust}"
                    )

                if st.button("💾 단가 저장", key="hq_price_save_btn", type="primary"):
                    updated_info = {**cust_info,
                                    'price_food': price_food,
                                    'price_recycle': price_recycle,
                                    'price_general': price_general}
                    ok = save_customer_to_db(sel_vendor, sel_cust, updated_info)
                    if ok:
                        st.success(f"'{sel_cust}' 단가 저장 완료! (음식물: {price_food:,.0f}원 / 재활용: {price_recycle:,.0f}원 / 사업장: {price_general:,.0f}원)")
                        try:
                            from services.github_storage import _github_get_cached
                            _github_get_cached.clear()
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error("저장 실패")
