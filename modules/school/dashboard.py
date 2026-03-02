# zeroda_platform/modules/school/dashboard.py
# ==========================================
# 학교 대시보드 (행정실 + 영양사 공통)
# role: school_admin / school_nutrition
# ==========================================

import streamlit as st
from config.settings import COMMON_CSS, CO2_FACTOR, TREE_FACTOR, CURRENT_YEAR, CURRENT_MONTH
from database.db_manager import db_get, load_schedule


def render_dashboard(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    role     = user.get('role', 'school_admin')
    name     = user.get('name', '')
    schools  = [s.strip() for s in user.get('schools', '').split(',') if s.strip()]

    if not schools:
        st.warning("배정된 학교가 없습니다. 관리자에게 문의하세요.")
        return

    # 학교 선택 (다중 학교 계정인 경우)
    school = schools[0] if len(schools) == 1 else \
             st.selectbox("학교 선택", schools, key="sch_select")

    icon = "🍱" if role == 'school_nutrition' else "🏫"
    role_label = "영양사" if role == 'school_nutrition' else "행정실"
    st.markdown(f"## {icon} {school} ({role_label})")

    year  = st.session_state.get('sch_year',  CURRENT_YEAR)
    month = st.session_state.get('sch_month', CURRENT_MONTH)

    col_y, col_m, _ = st.columns([1, 1, 4])
    with col_y:
        year  = st.selectbox("년도", list(range(2023, CURRENT_YEAR + 1)),
                             index=list(range(2023, CURRENT_YEAR + 1)).index(year),
                             key="sch_year_sel")
    with col_m:
        month = st.selectbox("월", list(range(1, 13)),
                             index=month - 1, key="sch_month_sel")

    st.session_state['sch_year']  = year
    st.session_state['sch_month'] = month

    # ── 수거 데이터 ──
    rows = db_get('real_collection')
    rows = [r for r in rows
            if r.get('학교명') == school
            and int(r.get('월', 0) or 0) == month
            and str(r.get('년도', '')) == str(year)]

    total_food    = sum(float(r.get('음식물(kg)', 0) or 0) for r in rows)
    total_recycle = sum(float(r.get('재활용(kg)', 0) or 0) for r in rows)
    co2_saved     = round(total_food * CO2_FACTOR, 1)
    trees         = round(co2_saved / TREE_FACTOR, 1)

    # ── KPI 카드 ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="custom-card">
            <div class="metric-title">🍱 음식물 수거량</div>
            <div class="metric-value-food">{total_food:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="custom-card custom-card-green">
            <div class="metric-title">♻️ 재활용 수거량</div>
            <div class="metric-value-recycle">{total_recycle:,.1f} kg</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="custom-card custom-card-orange">
            <div class="metric-title">🌿 CO₂ 감축</div>
            <div class="metric-value-total">{co2_saved:,} kg</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="custom-card custom-card-green">
            <div class="metric-title">🌲 소나무 효과</div>
            <div class="metric-value-recycle">{trees:,} 그루</div>
        </div>""", unsafe_allow_html=True)

    # ── 역할별 분기 ──
    if role == 'school_nutrition':
        _render_nutrition_view(school, rows)
    else:
        _render_admin_view(school, rows, year, month)


def _render_nutrition_view(school: str, rows: list):
    """영양사: 수거일정 + 수거량 조회만 (정산 정보 비표시)"""
    st.markdown("### 📅 수거 일정")

    from database.db_manager import db_get as _db_get
    school_rows = _db_get('school_master', {'school_name': school})
    vendor = school_rows[0].get('vendor', '') if school_rows else ''

    from datetime import date
    today = date.today()
    sched = load_schedule(vendor, today.month) if vendor else None

    if sched:
        weekdays = ', '.join(sched.get('요일', []))
        items    = ', '.join(sched.get('품목', []))
        st.info(f"수거 요일: {weekdays}요일  |  수거 품목: {items}")
    else:
        st.info("수거일정 정보가 없습니다.")

    st.markdown("### 📋 수거 내역")
    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)
        display_cols = ['날짜', '음식물(kg)', '재활용(kg)', '수거업체']
        display_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True)
    else:
        st.info("수거 데이터가 없습니다.")


def _render_admin_view(school: str, rows: list, year: int, month: int):
    """행정실: 수거 내역 + 정산서 + PDF 다운로드"""
    st.markdown("### 📋 수거 내역 및 정산")

    if not rows:
        st.info("수거 데이터가 없습니다.")
        return

    import pandas as pd
    df = pd.DataFrame(rows)
    display_cols = ['날짜', '음식물(kg)', '단가(원)', '공급가', '수거업체', '수거기사']
    display_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True)

    total_kg  = df['음식물(kg)'].astype(float).sum() if '음식물(kg)' in df.columns else 0
    total_amt = df['공급가'].astype(float).sum()     if '공급가'    in df.columns else 0
    supply    = int(total_amt / 1.1)
    vat       = int(total_amt) - supply

    st.markdown(f"""
    <div class="custom-card">
        <div class="metric-title">정산 요약</div>
        <div>총 수거량: <strong>{total_kg:,.1f} kg</strong></div>
        <div>공급가액: <strong>{supply:,} 원</strong></div>
        <div>부가세:   <strong>{vat:,} 원</strong></div>
        <div style="font-size:20px;font-weight:900;color:#1a73e8;">
            합계: {int(total_amt):,} 원</div>
    </div>""", unsafe_allow_html=True)

    if st.button("📄 정산서 PDF 다운로드", key="sch_pdf"):
        from services.pdf_generator import generate_collection_report_pdf
        pdf = generate_collection_report_pdf(school, year, month, rows)
        if pdf:
            st.download_button("💾 저장", pdf,
                file_name=f"{year}{month:02d}_{school}_정산서.pdf",
                mime="application/pdf")
        else:
            st.error("PDF 생성 실패")