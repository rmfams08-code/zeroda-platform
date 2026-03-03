# modules/vendor_admin/collection_tab.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.db_manager import db_get, db_upsert, get_schools_by_vendor
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_collection_tab(vendor):
    st.markdown("## 수거 데이터")

    tab1, tab2 = st.tabs(["수거 내역", "수거 입력"])

    with tab1:
        # 새로고침 버튼 - 캐시 무효화
        col_r, _ = st.columns([1, 4])
        with col_r:
            if st.button("🔄 새로고침", key="va_refresh"):
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
                st.rerun()

        rows = [r for r in db_get('real_collection') if r.get('vendor') == vendor]

        if rows:
            df = pd.DataFrame(rows)
            # 상태 한글 표시
            if 'status' in df.columns:
                df['status'] = df['status'].map({
                    'draft':     '📋 임시저장',
                    'submitted': '✅ 전송완료',
                    'confirmed': '✔️ 확인완료',
                    'rejected':  '❌ 반려',
                }).fillna(df['status'])

            show = [c for c in ['collect_date','school_name','item_type',
                                'weight','driver','status','memo'] if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                if 'weight' in df.columns:
                    st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")
            with c2:
                submitted = len([r for r in rows if r.get('status') == 'submitted'])
                st.metric("미확인 전송", f"{submitted}건")
        else:
            st.info("수거 데이터가 없습니다.")

    with tab2:
        st.markdown("### 수거 입력")
        schools = get_schools_by_vendor(vendor)
        col1, col2 = st.columns(2)
        with col1:
            school       = st.selectbox("학교", schools if schools else ['학교 없음'])
            collect_date = st.date_input("수거일", value=date.today())
            item_type    = st.selectbox("품목", ["음식물", "재활용", "일반"])
        with col2:
            weight = st.number_input("수거량 (kg)", min_value=0.0, step=0.1)
            driver = st.text_input("기사명")
            memo   = st.text_input("메모")

        if st.button("저장", type="primary"):
            if not school or school == '학교 없음':
                st.error("학교를 선택하세요.")
            else:
                ok = db_upsert('real_collection', {
                    'vendor':       vendor,
                    'school_name':  school,
                    'collect_date': str(collect_date),
                    'item_type':    item_type,
                    'weight':       weight,
                    'driver':       driver,
                    'memo':         memo,
                    'status':       'confirmed',
                    'created_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                if ok:
                    st.success("저장 완료!")
                    from services.github_storage import _github_get_cached
                    _github_get_cached.clear()
                else:
                    st.error("저장 실패")
