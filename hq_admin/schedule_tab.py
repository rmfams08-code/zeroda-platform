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
    # 탭1: 일정 조회 (기존 유지)
    # ══════════════════════════════════════════════
    with tab1:
        vendors = get_all_vendors()
        if not vendors:
            st.info("등록된 업체가 없습니다.")
        else:
            vendor = st.selectbox("업체 선택", vendors, key="hq_sch_view_vendor")
            schedules = load_all_schedules(vendor)
            if not isinstance(schedules, dict):
                schedules = {}

            if not schedules:
                st.info(f"{vendor} 의 일정이 없습니다.")
            else:
                st.markdown(f"**총 {len(schedules)}개월 일정 등록됨**")
                for month, info in sorted(schedules.items()):
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
    # 탭2: 일정 등록/수정 (신규)
    # ══════════════════════════════════════════════
    with tab2:
        st.markdown("### 수거일정 등록/수정")

        vendors = get_all_vendors()
        if not vendors:
            st.warning("등록된 업체가 없습니다. 외주업체 관리에서 먼저 등록하세요.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                vendor = st.selectbox("업체 선택", vendors, key="hq_sch_reg_vendor")
                year   = st.selectbox("연도", [2025, 2026],
                                      index=0 if CURRENT_YEAR not in [2025,2026] else [2025,2026].index(CURRENT_YEAR),
                                      key="hq_sch_reg_year")
                month  = st.selectbox("월", list(range(1, 13)),
                                      index=CURRENT_MONTH - 1, key="hq_sch_reg_month")
                weekdays = st.multiselect("수거 요일", ["월","화","수","목","금","토"],
                                          key="hq_sch_reg_days")
            with col2:
                # customer_info에서 해당 업체 학교 목록 로딩
                customer_rows = db_get('customer_info', {'vendor': vendor})
                if not customer_rows:
                    # vendor_id로도 시도
                    vendor_rows = db_get('vendor_info', {'vendor_id': vendor})
                    if not vendor_rows:
                        vendor_rows = db_get('vendor_info', {'name': vendor})
                    if vendor_rows:
                        vid = vendor_rows[0].get('vendor_id', vendor)
                        customer_rows = db_get('customer_info', {'vendor': vid})

                school_list = [r.get('name', '') for r in customer_rows if r.get('name')]

                if not school_list:
                    st.warning(f"'{vendor}' 업체에 등록된 학교가 없습니다.\n거래처 관리에서 학교를 먼저 등록하세요.")
                    sel_schools = []
                else:
                    sel_schools = st.multiselect("담당 학교", school_list,
                                                  key="hq_sch_reg_schools")

                items  = st.multiselect("수거 품목", ["음식물","재활용","일반"],
                                        key="hq_sch_reg_items")

                # 기사 목록: users 테이블에서 role=driver 조회
                driver_rows = [r for r in db_get('users')
                               if r.get('role') == 'driver'
                               and r.get('vendor') == vendor]
                if not driver_rows:
                    # 업체 필터 없이 전체 기사 목록
                    driver_rows = [r for r in db_get('users')
                                   if r.get('role') == 'driver']
                driver_names = [r.get('name') or r.get('user_id', '') for r in driver_rows]
                driver_names = [d for d in driver_names if d]

                if driver_names:
                    driver = st.selectbox("담당 기사", ["(선택 안 함)"] + driver_names,
                                          key="hq_sch_reg_driver")
                    if driver == "(선택 안 함)":
                        driver = ""
                else:
                    driver = st.text_input("담당 기사 (직접 입력)",
                                           placeholder="등록된 기사가 없습니다",
                                           key="hq_sch_reg_driver")

            # 미리보기
            if weekdays or sel_schools or items:
                st.info(f"📌 {year}년 {month}월 | 요일: {', '.join(weekdays) if weekdays else '-'} "
                        f"| 학교: {len(sel_schools)}개 | 품목: {', '.join(items) if items else '-'} "
                        f"| 기사: {driver or '-'}")

            col_s, col_d = st.columns(2)
            with col_s:
                if st.button("💾 일정 저장", type="primary",
                             use_container_width=True, key="hq_sch_save"):
                    if not weekdays:
                        st.error("수거 요일을 선택하세요.")
                    elif not sel_schools:
                        st.error("수거 학교를 선택하세요.")
                    elif not items:
                        st.error("수거 품목을 선택하세요.")
                    else:
                        month_str = f"{year}-{str(month).zfill(2)}"
                        ok = save_schedule(vendor, month_str, weekdays,
                                           sel_schools, items, driver)
                        if ok:
                            st.success(f"✅ {year}년 {month}월 일정 저장 완료!")
                            st.rerun()
                        else:
                            st.error("저장 실패")

            with col_d:
                # 기존 일정 삭제
                schedules = load_all_schedules(vendor)
                if not isinstance(schedules, dict):
                    schedules = {}
                if schedules:
                    del_month = st.selectbox("삭제할 월 선택",
                                              list(schedules.keys()),
                                              key="hq_sch_del_month")
                    if st.button("🗑️ 삭제", use_container_width=True,
                                 key="hq_sch_del"):
                        delete_schedule(vendor, del_month)
                        st.success(f"{del_month} 일정 삭제 완료")
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
                    'submitted': '✅ 전송완료',
                    'confirmed': '✔️ 확인완료',
                }).fillna(df['status'])
            show = [c for c in ['school_name','vendor','item_type',
                                'weight','driver','status'] if c in df.columns]
            st.dataframe(df[show], use_container_width=True, hide_index=True)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")
            with c2:
                st.metric("수거 건수", f"{len(df)}건")
