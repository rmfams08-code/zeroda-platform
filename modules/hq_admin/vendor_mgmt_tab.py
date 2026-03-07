# modules/hq_admin/vendor_mgmt_tab.py
import streamlit as st
from database.db_manager import (db_get, db_upsert, db_delete, get_all_schools,
                                  load_customers_from_db, save_customer_to_db,
                                  add_violation, calculate_safety_score,
                                  get_safety_scores, get_violations)


def render_vendor_mgmt_tab():
    st.markdown("## 외주업체 관리")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["업체 목록", "업체 등록", "학교 별칭 관리", "품목별 단가 관리", "🛡️ 안전관리 평가"])

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

    # ── tab5: 안전관리 평가 (신규 추가) ─────────────────────────────────
    with tab5:
        _render_safety_eval()


# ─────────────────────────────────────────────────────────────────────────────
# FEAT-02: 안전관리 평가 탭 렌더 함수 (추가 - 기존 코드 유지)
# ─────────────────────────────────────────────────────────────────────────────

_GRADE_EMOJI  = {'S': '⭐ S등급', 'A': '✅ A등급', 'B': '⚠️ B등급', 'C': '🔶 C등급', 'D': '🚨 D등급'}
_GRADE_COLOR  = {'S': '#1565C0', 'A': '#2D7D46', 'B': '#F9A825', 'C': '#E07B39', 'D': '#C0392B'}
_GRADE_DESC   = {'S': '최우수 (90~100점)', 'A': '우수 (75~89점)',
                 'B': '보통 (60~74점)',    'C': '주의 (40~59점)', 'D': '불량 (0~39점)'}


