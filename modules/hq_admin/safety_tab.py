# modules/hq_admin/safety_tab.py
import streamlit as st
import pandas as pd
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo
from database.db_manager import (
    db_get, db_insert, get_all_vendors,
    get_daily_safety_checks, get_driver_last_activity,
)
from config.settings import (
    CURRENT_YEAR, CURRENT_MONTH,
    DAILY_SAFETY_CHECKLIST, DRIVER_MONITORING_CONFIG,
)


def render_safety_tab():
    st.markdown("## 안전관리")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📚 안전교육 조회", "🔧 안전점검 조회", "🚨 사고 신고 관리",
        "📋 일일안전점검 조회", "🛰️ 기사 활동 모니터링",
    ])

    with tab1:
        _render_education()
    with tab2:
        _render_checklist()
    with tab3:
        _render_accident()
    with tab4:
        _render_daily_checks()
    with tab5:
        _render_driver_monitoring()


def _render_education():
    st.markdown("### 안전교육 이력")

    col1, col2 = st.columns(2)
    with col1:
        vendors = ['전체'] + get_all_vendors()
        vendor_filter = st.selectbox("업체", vendors, key="sf_edu_vendor")
    with col2:
        result_filter = st.selectbox("이수 여부", ['전체', '이수', '미이수'], key="sf_edu_result")

    rows = db_get('safety_education')
    if not rows:
        st.info("등록된 안전교육 이력이 없습니다.")
        return

    df = pd.DataFrame(rows)
    if vendor_filter != '전체' and 'vendor' in df.columns:
        df = df[df['vendor'] == vendor_filter]
    if result_filter != '전체' and 'result' in df.columns:
        df = df[df['result'] == result_filter]

    # 요약
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 교육 건수", f"{len(df)}건")
    with c2:
        isu = len(df[df['result'] == '이수']) if 'result' in df.columns else 0
        st.metric("이수", f"{isu}건")
    with c3:
        misu = len(df[df['result'] == '미이수']) if 'result' in df.columns else 0
        st.metric("미이수", f"{misu}건")

    show = [c for c in ['edu_date','vendor','driver','edu_type','edu_hours','instructor','result','memo'] if c in df.columns]
    st.dataframe(df[show].sort_values('edu_date', ascending=False) if 'edu_date' in df.columns else df[show],
                 use_container_width=True, hide_index=True)


