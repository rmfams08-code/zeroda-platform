# modules/hq_admin/schedule_tab.py
import streamlit as st
import pandas as pd
from datetime import date
from database.db_manager import (db_get, get_all_vendors, load_all_schedules,
                                  save_schedule, delete_schedule)
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_schedule_tab():
    st.markdown("## 수거일정 관리")

    tab1, tab2, tab3 = st.tabs(["📋 일정 조회", "✏️ 일정 등록/수정", "📅 오늘 수거 현황"])

    # ══════════════════════════════════════════════
    # 탭1: 일정 조회 (기존 유지 + 일별 필터 추가)
    # ══════════════════════════════════════════════
    with tab1:
        vendors = get_all_vendors()
        if not vendors:
            st.info("등록된 업체가 없습니다.")
        else:
            # ── 필터 영역 ──────────────────────────────────────────────────
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                vendor = st.selectbox("업체 선택", vendors, key="hq_sch_view_vendor")
            with fc2:
                filter_year = st.selectbox(
                    "연도 필터", ['전체', 2024, 2025, 2026],
                    key="hq_sch_view_year"
                )
            with fc3:
                filter_month = st.selectbox(
                    "월 필터", ['전체'] + list(range(1, 13)),
                    key="hq_sch_view_month"
                )
            with fc4:
                # 일 옵션: 월이 선택된 경우 해당 월 최대 일수 계산
                if filter_year != '전체' and filter_month != '전체':
                    import calendar
                    max_day = calendar.monthrange(int(filter_year), int(filter_month))[1]
                else:
                    max_day = 31
                filter_day = st.selectbox(
                    "일 필터", ['전체'] + list(range(1, max_day + 1)),
                    key="hq_sch_view_day"
                )

            schedules = load_all_schedules(vendor)
            if not isinstance(schedules, dict):
                schedules = {}

            if not schedules:
                st.info(f"{vendor} 의 일정이 없습니다.")
            else:
                # ── 필터 적용 ──────────────────────────────────────────────
                filtered = {}
                for month_key, info in schedules.items():
                    # month_key 형식: "YYYY-MM"
                    parts = str(month_key).split('-')
                    sch_year  = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else None
                    sch_month = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else None

                    if filter_year != '전체' and sch_year != int(filter_year):
                        continue
                    if filter_month != '전체' and sch_month != int(filter_month):
                        continue
                    # 일 필터: 해당 월 일정 내 수거 날짜 목록 검사
                    # (일정은 월 단위 저장이므로, 일 필터 선택 시 해당 일이
                    #  수거 요일 조건에 해당하는지 캘린더 계산으로 확인)
                    if filter_day != '전체' and sch_year and sch_month:
                        import calendar, datetime as _dt
                        target_date = _dt.date(int(sch_year), int(sch_month), int(filter_day))
                        weekday_kr  = ['월','화','수','목','금','토','일'][target_date.weekday()]
                        if weekday_kr not in info.get('요일', []):
                            continue

                    filtered[month_key] = info

                st.markdown(f"**{len(filtered)}건 일정 표시** (전체 {len(schedules)}개월 중)")

                if not filtered:
                    st.info("선택한 조건에 맞는 일정이 없습니다.")
                else:
                    for month, info in sorted(filtered.items()):
                        with st.expander(f"📅 {month} 일정"):
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

    # ══════════════════════════════════════════════
    # 탭2: 일정 등록/수정 (월별 + 일별 모드)
    # ══════════════════════════════════════════════
    with tab2:
        st.markdown("### 수거일정 등록/수정")

        vendors = get_all_vendors()
        if not vendors:
            st.warning("등록된 업체가 없습니다. 외주업체 관리에서 먼저 등록하세요.")
        else:
            # ── 날짜별 수거 미리보기 ────────────────────────────────────────
            with st.expander("📅 날짜별 수거 일정 미리보기", expanded=False):
                pv1, pv2, pv3 = st.columns(3)
                with pv1:
                    pv_vendor = st.selectbox("업체 선택", vendors, key="hq_sch_pv_vendor")
                with pv2:
                    pv_date = st.date_input("조회할 날짜", value=date.today(), key="hq_sch_pv_date")
                with pv3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    pv_search = st.button("🔍 조회", key="hq_sch_pv_btn", use_container_width=True)

                if pv_search or True:
                    pv_ym      = pv_date.strftime('%Y-%m')
                    pv_ymd     = pv_date.strftime('%Y-%m-%d')
                    pv_weekday = ['월','화','수','목','금','토','일'][pv_date.weekday()]
                    pv_sched   = load_all_schedules(pv_vendor)
                    if not isinstance(pv_sched, dict):
                        pv_sched = {}

                    # 일별 일정 우선, 없으면 월별 일정 확인
                    pv_info = pv_sched.get(pv_ymd) or pv_sched.get(pv_ym)
                    pv_mode = '일별' if pv_ymd in pv_sched else ('월별' if pv_ym in pv_sched else None)

                    st.markdown(
                        f"**{pv_date.strftime('%Y년 %m월 %d일')} ({pv_weekday}요일)**  |  "
                        f"업체: `{pv_vendor}`"
                        + (f"  |  적용: `{pv_mode}` 일정" if pv_mode else "")
                    )

                    if not pv_info:
                        st.warning(f"등록된 일정이 없습니다. ({pv_ymd} 또는 {pv_ym})")
                    else:
                        reg_days = pv_info.get('요일', [])
                        # 일별 일정은 요일 무관 적용, 월별은 요일 체크
                        is_collection = (pv_mode == '일별') or (pv_weekday in reg_days)
                        if is_collection:
                            st.success(f"✅ 수거일입니다. ({pv_mode} 일정 적용)")
                            sc1, sc2 = st.columns(2)
                            with sc1:
                                st.write(f"**수거 품목:** {', '.join(pv_info.get('품목', []))}")
                                st.write(f"**담당 기사:** {pv_info.get('기사', '-')}")
                            with sc2:
                                sch_list = pv_info.get('학교', [])
                                st.write(f"**수거 학교 ({len(sch_list)}개):**")
                                for s in sch_list:
                                    st.write(f"  • {s}")
                        else:
                            st.info(
                                f"ℹ️ {pv_weekday}요일은 수거일이 아닙니다. "
                                f"(등록 요일: {', '.join(reg_days) if reg_days else '없음'})"
                            )

            st.divider()

            # ── 등록 모드 선택 ──────────────────────────────────────────────
            reg_mode = st.radio(
                "등록 단위 선택",
                ["📅 월별 등록 (수거 요일 반복)", "📌 일별 등록 (특정 날짜 지정)"],
                horizontal=True,
                key="hq_sch_reg_mode"
            )
            is_daily = reg_mode.startswith("📌")

            st.markdown("---")

            col1, col2 = st.columns(2)
            with col1:
                vendor = st.selectbox("업체 선택", vendors, key="hq_sch_reg_vendor")

                if is_daily:
                    # 일별: 날짜 직접 선택
                    reg_date = st.date_input(
                        "수거 날짜", value=date.today(), key="hq_sch_reg_date"
                    )
                    reg_year  = reg_date.year
                    reg_month = reg_date.month
                    # 일별 모드에서는 요일 표시만 (자동 계산)
                    auto_weekday = ['월','화','수','목','금','토','일'][reg_date.weekday()]
                    st.info(f"선택 날짜: **{reg_date.strftime('%Y년 %m월 %d일')} ({auto_weekday}요일)**")
                    weekdays = [auto_weekday]  # 저장용 (해당 요일 1개)
                    reg_key  = reg_date.strftime('%Y-%m-%d')   # 저장 키: YYYY-MM-DD
                else:
                    # 월별: 연도·월·요일 선택
                    year     = st.selectbox("연도", [2025, 2026],
                                            index=0 if CURRENT_YEAR not in [2025,2026]
                                            else [2025,2026].index(CURRENT_YEAR),
                                            key="hq_sch_reg_year")
                    month    = st.selectbox("월", list(range(1, 13)),
                                            index=CURRENT_MONTH - 1, key="hq_sch_reg_month")
                    weekdays = st.multiselect("수거 요일", ["월","화","수","목","금","토"],
                                              key="hq_sch_reg_days")
                    reg_key  = f"{year}-{str(month).zfill(2)}"  # 저장 키: YYYY-MM
                    reg_year = year
                    reg_month = month

            with col2:
                # 거래처 학교 목록 로딩
                customer_rows = db_get('customer_info', {'vendor': vendor})
                if not customer_rows:
                    vendor_rows = db_get('vendor_info', {'vendor_id': vendor})
                    if not vendor_rows:
                        vendor_rows = db_get('vendor_info', {'name': vendor})
                    if vendor_rows:
                        vid = vendor_rows[0].get('vendor_id', vendor)
                        customer_rows = db_get('customer_info', {'vendor': vid})

                school_list = [r.get('name', '') for r in customer_rows if r.get('name')]

                if not school_list:
                    st.warning(f"'{vendor}' 업체에 등록된 학교가 없습니다.\n거래처 관리에서 먼저 등록하세요.")
                    sel_schools = []
                else:
                    sel_schools = st.multiselect("담당 학교", school_list,
                                                  key="hq_sch_reg_schools")

                items = st.multiselect("수거 품목", ["음식물","재활용","일반"],
                                       key="hq_sch_reg_items")

                # 기사 목록
                driver_rows = [r for r in db_get('users')
                               if r.get('role') == 'driver' and r.get('vendor') == vendor]
                if not driver_rows:
                    driver_rows = [r for r in db_get('users') if r.get('role') == 'driver']
                driver_names = [r.get('name') or r.get('user_id', '') for r in driver_rows]
                driver_names = [d for d in driver_names if d]

                if driver_names:
                    driver = st.selectbox("담당 기사", ["(선택 안 함)"] + driver_names,
                                          key="hq_sch_reg_driver_sel")
                    if driver == "(선택 안 함)":
                        driver = ""
                else:
                    driver = st.text_input("담당 기사 (직접 입력)",
                                           placeholder="등록된 기사가 없습니다",
                                           key="hq_sch_reg_driver_txt")

            # 미리보기
            if (weekdays or sel_schools or items):
                if is_daily:
                    label = f"📌 {reg_date.strftime('%Y년 %m월 %d일')} ({auto_weekday}요일)"
                else:
                    label = f"📅 {reg_year}년 {reg_month}월 | 요일: {', '.join(weekdays) if weekdays else '-'}"
                st.info(
                    f"{label}  |  학교: {len(sel_schools)}개  "
                    f"|  품목: {', '.join(items) if items else '-'}  "
                    f"|  기사: {driver or '-'}"
                )

            col_s, col_d = st.columns(2)
            with col_s:
                save_label = "💾 일별 일정 저장" if is_daily else "💾 월별 일정 저장"
                if st.button(save_label, type="primary",
                             use_container_width=True, key="hq_sch_save"):
                    if not is_daily and not weekdays:
                        st.error("수거 요일을 선택하세요.")
                    elif not sel_schools:
                        st.error("수거 학교를 선택하세요.")
                    elif not items:
                        st.error("수거 품목을 선택하세요.")
                    else:
                        # ── 중복 체크 1: 같은 월 같은 학교 중복 방지 ──────────
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
                            st.warning(f"⚠️ 이미 등록된 학교: {', '.join(_dup_schools)} — 덮어쓰기 됩니다")
                            _overwrite = st.checkbox(
                                "중복 학교 포함하여 저장하시겠습니까?",
                                key="hq_sch_overwrite_confirm"
                            )
                            if not _overwrite:
                                _block_save = True
                                st.info("☑️ 체크박스를 선택하면 저장이 진행됩니다.")

                        # ── 중복 체크 2: 타 업체 같은 요일+학교 중복 안내 ─────
                        if not _block_save:
                            _all_vendors = get_all_vendors()
                            _cross_dup_msgs = []
                            for _ov in _all_vendors:
                                if _ov == vendor:
                                    continue
                                _ov_scheds = load_all_schedules(_ov)
                                if not isinstance(_ov_scheds, dict):
                                    continue
                                # 같은 reg_key(월/일) 또는 월별↔일별 교차 비교
                                _check_keys = [reg_key]
                                # 일별이면 해당 월도 확인, 월별이면 해당 월의 일별도 확인
                                if is_daily:
                                    _check_keys.append(reg_key[:7])  # YYYY-MM
                                else:
                                    _check_keys.extend(
                                        [k for k in _ov_scheds if k.startswith(reg_key)]
                                    )
                                for _ck in _check_keys:
                                    _ov_info = _ov_scheds.get(_ck)
                                    if not _ov_info:
                                        continue
                                    _ov_days = set(_ov_info.get('요일', []))
                                    _ov_schs = set(_ov_info.get('학교', []))
                                    _common_days = _ov_days & set(weekdays)
                                    _common_schs = _ov_schs & set(sel_schools)
                                    if _common_days and _common_schs:
                                        for _cs in sorted(_common_schs):
                                            _cross_dup_msgs.append(
                                                f"{_cs} ({', '.join(sorted(_common_days))}요일) → 업체: {_ov}"
                                            )
                            if _cross_dup_msgs:
                                _unique_msgs = sorted(set(_cross_dup_msgs))
                                st.info(
                                    "ℹ️ 아래 학교는 같은 요일에 다른 업체에도 등록되어 있습니다:\n"
                                    + "\n".join(f"  • {m}" for m in _unique_msgs)
                                )

                        # ── 저장 실행 (기존 로직 유지) ────────────────────────
                        if not _block_save:
                            ok = save_schedule(vendor, reg_key, weekdays,
                                               sel_schools, items, driver)
                            if ok:
                                if is_daily:
                                    st.success(f"✅ {reg_date.strftime('%Y년 %m월 %d일')} 일별 일정 저장 완료!")
                                else:
                                    st.success(f"✅ {reg_year}년 {reg_month}월 일정 저장 완료!")
                                st.rerun()
                            else:
                                st.error("저장 실패")

            with col_d:
                schedules = load_all_schedules(vendor)
                if not isinstance(schedules, dict):
                    schedules = {}
                if schedules:
                    # 월별/일별 구분 표시
                    def _fmt_key(k):
                        return f"📌 {k} (일별)" if len(k) == 10 else f"📅 {k} (월별)"
                    del_opts = {_fmt_key(k): k for k in sorted(schedules.keys(), reverse=True)}
                    del_label = st.selectbox("삭제할 일정 선택",
                                              list(del_opts.keys()),
                                              key="hq_sch_del_month")
                    if st.button("🗑️ 삭제", use_container_width=True,
                                 key="hq_sch_del"):
                        delete_schedule(vendor, del_opts[del_label])
                        st.success(f"{del_label} 삭제 완료")
                        st.rerun()

    # ══════════════════════════════════════════════
    # 탭3: 오늘 수거 현황
    # ══════════════════════════════════════════════
    with tab3:
        today_str = str(date.today())
        today_rows = [r for r in db_get('real_collection')
                      if str(r.get('collect_date', '')) == today_str]

        if not today_rows:
            st.info("오늘 수거 데이터가 없습니다.")
        else:
            df = pd.DataFrame(today_rows)
            if 'status' in df.columns:
                df['status'] = df['status'].map({
                    'draft':     '📋 임시저장',
                    'submitted': '📤 전송완료',
                    'confirmed': '✅ 확인완료',
                    'rejected':  '❌ 반려',
                }).fillna(df['status'])
            show = [c for c in ['school_name','vendor','item_type',
                                'weight','driver','status'] if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")
            with c2:
                st.metric("수거 건수", f"{len(df)}건")
