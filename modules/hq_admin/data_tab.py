# modules/hq_admin/data_tab.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, db_upsert, get_all_schools, get_all_vendors
from services.upload_handler import read_file, map_columns, get_column_mapping_info, save_to_db
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_data_tab():
    st.markdown("## 수거 데이터")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 데이터 업로드",
        "⏳ 전송 대기 (미확인)",
        "📋 전체 수거 내역",
        "🔬 시뮬레이션"
    ])

    with tab1:
        _render_upload()

    with tab2:
        _render_pending()

    with tab3:
        _render_collection_table('real_collection', "실제 수거")

    with tab4:
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
    from zoneinfo import ZoneInfo
    from datetime import datetime
    from services.collection_view import render_collection_table, render_collection_edit

    # ── 필터 행 1: 업체 + 월별 ──────────────
    _fc1, _fc2 = st.columns(2)
    with _fc1:
        vendors = ['전체'] + get_all_vendors()
        vendor_filter = st.selectbox("업체", vendors, key=f"v_{table}")
    with _fc2:
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
            key=f"hq_data_month_{table}"
        )

    # ── 필터 행 2: 학교/거래처 (업체 연동) ────
    if vendor_filter != '전체':
        customer_rows = db_get('customer_info', {'vendor': vendor_filter})
        if not customer_rows:
            customer_rows = []
        school_options = ["전체"] + [
            r.get('name', '') for r in customer_rows
            if r.get('name')
        ]
    else:
        school_options = ['전체'] + get_all_schools()
    sel_school = st.selectbox(
        "학교/거래처",
        school_options,
        key=f"hq_data_school_{table}"
    )

    rows = db_get(table)
    if not rows:
        st.info(f"{label} 데이터가 없습니다.")
        return

    # 필터 적용
    filtered = rows
    if vendor_filter != '전체':
        filtered = [r for r in filtered if r.get('vendor') == vendor_filter]
    if sel_school != '전체':
        filtered = [r for r in filtered if r.get('school_name') == sel_school]
    if sel_month != '전체':
        filtered = [r for r in filtered
                    if str(r.get('collect_date', '')).startswith(sel_month)]

    # 공통 테이블 렌더 + 수정 UI
    render_collection_table(filtered, key_prefix=f"hq_{table}")
    render_collection_edit(filtered, key_prefix=f"hq_{table}")


def _render_upload():
    """CSV / 엑셀 파일 업로드 → DB 저장"""
    st.markdown("### 데이터 업로드")
    st.caption("CSV 또는 XLSX 파일을 업로드하여 수거 데이터를 일괄 등록합니다.")

    col1, col2 = st.columns(2)
    with col1:
        table = st.selectbox("저장 테이블",
                             ["real_collection", "sim_collection"],
                             format_func=lambda x: "실제 수거 데이터" if x == "real_collection" else "시뮬레이션 데이터",
                             key="up_table")
    with col2:
        dup_action = st.selectbox("중복 데이터 처리",
                                  ["skip", "overwrite"],
                                  format_func=lambda x: "건너뛰기 (권장)" if x == "skip" else "덮어쓰기",
                                  key="up_dup")

    vendors = get_all_vendors()
    default_vendor = st.selectbox("기본 업체 (vendor 컬럼 없을 때 적용)",
                                   [""] + vendors, key="up_vendor")

    uploaded = st.file_uploader("파일 선택 (CSV, XLSX)",
                                 type=["csv", "xlsx", "xls"],
                                 key="up_file")

    if uploaded is None:
        st.info("CSV 또는 XLSX 파일을 업로드하세요.")
        st.markdown("""
**지원 컬럼 (한글/영문 모두 가능):**
`날짜`, `학교명`, `음식물(kg)`, `단가(원)`, `공급가`, `재활용방법`, `재활용업체`
""")
        return

    try:
        df = read_file(uploaded)
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")
        return

    st.markdown(f"**총 {len(df)}행 읽음**")

    # 컬럼 매핑 정보 표시
    with st.expander("컬럼 매핑 확인"):
        mapping_info = get_column_mapping_info(df)
        for orig, mapped in mapping_info.items():
            st.write(f"`{orig}` {mapped}")

    # 상위 10행 미리보기
    st.markdown("#### 미리보기 (상위 10행)")
    st.dataframe(df.head(10), use_container_width=True)

    st.divider()

    if st.button("💾 DB에 저장", type="primary", use_container_width=True, key="up_save"):
        mapped_df = map_columns(df)
        with st.spinner(f"{len(df)}행 저장 중..."):
            result = save_to_db(mapped_df, table,
                                duplicate_action=dup_action,
                                default_vendor=default_vendor)

        # 결과 요약
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("✅ 성공", f"{result['success']}건")
        with c2:
            st.metric("⏭️ 건너뜀", f"{result['skip']}건")
        with c3:
            st.metric("❌ 실패", f"{result['fail']}건")

        if result['success'] > 0:
            st.success(f"{result['success']}건 저장 완료!")
        if result['errors']:
            with st.expander(f"오류 상세 ({len(result['errors'])}건)"):
                for err in result['errors'][:20]:
                    st.write(f"• {err}")