def _render_safety_eval():
    """안전관리 평가 탭"""
    st.markdown("### 🛡️ 외주업체 안전관리 평가")
    st.caption("평가 기준: 스쿨존 위반 40점 + 차량점검 이행률 30점 + 교육이수율 30점 = 100점")

    from config.settings import CURRENT_YEAR, CURRENT_MONTH

    vendors = db_get('vendor_info')
    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return

    vendor_opts = {v.get('biz_name', v['vendor']): v['vendor'] for v in vendors}

    # ── 섹션1: 평가 실행 ────────────────────────────────────────────────
    st.markdown("#### 📊 월별 평가 실행")
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        eval_vendor_label = st.selectbox("업체 선택", list(vendor_opts.keys()), key="sv_eval_vendor")
        eval_vendor = vendor_opts[eval_vendor_label]
    with ec2:
        eval_year  = st.selectbox("연도", [2024, 2025, 2026],
                                   index=[2024,2025,2026].index(CURRENT_YEAR)
                                   if CURRENT_YEAR in [2024,2025,2026] else 2,
                                   key="sv_eval_year")
    with ec3:
        eval_month = st.selectbox("월", list(range(1, 13)),
                                   index=CURRENT_MONTH - 1, key="sv_eval_month")

    year_month = f"{eval_year}-{str(eval_month).zfill(2)}"

    if st.button("🔄 평가 점수 계산/갱신", key="sv_calc_btn", type="primary"):
        result = calculate_safety_score(eval_vendor, year_month)
        grade  = result['grade']
        color  = _GRADE_COLOR.get(grade, '#333')
        st.markdown(
            f"<div style='background:{color};color:white;padding:16px;border-radius:8px;"
            f"text-align:center;font-size:18px;font-weight:bold;'>"
            f"{_GRADE_EMOJI.get(grade, grade)}  |  총점 {result['total_score']}점  |  {_GRADE_DESC.get(grade,'')}"
            f"</div>", unsafe_allow_html=True
        )
        st.markdown("")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("스쿨존 위반 점수", f"{result['violation_score']:.0f} / 40점")
        with sc2:
            st.metric("차량점검 점수", f"{result['checklist_score']:.1f} / 30점")
        with sc3:
            st.metric("교육이수 점수", f"{result['education_score']:.1f} / 30점")

    st.divider()

    # ── 섹션2: 스쿨존 위반 기록 입력 ────────────────────────────────────
    st.markdown("#### 🚨 스쿨존 위반 기록 등록")
    with st.expander("위반 내역 입력", expanded=False):
        vc1, vc2 = st.columns(2)
        with vc1:
            v_vendor_label = st.selectbox("업체", list(vendor_opts.keys()), key="sv_viol_vendor")
            v_vendor = vendor_opts[v_vendor_label]
            v_date   = st.date_input("위반일", key="sv_viol_date")
            v_type   = st.selectbox("위반 유형",
                                     ["과속", "신호위반", "주정차위반", "보행자보호 위반", "기타"],
                                     key="sv_viol_type")
        with vc2:
            # 해당 업체 기사 목록
            d_rows = [r for r in db_get('users')
                      if r.get('role') == 'driver' and r.get('vendor') == v_vendor]
            d_names = [r.get('name') or r.get('user_id', '') for r in d_rows if r.get('name') or r.get('user_id')]
            if d_names:
                v_driver = st.selectbox("기사 선택", ['(직접 입력)'] + d_names, key="sv_viol_driver_sel")
                if v_driver == '(직접 입력)':
                    v_driver = st.text_input("기사명 직접 입력", key="sv_viol_driver_txt")
            else:
                v_driver = st.text_input("기사명", key="sv_viol_driver_txt2")
            v_location = st.text_input("위반 장소 (학교명 또는 주소)", key="sv_viol_loc")
            v_fine     = st.number_input("과태료 (원)", min_value=0, step=10000, key="sv_viol_fine")
        v_memo = st.text_input("비고", key="sv_viol_memo")

        if st.button("📝 위반 기록 저장", key="sv_viol_save"):
            if not v_driver:
                st.error("기사명을 입력하세요.")
            else:
                ok = add_violation(
                    vendor=v_vendor, driver=v_driver,
                    violation_date=str(v_date),
                    violation_type=v_type, location=v_location,
                    fine_amount=int(v_fine), memo=v_memo,
                )
                if ok:
                    st.success(f"✅ 위반 기록 저장 완료 ({v_type} / {v_date})")
                    st.rerun()
                else:
                    st.error("저장 실패")

    st.divider()

    # ── 섹션3: 전체 업체 평가 현황 조회 ─────────────────────────────────
    st.markdown("#### 📋 평가 현황 조회")
    qc1, qc2 = st.columns(2)
    with qc1:
        q_year  = st.selectbox("조회 연도", [2024, 2025, 2026],
                                index=[2024,2025,2026].index(CURRENT_YEAR)
                                if CURRENT_YEAR in [2024,2025,2026] else 2,
                                key="sv_q_year")
    with qc2:
        q_month = st.selectbox("조회 월", ['전체'] + list(range(1, 13)), key="sv_q_month")

    q_ym = f"{q_year}-{str(q_month).zfill(2)}" if q_month != '전체' else None

    scores = get_safety_scores(year_month=q_ym)
    if scores:
        import pandas as pd
        df_s = pd.DataFrame(scores)
        # 등급 이모지 컬럼 추가
        df_s['등급'] = df_s['grade'].map(_GRADE_EMOJI).fillna(df_s['grade'])
        show_cols = [c for c in ['vendor','year_month','violation_score',
                                 'checklist_score','education_score','total_score','등급']
                     if c in df_s.columns]
        rename_map = {
            'vendor': '업체', 'year_month': '평가월',
            'violation_score': '위반점수', 'checklist_score': '점검점수',
            'education_score': '교육점수', 'total_score': '총점',
        }
        st.dataframe(df_s[show_cols].rename(columns=rename_map).sort_values('총점', ascending=False),
                     use_container_width=True, hide_index=True)
    else:
        st.info("평가 기록이 없습니다. 위에서 [평가 점수 계산/갱신]을 실행하세요.")

    st.divider()

    # ── 섹션4: 스쿨존 위반 이력 조회 ────────────────────────────────────
    st.markdown("#### 🚨 스쿨존 위반 이력")
    vc1b, vc2b = st.columns(2)
    with vc1b:
        vq_vendor_label = st.selectbox("업체", ['전체'] + list(vendor_opts.keys()), key="sv_vq_vendor")
        vq_vendor = vendor_opts.get(vq_vendor_label) if vq_vendor_label != '전체' else None
    with vc2b:
        vq_month_opt = st.selectbox("월", ['전체'] + list(range(1, 13)), key="sv_vq_month")
        vq_ym = f"{q_year}-{str(vq_month_opt).zfill(2)}" if vq_month_opt != '전체' else None

    violations = get_violations(vendor=vq_vendor, year_month=vq_ym)
    if violations:
        import pandas as pd
        df_v = pd.DataFrame(violations)
        show_v = [c for c in ['violation_date','vendor','driver','violation_type',
                               'location','fine_amount','memo'] if c in df_v.columns]
        rename_v = {
            'violation_date': '위반일', 'vendor': '업체', 'driver': '기사',
            'violation_type': '유형', 'location': '장소',
            'fine_amount': '과태료(원)', 'memo': '비고',
        }
        st.dataframe(df_v[show_v].rename(columns=rename_v).sort_values('위반일', ascending=False),
                     use_container_width=True, hide_index=True)
        st.metric("위반 건수", f"{len(violations)}건")
    else:
        st.info("위반 기록이 없습니다.")
