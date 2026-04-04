# modules/hq_admin/vendor_mgmt_tab.py
import streamlit as st
from database.db_manager import (db_get, db_upsert, db_delete, get_all_schools,
                                  load_customers_from_db, save_customer_to_db,
                                  add_violation, calculate_safety_score,
                                  get_safety_scores, get_violations)


def render_vendor_mgmt_tab():
    st.markdown("## 외주업체 관리")

    tab1, tab2, tab2b, tab3, tab5 = st.tabs(
        ["업체 목록", "업체 등록", "✏️ 업체 수정", "학교 별칭 관리", "🛡️ 안전관리 평가"])
    # ※ 품목별 단가 관리는 '거래처 관리' 메뉴로 통합 (중복 제거)

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

        vehicle_no = st.text_input("차량번호 (쉼표로 구분하여 여러 대 입력 가능)",
                                   key="new_vvehicle",
                                   help="예: 12가3456,78나9012")

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
                    'email': email, 'vehicle_no': vehicle_no,
                })
                if ok:
                    for s in assigned:
                        db_upsert('school_master', {'school_name': s, 'vendor': vendor_id})
                    st.success(f"업체 '{biz_name}' 등록 완료!")
                else:
                    st.error("등록 실패")

    with tab2b:
        _render_vendor_edit()

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

    # ── tab5: 안전관리 평가 ─────────────────────────────────
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
    st.caption("평가 기준: 스쿨존 위반 40점 + 차량점검 15점 + 일일안전점검 15점 + 교육이수율 30점 = 100점")

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
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("스쿨존 위반 점수", f"{result['violation_score']:.0f} / 40점")
        with sc2:
            st.metric("차량점검 점수", f"{result['checklist_score']:.1f} / 15점")
        with sc3:
            st.metric("일일안전점검 점수", f"{result.get('daily_check_score', 0):.1f} / 15점")
        with sc4:
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
                                 'checklist_score','daily_check_score',
                                 'education_score','total_score','등급']
                     if c in df_s.columns]
        rename_map = {
            'vendor': '업체', 'year_month': '평가월',
            'violation_score': '위반(40)', 'checklist_score': '차량점검(15)',
            'daily_check_score': '일일점검(15)',
            'education_score': '교육(30)', 'total_score': '총점',
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


# ─────────────────────────────────────────────────────────────────────────────
# FEAT: 업체 정보 수정 탭 (기존 정보 불러오기 → 수정 → 저장)
# ─────────────────────────────────────────────────────────────────────────────

def _render_vendor_edit():
    """업체 정보 수정 — 기존 데이터 불러오기 + 차량번호 포함"""
    st.markdown("### ✏️ 업체 정보 수정")
    st.caption("수정할 업체를 선택하면 기존 정보를 불러옵니다. 변경 후 [수정 저장] 버튼을 클릭하세요.")

    vendors = db_get('vendor_info')
    if not vendors:
        st.info("등록된 업체가 없습니다. 먼저 '업체 등록' 탭에서 업체를 등록하세요.")
        return

    # 업체 선택
    vendor_labels = {f"{v.get('biz_name', '')} ({v['vendor']})": v['vendor'] for v in vendors}
    sel_label = st.selectbox("수정할 업체 선택", list(vendor_labels.keys()), key="edit_vendor_sel")
    sel_vendor_id = vendor_labels[sel_label]

    # 선택된 업체의 기존 정보 불러오기
    cur = next((v for v in vendors if v['vendor'] == sel_vendor_id), {})

    st.divider()

    # 수정 폼 (기존 값 pre-fill)
    col1, col2 = st.columns(2)
    with col1:
        edit_biz_name = st.text_input("상호명", value=cur.get('biz_name', ''), key="edit_vname")
        edit_rep      = st.text_input("대표자", value=cur.get('rep', ''), key="edit_vrep")
        edit_biz_no   = st.text_input("사업자번호", value=cur.get('biz_no', ''), key="edit_vbizno")
    with col2:
        edit_address  = st.text_input("주소", value=cur.get('address', ''), key="edit_vaddr")
        edit_contact  = st.text_input("연락처", value=cur.get('contact', ''), key="edit_vcontact")
        edit_email    = st.text_input("이메일", value=cur.get('email', ''), key="edit_vemail")

    edit_vehicle  = st.text_input("차량번호 (쉼표로 구분)",
                                  value=cur.get('vehicle_no', ''),
                                  key="edit_vvehicle",
                                  help="예: 12가3456,78나9012")

    # 담당 학교 수정
    all_schools = get_all_schools()
    # 현재 배정된 학교 목록 조회
    school_master = db_get('school_master')
    current_schools = [s['school_name'] for s in (school_master or [])
                       if s.get('vendor') == sel_vendor_id]
    edit_schools = st.multiselect("담당 학교", all_schools,
                                  default=[s for s in current_schools if s in all_schools],
                                  key="edit_vschools")

    st.divider()

    # 현재 정보 vs 변경 정보 비교 표시
    with st.expander("📋 현재 등록 정보 확인", expanded=False):
        import pandas as pd
        info_data = {
            '항목': ['상호명', '대표자', '사업자번호', '주소', '연락처', '이메일', '차량번호', '담당학교'],
            '현재 값': [
                cur.get('biz_name', ''), cur.get('rep', ''), cur.get('biz_no', ''),
                cur.get('address', ''), cur.get('contact', ''), cur.get('email', ''),
                cur.get('vehicle_no', ''), ', '.join(current_schools),
            ],
        }
        st.dataframe(pd.DataFrame(info_data), use_container_width=True, hide_index=True)

    if st.button("💾 수정 저장", key="edit_vendor_save", type="primary"):
        ok = db_upsert('vendor_info', {
            'vendor': sel_vendor_id,
            'biz_name': edit_biz_name,
            'rep': edit_rep,
            'biz_no': edit_biz_no,
            'address': edit_address,
            'contact': edit_contact,
            'email': edit_email,
            'vehicle_no': edit_vehicle,
        })
        if ok:
            # 담당 학교 업데이트: 기존 배정 해제 후 새로 배정
            for s in current_schools:
                if s not in edit_schools:
                    # 학교에서 업체 배정 해제 (vendor를 빈값으로)
                    db_upsert('school_master', {'school_name': s, 'vendor': ''})
            for s in edit_schools:
                db_upsert('school_master', {'school_name': s, 'vendor': sel_vendor_id})
            st.success(f"✅ '{edit_biz_name}' 업체 정보가 수정되었습니다.")
            st.rerun()
        else:
            st.error("수정 저장에 실패했습니다.")
