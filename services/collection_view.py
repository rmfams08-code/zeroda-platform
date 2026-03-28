# services/collection_view.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 수거 데이터 조회·수정 공통 UI 함수 (본사·외주업체 공용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import streamlit as st
import pandas as pd
from database.db_manager import db_upsert


# 상태 이모지 맵 (플랫폼 전역 표준)
STATUS_MAP = {
    'draft':     '📋 임시저장',
    'submitted': '📤 전송완료',
    'confirmed': '✅ 확인완료',
    'rejected':  '❌ 반려',
}


def render_collection_table(rows, key_prefix="col"):
    """
    수거 데이터 테이블 + 합계 + 수정 UI 를 렌더링.
    rows: list[dict] — 이미 필터링된 수거 데이터
    key_prefix: Streamlit widget key 충돌 방지용 접두어
    """
    if not rows:
        st.info("수거 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)

    # 상태 한글 표시
    if 'status' in df.columns:
        df['status'] = df['status'].map(STATUS_MAP).fillna(df['status'])

    # collect_date 기준 내림차순 정렬
    if 'collect_date' in df.columns:
        df = df.sort_values('collect_date', ascending=False)

    # 표시 컬럼 순서 고정
    show_cols = [
        c for c in [
            'collect_date', 'collect_time',
            'school_name', 'vendor',
            'item_type', 'weight',
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


def render_collection_edit(rows, key_prefix="col"):
    """
    수거량 수정 UI. rows: 원본 list[dict] (status 필터링 전)
    key_prefix: widget key 접두어
    """
    st.divider()
    st.markdown("#### ✏️ 수거량 수정")
    st.caption("기사가 입력한 수거량을 수정할 수 있습니다.")

    edit_rows = [r for r in rows
                 if r.get('status') in ('submitted', 'confirmed')]

    if not edit_rows:
        st.info("수정 가능한 수거 데이터가 없습니다.")
        return

    edit_options = [
        f"{r.get('collect_date', '')} | "
        f"{r.get('school_name', '')} | "
        f"{r.get('item_type', '')} | "
        f"{r.get('weight', 0)}kg"
        for r in edit_rows
    ]

    _ec1, _ec2, _ec3 = st.columns(3)
    with _ec1:
        sel_idx = st.selectbox(
            "수정할 항목 선택",
            range(len(edit_options)),
            format_func=lambda i: edit_options[i],
            key=f"{key_prefix}_edit_sel"
        )
        sel_row = edit_rows[sel_idx]
    with _ec2:
        new_weight = st.number_input(
            "수정 수거량 (kg)",
            min_value=0.0,
            value=float(sel_row.get('weight', 0) or 0),
            step=0.5,
            format="%.1f",
            key=f"{key_prefix}_edit_weight"
        )
    with _ec3:
        st.write("")
        st.write("")
        if st.button(
            "💾 수거량 수정",
            key=f"{key_prefix}_edit_save",
            use_container_width=True
        ):
            updated = dict(sel_row)
            updated['weight'] = new_weight
            unit_price = float(sel_row.get('unit_price', 0) or 0)
            updated['amount'] = round(new_weight * unit_price, 0)
            ok = db_upsert('real_collection', updated)
            if ok:
                st.success("✅ 수거량 수정 완료")
                st.rerun()
            else:
                st.error("수정 실패")
