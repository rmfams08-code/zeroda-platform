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

    tab1, tab2 = st.tabs(["📅 일정 조회/삭제", "✏️ 일정 등록/수정"])

    # ══════════════════════════════════════════════
    # 탭1: 일정 조회/삭제
    # ══════════════════════════════════════════════
    with tab1:
        schedules = load_all_schedules(vendor)
        if not schedules:
            st.info("등록된 일정이 없습니다. '일정 등록/수정' 탭에서 추가하세요.")
        else:
            st.markdown(f"**총 {len(schedules)}개 일정 등록됨**")
            for month_key, info in sorted(schedules.items()):
                # 월별/일별 구분 표시
                _key_label = f"📌 {month_key} (일별)" if len(month_key) == 10 else f"📅 {month_key} (월별)"
                with st.expander(_key_label):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**수거 요일:** {', '.join(info.get('요일', []))}")
                        st.write(f"**수거 품목:** {', '.join(info.get('품목', []))}")
                        st.write(f"**담당 기사:** {info.get('기사', '-')}")
                    with col2:
                        schools_list = info.get('학교', [])
                        st.write(f"**담당 거래처 ({len(schools_list)}개):**")
                        for s in schools_list:
                            st.write(f"  • {s}")

                    # 본사 등록 일정은 삭제 불가 안내
                    _reg_by = info.get('registered_by', 'admin')
                    if _reg_by == 'vendor':
                        if st.button("🗑 삭제", key=f"del_{month_key}", type="secondary"):
                            delete_schedule(vendor, month_key)
                            st.success(f"{month_key} 일정 삭제 완료")
                            st.rerun()
                    else:
                        st.caption("ℹ️ 본사 등록 일정 (삭제 불가)")

    # ══════════════════════════════════════════════
    # 탭2: 일정 등록/수정 (통합 — 기존 tab3 승격)
    # ══════════════════════════════════════════════
    with tab2:
        st.markdown("### 수거일정 등록/수정")

        # 등록 모드 선택
        vnd_reg_mode = st.radio(
            "등록 단위 선택",
            ["📅 월별 등록 (수거 요일 반복)", "📌 일별 등록 (특정 날짜 지정)"],
            horizontal=True,
            key="vnd_sch_reg_mode"
        )
        vnd_is_daily = vnd_reg_mode.startswith("📌")

        col1, col2 = st.columns(2)
        with col1:
            if vnd_is_daily:
                vnd_reg_date = st.date_input(
                    "수거 날짜", value=date.today(), key="vnd_sch_reg_date"
                )
                vnd_auto_wd = ['월','화','수','목','금','토','일'][vnd_reg_date.weekday()]
                st.info(f"선택 날짜: **{vnd_reg_date.strftime('%Y년 %m월 %d일')} ({vnd_auto_wd}요일)**")
                weekdays = [vnd_auto_wd]
            else:
                year = st.selectbox(
                    "연도", [2025, 2026],
                    index=0 if CURRENT_YEAR not in [2025, 2026]
                    else [2025, 2026].index(CURRENT_YEAR),
                    key="vnd_sch_year"
                )
                month = st.selectbox(
                    "월", list(range(1, 13)),
                    index=CURRENT_MONTH - 1,
                    key="vnd_sch_month"
                )
                weekdays = st.multiselect(
                    "수거 요일",
                    ["월", "화", "수", "목", "금", "토"],
                    key="vnd_sch_days"
                )

        with col2:
            # 담당 거래처 선택 — customer_info에서 vendor 기준 조회
            customer_rows = db_get('customer_info', {'vendor': vendor})
            if not customer_rows:
                customer_rows = []

            # 거래처 구분 필터
            _cust_types_found = sorted(set(
                r.get('cust_type', '학교') for r in customer_rows if r.get('name')
            ))
            if not _cust_types_found:
                _cust_types_found = ['학교']
            _cust_filter = st.selectbox(
                "거래처 구분",
                ["전체"] + _cust_types_found,
                key="vnd_sch_reg_cust_type"
            )
            # 필터 적용
            if _cust_filter == "전체":
                _filtered_rows = [r for r in customer_rows if r.get('name')]
            else:
                _filtered_rows = [
                    r for r in customer_rows
                    if r.get('name') and r.get('cust_type', '학교') == _cust_filter
                ]
            school_list = [r.get('name', '') for r in _filtered_rows]

            if not school_list:
                st.warning(
                    f"'{vendor}' 업체에 등록된 거래처가 없습니다.\n"
                    "거래처 관리에서 먼저 등록하세요."
                )
                sel_schools = []
            else:
                sel_schools = st.multiselect(
                    f"담당 거래처 ({_cust_filter})" if _cust_filter != "전체"
                    else "담당 거래처 (전체)",
                    school_list,
                    key="vnd_sch_schools"
                )

            items = st.multiselect(
                "수거 품목",
                ["음식물", "재활용", "일반"],
                key="vnd_sch_items"
            )

            # 담당 기사 선택 (selectbox — 본사와 동일 패턴)
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
                    f"| 거래처: {len(sel_schools)}개 "
                    f"| 품목: {', '.join(items) if items else '-'} "
                    f"| 기사: {driver or '-'}"
                )
            else:
                st.info(
                    f"📅 {year}년 {month}월 "
                    f"| 요일: {', '.join(weekdays) if weekdays else '-'} "
                    f"| 거래처: {len(sel_schools)}개 "
                    f"| 품목: {', '.join(items) if items else '-'} "
                    f"| 기사: {driver or '-'}"
                )

        # 저장 키 계산
        if vnd_is_daily:
            reg_key = vnd_reg_date.strftime('%Y-%m-%d')
        else:
            reg_key = f"{year}-{str(month).zfill(2)}"

        # 저장 버튼
        save_label = "💾 일별 일정 저장" if vnd_is_daily else "💾 월별 일정 저장"
        if st.button(save_label, type="primary",
                     use_container_width=True, key="vnd_sch_save"):
            if not vnd_is_daily and not weekdays:
                st.error("수거 요일을 선택하세요.")
            elif not sel_schools:
                st.error("수거 거래처를 선택하세요.")
            elif not items:
                st.error("수거 품목을 선택하세요.")
            else:
                # ── 중복 체크: 같은 월 같은 학교 ──────────
                _existing_sched = load_all_schedules(vendor)
                if not isinstance(_existing_sched, dict):
                    _existing_sched = {}
                _existing_info = _existing_sched.get(reg_key)
                _dup_schools = []
                if _existing_info:
                    _existing_schools = _existing_info.get('학교', [])
                    _dup_schools = [s for s in sel_schools if s in _existing_schools]

                _block_save = False
                if _dup_schools:
                    st.warning(f"⚠️ 이미 등록된 거래처: {', '.join(_dup_schools)} — 덮어쓰기 됩니다")
                    _overwrite = st.checkbox(
                        "중복 거래처 포함하여 저장하시겠습니까?",
                        key="vnd_sch_overwrite_confirm"
                    )
                    if not _overwrite:
                        _block_save = True
                        st.info("☑️ 체크박스를 선택하면 저장이 진행됩니다.")

                # ── 저장 실행 ────────────────────────
                if not _block_save:
                    ok = save_schedule_by_vendor(
                        vendor, reg_key, weekdays,
                        sel_schools, items, driver
                    )
                    if ok:
                        _label = vnd_reg_date.strftime('%Y년 %m월 %d일') if vnd_is_daily else f"{year}년 {month}월"
                        st.success(f"✅ {_label} 일정 저장 완료!")
                        st.rerun()
                    else:
                        st.error("저장 실패")
