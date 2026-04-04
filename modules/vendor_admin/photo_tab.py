# modules/vendor_admin/photo_tab.py
# 업체관리자 - 현장 사진 조회 탭
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services.photo_storage import get_photo_records
from database.db_manager import db_get


def render_photo_tab(user: dict):
    vendor = user.get('vendor', '')
    st.markdown("### 📸 현장 사진 조회")

    # ── 필터 ──
    col1, col2, col3 = st.columns(3)
    with col1:
        photo_types = {"전체": None, "수거 증빙": "collection",
                       "계근표": "processing", "차량/장비": "vehicle", "사고/이슈": "accident"}
        type_sel = st.selectbox("사진 종류", list(photo_types.keys()), key="vd_photo_type")
    with col2:
        date_from = st.date_input("시작일", value=date.today() - timedelta(days=7),
                                   key="vd_photo_date_from")
    with col3:
        date_to = st.date_input("종료일", value=date.today(), key="vd_photo_date_to")

    # ── 데이터 조회 (자기 업체만) ──
    records = get_photo_records(
        vendor=vendor,
        photo_type=photo_types[type_sel],
    )

    # 날짜 필터
    records = [r for r in records
               if str(date_from) <= r.get('collect_date', '')[:10] <= str(date_to)]

    if not records:
        st.info("📷 조회된 사진이 없습니다.")
        return

    st.caption(f"총 {len(records)}장")

    # ── 사진 갤러리 (3열) ──
    type_label = {"collection": "수거 증빙", "processing": "계근표",
                  "vehicle": "차량/장비", "accident": "사고/이슈"}

    for i in range(0, len(records), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(records):
                break
            r = records[idx]
            with col:
                photo_url = r.get('photo_url', '')
                if photo_url:
                    st.image(photo_url, use_container_width=True)
                st.caption(
                    f"**{r.get('school_name', '-')}**\n"
                    f"📅 {r.get('collect_date', '-')} | "
                    f"🏷️ {type_label.get(r.get('photo_type', ''), '-')}\n"
                    f"🚛 {r.get('driver', '-')}"
                )
                if r.get('memo'):
                    st.caption(f"📝 {r['memo']}")
                st.divider()