def _render_checklist():
    st.markdown("### 안전점검 결과")

    rows = db_get('safety_checklist')
    if not rows:
        st.info("등록된 안전점검 내역이 없습니다.")
        return

    df = pd.DataFrame(rows)
    show = [c for c in ['check_date','vendor','driver','vehicle_no','total_ok','total_fail','inspector'] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    if 'total_fail' in df.columns:
        fail_count = df[df['total_fail'] > 0]
        if not fail_count.empty:
            st.warning(f"⚠️ 불합격 항목이 있는 점검: {len(fail_count)}건")


def _render_accident():
    st.markdown("### 사고 신고 현황")

    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("처리 상태", ['전체', '신고완료', '처리중', '완료'], key="sf_acc_status")
    with col2:
        type_filter = st.selectbox("사고 유형", ['전체', '교통사고', '작업중사고', '차량고장', '기타'], key="sf_acc_type")

    rows = db_get('accident_report')
    if not rows:
        st.info("신고된 사고가 없습니다.")
        return

    df = pd.DataFrame(rows)
    if status_filter != '전체' and 'status' in df.columns:
        df = df[df['status'] == status_filter]
    if type_filter != '전체' and 'accident_type' in df.columns:
        df = df[df['accident_type'] == type_filter]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("전체 사고", f"{len(df)}건")
    with c2:
        processing = len(df[df['status'] == '처리중']) if 'status' in df.columns else 0
        st.metric("처리중", f"{processing}건")
    with c3:
        done = len(df[df['status'] == '완료']) if 'status' in df.columns else 0
        st.metric("완료", f"{done}건")

    # 상태 이모지 매핑 (외주업체와 통일)
    _acc_status_map = {'신고완료': '📋 신고완료', '처리중': '⏳ 처리중', '완료': '✅ 완료'}
    if 'status' in df.columns:
        df['status'] = df['status'].map(_acc_status_map).fillna(df['status'])

    show = [c for c in ['occur_date','vendor','driver','accident_type','severity','status','occur_location'] if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)

    # 처리 상태 변경
    if not df.empty and 'id' in df.columns:
        st.divider()
        st.markdown("#### 처리 상태 변경")
        import sqlite3
        from config.settings import DB_PATH
        sel_id = st.number_input("사고 ID", min_value=1, step=1, key="acc_id")
        new_status = st.selectbox("변경할 상태", ['처리중', '완료'], key="acc_new_status")
        if st.button("상태 변경", key="acc_update"):
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE accident_report SET status=? WHERE id=?", (new_status, sel_id))
                conn.commit()
                conn.close()
                st.success(f"ID {sel_id} 상태 → {new_status}")
                st.rerun()
            except Exception as e:
                st.error(f"오류: {e}")


# ── 일일안전점검 조회 (신규 Phase 3) ──────────────────────────────────
def _render_daily_checks():
    st.markdown("### 일일안전보건 점검 이력")

    col1, col2, col3 = st.columns(3)
    with col1:
        vendors = ['전체'] + get_all_vendors()
        v_filter = st.selectbox("업체", vendors, key="hq_dc_vendor")
    with col2:
        ym = st.text_input("년월 (YYYY-MM)", value=date.today().strftime('%Y-%m'), key="hq_dc_ym")
    with col3:
        cat_options = ['전체'] + [v['label'] for v in DAILY_SAFETY_CHECKLIST.values()]
        cat_filter = st.selectbox("점검 카테고리", cat_options, key="hq_dc_cat")

    # 카테고리 label → key 역매핑
    _label_to_key = {v['label']: k for k, v in DAILY_SAFETY_CHECKLIST.items()}

    vendor_arg = None if v_filter == '전체' else v_filter
    rows = get_daily_safety_checks(vendor=vendor_arg, year_month=ym)

    if cat_filter != '전체':
        cat_key = _label_to_key.get(cat_filter, '')
        rows = [r for r in rows if r.get('category') == cat_key]

    if not rows:
        st.info("해당 조건의 점검 이력이 없습니다.")
        return

    df = pd.DataFrame(rows)

    # ── 요약 메트릭 ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 점검 건수", f"{len(df)}건")
    with c2:
        total_ok = int(df['total_ok'].sum()) if 'total_ok' in df.columns else 0
        st.metric("양호 항목 합계", f"{total_ok}개")
    with c3:
        total_fail = int(df['total_fail'].sum()) if 'total_fail' in df.columns else 0
        st.metric("불량 항목 합계", f"{total_fail}개")
    with c4:
        all_items = total_ok + total_fail
        rate = (total_ok / all_items * 100) if all_items > 0 else 0
        st.metric("양호율", f"{rate:.1f}%")

    # ── 불량 항목 경고 ──
    if 'total_fail' in df.columns:
        fail_rows = df[df['total_fail'] > 0]
        if not fail_rows.empty:
            st.warning(f"⚠️ 불량 항목 포함 점검: {len(fail_rows)}건")
            for _, fr in fail_rows.iterrows():
                fail_memo = fr.get('fail_memo', '')
                items_json = fr.get('check_items', '{}')
                try:
                    items_dict = json.loads(items_json) if isinstance(items_json, str) else items_json
                    fails = [k for k, v in items_dict.items() if '불량' in str(v) or v is False]
                except Exception:
                    fails = []
                cat_label = DAILY_SAFETY_CHECKLIST.get(fr.get('category', ''), {}).get('label', fr.get('category', ''))
                st.caption(
                    f"📅 {fr.get('check_date','')} | 🏢 {fr.get('vendor','')} | "
                    f"👤 {fr.get('driver','')} | 📂 {cat_label} | "
                    f"❌ 불량 {fr.get('total_fail',0)}개"
                    + (f" | 메모: {fail_memo}" if fail_memo else "")
                )

    # ── 카테고리 라벨 표시용 변환 ──
    if 'category' in df.columns:
        df['category_label'] = df['category'].map(
            lambda x: DAILY_SAFETY_CHECKLIST.get(x, {}).get('label', x)
        )

    show = [c for c in ['check_date','vendor','driver','vehicle_no','category_label','total_ok','total_fail','fail_memo'] if c in df.columns]
    col_config = {'category_label': '점검 카테고리'}
    st.dataframe(
        df[show].sort_values('check_date', ascending=False) if 'check_date' in df.columns else df[show],
        use_container_width=True, hide_index=True, column_config=col_config,
    )

    # ── 기사별 이행률 요약 ──
    st.divider()
    st.markdown("#### 기사별 일일점검 이행률")
    required_cats = len(DAILY_SAFETY_CHECKLIST)
    if 'driver' in df.columns and 'check_date' in df.columns:
        grouped = df.groupby(['vendor', 'driver', 'check_date']).agg(
            cats_done=('category', 'nunique'),
            fail_total=('total_fail', 'sum'),
        ).reset_index()
        grouped['이행률'] = (grouped['cats_done'] / required_cats * 100).round(1)
        driver_summary = grouped.groupby(['vendor', 'driver']).agg(
            점검일수=('check_date', 'nunique'),
            평균이행률=('이행률', 'mean'),
            총불량=('fail_total', 'sum'),
        ).reset_index()
        driver_summary['평균이행률'] = driver_summary['평균이행률'].round(1).astype(str) + '%'
        st.dataframe(driver_summary, use_container_width=True, hide_index=True)

    # ── 엑셀 다운로드 (감사·법정보존용) ──
    st.divider()
    st.markdown("#### 📥 일일안전점검 이력 엑셀 다운로드")
    st.caption("산업안전보건법 시행규칙 제37조에 따른 위험성평가 기록물(3년 보존)용 엑셀 파일입니다.")

    if st.button("📥 엑셀 파일 생성", key="hq_dc_excel_btn", type="primary"):
        try:
            from io import BytesIO
            excel_buf = BytesIO()
            # 상세 이력 시트
            df_export = df[show].copy()
            df_export.columns = ['점검일', '업체', '기사명', '차량번호', '점검 카테고리', '양호', '불량', '메모']

            with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
                df_export.sort_values('점검일', ascending=False).to_excel(
                    writer, sheet_name='점검이력', index=False)
                # 이행률 요약 시트
                if 'driver' in df.columns and 'check_date' in df.columns:
                    driver_summary.to_excel(writer, sheet_name='기사별이행률', index=False)

            st.download_button(
                label="⬇️ 엑셀 다운로드",
                data=excel_buf.getvalue(),
                file_name=f"일일안전점검이력_{ym}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="hq_dc_excel_download",
            )
            st.success("✅ 엑셀 파일이 생성되었습니다.")
        except Exception as e:
            st.error(f"엑셀 생성 오류: {e}")


# ── 기사 활동 모니터링 (신규 Phase 3) ──────────────────────────────────
def _render_driver_monitoring():
    st.markdown("### 기사 활동 모니터링")
    st.caption("수거량 입력 시간 기반으로 기사 활동 상태를 실시간 추적합니다.")

    col1, col2 = st.columns([2, 1])
    with col1:
        vendors = ['전체'] + get_all_vendors()
        v_filter = st.selectbox("업체", vendors, key="hq_mon_vendor")
    with col2:
        if st.button("🔄 새로고침", key="hq_mon_refresh"):
            st.rerun()

    cfg = DRIVER_MONITORING_CONFIG
    vendor_arg = None if v_filter == '전체' else v_filter
    activities = get_driver_last_activity(vendor=vendor_arg)

    if not activities:
        st.info("수거 입력 이력이 없어 모니터링 데이터가 없습니다.")
        return

    now = datetime.now(ZoneInfo('Asia/Seoul'))
    today_str = now.strftime('%Y-%m-%d')

    # ── 기사별 상태 계산 ──
    status_list = []
    for act in activities:
        last_at = act.get('last_activity') or act.get('created_at', '')
        driver = act.get('driver', '')
        last_school = act.get('school_name', '')

        if not last_at:
            status_list.append({
                'driver': driver, 'last_school': last_school,
                'last_time': '-', 'elapsed_min': 999,
                'status': '⚫ 데이터없음',
            })
            continue

        try:
            if len(last_at) <= 10:  # 날짜만 있는 경우
                last_dt = datetime.strptime(last_at, '%Y-%m-%d').replace(tzinfo=ZoneInfo('Asia/Seoul'))
            else:
                last_dt = datetime.strptime(last_at[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Seoul'))
            elapsed = (now - last_dt).total_seconds() / 60
        except Exception:
            elapsed = 999
            last_dt = None

        # 오늘 데이터만 상태 판정
        is_today = last_at.startswith(today_str)

        if not is_today:
            status = '⚫ 금일미입력'
        elif elapsed <= cfg['alert_threshold_min']:
            status = '🟢 정상'
        elif elapsed <= cfg['warning_threshold_min']:
            status = '🟡 주의'
        elif elapsed <= cfg['emergency_threshold_min']:
            status = '🟠 경고'
        else:
            status = '🔴 긴급확인'

        status_list.append({
            'driver': driver,
            'vendor': act.get('vendor', v_filter if v_filter != '전체' else ''),
            'last_school': last_school,
            'last_time': last_at[:16] if last_at else '-',
            'elapsed_min': round(elapsed, 1) if elapsed < 999 else '-',
            'status': status,
        })

    # ── 상태별 요약 ──
    c1, c2, c3, c4 = st.columns(4)
    normal = sum(1 for s in status_list if '정상' in s['status'])
    caution = sum(1 for s in status_list if '주의' in s['status'])
    warning = sum(1 for s in status_list if '경고' in s['status'])
    urgent = sum(1 for s in status_list if '긴급' in s['status'])
    with c1:
        st.metric("🟢 정상", f"{normal}명")
    with c2:
        st.metric("🟡 주의", f"{caution}명")
    with c3:
        st.metric("🟠 경고", f"{warning}명")
    with c4:
        st.metric("🔴 긴급확인", f"{urgent}명")

    # ── 기준 안내 ──
    st.caption(
        f"기준: 정상 ≤{cfg['alert_threshold_min']}분 | "
        f"주의 ≤{cfg['warning_threshold_min']}분 | "
        f"경고 ≤{cfg['emergency_threshold_min']}분 | "
        f"긴급 >{cfg['emergency_threshold_min']}분"
    )

    # ── 상세 테이블 ──
    df_mon = pd.DataFrame(status_list)
    show_cols = [c for c in ['status','driver','vendor','last_school','last_time','elapsed_min'] if c in df_mon.columns]
    col_config = {
        'status': '상태', 'driver': '기사명', 'vendor': '업체',
        'last_school': '마지막 거래처', 'last_time': '마지막 입력',
        'elapsed_min': '경과(분)',
    }
    st.dataframe(df_mon[show_cols], use_container_width=True, hide_index=True, column_config=col_config)

    # ── 긴급 알림 영역 ──
    urgents = [s for s in status_list if '긴급' in s['status'] or '경고' in s['status']]
    if urgents:
        st.divider()
        st.markdown("#### ⚠️ 즉시 확인 필요")
        for u in urgents:
            emoji = '🔴' if '긴급' in u['status'] else '🟠'
            st.error(
                f"{emoji} **{u['driver']}** — "
                f"마지막 입력: {u['last_time']} | "
                f"경과: {u['elapsed_min']}분 | "
                f"마지막 거래처: {u['last_school']}"
            )
