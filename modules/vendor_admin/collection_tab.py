# modules/vendor_admin/collection_tab.py
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.db_manager import db_get, db_upsert, get_schools_by_vendor
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_collection_tab(vendor):
    st.markdown("## 수거 데이터")

    tab1, tab2, tab3 = st.tabs(["📋 수거 내역", "✏️ 수거 입력", "⚖️ 처리확인"])

    with tab1:
        from zoneinfo import ZoneInfo
        from services.collection_view import render_collection_table, render_collection_edit

        # 새로고침 버튼 - 캐시 무효화
        col_r, _ = st.columns([1, 4])
        with col_r:
            if st.button("🔄 새로고침", key="va_refresh"):
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
                st.rerun()

        # ── 필터: 월별 + 학교/거래처 ──────────────
        _fc1, _fc2 = st.columns(2)
        with _fc1:
            now_kst = datetime.now(ZoneInfo('Asia/Seoul'))
            month_options = []
            for i in range(12):
                y = now_kst.year
                m = now_kst.month - i
                while m <= 0:
                    m += 12
                    y -= 1
                month_options.append(f"{y}-{str(m).zfill(2)}")
            month_options = ["전체"] + month_options
            sel_month = st.selectbox(
                "월별",
                month_options,
                key="vnd_col_month"
            )
        with _fc2:
            customer_rows = db_get('customer_info', {'vendor': vendor})
            if not customer_rows:
                customer_rows = []
            school_options = ["전체"] + [
                r.get('name', '') for r in customer_rows
                if r.get('name')
            ]
            sel_school = st.selectbox(
                "학교/거래처",
                school_options,
                key="vnd_col_school"
            )

        rows = [r for r in db_get('real_collection') if r.get('vendor') == vendor]

        # 월별 필터 적용
        if sel_month != "전체":
            rows = [r for r in rows
                    if str(r.get('collect_date', '')).startswith(sel_month)]
        # 학교 필터 적용
        if sel_school != "전체":
            rows = [r for r in rows
                    if str(r.get('school_name', '')) == sel_school]

        # 공통 테이블 렌더 + 수정 UI
        render_collection_table(rows, key_prefix="vnd_col")
        render_collection_edit(rows, key_prefix="vnd_col")

    with tab2:
        st.markdown("### 수거 입력")
        schools = get_schools_by_vendor(vendor)
        col1, col2 = st.columns(2)
        with col1:
            school       = st.selectbox("학교", schools if schools else ['학교 없음'])
            collect_date = st.date_input("수거일", value=date.today())
            item_type    = st.selectbox("품목", ["음식물", "재활용", "일반"])
        with col2:
            weight = st.number_input("수거량 (kg)", min_value=0.0, step=0.1)
            driver = st.text_input("기사명")
            memo   = st.text_input("메모")

        if st.button("저장", type="primary"):
            if not school or school == '학교 없음':
                st.error("학교를 선택하세요.")
            else:
                ok = db_upsert('real_collection', {
                    'vendor':       vendor,
                    'school_name':  school,
                    'collect_date': str(collect_date),
                    'item_type':    item_type,
                    'weight':       weight,
                    'driver':       driver,
                    'memo':         memo,
                    'status':       'confirmed',
                    'created_at':   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
                if ok:
                    st.success("저장 완료!")
                    from services.github_storage import _github_get_cached
                    _github_get_cached.clear()
                else:
                    st.error("저장 실패")

    with tab3:
        _render_vendor_processing(vendor)


def _render_vendor_processing(vendor):
    """외주업체관리자 처리확인 탭 (자사 기사 데이터만)"""
    st.markdown("### ⚖️ 처리확인 (계근표)")
    st.caption("소속 기사가 전송한 처리확인 데이터입니다.")

    all_proc = [r for r in db_get('processing_confirm')
                if r.get('vendor') == vendor]

    if not all_proc:
        st.info("아직 처리확인 데이터가 없습니다.")
        return

    # 필터
    fc1, fc2 = st.columns(2)
    with fc1:
        drivers = sorted(set(r.get('driver', '') for r in all_proc if r.get('driver')))
        sel_driver = st.selectbox("기사", ['전체'] + drivers, key="va_proc_driver")
    with fc2:
        status_filter = st.selectbox("상태", ['전체', 'submitted', 'confirmed', 'rejected'],
                                     format_func=lambda x: {'전체': '전체', 'submitted': '📤 대기',
                                         'confirmed': '✅ 확인', 'rejected': '❌ 반려'}.get(x, x),
                                     key="va_proc_status")

    filtered = all_proc
    if sel_driver != '전체':
        filtered = [r for r in filtered if r.get('driver') == sel_driver]
    if status_filter != '전체':
        filtered = [r for r in filtered if r.get('status') == status_filter]

    if not filtered:
        st.warning("조건에 맞는 데이터가 없습니다.")
        return

    # 요약
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        pending_cnt = len([r for r in filtered if r.get('status') == 'submitted'])
        st.metric("📤 대기", f"{pending_cnt}건")
    with mc2:
        confirmed_cnt = len([r for r in filtered if r.get('status') == 'confirmed'])
        st.metric("✅ 확인", f"{confirmed_cnt}건")
    with mc3:
        total_w = sum(float(r.get('total_weight', 0)) for r in filtered)
        st.metric("총 처리량", f"{total_w:,.1f} kg")

    # 수거량 vs 처리량 비교 (오늘)
    _today_str = datetime.now().strftime('%Y-%m-%d')
    today_coll = [r for r in db_get('real_collection')
                  if r.get('vendor') == vendor
                  and str(r.get('collect_date', '')) == _today_str]
    coll_weight = sum(float(r.get('weight', 0)) for r in today_coll)
    proc_weight = sum(float(r.get('total_weight', 0)) for r in filtered
                      if r.get('confirm_date') == _today_str)
    if coll_weight > 0 or proc_weight > 0:
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.metric("오늘 수거량", f"{coll_weight:,.1f} kg")
        with cc2:
            st.metric("오늘 처리량", f"{proc_weight:,.1f} kg")
        with cc3:
            diff = proc_weight - coll_weight
            st.metric("차이", f"{diff:+,.1f} kg")

    st.divider()

    # 데이터 테이블
    df = pd.DataFrame(filtered)
    display_cols = ['confirm_date', 'confirm_time', 'driver',
                    'total_weight', 'location_name', 'latitude', 'longitude',
                    'photo_attached', 'status', 'memo']
    display_cols = [c for c in display_cols if c in df.columns]
    df_show = df[display_cols].copy()

    col_rename = {
        'confirm_date': '처리일자', 'confirm_time': '시각', 'driver': '기사',
        'total_weight': '처리량(kg)', 'location_name': '처리장',
        'latitude': '위도', 'longitude': '경도',
        'photo_attached': '사진', 'status': '상태', 'memo': '메모',
    }
    df_show = df_show.rename(columns=col_rename)

    if '사진' in df_show.columns:
        df_show['사진'] = df_show['사진'].map(lambda x: '📷' if int(x or 0) else '-')
    if '상태' in df_show.columns:
        df_show['상태'] = df_show['상태'].map({
            'submitted': '📤 대기', 'confirmed': '✅ 확인', 'rejected': '❌ 반려'
        }).fillna(df_show['상태'])

    st.dataframe(df_show, use_container_width=True, hide_index=True)

    # 개별 확인/반려 (대기 건만)
    pending_rows = [r for r in filtered if r.get('status') == 'submitted']
    if pending_rows:
        st.markdown("#### 미확인 건 처리")
        for pr in pending_rows:
            _pid = pr.get('id', '')
            _info = (f"📅 {pr.get('confirm_date','')} {pr.get('confirm_time','')[:5]} | "
                     f"🚛 {pr.get('driver','')} | "
                     f"⚖️ {float(pr.get('total_weight',0)):.1f}kg | "
                     f"📍 {pr.get('location_name','')}")
            if pr.get('latitude') and float(pr.get('latitude', 0)) != 0:
                _info += f" ({float(pr['latitude']):.4f}, {float(pr['longitude']):.4f})"

            with st.expander(_info):
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("✅ 확인", key=f"va_proc_ok_{_pid}"):
                        _updated = dict(pr)
                        _updated['status'] = 'confirmed'
                        _updated['confirmed_by'] = 'vendor_admin'
                        _updated['confirmed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        db_upsert('processing_confirm', _updated)
                        st.success("확인 처리 완료")
                        st.rerun()
                with bc2:
                    if st.button("❌ 반려", key=f"va_proc_no_{_pid}"):
                        _updated = dict(pr)
                        _updated['status'] = 'rejected'
                        _updated['confirmed_by'] = 'vendor_admin'
                        _updated['confirmed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        db_upsert('processing_confirm', _updated)
                        st.warning("반려 처리 완료")
                        st.rerun()
