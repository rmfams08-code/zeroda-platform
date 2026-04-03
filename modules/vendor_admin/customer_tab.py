# modules/vendor_admin/customer_tab.py
import streamlit as st
import pandas as pd
from database.db_manager import load_customers_from_db, save_customer_to_db, delete_customer_from_db, get_unit_price


def render_customer_tab(vendor):
    st.markdown("## 거래처 관리")

    customers = load_customers_from_db(vendor)

    tab1, tab2 = st.tabs(["거래처 목록", "거래처 등록/수정"])

    with tab1:
        if not customers:
            st.info("등록된 거래처가 없습니다.")
        else:
            df = pd.DataFrame(customers.values())
            # 구분별 필터
            cust_types = ['전체'] + sorted(set(
                str(r.get('구분', '학교')) for r in customers.values() if r.get('구분')
            ))
            _ct_filter = st.selectbox("구분 필터", cust_types, key="cust_type_filter")
            if _ct_filter != '전체' and '구분' in df.columns:
                df = df[df['구분'] == _ct_filter]
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"표시: {len(df)}개 / 전체: {len(customers)}개")

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
        # ── 하위 모드: 신규등록 / 수정 ──
        cust_type_options = ["학교", "기업", "관공서", "일반업장", "기타", "기타1(면세사업장)", "기타2(부가세포함)"]
        mode = st.radio(
            "작업 선택", ["📝 신규등록", "✏️ 수정"],
            horizontal=True, key="cust_reg_mode"
        )

        if mode == "📝 신규등록":
            # ────── 신규등록 모드 ──────
            st.markdown("### 거래처 신규등록")
            col1, col2 = st.columns(2)
            with col1:
                name    = st.text_input("상호명 *", key="new_cust_name")
                biz_no  = st.text_input("사업자번호", key="new_cust_bizno")
                rep     = st.text_input("대표자", key="new_cust_rep")
                ctype   = st.selectbox("구분", cust_type_options, key="new_cust_type")
            with col2:
                addr    = st.text_input("주소", key="new_cust_addr")
                biz_type= st.text_input("업태", key="new_cust_biztype")
                biz_item= st.text_input("종목", key="new_cust_bizitem")
                email   = st.text_input("이메일", key="new_cust_email")
                phone   = st.text_input("전화번호", placeholder="010-0000-0000", key="new_cust_phone")
            recycler = st.text_input("♻️ 재활용자(처리자)", placeholder="예: 청명제2공장", key="new_cust_recycler")

            # ── 기타/기타2 구분: 월 고정비용 입력 ──
            new_fixed_fee = 0.0
            if ctype in ('기타', '기타2(부가세포함)'):
                _fee_label = "기타2: 부가세 10% 포함" if ctype == '기타2(부가세포함)' else "기타: 부가세 없음 (단순 금액)"
                st.markdown(f"**📋 월 고정비용 ({_fee_label})**")
                new_fixed_fee = st.number_input(
                    "월 고정비용 (계약금액, 원)", min_value=0.0, step=10000.0,
                    format="%.0f", value=0.0, key="new_cust_fixed_fee"
                )
                st.caption("월 고정비용으로 정산됩니다. (수거량×단가 아님)")

            if st.button("💾 신규 저장", type="primary", key="new_cust_save"):
                if not name:
                    st.error("상호명은 필수입니다.")
                elif name in customers:
                    st.warning(f"'{name}'은(는) 이미 등록된 거래처입니다. 수정 모드를 이용해주세요.")
                else:
                    ok = save_customer_to_db(vendor, name, {
                        '사업자번호': biz_no, '대표자': rep, '주소': addr,
                        '업태': biz_type, '종목': biz_item, '이메일': email,
                        '전화번호': phone, '구분': ctype, '재활용자': recycler,
                        'fixed_monthly_fee': new_fixed_fee,
                    })
                    if ok:
                        st.success(f"'{name}' 신규 등록 완료!")
                        try:
                            from services.github_storage import _github_get_cached
                            _github_get_cached.clear()
                        except Exception:
                            pass
                        st.rerun()
                    else:
                        st.error("저장 실패")

        else:
            # ────── 수정 모드 ──────
            st.markdown("### 거래처 수정")

            if not customers:
                st.info("등록된 거래처가 없습니다. 먼저 신규등록을 해주세요.")
            else:
                # ── 필터 영역 ──
                st.markdown("**거래처 검색**")
                fcol1, fcol2 = st.columns([1, 2])
                with fcol1:
                    edit_type_filter = st.selectbox(
                        "구분 필터",
                        ["전체"] + cust_type_options,
                        key="edit_cust_type_filter"
                    )
                # 필터 적용
                if edit_type_filter == "전체":
                    filtered_names = list(customers.keys())
                else:
                    filtered_names = [
                        n for n, info in customers.items()
                        if str(info.get('구분', '')) == edit_type_filter
                    ]

                if not filtered_names:
                    st.warning(f"'{edit_type_filter}' 구분에 해당하는 거래처가 없습니다.")
                else:
                    with fcol2:
                        edit_target = st.selectbox(
                            "수정할 거래처 선택",
                            filtered_names,
                            key="edit_cust_select"
                        )

                    # ── 기존 정보 불러오기 (key에 거래처명 포함 → 선택 변경 시 자동 초기화) ──
                    ci = customers.get(edit_target, {})
                    _kp = edit_target.replace(" ", "_")  # key prefix

                    st.divider()
                    st.markdown(f"**📌 '{edit_target}' 정보 수정**")

                    ecol1, ecol2 = st.columns(2)
                    with ecol1:
                        edit_name = st.text_input(
                            "상호명 *", value=edit_target,
                            key=f"ec_name_{_kp}"
                        )
                        edit_biz_no = st.text_input(
                            "사업자번호", value=str(ci.get('사업자번호', '') or ''),
                            key=f"ec_bizno_{_kp}"
                        )
                        edit_rep = st.text_input(
                            "대표자", value=str(ci.get('대표자', '') or ''),
                            key=f"ec_rep_{_kp}"
                        )
                        cur_type = str(ci.get('구분', '학교') or '학교')
                        type_idx = cust_type_options.index(cur_type) if cur_type in cust_type_options else 0
                        edit_ctype = st.selectbox(
                            "구분", cust_type_options,
                            index=type_idx, key=f"ec_type_{_kp}"
                        )
                    with ecol2:
                        edit_addr = st.text_input(
                            "주소", value=str(ci.get('주소', '') or ''),
                            key=f"ec_addr_{_kp}"
                        )
                        edit_biz_type = st.text_input(
                            "업태", value=str(ci.get('업태', '') or ''),
                            key=f"ec_biztype_{_kp}"
                        )
                        edit_biz_item = st.text_input(
                            "종목", value=str(ci.get('종목', '') or ''),
                            key=f"ec_bizitem_{_kp}"
                        )
                        edit_email = st.text_input(
                            "이메일", value=str(ci.get('이메일', '') or ''),
                            key=f"ec_email_{_kp}"
                        )
                        edit_phone = st.text_input(
                            "전화번호", value=str(ci.get('전화번호', '') or ''),
                            placeholder="010-0000-0000", key=f"ec_phone_{_kp}"
                        )

                    # ── 재활용자(처리자) ──
                    edit_recycler = st.text_input(
                        "♻️ 재활용자(처리자)",
                        value=str(ci.get('재활용자', '') or ''),
                        placeholder="예: 청명제2공장",
                        key=f"ec_recycler_{_kp}"
                    )

                    # ── 단가 / 고정비용 정보 (구분에 따라 분기) ──
                    edit_fixed_fee = 0.0
                    edit_price_food = 0.0
                    edit_price_recycle = 0.0
                    edit_price_general = 0.0

                    if edit_ctype in ('기타', '기타2(부가세포함)'):
                        # 기타/기타2: 월 고정비용만 입력
                        _fee_label2 = "기타2: 부가세 10% 포함" if edit_ctype == '기타2(부가세포함)' else "기타: 부가세 없음 (단순 금액)"
                        st.markdown(f"**📋 월 고정비용 ({_fee_label2})**")
                        edit_fixed_fee = st.number_input(
                            "월 고정비용 (계약금액, 원)",
                            min_value=0.0, step=10000.0, format="%.0f",
                            value=float(ci.get('fixed_monthly_fee', 0) or 0),
                            key=f"ec_fixedfee_{_kp}"
                        )
                        st.caption("월 고정비용으로 정산됩니다. (수거량×단가 아님)")
                    else:
                        # 학교/기업/관공서/일반업장/기타1: 품목별 단가
                        st.markdown("**💰 단가 정보**")
                        pcol1, pcol2, pcol3 = st.columns(3)
                        with pcol1:
                            edit_price_food = st.number_input(
                                "🍱 음식물 단가 (원/kg)",
                                min_value=0.0, step=10.0, format="%.0f",
                                value=float(ci.get('price_food', 0) or 0),
                                key=f"ec_pfood_{_kp}"
                            )
                        with pcol2:
                            edit_price_recycle = st.number_input(
                                "♻️ 재활용 단가 (원/kg)",
                                min_value=0.0, step=10.0, format="%.0f",
                                value=float(ci.get('price_recycle', 0) or 0),
                                key=f"ec_precycle_{_kp}"
                            )
                        with pcol3:
                            edit_price_general = st.number_input(
                                "🗑️ 사업장폐기물 단가 (원/kg)",
                                min_value=0.0, step=10.0, format="%.0f",
                                value=float(ci.get('price_general', 0) or 0),
                                key=f"ec_pgeneral_{_kp}"
                            )

                    # ── 저장 / 삭제 버튼 ──
                    btn_col1, btn_col2 = st.columns([1, 1])
                    with btn_col1:
                        if st.button("💾 수정 저장", type="primary", key=f"ec_save_{_kp}"):
                            if not edit_name:
                                st.error("상호명은 필수입니다.")
                            else:
                                updated_info = {
                                    '사업자번호': edit_biz_no,
                                    '대표자': edit_rep,
                                    '주소': edit_addr,
                                    '업태': edit_biz_type,
                                    '종목': edit_biz_item,
                                    '이메일': edit_email,
                                    '전화번호': edit_phone,
                                    '구분': edit_ctype,
                                    '재활용자': edit_recycler,
                                    'price_food': edit_price_food,
                                    'price_recycle': edit_price_recycle,
                                    'price_general': edit_price_general,
                                    'fixed_monthly_fee': edit_fixed_fee,
                                }
                                if edit_name != edit_target:
                                    delete_customer_from_db(vendor, edit_target)
                                ok = save_customer_to_db(vendor, edit_name, updated_info)
                                if ok:
                                    msg = f"'{edit_name}' 수정 완료!"
                                    if edit_name != edit_target:
                                        msg += f" (상호명 변경: {edit_target} → {edit_name})"
                                    st.success(msg)
                                    try:
                                        from services.github_storage import _github_get_cached
                                        _github_get_cached.clear()
                                    except Exception:
                                        pass
                                    st.rerun()
                                else:
                                    st.error("저장 실패")
                    with btn_col2:
                        if st.button("🗑️ 거래처 삭제", type="secondary", key=f"ec_del_{_kp}"):
                            ok = delete_customer_from_db(vendor, edit_target)
                            if ok:
                                st.success(f"'{edit_target}' 삭제 완료")
                                try:
                                    from services.github_storage import _github_get_cached
                                    _github_get_cached.clear()
                                except Exception:
                                    pass
                                st.rerun()
                            else:
                                st.error("삭제 실패")

