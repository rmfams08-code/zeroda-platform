# modules/vendor_admin/schedule_tab.py
import streamlit as st
from database.db_manager import (
    get_schools_by_vendor, save_schedule, load_all_schedules,
    delete_schedule, db_get, save_schedule_by_vendor
)
from config.settings import CURRENT_YEAR, CURRENT_MONTH
from zoneinfo import ZoneInfo
from datetime import datetime, date


def render_schedule_tab(vendor):
    st.markdown("## 수거일정 관리")

    tab1, tab2, tab3 = st.tabs(["📅 일정 조회/삭제", "📋 일정 등록", "✏️ 일정 등록/수정"])

    # ── 등록 탭 ───────────────
    with tab2:
        st.markdown("### 일정 등록")

        # 등록 모드 선택 (본사와 동일)
        reg_mode = st.radio(
            "등록 단위 선택",
            ["📅 월별 등록 (수거 요일 반복)", "📌 일별 등록 (특정 날짜 지정)"],
            horizontal=True,
            key="sch_reg_mode"
        )
        is_daily = reg_mode.startswith("📌")

        col1, col2 = st.columns(2)
        with col1:
            if is_daily:
                reg_date = st.date_input(
                    "수거 날짜", value=date.today(), key="sch_reg_date"
                )
                auto_weekday = ['월','화','수','목','금','토','일'][reg_date.weekday()]
                st.info(f"선택 날짜: **{reg_date.strftime('%Y년 %m월 %d일')} ({auto_weekday}요일)**")
                weekdays = [auto_weekday]
                month_str = reg_date.strftime('%Y-%m-%d')
            else:
                year     = st.selectbox("연도", [2025, 2026], key="sch_reg_year")
                month    = st.selectbox("월", list(range(1, 13)),
                                        index=CURRENT_MONTH - 1, key="sch_reg_month")
                weekdays = st.multiselect("수거 요일",
                                          ["월", "화", "수", "목", "금", "토"],
                                          key="sch_reg_days")
                month_str = f"{year}-{str(month).zfill(2)}"
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
            if is_daily:
                st.info(f"📌 {reg_date.strftime('%Y년 %m월 %d일')} ({auto_weekday}요일) "
                        f"| 학교: {len(sel_schools)}개 | 품목: {', '.join(items) if items else '-'} "
                        f"| 기사: {driver or '-'}")
            else:
                st.info(f"📌 {year}년 {month}월 | 요일: {', '.join(weekdays) if weekdays else '-'} "
                        f"| 학교: {len(sel_schools)}개 | 품목: {', '.join(items) if items else '-'} "
                        f"| 기사: {driver or '-'}")

        if st.button("💾 일정 저장", type="primary", use_container_width=True, key="sch_save"):
            if not is_daily and not weekdays:
                st.error("수거 요일을 선택하세요.")
            elif not sel_schools:
                st.error("수거 학교를 선택하세요.")
            elif not items:
                st.error("수거 품목을 선택하세요.")
            else:
                ok = save_schedule(vendor, month_str, weekdays, sel_schools, items, driver)
                if ok:
                    _label = reg_date.strftime('%Y년 %m월 %d일') if is_daily else f"{year}년 {month}월"
                    st.success(f"✅ {_label} 일정 저장 완료!")
                    st.rerun()
                else:
                    st.error("저장 실패 - 관리자에게 문의하세요.")

    # ── 조회/삭제 탭 (첫 번째) ─────────────────────
    with tab1:
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

    # ── 외주업체 일정 등록/수정 탭 ──────────────
    with tab3:
        st.markdown("### 수거일정 등록/수정")

        # 등록 모드 선택 (본사와 동일)
        vnd_reg_mode = st.radio(
            "등록 단위 선택",
            ["📅 월별 등록 (수거 요일 반복)", "📌 일별 등록 (특정 날짜 지정)"],
            horizontal=True,
            key="vnd_sch_reg_mode"
        )
        vnd_is_daily = vnd_reg_mode.startswith("📌")

        if vnd_is_daily:
            vnd_reg_date = st.date_input(
                "수거 날짜", value=date.today(), key="vnd_sch_reg_date"
            )
            vnd_auto_wd = ['월','화','수','목','금','토','일'][vnd_reg_date.weekday()]
            st.info(f"선택 날짜: **{vnd_reg_date.strftime('%Y년 %m월 %d일')} ({vnd_auto_wd}요일)**")
            weekdays = [vnd_auto_wd]
        else:
            # 연도·월 선택
            col1, col2 = st.columns(2)
            with col1:
                year = st.selectbox(
                    "연도", [2025, 2026],
                    key="vnd_sch_year"
                )
            with col2:
                month = st.selectbox(
                    "월", list(range(1, 13)),
                    key="vnd_sch_month"
                )

            # 수거 요일 선택
            weekdays = st.multiselect(
                "수거 요일",
                ["월", "화", "수", "목", "금", "토"],
                key="vnd_sch_days"
            )

        # 담당 학교 선택 — customer_info에서 vendor 기준 조회
        customer_rows = db_get('customer_info', {'vendor': vendor})
        if not customer_rows:
            customer_rows = []
        school_list = [
            r.get('name', '') for r in customer_rows
            if r.get('name')
        ]
        if not school_list:
            st.warning(
                f"'{vendor}' 업체에 등록된 학교가 없습니다.\n"
                "거래처 관리에서 학교를 먼저 등록하세요."
            )
            sel_schools = []
        else:
            sel_schools = st.multiselect(
                "담당 학교", school_list,
                key="vnd_sch_schools"
            )

        # 수거 품목 선택
        items = st.multiselect(
            "수거 품목",
            ["음식물", "재활용", "일반"],
            key="vnd_sch_items"
        )

        # 담당 기사 선택
        driver_rows = [
            r for r in db_get('users')
            if r.get('role') == 'driver'
            and r.get('vendor') == vendor
        ]
        driver_names = [
            r.get('name') or r.get('user_id', '')
            for r in driver_rows
            if r.get('name') or r.get('user_id')
        ]
        if driver_names:
            driver = st.selectbox(
                "담당 기사",
                ["(선택 안 함)"] + driver_names,
                key="vnd_sch_driver_sel"
            )
            if driver == "(선택 안 함)":
                driver = ""
        else:
            driver = st.text_input(
                "담당 기사 (직접 입력)",
                key="vnd_sch_driver_txt"
            )

        # 미리보기
        if weekdays or sel_schools or items:
            if vnd_is_daily:
                st.info(
                    f"📌 {vnd_reg_date.strftime('%Y년 %m월 %d일')} ({vnd_auto_wd}요일) "
                    f"| 학교: {len(sel_schools)}개 "
                    f"| 품목: {', '.join(items) if items else '-'} "
                    f"| 기사: {driver or '-'}"
                )
            else:
                st.info(
                    f"📌 {year}년 {month}월 "
                    f"| 요일: {', '.join(weekdays) if weekdays else '-'} "
                    f"| 학교: {len(sel_schools)}개 "
                    f"| 품목: {', '.join(items) if items else '-'} "
                    f"| 기사: {driver or '-'}"
                )

        # 저장/삭제 버튼
        col_s, col_d = st.columns(2)
        with col_s:
            if st.button(
                "💾 일정 저장", type="primary",
                use_container_width=True,
                key="vnd_sch_save"
            ):
                if not vnd_is_daily and not weekdays:
                    st.error("수거 요일을 선택하세요.")
                elif not sel_schools:
                    st.error("수거 학교를 선택하세요.")
                elif not items:
                    st.error("수거 품목을 선택하세요.")
                else:
                    if vnd_is_daily:
                        month_str = vnd_reg_date.strftime('%Y-%m-%d')
                    else:
                        month_str = f"{year}-{str(month).zfill(2)}"
                    ok = save_schedule_by_vendor(
                        vendor, month_str, weekdays,
                        sel_schools, items, driver
                    )
                    if ok:
                        _label = vnd_reg_date.strftime('%Y년 %m월 %d일') if vnd_is_daily else f"{year}년 {month}월"
                        st.success(f"✅ {_label} 일정 저장 완료!")
                        st.rerun()
                    else:
                        st.error("저장 실패")

        with col_d:
            # 삭제: 본인 업체 일정만, registered_by='vendor'인 것만 삭제 허용
            schedules = load_all_schedules(vendor)
            if not isinstance(schedules, dict):
                schedules = {}
            deletable = {
                k: v for k, v in schedules.items()
                if v.get('registered_by', 'admin') == 'vendor'
            }
            if deletable:
                del_month = st.selectbox(
                    "삭제할 월 선택",
                    list(deletable.keys()),
                    key="vnd_sch_del_month"
                )
                if st.button(
                    "🗑️ 삭제",
                    use_container_width=True,
                    key="vnd_sch_del"
                ):
                    delete_schedule(vendor, del_month)
                    st.success(f"{del_month} 일정 삭제 완료")
                    st.rerun()
            else:
                st.caption(
                    "직접 등록한 일정이 없습니다.\n"
                    "본사 등록 일정은 삭제할 수 없습니다."
                )
