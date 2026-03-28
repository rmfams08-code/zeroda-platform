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

        if rows:
            df = pd.DataFrame(rows)

            # 상태 한글 표시
            if 'status' in df.columns:
                df['status'] = df['status'].map({
                    'draft':     '📋 임시저장',
                    'submitted': '📤 전송완료',
                    'confirmed': '✅ 확인완료',
                    'rejected':  '❌ 반려',
                }).fillna(df['status'])

            # collect_date 기준 내림차순 정렬
            if 'collect_date' in df.columns:
                df = df.sort_values('collect_date', ascending=False)

            # 표시 컬럼 순서 고정
            show_cols = [
                c for c in [
                    'collect_date', 'collect_time',
                    'school_name', 'item_type', 'weight',
                    'unit_price', 'amount',
                    'driver', 'memo', 'status'
                ] if c in df.columns
            ]
            st.dataframe(
                df[show_cols] if show_cols else df,
                use_container_width=True,
                hide_index=True
            )

            # 합계 표시
            if 'weight' in df.columns:
                total_weight = df['weight'].sum()
                total_amount = df['amount'].sum() if 'amount' in df.columns else 0
                _mc1, _mc2 = st.columns(2)
                with _mc1:
                    st.metric("총 수거량", f"{total_weight:,.1f} kg")
                with _mc2:
                    st.metric("총 금액", f"{total_amount:,.0f} 원")

            # ── 수거량 수정 UI ─────────────────────────
            st.divider()
            st.markdown("#### ✏️ 수거량 수정")
            st.caption("기사가 입력한 수거량을 수정할 수 있습니다.")

            edit_rows = [r for r in rows
                         if r.get('status') in ('submitted', 'confirmed')]

            if not edit_rows:
                st.info("수정 가능한 수거 데이터가 없습니다.")
            else:
                edit_options = [
                    f"{r.get('collect_date', '')} | "
                    f"{r.get('school_name', '')} | "
                    f"{r.get('item_type', '')} | "
                    f"{r.get('weight', 0)}kg"
                    for r in edit_rows
                ]

                _vc1, _vc2, _vc3 = st.columns(3)
                with _vc1:
                    sel_idx = st.selectbox(
                        "수정할 항목 선택",
                        range(len(edit_options)),
                        format_func=lambda i: edit_options[i],
                        key="vnd_col_edit_sel"
                    )
                    sel_row = edit_rows[sel_idx]
                with _vc2:
                    new_weight = st.number_input(
                        "수정 수거량 (kg)",
                        min_value=0.0,
                        value=float(sel_row.get('weight', 0) or 0),
                        step=0.5,
                        format="%.1f",
                        key="vnd_col_edit_weight"
                    )
                with _vc3:
                    st.write("")
                    st.write("")
                    if st.button(
                        "💾 수거량 수정",
                        key="vnd_col_edit_save",
                        use_container_width=True
                    ):
                        updated = dict(sel_row)
                        updated['weight'] = new_weight
                        unit_price = float(
                            sel_row.get('unit_price', 0) or 0)
                        updated['amount'] = round(
                            new_weight * unit_price, 0)
                        ok = db_upsert('real_collection', updated)
                        if ok:
                            st.success("✅ 수거량 수정 완료")
                            st.rerun()
                        else:
                            st.error("수정 실패")
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
