# modules/driver/dashboard.py
# 기사 전용 앱 - 오늘일정 + 수거입력 + 안전 + 퇴근
import streamlit as st
import pandas as pd
import urllib.parse
from datetime import date, datetime
from database.db_manager import db_insert, db_get, get_schools_by_vendor
from config.settings import COMMON_CSS

WEEKDAY_MAP = {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}

# 안전점검 항목 (확장 가능)
SAFETY_CHECKS = [
    ("chk_camera",    "차량 후방 카메라 정상 작동"),
    ("chk_assistant", "조수석 안전 요원 탑승 확인"),
    ("chk_schoolzone","스쿨존 서행 운행 숙지"),
    ("chk_brake",     "브레이크 작동 정상 확인"),
    ("chk_tire",      "타이어 공기압 이상 없음"),
]


def render_dashboard(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    driver_name = user.get('name', '')
    vendor      = user.get('vendor', '')
    today       = date.today()
    today_str   = str(today)
    today_wd    = WEEKDAY_MAP[today.weekday()]

    # ── 헤더 ──────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a73e8,#34a853);
                padding:20px;border-radius:12px;text-align:center;margin-bottom:16px;">
        <div style="color:white;font-size:22px;font-weight:900;">🚚 수거기사 전용 앱</div>
        <div style="color:rgba(255,255,255,0.85);font-size:14px;margin-top:6px;">
            {driver_name} 기사님 &nbsp;|&nbsp; 📅 {today.strftime('%Y.%m.%d')} ({today_wd}요일)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 메인 탭 4개 ────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 오늘 일정",
        "📤 수거 입력",
        "🚨 안전",
        "🏠 퇴근"
    ])

    # ══════════════════════════════════════════════
    # 탭1: 오늘 수거일정 + 내비 연동
    # ══════════════════════════════════════════════
    with tab1:
        schools = get_schools_by_vendor(vendor)

        if not schools:
            st.warning("담당 학교가 없습니다. 관리자에게 문의하세요.")
        else:
            # 오늘 완료 학교
            today_done = [r for r in db_get('real_collection')
                          if r.get('driver') == driver_name
                          and str(r.get('collect_date', '')) == today_str
                          and r.get('status') == 'submitted']
            done_schools = {r.get('school_name') for r in today_done}

            # 요약
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("담당 학교", f"{len(schools)}개")
            with c2:
                st.metric("완료", f"{len(done_schools)}개")
            with c3:
                remain = len(schools) - len(done_schools)
                st.metric("남은 학교", f"{remain}개")

            st.progress(len(done_schools) / len(schools) if schools else 0)
            st.divider()

            # 학교별 카드 + 내비 버튼
            for school in schools:
                done   = school in done_schools
                color  = "#34a853" if done else "#ea4335"
                status = "✅ 완료"  if done else "⏳ 대기"
                encoded = urllib.parse.quote(school)
                kakao   = f"https://map.kakao.com/link/search/{encoded}"
                tmap    = f"tmap://search?name={encoded}"
                naver   = f"https://map.naver.com/v5/search/{encoded}"

                st.markdown(f"""
                <div style="background:#f8f9fa;border-radius:10px;padding:14px;
                            margin-bottom:6px;border-left:5px solid {color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-weight:700;font-size:15px;">🏫 {school}</span>
                        <span style="color:{color};font-weight:700;">{status}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 미완료 학교만 내비 버튼 표시
                if not done:
                    n1, n2, n3 = st.columns(3)
                    with n1:
                        st.markdown(
                            f'<a href="{kakao}" target="_blank" style="display:block;text-align:center;'
                            f'background:#FEE500;color:#000;padding:8px;border-radius:8px;'
                            f'text-decoration:none;font-size:13px;font-weight:700;">🗺️ 카카오맵</a>',
                            unsafe_allow_html=True)
                    with n2:
                        st.markdown(
                            f'<a href="{tmap}" target="_blank" style="display:block;text-align:center;'
                            f'background:#0064FF;color:#fff;padding:8px;border-radius:8px;'
                            f'text-decoration:none;font-size:13px;font-weight:700;">🚗 티맵</a>',
                            unsafe_allow_html=True)
                    with n3:
                        st.markdown(
                            f'<a href="{naver}" target="_blank" style="display:block;text-align:center;'
                            f'background:#03C75A;color:#fff;padding:8px;border-radius:8px;'
                            f'text-decoration:none;font-size:13px;font-weight:700;">🟢 네이버지도</a>',
                            unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # 탭2: 수거 입력 + 카메라 촬영
    # ══════════════════════════════════════════════
    with tab2:
        schools = get_schools_by_vendor(vendor)
        if not schools:
            st.warning("담당 학교가 없습니다.")
        else:
            # 현장 증빙 사진
            with st.expander("📸 현장 증빙 사진 (선택)", expanded=False):
                photo = st.camera_input("카메라로 촬영하세요", key="drv_camera")
                if photo:
                    st.success("📸 사진이 첨부되었습니다.")

            st.divider()

            col1, col2 = st.columns(2)
            with col1:
                school       = st.selectbox("학교 *", schools, key="drv_school")
                collect_date = st.date_input("수거일 *", value=today, key="drv_date")
                item_type    = st.selectbox("품목 *", ["음식물", "재활용", "일반"], key="drv_item")
            with col2:
                weight       = st.number_input("수거량 (kg) *", min_value=0.0, step=0.1, key="drv_weight")
                unit_price   = st.number_input("단가 (원)", min_value=0, step=1, key="drv_price")
                collect_time = st.text_input("수거 시간",
                                              value=datetime.now().strftime("%H:%M"),
                                              key="drv_time")

            memo = st.text_area("메모", placeholder="특이사항 입력...", height=70, key="drv_memo")

            if weight > 0 and unit_price > 0:
                st.info(f"💰 예상 금액: {weight:.1f}kg × {unit_price:,}원 = **{weight*unit_price:,.0f}원**")

            st.divider()

            b1, b2 = st.columns(2)
            with b1:
                if st.button("📋 임시저장", use_container_width=True, key="btn_draft"):
                    if _validate(school, weight):
                        row_id = _save(vendor, school, collect_date, collect_time,
                                       item_type, weight, unit_price, driver_name, memo, 'draft')
                        st.success(f"임시저장 완료 (ID:{row_id})") if row_id else st.error("저장 실패")

            with b2:
                if st.button("✅ 수거완료 · 본사전송", type="primary",
                             use_container_width=True, key="btn_submit"):
                    if _validate(school, weight):
                        row_id = _save(vendor, school, collect_date, collect_time,
                                       item_type, weight, unit_price, driver_name, memo, 'submitted')
                        if row_id:
                            st.success(f"✅ 본사 전송 완료! (ID:{row_id})")
                            st.balloons()
                        else:
                            st.error("전송 실패")

            # 오늘 입력 현황
            st.divider()
            st.markdown("#### 오늘 입력 현황")
            today_rows = [r for r in db_get('real_collection')
                          if r.get('driver') == driver_name
                          and str(r.get('collect_date', '')) == today_str]

            if not today_rows:
                st.info("오늘 입력된 수거 실적이 없습니다.")
            else:
                df = pd.DataFrame(today_rows)
                if 'status' in df.columns:
                    df['status'] = df['status'].map({
                        'draft':     '📋 임시저장',
                        'submitted': '✅ 전송완료',
                    }).fillna(df['status'])
                show = [c for c in ['school_name','item_type','weight','status','memo'] if c in df.columns]
                st.dataframe(df[show], use_container_width=True, hide_index=True)

                m1, m2 = st.columns(2)
                with m1:
                    st.metric("오늘 수거량", f"{df['weight'].sum():,.1f} kg")
                with m2:
                    submitted = len([r for r in today_rows if r.get('status') == 'submitted'])
                    st.metric("전송 완료", f"{submitted}건")

    # ══════════════════════════════════════════════
    # 탭3: 안전 (운행 전 점검 + 스쿨존 알림)
    # ══════════════════════════════════════════════
    with tab3:
        # 운행 전 안전점검
        st.markdown("### 📋 운행 전 안전점검")
        st.caption("출발 전 반드시 확인하세요.")

        results = {}
        for key, label in SAFETY_CHECKS:
            results[key] = st.checkbox(label, key=key)

        checked_count = sum(results.values())
        total_count   = len(SAFETY_CHECKS)
        st.progress(checked_count / total_count)
        st.caption(f"{checked_count} / {total_count} 항목 완료")

        if checked_count == total_count:
            st.success("✅ 모든 안전점검 완료! 안전 운행하세요. 🚦")
        else:
            st.warning(f"⚠️ {total_count - checked_count}개 항목을 확인해 주세요.")

        st.divider()

        # 스쿨존 GPS 알림 토글
        st.markdown("### 🚸 스쿨존 알림")
        schoolzone = st.toggle("스쿨존 진입 알림 활성화", key="schoolzone_toggle")

        if schoolzone:
            st.error("🚨 스쿨존 진입! 속도를 30km 이하로 줄이세요.")
            st.markdown("""
            <div style="text-align:center;background:#d93025;border-radius:50%;
                        width:120px;height:120px;margin:0 auto;
                        display:flex;align-items:center;justify-content:center;">
                <span style="color:white;font-size:56px;font-weight:900;">30</span>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='text-align:center;color:#d93025;font-weight:700;margin-top:8px;'>제한속도 30km/h</div>",
                        unsafe_allow_html=True)
        else:
            st.info("스쿨존 구역 진입 시 토글을 켜세요.")

    # ══════════════════════════════════════════════
    # 탭4: 퇴근
    # ══════════════════════════════════════════════
    with tab4:
        today_all     = [r for r in db_get('real_collection')
                         if r.get('driver') == driver_name
                         and str(r.get('collect_date', '')) == today_str]
        submitted_cnt = len([r for r in today_all if r.get('status') == 'submitted'])
        total_weight  = sum(float(r.get('weight', 0)) for r in today_all)
        all_schools   = get_schools_by_vendor(vendor)
        done_schools  = {r.get('school_name') for r in today_all if r.get('status') == 'submitted'}

        st.markdown("### 오늘 실적 요약")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("전송 완료", f"{submitted_cnt}건")
        with c2:
            st.metric("총 수거량", f"{total_weight:,.1f} kg")
        with c3:
            st.metric("학교 완료율", f"{len(done_schools)}/{len(all_schools)}개")

        # 미완료 학교 표시
        remain = [s for s in all_schools if s not in done_schools]
        if remain:
            st.warning(f"⚠️ 미완료 학교 {len(remain)}곳: {', '.join(remain)}")

        st.divider()

        # 안전점검 미완료 경고
        safety_done = all(
            st.session_state.get(key, False) for key, _ in SAFETY_CHECKS
        )
        if not safety_done:
            st.warning("⚠️ 안전점검이 완료되지 않았습니다. [안전] 탭에서 확인하세요.")

        if st.button("🏠 퇴근하기", use_container_width=True,
                     type="primary", key="btn_off"):
            now_time = datetime.now().strftime('%H시 %M분')
            st.balloons()
            st.success(f"✅ {driver_name}님, {now_time} 퇴근 처리 완료! 수고하셨습니다. 🎉")
            st.caption("퇴근 기록이 본사에 자동 전송됩니다.")


# ── 내부 유틸 ──────────────────────────────────────
def _validate(school, weight):
    if not school:
        st.error("학교를 선택하세요.")
        return False
    if weight <= 0:
        st.error("수거량을 입력하세요.")
        return False
    return True


def _save(vendor, school, collect_date, collect_time,
          item_type, weight, unit_price, driver, memo, status):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return db_insert('real_collection', {
        'vendor':       vendor,
        'school_name':  school,
        'collect_date': str(collect_date),
        'collect_time': collect_time,
        'item_type':    item_type,
        'weight':       weight,
        'unit_price':   unit_price,
        'amount':       weight * unit_price,
        'driver':       driver,
        'memo':         memo,
        'status':       status,
        'submitted_at': now if status == 'submitted' else '',
        'created_at':   now,
    })
