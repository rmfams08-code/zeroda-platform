# modules/vendor_admin/safety_tab.py
import streamlit as st
import pandas as pd
import json
from datetime import date, datetime
from database.db_manager import db_get, db_insert


CHECKLIST_ITEMS = ['브레이크', '타이어', '등화장치', '와이퍼', '냉각수', '엔진오일', '안전벨트', '소화기']


def render_safety_tab(vendor):
    st.markdown("## 안전관리")

    tab1, tab2, tab3 = st.tabs(["📚 안전교육 입력/조회", "🔧 안전점검 입력/조회", "🚨 사고 신고 입력"])

    with tab1:
        _render_education(vendor)
    with tab2:
        _render_checklist(vendor)
    with tab3:
        _render_accident(vendor)


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
