# modules/vendor_admin/safety_tab.py
import streamlit as st
import pandas as pd
import json
from datetime import date, datetime
from database.db_manager import db_get, db_insert, get_daily_safety_checks
from config.settings import DAILY_SAFETY_CHECKLIST


# 수거차량 특화 점검항목 (기존 일반차량 8항목 → 폐기물수집운반 특화 8항목)
CHECKLIST_ITEMS = [
    '타이어·제동장치·오일류',
    '리프트 유압호스·연결부',
    '리프트 비상정지 스위치',
    '리프트 승강구간 이물질',
    '체인·와이어로프 상태',
    '적재함 도어 잠금장치',
    '후진경보음·경광등',
    '사이드브레이크·고임목',
]


def render_safety_tab(vendor):
    st.markdown("## 안전관리")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📚 안전교육 입력/조회", "🔧 안전점검 입력/조회",
        "🚨 사고 신고 입력", "📋 일일안전점검 조회",
    ])

    with tab1:
        _render_education(vendor)
    with tab2:
        _render_checklist(vendor)
    with tab3:
        _render_accident(vendor)
    with tab4:
        _render_daily_checks(vendor)


def _render_education(vendor):
    st.markdown("### 안전교육 입력")

    with st.form("edu_form"):
        col1, col2 = st.columns(2)
        with col1:
            driver   = st.text_input("기사명 *")
            edu_date = st.date_input("교육일", value=date.today())
            edu_type = st.selectbox("교육 유형", ["정기교육", "신규교육", "특별교육"])
        with col2:
            edu_hours  = st.number_input("교육 시간(h)", min_value=1, max_value=24, value=2)
            instructor = st.text_input("강사/기관명")
            result     = st.selectbox("이수 여부", ["이수", "미이수"])
        memo = st.text_input("메모 (선택)")

        if st.form_submit_button("교육 이력 저장", type="primary"):
            if not driver:
                st.error("기사명을 입력하세요.")
            else:
                row_id = db_insert('safety_education', {
                    'vendor':     vendor,
                    'driver':     driver,
                    'edu_date':   str(edu_date),
                    'edu_type':   edu_type,
                    'edu_hours':  edu_hours,
                    'instructor': instructor,
                    'result':     result,
                    'memo':       memo,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                if row_id:
                    st.success("교육 이력 저장 완료!")
                else:
                    st.error("저장 실패")

    st.divider()
    st.markdown("### 교육 이력 조회")
    rows = [r for r in db_get('safety_education') if r.get('vendor') == vendor]
    if not rows:
        st.info("등록된 교육 이력이 없습니다.")
    else:
        df = pd.DataFrame(rows)
        show = [c for c in ['edu_date','driver','edu_type','edu_hours','instructor','result','memo'] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)


def _render_checklist(vendor):
    st.markdown("### 차량 안전점검")

    with st.form("check_form"):
        col1, col2 = st.columns(2)
        with col1:
            driver     = st.text_input("기사명 *")
            check_date = st.date_input("점검일", value=date.today())
        with col2:
            vehicle_no = st.text_input("차량번호")
            inspector  = st.text_input("점검자")

        st.markdown("**점검 항목**")
        check_results = {}
        cols = st.columns(4)
        for i, item in enumerate(CHECKLIST_ITEMS):
            with cols[i % 4]:
                check_results[item] = st.selectbox(item, ["✅ 양호", "❌ 불량"], key=f"chk_{item}")

        memo = st.text_input("특이사항")

        if st.form_submit_button("점검 결과 저장", type="primary"):
            if not driver:
                st.error("기사명을 입력하세요.")
            else:
                total_ok   = sum(1 for v in check_results.values() if "양호" in v)
                total_fail = sum(1 for v in check_results.values() if "불량" in v)
                row_id = db_insert('safety_checklist', {
                    'vendor':      vendor,
                    'driver':      driver,
                    'check_date':  str(check_date),
                    'vehicle_no':  vehicle_no,
                    'check_items': json.dumps(check_results, ensure_ascii=False),
                    'total_ok':    total_ok,
                    'total_fail':  total_fail,
                    'inspector':   inspector,
                    'memo':        memo,
                    'created_at':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                if row_id:
                    if total_fail > 0:
                        st.warning(f"저장 완료 - ⚠️ 불량 항목 {total_fail}개 있습니다!")
                    else:
                        st.success("점검 결과 저장 완료! 모든 항목 양호")
                else:
                    st.error("저장 실패")

    st.divider()
    st.markdown("### 점검 이력")
    rows = [r for r in db_get('safety_checklist') if r.get('vendor') == vendor]
    if not rows:
        st.info("점검 이력이 없습니다.")
    else:
        df = pd.DataFrame(rows)
        show = [c for c in ['check_date','driver','vehicle_no','total_ok','total_fail','inspector','memo'] if c in df.columns]
        st.dataframe(df[show], use_container_width=True, hide_index=True)


def _render_accident(vendor):
    st.markdown("### 사고 신고")

    with st.form("accident_form"):
        col1, col2 = st.columns(2)
        with col1:
            driver       = st.text_input("기사명 *")
            occur_date   = st.date_input("발생일", value=date.today())
            accident_type = st.selectbox("사고 유형", ["교통사고", "작업중사고", "차량고장", "기타"])
        with col2:
            occur_location = st.text_input("발생 장소")
            severity       = st.selectbox("심각도", ["재산피해", "경상", "중상", "사망"])

        description  = st.text_area("사고 경위 *", height=80)
        action_taken = st.text_area("조치 사항", height=60)

        if st.form_submit_button("사고 신고", type="primary"):
            if not driver or not description:
                st.error("기사명과 사고 경위는 필수입니다.")
            else:
                row_id = db_insert('accident_report', {
                    'vendor':          vendor,
                    'driver':          driver,
                    'occur_date':      str(occur_date),
                    'occur_location':  occur_location,
                    'accident_type':   accident_type,
                    'severity':        severity,
                    'description':     description,
                    'action_taken':    action_taken,
                    'status':          '신고완료',
                    'created_at':      datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                if row_id:
                    st.success("사고 신고 완료! 본사에 전달되었습니다.")
                else:
                    st.error("신고 실패")

    st.divider()
    st.markdown("### 사고 이력")
    rows = [r for r in db_get('accident_report') if r.get('vendor') == vendor]
    if not rows:
        st.info("신고된 사고가 없습니다.")
    else:
        df = pd.DataFrame(rows)
        show = [c for c in ['occur_date','driver','accident_type','severity','status','occur_location'] if c in df.columns]
        status_map = {'신고완료': '📋 신고완료', '처리중': '⏳ 처리중', '완료': '✅ 완료'}
        if 'status' in df.columns:
            df['status'] = df['status'].map(status_map).fillna(df['status'])
        st.dataframe(df[show], use_container_width=True, hide_index=True)


def _render_daily_checks(vendor):
    """기사 일일안전보건 점검 이력 조회 (업체관리자용)"""
    st.markdown("### 일일안전보건 점검 이력")
    st.caption("기사가 매일 출발 전 입력한 27개 항목 점검 결과를 조회합니다.")

    col1, col2 = st.columns(2)
    with col1:
        ym = st.text_input("년월 (YYYY-MM)",
                           value=date.today().strftime('%Y-%m'),
                           key="va_dc_ym")
    with col2:
        cat_options = ['전체'] + [v['label'] for v in DAILY_SAFETY_CHECKLIST.values()]
        cat_filter = st.selectbox("점검 카테고리", cat_options, key="va_dc_cat")

    _label_to_key = {v['label']: k for k, v in DAILY_SAFETY_CHECKLIST.items()}

    rows = get_daily_safety_checks(vendor=vendor, year_month=ym)

    if cat_filter != '전체':
        cat_key = _label_to_key.get(cat_filter, '')
        rows = [r for r in rows if r.get('category') == cat_key]

    if not rows:
        st.info("해당 기간의 점검 이력이 없습니다.")
        return

    df = pd.DataFrame(rows)

    # ── 요약 메트릭 ──
    c1, c2, c3, c4 = st.columns(4)
    total_ok = int(df['total_ok'].sum()) if 'total_ok' in df.columns else 0
    total_fail = int(df['total_fail'].sum()) if 'total_fail' in df.columns else 0
    all_items = total_ok + total_fail
    rate = (total_ok / all_items * 100) if all_items > 0 else 0
    with c1:
        st.metric("점검 건수", f"{len(df)}건")
    with c2:
        st.metric("양호 항목", f"{total_ok}개")
    with c3:
        st.metric("불량 항목", f"{total_fail}개")
    with c4:
        st.metric("양호율", f"{rate:.1f}%")

    # ── 불량 경고 ──
    if 'total_fail' in df.columns:
        fail_rows = df[df['total_fail'] > 0]
        if not fail_rows.empty:
            st.warning(f"⚠️ 불량 항목 포함 점검: {len(fail_rows)}건")
            for _, fr in fail_rows.iterrows():
                cat_label = DAILY_SAFETY_CHECKLIST.get(
                    fr.get('category', ''), {}).get('label', fr.get('category', ''))
                st.caption(
                    f"📅 {fr.get('check_date','')} | 👤 {fr.get('driver','')} | "
                    f"📂 {cat_label} | ❌ 불량 {fr.get('total_fail',0)}개"
                    + (f" | 메모: {fr.get('fail_memo','')}" if fr.get('fail_memo') else "")
                )

    # ── 카테고리 라벨 변환 ──
    if 'category' in df.columns:
        df['category_label'] = df['category'].map(
            lambda x: DAILY_SAFETY_CHECKLIST.get(x, {}).get('label', x))

    show_dc = [c for c in ['check_date','driver','vehicle_no','category_label',
                            'total_ok','total_fail','fail_memo'] if c in df.columns]
    st.dataframe(
        df[show_dc].sort_values('check_date', ascending=False)
        if 'check_date' in df.columns else df[show_dc],
        use_container_width=True, hide_index=True,
        column_config={'category_label': '점검 카테고리'},
    )

    # ── 기사별 이행률 ──
    st.divider()
    st.markdown("#### 기사별 점검 이행률")
    required_cats = len(DAILY_SAFETY_CHECKLIST)
    if 'driver' in df.columns and 'check_date' in df.columns:
        grouped = df.groupby(['driver', 'check_date']).agg(
            cats_done=('category', 'nunique'),
            fail_total=('total_fail', 'sum'),
        ).reset_index()
        grouped['이행률'] = (grouped['cats_done'] / required_cats * 100).round(1)
        summary = grouped.groupby('driver').agg(
            점검일수=('check_date', 'nunique'),
            평균이행률=('이행률', 'mean'),
            총불량=('fail_total', 'sum'),
        ).reset_index()
        summary['평균이행률'] = summary['평균이행률'].round(1).astype(str) + '%'
        st.dataframe(summary, use_container_width=True, hide_index=True)
