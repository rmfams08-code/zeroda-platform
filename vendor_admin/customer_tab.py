# modules/vendor_admin/customer_tab.py
import streamlit as st
import pandas as pd
from database.db_manager import load_customers_from_db, save_customer_to_db, delete_customer_from_db, get_unit_price


def render_customer_tab(vendor):
    st.markdown("## 거래처 관리 (학교)")

    customers = load_customers_from_db(vendor)

    tab1, tab2 = st.tabs(["거래처 목록", "거래처 등록/수정"])

    with tab1:
        if not customers:
            st.info("등록된 거래처가 없습니다.")
        else:
            df = pd.DataFrame(customers.values())
            st.dataframe(df, use_container_width=True)
            st.caption(f"총 {len(customers)}개")

        # ── 품목별 단가 입력/수정 ────────────────────────────────
        st.divider()
        st.markdown("### 📋 품목별 단가 설정")
        st.caption("거래처(학교)별로 품목별 단가를 등록하면 거래명세서에 자동 반영됩니다.")

        if not customers:
            st.info("먼저 거래처를 등록해주세요.")
        else:
            sel_cust = st.selectbox("거래처 선택", list(customers.keys()), key="price_cust_sel")
            cust_info = customers.get(sel_cust, {})

            col1, col2, col3 = st.columns(3)
            with col1:
                price_food = st.number_input(
                    "🍱 음식물쓰레기 단가 (원/kg)",
                    min_value=0.0, step=10.0, format="%.0f",
                    value=float(cust_info.get('price_food', 0) or 0),
                    key=f"price_food_{sel_cust}"
                )
            with col2:
                price_recycle = st.number_input(
                    "♻️ 재활용 단가 (원/kg)",
                    min_value=0.0, step=10.0, format="%.0f",
                    value=float(cust_info.get('price_recycle', 0) or 0),
                    key=f"price_recycle_{sel_cust}"
                )
            with col3:
                price_general = st.number_input(
                    "🗑️ 사업장폐기물 단가 (원/kg)",
                    min_value=0.0, step=10.0, format="%.0f",
                    value=float(cust_info.get('price_general', 0) or 0),
                    key=f"price_general_{sel_cust}"
                )

            if st.button("💾 단가 저장", key="price_save_btn", type="primary"):
                updated_info = {**cust_info,
                                'price_food': price_food,
                                'price_recycle': price_recycle,
                                'price_general': price_general}
                ok = save_customer_to_db(vendor, sel_cust, updated_info)
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

    with tab2:
        st.markdown("### 거래처 등록")
        col1, col2 = st.columns(2)
        with col1:
            name    = st.text_input("상호명 *")
            biz_no  = st.text_input("사업자번호")
            rep     = st.text_input("대표자")
            ctype   = st.selectbox("구분", ["학교", "기업", "관공서", "기타"])
        with col2:
            addr    = st.text_input("주소")
            biz_type= st.text_input("업태")
            biz_item= st.text_input("종목")
            email   = st.text_input("이메일")

        if st.button("저장", type="primary"):
            if not name:
                st.error("상호명은 필수입니다.")
            else:
                ok = save_customer_to_db(vendor, name, {
                    '사업자번호': biz_no, '대표자': rep, '주소': addr,
                    '업태': biz_type, '종목': biz_item, '이메일': email, '구분': ctype
                })
                if ok:
                    st.success(f"'{name}' 저장 완료!")
                    st.rerun()
                else:
                    st.error("저장 실패")

        if customers:
            st.markdown("### 거래처 삭제")
            del_name = st.selectbox("삭제할 거래처", list(customers.keys()))
            if st.button("삭제", type="secondary"):
                ok = delete_customer_from_db(vendor, del_name)
                if ok:
                    st.success("삭제 완료")
                    st.rerun()

