# modules/vendor_admin/collection_tab.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.db_manager import db_get, db_upsert, get_schools_by_vendor
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_collection_tab(vendor):
    st.markdown("## 수거 데이터")

    tab1, tab2 = st.tabs(["📋 수거 내역", "✏️ 수거 입력"])

    with tab1:
        from zoneinfo import ZoneInfo
        from services.collection_view import render_collection_table, render_collection_edit

        # 새로고침 버튼 - 캐시 무효화
        col_r, _ = st.columns([1, 4])
        with col_r:
            if st.button("🔄 새로고침", key="va_refresh"):
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
                st.rerun()

        # ── 필터: 월별 + 학교/거래처 ──────────────
        _fc1, _fc2 = st.columns(2)
        with _fc1:
            now_kst = datetime.now(ZoneInfo('Asia/Seoul'))
            month_options = []
            for i in range(12):
                y = now_kst.year
                m = now_kst.month - i
                while m <= 0:
                    m += 12
                    y -= 1
                month_options.append(f"{y}-{str(m).zfill(2)}")
            month_options = ["전체"] + month_options
            sel_month = st.selectbox(
                "월별",
                month_options,
                key="vnd_col_month"
            )
        with _fc2:
            customer_rows = db_get('customer_info', {'vendor': vendor})
            if not customer_rows:
                customer_rows = []
            school_options = ["전체"] + [
                r.get('name', '') for r in customer_rows
                if r.get('name')
            ]
            sel_school = st.selectbox(
                "학교/거래처",
                school_options,
                key="vnd_col_school"
            )

        rows = [r for r in db_get('real_collection') if r.get('vendor') == vendor]

        # 월별 필터 적용
        if sel_month != "전체":
            rows = [r for r in rows
                    if str(r.get('collect_date', '')).startswith(sel_month)]
        # 학교 필터 적용
        if sel_school != "전체":
            rows = [r for r in rows
                    if str(r.get('school_name', '')) == sel_school]

        # 공통 테이블 렌더 + 수정 UI
        render_collection_table(rows, key_prefix="vnd_col")
        render_collection_edit(rows, key_prefix="vnd_col")

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
