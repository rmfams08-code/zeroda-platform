# modules/vendor_admin/schedule_tab.py
import streamlit as st
import calendar
import pandas as pd
from database.db_manager import (
    get_schools_by_vendor, save_schedule, load_all_schedules,
    delete_schedule, db_get, save_schedule_by_vendor,
    load_customers_from_db, save_meal_schedule_bulk, get_meal_schedules,
    approve_meal_schedules
)
from config.settings import CURRENT_YEAR, CURRENT_MONTH
from zoneinfo import ZoneInfo
from datetime import datetime, date, timedelta


def render_schedule_tab(vendor):
    st.markdown("## 수거일정 관리")

    tab1, tab2, tab3, tab4 = st.tabs(["📅 일정 조회/삭제", "✏️ 일정 등록/수정", "🍽️ NEIS 급식일정 연동", "✅ 식단기반 일정 승인"])

    # ══════════════════════════════════════════════
    # 탭1: 일정 조회/삭제
    # ══════════════════════════════════════════════
    with tab1:
        schedules = load_all_schedules(vendor)
        if not isinstance(schedules, dict):
            schedules = {}

        # ── 오늘 수거 완료 데이터 조회 (완료 표시용) ─────────────
        _today_str = str(date.today())
        _today_weekday = ['월','화','수','목','금','토','일'][date.today().weekday()]
        _today_collections = db_get('real_collection')
        if not isinstance(_today_collections, list):
            _today_collections = []
        _done_set = set()
        for _tc in _today_collections:
            if (str(_tc.get('collect_date', '')) == _today_str
                    and _tc.get('vendor', '') == vendor):
                _sn = _tc.get('school_name', '') or _tc.get('학교명', '')
                if _sn:
                    _done_set.add(_sn)

        if not schedules:
            st.info("등록된 일정이 없습니다. '일정 등록/수정' 탭에서 추가하세요.")
        else:
            # ── 요일 필터 ────────────────────────────────────────
            _all_days = ["월", "화", "수", "목", "금", "토"]
            _day_cols = st.columns(len(_all_days))
            _sel_days = []
            for _di, _dc in enumerate(_all_days):
                with _day_cols[_di]:
                    if st.checkbox(_dc, value=True, key=f"vnd_sch_vday_{_dc}"):
                        _sel_days.append(_dc)

            # ── 전체 entry flat list 펼침 ────────────────────────
            all_entries = []
            for month_key, entry_list in schedules.items():
                if not isinstance(entry_list, list):
                    entry_list = [entry_list]
                for entry in entry_list:
                    entry_days = entry.get('요일', [])
                    if _sel_days and entry_days:
                        if not set(entry_days) & set(_sel_days):
                            continue
                    all_entries.append({**entry, '_month': month_key})

            if not all_entries:
                st.info("선택한 조건에 맞는 일정이 없습니다.")
            else:
                # ── 품목별 하위 탭 ────────────────────────────────
                _item_set = set()
                for _e in all_entries:
                    for _it in _e.get('품목', []):
                        _item_set.add(_it)
                _item_tabs = ["전체"] + sorted(_item_set)
                _sub_tabs = st.tabs(
                    [f"📦 {_it}" if _it != "전체" else "📋 전체" for _it in _item_tabs]
                )

                for _ti, _tab_name in enumerate(_item_tabs):
                    with _sub_tabs[_ti]:
                        if _tab_name == "전체":
                            _show = all_entries
                        else:
                            _show = [
                                e for e in all_entries
                                if _tab_name in e.get('품목', [])
                            ]
                        st.markdown(f"**{len(_show)}건 일정**")
                        for _ei, _entry in enumerate(_show):
                            _mk = _entry.get('_month', '')
                            _label = f"📌 {_mk} (일별)" if len(_mk) == 10 else f"📅 {_mk} (월별)"
                            _items_str = ', '.join(_entry.get('품목', []))
                            with st.expander(
                                f"{_label} | {_items_str} | "
                                f"{', '.join(_entry.get('요일', []))}요일"
                            ):
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.write(f"**수거 요일:** {', '.join(_entry.get('요일', []))}")
                                    st.write(f"**수거 품목:** {_items_str}")
                                    st.write(f"**담당 기사:** {_entry.get('기사', '-')}")
                                with c2:
                                    schools_list = _entry.get('학교', [])
                                    _entry_days = _entry.get('요일', [])
                                    _is_today_schedule = _today_weekday in _entry_days
                                    if _is_today_schedule:
                                        _done_cnt = sum(1 for s in schools_list if s in _done_set)
                                        _total = len(schools_list)
                                        st.write(
                                            f"**담당 거래처 ({_total}개)** — "
                                            f"오늘: ✅ {_done_cnt}완료 / ⬜ {_total - _done_cnt}미수거"
                                        )
                                        for s in schools_list:
                                            _mark = "✅" if s in _done_set else "⬜"
                                            st.write(f"  {_mark} {s}")
                                    else:
                                        st.write(f"**담당 거래처 ({len(schools_list)}개):**")
                                        for s in schools_list:
                                            st.write(f"  • {s}")

                                # 본사 등록 일정은 삭제 불가 안내
                                _reg_by = _entry.get('registered_by', 'admin')
                                if _reg_by == 'vendor':
                                    if st.button("🗑 삭제", key=f"vnd_del_{_mk}_{_ti}_{_ei}", type="secondary"):
                                        delete_schedule(vendor, _mk)
                                        st.success(f"{_mk} 일정 삭제 완료")
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
                # ── 중복 체크: 같은 월+요일에 이미 등록된 거래처 안내 ─
                _existing_sched = load_all_schedules(vendor)
                if not isinstance(_existing_sched, dict):
                    _existing_sched = {}
                _existing_entries = _existing_sched.get(reg_key, [])
                if not isinstance(_existing_entries, list):
                    _existing_entries = [_existing_entries]
                _dup_schools = []
                _weekdays_key = sorted(weekdays)
                for _ex_entry in _existing_entries:
                    if sorted(_ex_entry.get('요일', [])) != _weekdays_key:
                        continue
                    _existing_schools = _ex_entry.get('학교', [])
                    _dup_schools.extend(
                        s for s in sel_schools
                        if s in _existing_schools and s not in _dup_schools
                    )
                _new_schools = [s for s in sel_schools if s not in _dup_schools]

                _block_save = False
                if _dup_schools:
                    st.info(
                        f"ℹ️ 이미 등록된 거래처: {', '.join(_dup_schools)} (중복 건너뜀)\n\n"
                        f"새로 추가될 거래처: {', '.join(_new_schools) if _new_schools else '없음'}"
                    )
                    if not _new_schools:
                        st.warning("⚠️ 모든 거래처가 이미 등록되어 있습니다.")
                        _block_save = True

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

    # ══════════════════════════════════════════════
    # 탭3: NEIS 급식일정 API 연동
    # ══════════════════════════════════════════════
    with tab3:
        st.markdown("### 🍽️ NEIS 급식일정 → 수거일정 자동 생성")
        st.caption("나이스(NEIS) Open API에서 학교 급식일을 조회하고, 급식일 기준 수거일정을 자동 생성합니다.")

        from services.neis_api import fetch_meal_dates, EDU_OFFICE_CODES

        # ── 조회 월 선택 ──
        now = datetime.now(ZoneInfo('Asia/Seoul'))
        neis_months = []
        for delta in range(-1, 3):
            m = now.month + delta
            y = now.year
            if m < 1:
                m += 12; y -= 1
            elif m > 12:
                m -= 12; y += 1
            neis_months.append(f"{y}-{m:02d}")
        neis_month = st.selectbox("조회 월", neis_months, index=1, key="vnd_neis_month")

        # ── NEIS 코드가 등록된 학교 목록 ──
        all_custs = load_customers_from_db(vendor)
        neis_schools = {
            name: info for name, info in all_custs.items()
            if info.get('neis_edu_code') and info.get('neis_school_code')
            and info.get('구분') == '학교'
        }

        if not neis_schools:
            st.warning(
                "NEIS 학교코드가 등록된 거래처가 없습니다.\n\n"
                "거래처 관리 → 학교 수정 → 'NEIS 학교코드' 항목에서 "
                "시도교육청코드와 학교표준코드를 먼저 입력하세요.\n\n"
                "예) 경기도: J10, 서울: B10 / 학교표준코드는 나이스 포털에서 확인"
            )
        else:
            neis_school_names = sorted(neis_schools.keys())
            sel_school = st.selectbox(
                f"학교 선택 (NEIS 코드 등록 {len(neis_school_names)}개)",
                neis_school_names, key="vnd_neis_school_sel"
            )

            sel_info = neis_schools[sel_school]
            edu_code = sel_info['neis_edu_code']
            sch_code = sel_info['neis_school_code']
            edu_name = EDU_OFFICE_CODES.get(edu_code, edu_code)

            st.info(f"🏫 {sel_school} · {edu_name} ({edu_code}) · 학교코드: {sch_code}")

            # ── API 조회 버튼 ──
            if st.button("🔍 NEIS 급식일 조회", type="primary",
                         use_container_width=True, key="vnd_neis_fetch"):
                year = int(neis_month[:4])
                month = int(neis_month[5:7])

                with st.spinner(f"{sel_school} {neis_month} 급식일 조회 중..."):
                    result = fetch_meal_dates(edu_code, sch_code, year, month)

                if result['success']:
                    st.success(result['message'])
                    st.session_state['vnd_neis_result'] = result
                    st.session_state['vnd_neis_school'] = sel_school
                    st.session_state['vnd_neis_month'] = neis_month
                else:
                    st.error(result['message'])

            # ── 조회 결과 표시 + 수거일정 생성 ──
            if 'vnd_neis_result' in st.session_state:
                result = st.session_state['vnd_neis_result']
                meal_dates = result.get('meal_dates', [])
                _stored_school = st.session_state.get('vnd_neis_school', '')
                _stored_month = st.session_state.get('vnd_neis_month', '')

                if meal_dates and _stored_school == sel_school and _stored_month == neis_month:
                    st.divider()
                    st.markdown(f"### 📅 {_stored_school} — {_stored_month} 급식일 ({len(meal_dates)}일)")

                    # 캘린더 뷰
                    _year = int(neis_month[:4])
                    _month = int(neis_month[5:7])
                    _cal = calendar.Calendar(firstweekday=0)
                    _weeks = _cal.monthdayscalendar(_year, _month)
                    _meal_day_set = set()
                    for d in meal_dates:
                        try:
                            _meal_day_set.add(int(d.split('-')[2]))
                        except (IndexError, ValueError):
                            pass

                    header = "| 월 | 화 | 수 | 목 | 금 | 토 | 일 |\n|:--:|:--:|:--:|:--:|:--:|:--:|:--:|"
                    rows_md = []
                    for week in _weeks:
                        cells = []
                        for day in week:
                            if day == 0:
                                cells.append("")
                            elif day in _meal_day_set:
                                cells.append(f"**🍽️{day}**")
                            else:
                                cells.append(f"{day}")
                        rows_md.append("| " + " | ".join(cells) + " |")
                    st.markdown(header + "\n" + "\n".join(rows_md))
                    st.caption("🍽️ = 급식일 (수거일정 생성 대상)")

                    # 메뉴 상세 (접기)
                    meal_details = result.get('meal_details', {})
                    if meal_details:
                        with st.expander("📋 급식 메뉴 상세", expanded=False):
                            for md_date in meal_dates:
                                detail = meal_details.get(md_date, {})
                                menu = detail.get('menu', '-')
                                cal_info = detail.get('cal', '')
                                st.caption(f"**{md_date}** {cal_info}")
                                st.text(menu)

                    # ── 수거일정 생성 옵션 ──
                    st.divider()
                    st.markdown("### 수거일정 생성")
                    oc1, oc2, oc3 = st.columns(3)
                    with oc1:
                        neis_offset = st.radio(
                            "수거 시점", [0, 1],
                            format_func=lambda x: "급식 당일" if x == 0 else "급식 다음날",
                            key="vnd_neis_offset", horizontal=True
                        )
                    with oc2:
                        neis_item = st.selectbox("수거 품목", ["음식물", "음식물+재활용"],
                                                  key="vnd_neis_item")
                    with oc3:
                        # 기사 배정
                        v_driver_rows = [r for r in db_get('users')
                                         if r.get('role') == 'driver'
                                         and r.get('vendor') == vendor]
                        v_driver_names = [r.get('name') or r.get('user_id', '')
                                          for r in v_driver_rows
                                          if r.get('name') or r.get('user_id')]
                        neis_driver = ''
                        if v_driver_names:
                            neis_driver = st.selectbox(
                                "기사 배정", ["(미지정)"] + v_driver_names,
                                key="vnd_neis_driver"
                            )
                            if neis_driver == "(미지정)":
                                neis_driver = ''

                    # 기존 수거일정 확인
                    existing_ms = get_meal_schedules(
                        school_name=sel_school, year_month=neis_month
                    )
                    existing_count = len(existing_ms)
                    if existing_count > 0:
                        st.info(f"ℹ️ 이미 등록된 식단 수거일정 {existing_count}건 (재생성 시 기존 대기건 교체)")

                    btn_label = f"🗓️ 수거일정 생성 ({len(meal_dates)}일)"
                    if st.button(btn_label, type="primary",
                                 use_container_width=True, key="vnd_neis_create"):
                        with st.spinner("수거일정 생성 중..."):
                            items_list = ['음식물']
                            if neis_item == '음식물+재활용':
                                items_list = ['음식물', '재활용']

                            total_ok = 0
                            total_fail = 0

                            for it in items_list:
                                # meal_schedules에 이력 저장
                                s, f = save_meal_schedule_bulk(
                                    school_name=sel_school,
                                    vendor=vendor,
                                    meal_dates=meal_dates,
                                    uploaded_by='neis_api',
                                    item_type=it,
                                    collect_offset=neis_offset,
                                )
                                total_ok += s
                                total_fail += f

                                # schedules 테이블에 바로 반영
                                _wd_names = ['월','화','수','목','금','토','일']
                                for md in meal_dates:
                                    try:
                                        _dt = datetime.strptime(md, '%Y-%m-%d')
                                        _collect_dt = _dt + timedelta(days=neis_offset)
                                        _cd = _collect_dt.strftime('%Y-%m-%d')
                                        _wd = _wd_names[_collect_dt.weekday()]

                                        save_schedule(
                                            vendor, _cd,
                                            [_wd], [sel_school], [it],
                                            neis_driver
                                        )
                                    except Exception as e:
                                        print(f"[vnd_neis_schedule] {md}: {e}")

                        if total_fail == 0:
                            st.success(
                                f"✅ 수거일정 {total_ok}건 생성 완료! "
                                f"기사 일정에 바로 반영되었습니다."
                            )
                            del st.session_state['vnd_neis_result']
                            st.rerun()
                        else:
                            st.warning(f"생성: 성공 {total_ok}건, 실패 {total_fail}건")

    # ══════════════════════════════════════════════
    # 탭4: 식단기반 수거일정 승인
    # ══════════════════════════════════════════════
    with tab4:
        st.markdown("### ✅ 식단기반 수거일정 승인")
        st.caption("급식담당자(영양사)가 식단 업로드 시 자동 생성된 수거일정 초안을 승인합니다.")

        # ── 조회 월 ──
        now_apv = datetime.now(ZoneInfo('Asia/Seoul'))
        apv_months = []
        for delta in range(-1, 3):
            m = now_apv.month + delta
            y = now_apv.year
            if m < 1:
                m += 12; y -= 1
            elif m > 12:
                m -= 12; y += 1
            apv_months.append(f"{y}-{m:02d}")
        apv_month = st.selectbox("조회 월", apv_months, index=1, key="vnd_apv_month")

        # ── draft 목록 조회 ──
        draft_rows = get_meal_schedules(
            vendor=vendor, status='draft', year_month=apv_month
        )
        approved_rows = get_meal_schedules(
            vendor=vendor, status='approved', year_month=apv_month
        )

        # 상태 요약
        mc1, mc2 = st.columns(2)
        with mc1:
            st.metric("⏳ 승인 대기", f"{len(draft_rows)}건")
        with mc2:
            st.metric("✅ 승인 완료", f"{len(approved_rows)}건")

        if not draft_rows:
            st.info("승인 대기 중인 식단기반 수거일정이 없습니다.")
        else:
            # ── 학교별 그룹핑 ──
            school_groups = {}
            for r in draft_rows:
                sn = r.get('school_name', '알수없음')
                if sn not in school_groups:
                    school_groups[sn] = []
                school_groups[sn].append(r)

            for school_name, rows in sorted(school_groups.items()):
                with st.expander(
                    f"🏫 {school_name} — {len(rows)}건 대기 "
                    f"(업로드: {rows[0].get('uploaded_by', '-')})",
                    expanded=True
                ):
                    display_data = []
                    for r in rows:
                        display_data.append({
                            '급식일': r.get('meal_date', ''),
                            '수거예정일': r.get('collect_date', ''),
                            '품목': r.get('item_type', ''),
                            '업로더': r.get('uploaded_by', ''),
                            '생성일': str(r.get('created_at', ''))[:10],
                        })
                    st.dataframe(
                        pd.DataFrame(display_data),
                        use_container_width=True, hide_index=True
                    )

                    oc1, oc2 = st.columns(2)
                    with oc1:
                        apv_offset = st.radio(
                            "수거 시점 조정",
                            [("유지", -1), ("급식 당일", 0), ("급식 다음날", 1)],
                            format_func=lambda x: x[0],
                            key=f"vnd_apv_offset_{school_name}",
                            horizontal=True,
                        )
                    with oc2:
                        _apv_driver_rows = [
                            r for r in db_get('users')
                            if r.get('role') == 'driver'
                            and r.get('vendor') == vendor
                        ]
                        _apv_driver_names = [
                            r.get('name') or r.get('user_id', '')
                            for r in _apv_driver_rows
                            if r.get('name') or r.get('user_id')
                        ]
                        apv_driver = ''
                        if _apv_driver_names:
                            apv_driver = st.selectbox(
                                "기사 배정",
                                ["(미지정)"] + _apv_driver_names,
                                key=f"vnd_apv_driver_{school_name}"
                            )
                            if apv_driver == "(미지정)":
                                apv_driver = ''

                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button(
                            f"✅ 전체 승인 ({len(rows)}건)",
                            type="primary", use_container_width=True,
                            key=f"vnd_apv_approve_{school_name}"
                        ):
                            from database.db_manager import db_upsert
                            _ids = []
                            for r in rows:
                                rid = r.get('id')
                                if apv_offset[1] >= 0:
                                    try:
                                        _meal_dt = datetime.strptime(
                                            r['meal_date'], '%Y-%m-%d'
                                        )
                                        _new_cd = (
                                            _meal_dt + timedelta(days=apv_offset[1])
                                        ).strftime('%Y-%m-%d')
                                        r['collect_date'] = _new_cd
                                        _upd = dict(r)
                                        _upd['collect_date'] = _new_cd
                                        db_upsert('meal_schedules', _upd)
                                    except Exception:
                                        pass
                                _ids.append(rid)

                            cnt = approve_meal_schedules(
                                _ids, approved_by='vendor_admin',
                                driver=apv_driver
                            )
                            st.success(
                                f"✅ {school_name} {cnt}건 승인 완료! "
                                f"기사 일정에 반영되었습니다."
                            )
                            st.rerun()

                    with bc2:
                        if st.button(
                            f"❌ 반려",
                            use_container_width=True,
                            key=f"vnd_apv_reject_{school_name}"
                        ):
                            from database.db_manager import cancel_meal_schedules
                            _ids = [r.get('id') for r in rows]
                            cancel_meal_schedules(_ids, note='업체관리자 반려')
                            st.warning(f"{school_name} {len(rows)}건 반려 완료")
                            st.rerun()
