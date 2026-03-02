# zeroda_platform/modules/vendor_admin/schedule_tab.py
# ==========================================
# 외주업체 관리자 - 수거일정 탭
# ==========================================

import streamlit as st
from datetime import date
from config.settings import CURRENT_MONTH
from database.db_manager import (
    load_schedule, load_all_schedules,
    get_schools_by_vendor
)

WEEKDAY_MAP = {0:'월',1:'화',2:'수',3:'목',4:'금',5:'토',6:'일'}


def render_schedule_tab(vendor: str):
    st.markdown("## 📅 수거일정")

    tab_month, tab_today = st.tabs(["월별 일정", "오늘 일정"])

    with tab_month:
        _render_monthly(vendor)
    with tab_today:
        _render_today(vendor)


def _render_monthly(vendor: str):
    st.markdown("### 월별 수거일정")

    month = st.selectbox("월 선택", list(range(1, 13)),
                         index=CURRENT_MONTH - 1, key="vs_month")
    sched = load_schedule(vendor, month)

    if not sched:
        st.info(f"{month}월 수거일정이 없습니다. 본사에서 등록 후 확인 가능합니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**수거 요일**")
        for wd in sched.get('요일', []):
            st.markdown(f"• {wd}요일")

        st.markdown("**수거 품목**")
        for item in sched.get('품목', []):
            st.markdown(f"• {item}")

        st.markdown(f"**담당 기사:** {sched.get('기사', '-')}")

    with col2:
        schools = sched.get('학교', [])
        st.markdown(f"**담당 학교 ({len(schools)}개)**")
        for s in schools:
            st.markdown(f"• {s}")

    # 전체 월 요약
    st.divider()
    st.markdown("### 전체 월별 일정 요약")
    all_scheds = load_all_schedules(vendor)
    if not all_scheds:
        return

    for m in sorted(all_scheds.keys()):
        s = all_scheds[m]
        weekdays = ', '.join(s.get('요일', []))
        school_count = len(s.get('학교', []))
        st.markdown(f"**{m}월** — {weekdays}요일 | {school_count}개 학교 | 기사: {s.get('기사','-')}")


def _render_today(vendor: str):
    st.markdown("### 오늘 수거 일정")

    today    = date.today()
    today_wd = WEEKDAY_MAP[today.weekday()]
    sched    = load_schedule(vendor, today.month)

    st.info(f"📅 {today.strftime('%Y년 %m월 %d일')} ({today_wd}요일)")

    if not sched:
        st.warning("이번 달 수거일정이 등록되지 않았습니다.")
        return

    if today_wd not in sched.get('요일', []):
        st.info(f"오늘({today_wd}요일)은 수거 일정이 없습니다.")
        return

    schools = sched.get('학교', [])
    items   = sched.get('품목', [])
    driver  = sched.get('기사', '-')

    st.success(f"오늘 수거 학교 {len(schools)}개")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**수거 품목:** {', '.join(items)}")
        st.markdown(f"**담당 기사:** {driver}")
    with col2:
        for s in schools:
            st.markdown(f"✅ {s}")