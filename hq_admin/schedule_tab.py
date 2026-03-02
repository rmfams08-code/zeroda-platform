# zeroda_platform/modules/hq_admin/schedule_tab.py
# ==========================================
# 본사 관리자 - 수거일정 탭
# ==========================================

import streamlit as st
from config.settings import CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import (
    db_get, get_all_vendors, get_schools_by_vendor,
    save_schedule, load_schedule, load_all_schedules, delete_schedule
)


WEEKDAY_OPTIONS = ['월', '화', '수', '목', '금']
ITEM_OPTIONS    = ['음식물', '재활용', '일반쓰레기', '사업장']


def render_schedule_tab():
    st.markdown("## 📅 수거일정 관리")

    tab_view, tab_edit, tab_today = st.tabs(
        ["일정 조회", "일정 등록/수정", "오늘 수거 현황"])

    with tab_view:
        _render_schedule_view()
    with tab_edit:
        _render_schedule_edit()
    with tab_today:
        _render_today_schedule()


def _render_schedule_view():
    st.markdown("### 수거일정 조회")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return

    vendor = st.selectbox("업체 선택", vendors, key="sched_view_vendor")
    month  = st.selectbox("월", list(range(1, 13)),
                          index=CURRENT_MONTH - 1, key="sched_view_month")

    sched = load_schedule(vendor, month)
    if not sched:
        st.info(f"{vendor} {month}월 일정이 없습니다.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**수거 요일:** {', '.join(sched.get('요일', []))}")
        st.markdown(f"**담당 기사:** {sched.get('기사', '-')}")
    with c2:
        st.markdown(f"**수거 품목:** {', '.join(sched.get('품목', []))}")
        schools = sched.get('학교', [])
        st.markdown(f"**담당 학교 ({len(schools)}개):** {', '.join(schools[:5])}"
                    + (" 외..." if len(schools) > 5 else ""))


def _render_schedule_edit():
    st.markdown("### 수거일정 등록/수정")

    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        vendor = st.selectbox("업체", vendors, key="sched_edit_vendor")
    with col2:
        month  = st.selectbox("월", list(range(1, 13)),
                              index=CURRENT_MONTH - 1, key="sched_edit_month")

    # 기존 일정 불러오기
    existing = load_schedule(vendor, month)

    weekdays = st.multiselect(
        "수거 요일", WEEKDAY_OPTIONS,
        default=existing.get('요일', []) if existing else [],
        key="sched_weekdays"
    )
    items = st.multiselect(
        "수거 품목", ITEM_OPTIONS,
        default=existing.get('품목', []) if existing else [],
        key="sched_items"
    )

    # 담당 학교 선택
    avail_schools = get_schools_by_vendor(vendor)
    if avail_schools:
        schools = st.multiselect(
            "담당 학교", avail_schools,
            default=[s for s in (existing.get('학교', []) if existing else [])
                     if s in avail_schools],
            key="sched_schools"
        )
    else:
        schools_txt = st.text_area(
            "담당 학교 (줄바꿈으로 구분)",
            value='\n'.join(existing.get('학교', []) if existing else []),
            key="sched_schools_txt"
        )
        schools = [s.strip() for s in schools_txt.split('\n') if s.strip()]

    # 담당 기사
    driver_rows = db_get('users')
    driver_rows = [r for r in driver_rows
                   if r.get('role') == 'driver'
                   and r.get('vendor') == vendor]
    driver_options = ['미지정'] + [r.get('name', r['user_id']) for r in driver_rows]
    driver = st.selectbox("담당 기사", driver_options, key="sched_driver")
    driver = '' if driver == '미지정' else driver

    col_save, col_del = st.columns([3, 1])
    with col_save:
        if st.button("💾 일정 저장", type="primary", key="btn_sched_save"):
            if not weekdays:
                st.error("수거 요일을 선택하세요.")
            elif not schools:
                st.error("담당 학교를 선택하세요.")
            else:
                ok = save_schedule(vendor, month, weekdays, schools, items, driver)
                if ok:
                    st.success(f"{vendor} {month}월 일정 저장 완료")
                    st.rerun()
                else:
                    st.error("저장 실패")

    with col_del:
        if existing and st.button("🗑️ 삭제", key="btn_sched_del"):
            delete_schedule(vendor, month)
            st.success("삭제 완료")
            st.rerun()


def _render_today_schedule():
    st.markdown("### 오늘 수거 현황")

    from datetime import date
    today = date.today()
    weekday_map = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
    today_weekday = weekday_map[today.weekday()]

    st.info(f"오늘: {today.strftime('%Y년 %m월 %d일')} ({today_weekday}요일)")

    vendors = get_all_vendors()
    has_schedule = False

    for vendor in vendors:
        sched = load_schedule(vendor, today.month)
        if not sched:
            continue
        if today_weekday not in sched.get('요일', []):
            continue

        has_schedule = True
        schools = sched.get('학교', [])
        with st.expander(f"🚚 {vendor} — {len(schools)}개 학교", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**수거 품목:** {', '.join(sched.get('품목', []))}")
                st.markdown(f"**담당 기사:** {sched.get('기사', '-')}")
            with col2:
                for s in schools:
                    st.markdown(f"• {s}")

    if not has_schedule:
        st.info(f"{today_weekday}요일 수거 일정이 없습니다.")