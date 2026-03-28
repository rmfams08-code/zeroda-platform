# modules/hq_admin/safety_tab.py
import streamlit as st
import pandas as pd
from datetime import date
from database.db_manager import db_get, db_insert, get_all_vendors
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_safety_tab():
    st.markdown("## 안전관리")

    tab1, tab2, tab3 = st.tabs(["📚 안전교육 조회", "🔧 안전점검 조회", "🚨 사고 신고 관리"])

    with tab1:
        _render_education()
    with tab2:
        _render_checklist()
    with tab3:
        _render_accident()


def _render_education():
    st.markdown("### 안전교육 이력")

    col1, col2 = st.columns(2)
    with col1:
        vendors = ['전체'] + get_all_vendors()
        vendor_filter = st.selectbox("업체", vendors, key="sf_edu_vendor")
    with col2:
        result_filter = st.selectbox("이수 여부", ['전체', '이수', '미이수'], key="sf_edu_result")

    rows = db_get('safety_education')
    if not rows:
        st.info("등록된 안전교육 이력이 없습니다.")
        return

    df = pd.DataFrame(rows)
    if vendor_filter != '전체' and 'vendor' in df.columns:
        df = df[df['vendor'] == vendor_filter]
    if result_filter != '전체' and 'result' in df.columns:
        df = df[df['result'] == result_filter]

    # 요약
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 교육 건수", f"{len(df)}건")
    with c2:
        isu = len(df[df['result'] == '이수']) if 'result' in df.columns else 0
        st.metric("이수", f"{isu}건")
    with c3:
        misu = len(df[df['result'] == '미이수']) if 'result' in df.columns else 0
        st.metric("미이수", f"{misu}건")

    show = [c for c in ['edu_date','vendor','driver','edu_type','edu_hours','instructor','result','memo'] if c in df.columns]
    st.dataframe(df[show].sort_values('edu_date', ascending=False) if 'edu_date' in df.columns else df[show],
                 use_container_width=True, hide_index=True)


def _render_checklist():
    st.markdown("### 안전점검 결과")

    rows = db_get('safety_checklist')
    if not rows:
        st.info("등록된 안전점검 내역이 없습니다.")
        return

    df = pd.DataFrame(rows)
    show = [c for c in ['check_date','vendor','driver','vehicle_no','total_ok','total_fail','inspector'] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    if 'total_fail' in df.columns:
        fail_count = df[df['total_fail'] > 0]
        if not fail_count.empty:
            st.warning(f"⚠️ 불합격 항목이 있는 점검: {len(fail_count)}건")


def _render_accident():
    st.markdown("### 사고 신고 현황")

    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("처리 상태", ['전체', '신고완료', '처리중', '완료'], key="sf_acc_status")
    with col2:
        type_filter = st.selectbox("사고 유형", ['전체', '교통사고', '작업중사고', '차량고장', '기타'], key="sf_acc_type")

    rows = db_get('accident_report')
    if not rows:
        st.info("신고된 사고가 없습니다.")
        return

    df = pd.DataFrame(rows)
    if status_filter != '전체' and 'status' in df.columns:
        df = df[df['status'] == status_filter]
    if type_filter != '전체' and 'accident_type' in df.columns:
        df = df[df['accident_type'] == type_filter]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("전체 사고", f"{len(df)}건")
    with c2:
        processing = len(df[df['status'] == '처리중']) if 'status' in df.columns else 0
        st.metric("처리중", f"{processing}건")
    with c3:
        done = len(df[df['status'] == '완료']) if 'status' in df.columns else 0
        st.metric("완료", f"{done}건")

    # 상태 이모지 매핑 (외주업체와 통일)
    _acc_status_map = {'신고완료': '📋 신고완료', '처리중': '⏳ 처리중', '완료': '✅ 완료'}
    if 'status' in df.columns:
        df['status'] = df['status'].map(_acc_status_map).fillna(df['status'])

    show = [c for c in ['occur_date','vendor','driver','accident_type','severity','status','occur_location'] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    # 처리 상태 변경
    if not df.empty and 'id' in df.columns:
        st.divider()
        st.markdown("#### 처리 상태 변경")
        import sqlite3
        from config.settings import DB_PATH
        sel_id = st.number_input("사고 ID", min_value=1, step=1, key="acc_id")
        new_status = st.selectbox("변경할 상태", ['처리중', '완료'], key="acc_new_status")
        if st.button("상태 변경", key="acc_update"):
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE accident_report SET status=? WHERE id=?", (new_status, sel_id))
                conn.commit()
                conn.close()
                st.success(f"ID {sel_id} 상태 → {new_status}")
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")
