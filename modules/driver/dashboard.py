# zeroda_platform/modules/driver/dashboard.py
# ==========================================
# 수거기사 대시보드
# ==========================================

import streamlit as st
from datetime import date
from config.settings import COMMON_CSS, CURRENT_MONTH
from database.db_manager import db_get, load_schedule, get_vendor_display_name

WEEKDAY_MAP = {0:'월',1:'화',2:'수',3:'목',4:'금',5:'토',6:'일'}


def render_dashboard(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    vendor   = user.get('vendor', '')
    name     = user.get('name', '')
    biz_name = get_vendor_display_name(vendor)

    st.markdown(f"## 🚚 {name} 기사님 안녕하세요!")
    st.markdown(f"소속: **{biz_name}**")

    today    = date.today()
    today_wd = WEEKDAY_MAP[today.weekday()]

    st.info(f"📅 {today.strftime('%Y년 %m월 %d일')} ({today_wd}요일)")

    # ── 오늘 수거 일정 ──
    sched = load_schedule(vendor, today.month)

    if not sched:
        st.warning("이번 달 수거일정이 등록되지 않았습니다. 관리자에게 문의하세요.")
        return

    if today_wd not in sched.get('요일', []):
        st.info(f"오늘({today_wd}요일)은 수거 일정이 없습니다. 수고하셨습니다! 🎉")
        _render_recent_collection(vendor, name)
        return

    schools = sched.get('학교', [])
    items   = sched.get('품목', [])

    st.success(f"오늘 수거 학교: **{len(schools)}개**")
    st.markdown(f"수거 품목: {', '.join(items)}")

    st.markdown("### 오늘 수거 학교 목록")

    # 오늘 입력 완료 여부 확인
    today_str = str(today)
    done_rows = db_get('real_collection')
    done_rows = [r for r in done_rows
                 if r.get('날짜') == today_str
                 and r.get('수거기사') == name]
    done_schools = {r.get('학교명') for r in done_rows}

    for s in schools:
        status = "✅ 완료" if s in done_schools else "⏳ 대기"
        color  = "#34a853"  if s in done_schools else "#ea4335"
        st.markdown(f"""
        <div style="background:#f8f9fa;border-radius:8px;padding:10px;
                    margin-bottom:6px;border-left:4px solid {color};
                    display:flex;justify-content:space-between;">
            <span style="font-weight:700;">{s}</span>
            <span style="color:{color};font-weight:700;">{status}</span>
        </div>""", unsafe_allow_html=True)

    total_done = len(done_schools & set(schools))
    st.markdown(f"**진행률: {total_done}/{len(schools)}**")
    st.progress(total_done / len(schools) if schools else 0)

    _render_recent_collection(vendor, name)


def _render_recent_collection(vendor: str, driver_name: str):
    """최근 7일 수거 실적"""
    st.markdown("### 📊 최근 수거 실적")

    rows = db_get('real_collection')
    rows = [r for r in rows
            if r.get('수거기사') == driver_name
            and r.get('수거업체') == vendor]
    rows = sorted(rows, key=lambda x: x.get('날짜', ''), reverse=True)[:10]

    if not rows:
        st.info("최근 수거 실적이 없습니다.")
        return

    for r in rows:
        kg  = float(r.get('음식물(kg)', 0) or 0)
        st.markdown(
            f"• {r.get('날짜','')} | {r.get('학교명','')} | {kg:.1f}kg")