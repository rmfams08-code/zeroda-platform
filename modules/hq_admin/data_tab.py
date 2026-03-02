# modules/hq_admin/data_tab.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, db_upsert, get_all_schools, get_all_vendors
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_data_tab():
    st.markdown("## 수거 데이터")

    tab1, tab2, tab3 = st.tabs(["전송 대기 (미확인)", "전체 수거 내역", "시뮬레이션"])

    with tab1:
        _render_pending()

    with tab2:
        _render_collection_table('real_collection', "실제 수거")

    with tab3:
        _render_collection_table('sim_collection', "시뮬레이션")


def _render_pending():
    """기사가 전송한 미확인 데이터"""
    rows = [r for r in db_get('real_collection') if r.get('status') == 'submitted']

    if not rows:
        st.success("미확인 전송 데이터가 없습니다.")
        return

    st.warning(f"⚠️ 기사 전송 데이터 {len(rows)}건 확인 필요")

    df = pd.DataFrame(rows)
    show = [c for c in ['id','collect_date','school_name','vendor','item_type','weight','driver','submitted_at','memo'] if c in df.columns]
    st.dataframe(df[show].sort_values('submitted_at', ascending=False) if 'submitted_at' in df.columns else df[show],
                 use_container_width=True, hide_index=True)

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ 전체 확인 처리", type="primary", use_container_width=True):
            import sqlite3
            from config.settings import DB_PATH
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE real_collection SET status='confirmed' WHERE status='submitted'")
                conn.commit()
                conn.close()
                st.success(f"{len(rows)}건 확인 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")

    with col2:
        if 'id' in df.columns:
            sel_id = st.number_input("특정 ID 반려", min_value=1, step=1, key="reject_id")
            if st.button("반려 처리", use_container_width=True):
                import sqlite3
                from config.settings import DB_PATH
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.execute("UPDATE real_collection SET status='rejected' WHERE id=?", (sel_id,))
                    conn.commit()
                    conn.close()
                    st.warning(f"ID {sel_id} 반려 처리됨")
                    st.rerun()
                except Exception as e:
                    st.error(f"오류: {e}")


def _render_collection_table(table, label):
    col1, col2, col3 = st.columns(3)
    with col1:
        vendors = ['전체'] + get_all_vendors()
        vendor_filter = st.selectbox("업체", vendors, key=f"v_{table}")
    with col2:
        schools = ['전체'] + get_all_schools()
        school_filter = st.selectbox("학교", schools, key=f"s_{table}")
    with col3:
        status_filter = st.selectbox("상태", ['전체','draft','submitted','confirmed','rejected'], key=f"st_{table}")

    rows = db_get(table)
    if not rows:
        st.info(f"{label} 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    if vendor_filter != '전체' and 'vendor' in df.columns:
        df = df[df['vendor'] == vendor_filter]
    if school_filter != '전체' and 'school_name' in df.columns:
        df = df[df['school_name'] == school_filter]
    if status_filter != '전체' and 'status' in df.columns:
        df = df[df['status'] == status_filter]

    # 상태 한글 표시
    if 'status' in df.columns:
        status_map = {
            'draft':     '📋 임시저장',
            'submitted': '📤 전송완료',
            'confirmed': '✅ 확인완료',
            'rejected':  '❌ 반려',
        }
        df['status'] = df['status'].map(status_map).fillna(df['status'])

    st.dataframe(df, use_container_width=True, hide_index=True)
    if 'weight' in df.columns:
        st.metric("합계", f"{df['weight'].sum():,.1f} kg")
