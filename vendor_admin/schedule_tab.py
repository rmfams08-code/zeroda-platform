# modules/vendor_admin/schedule_tab.py
import streamlit as st
from database.db_manager import get_schools_by_vendor, save_schedule, load_all_schedules, delete_schedule
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_schedule_tab(vendor):
    st.markdown("## 수거일정 관리")

    tab1, tab2 = st.tabs(["📋 일정 등록", "📅 일정 조회/삭제"])

    # ── 등록 탭 (첫 번째로) ───────────────
    with tab1:
        st.markdown("### 일정 등록")
        col1, col2 = st.columns(2)
        with col1:
            year     = st.selectbox("연도", [2025, 2026], key="sch_reg_year")
            month    = st.selectbox("월", list(range(1, 13)),
                                    index=CURRENT_MONTH - 1, key="sch_reg_month")
            weekdays = st.multiselect("수거 요일",
                                      ["월", "화", "수", "목", "금", "토"],
                                      key="sch_reg_days")
        with col2:
            schools     = get_schools_by_vendor(vendor)
            sel_schools = st.multiselect("수거 학교",
                                          schools if schools else [],
                                          key="sch_reg_schools")
            items  = st.multiselect("수거 품목",
                                    ["음식물", "재활용", "일반"],
                                    key="sch_reg_items")
            driver = st.text_input("담당 기사", key="sch_reg_driver")

        # 입력 요약 미리보기
        if weekdays or sel_schools or items:
            st.info(f"📌 {year}년 {month}월 | 요일: {', '.join(weekdays) if weekdays else '-'} "
                    f"| 학교: {len(sel_schools)}개 | 품목: {', '.join(items) if items else '-'} "
                    f"| 기사: {driver or '-'}")

        if st.button("💾 일정 저장", type="primary", use_container_width=True, key="sch_save"):
            if not weekdays:
                st.error("수거 요일을 선택하세요.")
            elif not sel_schools:
                st.error("수거 학교를 선택하세요.")
            elif not items:
                st.error("수거 품목을 선택하세요.")
            else:
                month_str = f"{year}-{str(month).zfill(2)}"
                ok = save_schedule(vendor, month_str, weekdays, sel_schools, items, driver)
                if ok:
                    st.success(f"✅ {year}년 {month}월 일정 저장 완료!")
                    st.rerun()
                else:
                    st.error("저장 실패 - 관리자에게 문의하세요.")

    # ── 조회/삭제 탭 ─────────────────────
    with tab2:
        schedules = load_all_schedules(vendor)
        if not schedules:
            st.info("등록된 일정이 없습니다. '일정 등록' 탭에서 추가하세요.")
        else:
            st.markdown(f"**총 {len(schedules)}개월 일정 등록됨**")
            for month_key, info in sorted(schedules.items()):
                with st.expander(f"📅 {month_key} 일정"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**수거 요일:** {', '.join(info.get('요일', []))}")
                        st.write(f"**수거 품목:** {', '.join(info.get('품목', []))}")
                        st.write(f"**담당 기사:** {info.get('기사', '-')}")
                    with col2:
                        schools_list = info.get('학교', [])
                        st.write(f"**담당 학교 ({len(schools_list)}개):**")
                        for s in schools_list:
                            st.write(f"  • {s}")

                    if st.button("🗑 삭제", key=f"del_{month_key}", type="secondary"):
                        delete_schedule(vendor, month_key)
                        st.success(f"{month_key} 일정 삭제 완료")
                        st.rerun()
