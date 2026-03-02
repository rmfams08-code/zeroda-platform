# zeroda_platform/modules/vendor_admin/biz_tab.py
# ==========================================
# 외주업체 관리자 - 일반업장 탭
# ==========================================

import streamlit as st
from database.db_manager import db_get, db_upsert, db_delete


def render_biz_tab(vendor: str):
    st.markdown("## 🏭 일반업장 관리")

    tab_list, tab_add = st.tabs(["업장 목록", "업장 등록"])

    with tab_list:
        _render_list(vendor)
    with tab_add:
        _render_add(vendor)


def _render_list(vendor: str):
    st.markdown("### 일반업장 목록")

    rows = db_get('biz_customers', {'vendor': vendor})
    if not rows:
        st.info("등록된 일반업장이 없습니다.")
        return

    for r in rows:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"🏭 **{r['biz_name']}**")
        with col2:
            if st.button("삭제", key=f"del_biz_{r['biz_name']}"):
                db_delete('biz_customers',
                          {'vendor': vendor, 'biz_name': r['biz_name']})
                st.success(f"'{r['biz_name']}' 삭제 완료")
                st.rerun()

    st.caption(f"총 {len(rows)}개 업장")


def _render_add(vendor: str):
    st.markdown("### 일반업장 등록")

    biz_name = st.text_input("업장명 *", key="biz_name_input",
                              placeholder="예: 화성시청 구내식당")

    if st.button("➕ 등록", type="primary", key="btn_biz_add"):
        if not biz_name.strip():
            st.error("업장명을 입력하세요.")
            return

        existing = db_get('biz_customers',
                          {'vendor': vendor, 'biz_name': biz_name})
        if existing:
            st.warning("이미 등록된 업장입니다.")
            return

        ok = db_upsert('biz_customers', {
            'vendor':   vendor,
            'biz_name': biz_name.strip()
        })
        if ok:
            st.success(f"'{biz_name}' 등록 완료")
            st.rerun()
        else:
            st.error("등록 실패")

    # ── 일괄 등록 ──
    st.divider()
    st.markdown("### 일괄 등록")
    bulk = st.text_area("업장명 목록 (줄바꿈으로 구분)",
                        key="biz_bulk",
                        placeholder="화성시청 구내식당\n동탄2청사 식당\n...")

    if st.button("일괄 등록", key="btn_biz_bulk"):
        names  = [n.strip() for n in bulk.split('\n') if n.strip()]
        if not names:
            st.error("업장명을 입력하세요.")
            return
        count = 0
        for name in names:
            existing = db_get('biz_customers',
                              {'vendor': vendor, 'biz_name': name})
            if not existing:
                ok = db_upsert('biz_customers',
                               {'vendor': vendor, 'biz_name': name})
                if ok:
                    count += 1
        st.success(f"{count}개 업장 등록 완료 (중복 제외)")
        st.rerun()