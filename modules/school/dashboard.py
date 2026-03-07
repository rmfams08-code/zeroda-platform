# modules/school/dashboard.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, filter_rows_by_school
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_dashboard(user):
    role = user.get('role', '')
    schools_str = user.get('schools', '')
    school_list = [s.strip() for s in schools_str.split(',') if s.strip()] if schools_str else []

    st.markdown("## 학교 수거 현황")

    # 새로고침 버튼
    col_r, _ = st.columns([1, 5])
    with col_r:
        if st.button("🔄 새로고침", key="sch_refresh"):
            try:
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
            except Exception:
                pass
            st.rerun()

    if not school_list:
        st.warning("담당 학교가 배정되지 않았습니다. 관리자에게 문의하세요.")
        return

    school = st.selectbox("학교 선택", school_list) if len(school_list) > 1 else school_list[0]
    st.markdown(f"### {school}")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 월별 현황", "📋 수거 내역", "💰 정산 확인", "🌿 ESG 보고서"])

    with tab1:
        _render_monthly(school)

    with tab2:
        _render_detail(school)

    with tab3:
        _render_settlement(school)

    with tab4:
        _render_esg(school)


def _render_monthly(school):
    # 연도/월 필터
    col1, col2 = st.columns(2)
    with col1:
        year  = st.selectbox("연도", [2024, 2025, 2026],
                              index=[2024,2025,2026].index(CURRENT_YEAR)
                              if CURRENT_YEAR in [2024,2025,2026] else 2,
                              key="sch_m_year")
    with col2:
        month = st.selectbox("기준 월", list(range(1, 13)),
                              index=CURRENT_MONTH - 1, key="sch_m_month")

    rows = filter_rows_by_school(db_get('real_collection'), school)
    if not rows:
        st.info("수거 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    if 'collect_date' not in df.columns:
        st.info("데이터 형식 오류")
        return

    df['collect_date'] = pd.to_datetime(df['collect_date'], errors='coerce')
    df['월'] = df['collect_date'].dt.to_period('M').astype(str)

    # 이번 선택 월 데이터
    month_str = f"{year}-{str(month).zfill(2)}"
    this_month = df[df['월'] == month_str]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("누적 수거량", f"{df['weight'].sum():,.1f} kg")
    with c2:
        st.metric(f"{year}년 {month}월 수거량", f"{this_month['weight'].sum():,.1f} kg")
    with c3:
        st.metric("수거 횟수", f"{len(df)}회")

    st.divider()

    # 월별 합계 전체 표시
    summary = df.groupby('월')['weight'].sum().reset_index()
    summary.columns = ['월', '수거량(kg)']
    summary = summary.sort_values('월', ascending=False)
    st.dataframe(summary, use_container_width=True, hide_index=True)


def _render_detail(school):
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                             index=[2024,2025,2026].index(CURRENT_YEAR)
                             if CURRENT_YEAR in [2024,2025,2026] else 2,
                             key="sch_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)), index=CURRENT_MONTH-1, key="sch_month")

    month_str = str(month).zfill(2)
    rows = [r for r in filter_rows_by_school(db_get('real_collection'), school)
            if str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    if not rows:
        st.info("해당 기간 수거 내역이 없습니다.")
        return

    df = pd.DataFrame(rows)
    if 'status' in df.columns:
        df['status'] = df['status'].map({
            'draft':     '📋 임시저장',
            'submitted': '✅ 전송완료',
            'confirmed': '✔️ 확인완료',
        }).fillna(df['status'])

    show = [c for c in ['collect_date','item_type','weight','driver','status','memo']
            if c in df.columns]
    st.dataframe(df[show], use_container_width=True, hide_index=True)
    st.metric("합계", f"{df['weight'].sum():,.1f} kg")


def _render_settlement(school):
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                             index=[2024,2025,2026].index(CURRENT_YEAR)
                             if CURRENT_YEAR in [2024,2025,2026] else 2,
                             key="sch_set_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)), index=CURRENT_MONTH-1, key="sch_set_month")

    month_str = str(month).zfill(2)
    rows = [r for r in filter_rows_by_school(db_get('real_collection'), school)
            if str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    if not rows:
        st.info("해당 기간 정산 데이터가 없습니다.")
        return

    total_weight = sum(float(r.get('weight', 0)) for r in rows)
    total_amount = sum(float(r.get('weight', 0)) * float(r.get('unit_price', 0)) for r in rows)
    vat = total_amount * 0.1

    st.markdown(f"### {year}년 {month}월 정산 내역")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with c2:
        st.metric("공급가액", f"{total_amount:,.0f} 원")
    with c3:
        st.metric("합계금액 (VAT포함)", f"{total_amount + vat:,.0f} 원")

    # 품목별 내역
    df = pd.DataFrame(rows)
    if 'item_type' in df.columns:
        by_item = df.groupby('item_type')['weight'].sum().reset_index()
        by_item.columns = ['품목', '수거량(kg)']
        st.dataframe(by_item, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# ESG 보고서 탭 (추가 - 기존 코드 유지)
# ─────────────────────────────────────────────────────────────────────────────

def _render_esg(school: str):
    """학교 ESG 보고서 탭"""
    st.markdown("### 🌿 ESG 폐기물 수거 실적보고서")

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR)
                            if CURRENT_YEAR in [2024,2025,2026] else 2,
                            key="sch_esg_year")
    with col2:
        month_opt = st.selectbox("기간", ['전체'] + [f"{m}월" for m in range(1, 13)],
                                 key="sch_esg_month")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)

    # 데이터 필터
    all_rows = filter_rows_by_school(db_get('real_collection'), school)
    rows = [r for r in all_rows if str(r.get('collect_date', '')).startswith(str(year))]

    if month_opt != '전체':
        m_num = int(month_opt.replace('월', ''))
        m_str = str(m_num).zfill(2)
        rows  = [r for r in rows if f"-{m_str}-" in str(r.get('collect_date', ''))]

    month_label = f"{year}년 {month_opt}" if month_opt != '전체' else f"{year}년 전체"

    if not rows:
        st.info("해당 기간 수거 데이터가 없습니다.")
        return

    # 지표 계산 (화면 미리보기)
    food_kg    = sum(float(r.get('weight', 0)) for r in rows
                     if str(r.get('item_type', r.get('재활용방법', ''))).startswith('음식물'))
    recycle_kg = sum(float(r.get('weight', 0)) for r in rows
                     if '재활용' in str(r.get('item_type', r.get('재활용방법', ''))))
    general_kg = sum(float(r.get('weight', 0)) for r in rows
                     if '사업장' in str(r.get('item_type', r.get('재활용방법', ''))) or
                        '일반' in str(r.get('item_type', r.get('재활용방법', ''))))
    total_kg   = sum(float(r.get('weight', 0)) for r in rows)
    carbon     = food_kg * 0.47 + recycle_kg * 0.21 + general_kg * 0.09
    pine       = carbon / 4.6
    trees      = carbon / 6.6

    # 핵심 지표 카드 미리보기
    st.markdown("#### 핵심 환경 성과 미리보기")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 수거량", f"{total_kg:,.0f} kg")
    with c2:
        st.metric("탄소 감축량", f"{carbon:,.1f} kgCO₂")
    with c3:
        st.metric("🌲 소나무 환산", f"{pine:,.1f} 그루")
    with c4:
        st.metric("나무 환산", f"{trees:,.1f} 그루")

    st.info(f"💡 이 기간 분리수거로 **소나무 {pine:,.1f}그루**가 1년간 흡수하는 CO₂와 동일한 양을 감축했습니다.\n"
            f"(국립산림과학원 기준: 소나무 1그루 연간 4.6 kgCO₂ 흡수)")

    st.divider()

    # PDF 생성 버튼
    st.markdown("#### PDF 보고서 다운로드")
    vendor = st.text_input("수거 업체명", value="하영자원", key="sch_esg_vendor")

    if st.button("📄 ESG 보고서 PDF 생성", key="sch_esg_pdf_btn", type="primary"):
        try:
            from services.pdf_generator import generate_school_esg_pdf
            pdf_bytes = generate_school_esg_pdf(
                school_name=school,
                year=year,
                month_label=month_label,
                rows=rows,
                vendor=vendor,
            )
            st.download_button(
                label="⬇️ PDF 다운로드",
                data=pdf_bytes,
                file_name=f"ESG보고서_{school}_{month_label.replace(' ','_')}.pdf",
                mime="application/pdf",
                key="sch_esg_download",
            )
            st.success("✅ ESG 보고서가 생성되었습니다.")
        except Exception as e:
            st.error(f"PDF 생성 오류: {e}")
