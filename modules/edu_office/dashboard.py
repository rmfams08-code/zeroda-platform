# modules/edu_office/dashboard.py
import streamlit as st
import pandas as pd
from database.db_manager import db_get, get_all_schools, get_all_vendors, filter_rows_by_school
from services.carbon_calculator import calculate_from_rows
from config.settings import CURRENT_YEAR, CURRENT_MONTH


def render_dashboard(user):
    st.markdown("## 교육청 - 학교 수거 현황")

    # 새로고침 버튼
    col_r, _ = st.columns([1, 5])
    with col_r:
        if st.button("🔄 새로고침", key="edu_dash_refresh"):
            try:
                from services.github_storage import _github_get_cached
                _github_get_cached.clear()
            except Exception:
                pass
            st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "전체 현황", "학교별 조회", "업체별 현황", "🌿 탄소감축 현황",
        "📊 ESG 종합 보고서", "🛡️ 안전관리 현황"
    ])

    with tab1:
        _render_overview()

    with tab2:
        _render_by_school()

    with tab3:
        _render_by_vendor()

    with tab4:
        _render_carbon()

    with tab5:
        _render_esg_report()

    with tab6:
        _render_safety()


def _render_overview():
    schools  = get_all_schools()
    all_rows = db_get('real_collection')

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("관할 학교 수", f"{len(schools)}개")
    with c2:
        total = sum(float(r.get('weight', 0)) for r in all_rows)
        st.metric("누적 수거량", f"{total:,.0f} kg")
    with c3:
        this = [r for r in all_rows if f"-{str(CURRENT_MONTH).zfill(2)}-" in str(r.get('collect_date', ''))]
        st.metric(f"{CURRENT_MONTH}월 수거량", f"{sum(float(r.get('weight',0)) for r in this):,.0f} kg")
    with c4:
        vendors = get_all_vendors()
        st.metric("등록 업체 수", f"{len(vendors)}개")

    st.divider()
    st.markdown("### 학교별 수거 현황")

    if not all_rows:
        st.info("수거 데이터가 없습니다.")
        return

    df = pd.DataFrame(all_rows)
    if 'school_name' in df.columns and 'weight' in df.columns:
        summary = df.groupby('school_name')['weight'].agg(['sum','count']).reset_index()
        summary.columns = ['학교명', '총수거량(kg)', '수거횟수']
        summary = summary.sort_values('총수거량(kg)', ascending=False)
        st.dataframe(summary, use_container_width=True, hide_index=True)


def _render_by_school():
    schools = get_all_schools()
    if not schools:
        st.info("등록된 학교가 없습니다.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        school = st.selectbox("학교 선택", schools, key="edu_school")
    with col2:
        year = st.selectbox("연도", [2024, 2025, 2026], key="edu_year")
    with col3:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="edu_month")

    rows = filter_rows_by_school(db_get('real_collection'), school)

    if month != '전체':
        month_str = str(month).zfill(2)
        rows = [r for r in rows if str(r.get('collect_date', '')).startswith(f"{year}-{month_str}")]

    if not rows:
        st.info("해당 조건의 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    show = [c for c in ['collect_date','vendor','item_type','weight','driver'] if c in df.columns]
    st.dataframe(df[show].sort_values('collect_date', ascending=False) if 'collect_date' in df.columns else df[show],
                 use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")
    with c2:
        st.metric("수거 횟수", f"{len(df)}회")


def _render_by_vendor():
    vendors = get_all_vendors()
    if not vendors:
        st.info("등록된 업체가 없습니다.")
        return

    col1, col2 = st.columns(2)
    with col1:
        vendor = st.selectbox("업체 선택", vendors, key="edu_vendor")
    with col2:
        year = st.selectbox("연도", [2024, 2025, 2026], key="edu_vendor_year")

    rows = [r for r in db_get('real_collection')
            if r.get('vendor') == vendor
            and str(r.get('collect_date', '')).startswith(str(year))]

    if not rows:
        st.info("해당 업체의 데이터가 없습니다.")
        return

    df = pd.DataFrame(rows)
    st.metric("총 수거량", f"{df['weight'].sum():,.1f} kg")

    if 'school_name' in df.columns:
        by_school = df.groupby('school_name')['weight'].sum().reset_index()
        by_school.columns = ['학교명', '수거량(kg)']
        by_school = by_school.sort_values('수거량(kg)', ascending=False)
        st.dataframe(by_school, use_container_width=True, hide_index=True)


def _render_carbon():
    st.markdown("### 탄소배출 감축 현황")

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR) if CURRENT_YEAR in [2024,2025,2026] else 1,
                            key="edu_cb_year")
    with col2:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="edu_cb_month")

    rows = [r for r in db_get('real_collection')
            if str(r.get('collect_date', '')).startswith(str(year))]
    if month != '전체':
        m = str(month).zfill(2)
        rows = [r for r in rows if f"-{m}-" in str(r.get('collect_date', ''))]

    if not rows:
        st.info("해당 기간 데이터가 없습니다.")
        return

    result = calculate_from_rows(rows)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total_kg = result['food_kg'] + result['recycle_kg'] + result['general_kg']
        st.metric("총 수거량", f"{total_kg:,.0f} kg")
    with c2:
        st.metric("탄소 감축량", f"{result['carbon_reduced']:,.1f} kg CO₂")
    with c3:
        st.metric("나무 식재 환산", f"{result['tree_equivalent']:,.0f} 그루")
    with c4:
        st.metric("CO₂ 톤 환산", f"{result['carbon_reduced']/1000:,.2f} tCO₂")

    st.divider()
    st.markdown("#### 학교별 탄소감축 순위")
    from collections import defaultdict
    by_school = defaultdict(list)
    for r in rows:
        sn = r.get('school_name', '')
        if sn:
            by_school[sn].append(r)

    ranking = []
    for school, school_rows in by_school.items():
        res = calculate_from_rows(school_rows)
        ranking.append({
            '학교명': school,
            '탄소감축(kg CO₂)': res['carbon_reduced'],
            '나무환산(그루)': res['tree_equivalent'],
        })

    if ranking:
        df = pd.DataFrame(ranking).sort_values('탄소감축(kg CO₂)', ascending=False).reset_index(drop=True)
        df.index += 1
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index('학교명')['탄소감축(kg CO₂)'])


# ─────────────────────────────────────────────────────────────────────────────
# ESG 종합 보고서 탭 (신규 추가)
# ─────────────────────────────────────────────────────────────────────────────

def _render_esg_report():
    """교육청 ESG 종합 보고서 탭"""
    st.markdown("### 📊 ESG 학교 폐기물 수거 종합 실적보고서")

    col1, col2, col3 = st.columns(3)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR)
                            if CURRENT_YEAR in [2024,2025,2026] else 2,
                            key="edu_esg_year")
    with col2:
        month_opt = st.selectbox("기간", ['전체'] + [f"{m}월" for m in range(1, 13)],
                                 key="edu_esg_month")
    with col3:
        edu_name = st.text_input("교육청명", value="경기도화성오산교육지원청", key="edu_esg_name")

    # 데이터 준비
    all_rows = db_get('real_collection')
    rows = [r for r in all_rows if str(r.get('collect_date', '')).startswith(str(year))]

    if month_opt != '전체':
        m_num = int(month_opt.replace('월', ''))
        m_str = str(m_num).zfill(2)
        rows  = [r for r in rows if f"-{m_str}-" in str(r.get('collect_date', ''))]

    month_label = f"{year}년 {month_opt}" if month_opt != '전체' else f"{year}년 전체"

    if not rows:
        st.info("해당 기간 수거 데이터가 없습니다.")
        return

    # 전체 지표
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

    # 관할 학교 수
    school_names = sorted(set(r.get('school_name', '') for r in rows if r.get('school_name')))

    # 핵심 지표 미리보기
    st.markdown("#### 관할 전체 핵심 성과 미리보기")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("관할 학교 수", f"{len(school_names)}개교")
    with c2:
        st.metric("총 수거량", f"{total_kg:,.0f} kg")
    with c3:
        st.metric("탄소 감축량", f"{carbon:,.1f} kgCO₂")
    with c4:
        st.metric("🌲 소나무 환산", f"{pine:,.1f} 그루")
    with c5:
        st.metric("나무 환산", f"{trees:,.1f} 그루")

    st.success(
        f"🌲 관할 {len(school_names)}개 학교의 분리수거로 **소나무 {pine:,.1f}그루** 효과 달성!\n\n"
        f"탄소 감축 총량 {carbon:,.1f} kgCO₂ = 소나무 {pine:,.1f}그루 × 연간 흡수량 4.6 kgCO₂\n\n"
        f"(출처: 국립산림과학원)"
    )

    # 학교별 순위 미리보기
    st.markdown("#### 학교별 수거 순위")
    from collections import defaultdict
    by_school = defaultdict(list)
    for r in rows:
        sn = r.get('school_name', '')
        if sn:
            by_school[sn].append(r)

    rank_list = []
    for sch, s_rows in by_school.items():
        s_food    = sum(float(r.get('weight',0)) for r in s_rows
                        if str(r.get('item_type',r.get('재활용방법',''))).startswith('음식물'))
        s_rec     = sum(float(r.get('weight',0)) for r in s_rows
                        if '재활용' in str(r.get('item_type',r.get('재활용방법',''))))
        s_gen     = sum(float(r.get('weight',0)) for r in s_rows
                        if '사업장' in str(r.get('item_type',r.get('재활용방법',''))) or
                           '일반' in str(r.get('item_type',r.get('재활용방법',''))))
        s_total   = sum(float(r.get('weight',0)) for r in s_rows)
        s_carbon  = s_food * 0.47 + s_rec * 0.21 + s_gen * 0.09
        s_pine    = s_carbon / 4.6
        rank_list.append({
            '학교명': sch,
            '수거량(kg)': round(s_total, 1),
            '탄소감축(kgCO₂)': round(s_carbon, 1),
            '소나무환산(그루)': round(s_pine, 1),
            '수거횟수': len(s_rows),
        })

    if rank_list:
        df_rank = pd.DataFrame(rank_list).sort_values('수거량(kg)', ascending=False).reset_index(drop=True)
        df_rank.index += 1
        st.dataframe(df_rank, use_container_width=True)

    st.divider()

    # PDF 생성
    st.markdown("#### PDF 보고서 다운로드")
    vendor = st.text_input("수거 업체명", value="하영자원", key="edu_esg_vendor")

    if st.button("📄 ESG 종합 보고서 PDF 생성", key="edu_esg_pdf_btn", type="primary"):
        try:
            from services.pdf_generator import generate_edu_office_esg_pdf
            school_data = [
                {'school': sch, 'rows': s_rows}
                for sch, s_rows in by_school.items()
            ]
            pdf_bytes = generate_edu_office_esg_pdf(
                edu_office_name=edu_name,
                year=year,
                month_label=month_label,
                school_data=school_data,
                vendor=vendor,
            )
            st.download_button(
                label="⬇️ PDF 다운로드",
                data=pdf_bytes,
                file_name=f"ESG종합보고서_{edu_name}_{month_label.replace(' ','_')}.pdf",
                mime="application/pdf",
                key="edu_esg_download",
            )
            st.success("✅ ESG 종합 보고서가 생성되었습니다.")
        except Exception as e:
            st.error(f"PDF 생성 오류: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# 안전관리 현황 탭 (신규 추가)
# ─────────────────────────────────────────────────────────────────────────────

def _render_safety():
    """교육청 안전관리 현황 탭"""
    st.markdown("### 🛡️ 학교별 안전관리 현황")

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR)
                            if CURRENT_YEAR in [2024,2025,2026] else 2,
                            key="edu_safety_year")
    with col2:
        month = st.selectbox("월", ['전체'] + list(range(1, 13)), key="edu_safety_month")

    # 안전교육 이수 현황
    st.markdown("#### 안전교육 이수 현황")
    edu_data = db_get('safety_education')
    if edu_data:
        rows = [r for r in edu_data if str(r.get('edu_date', '')).startswith(str(year))]
        if month != '전체':
            m_str = str(month).zfill(2)
            rows  = [r for r in rows if f"-{m_str}-" in str(r.get('edu_date', ''))]

        if rows:
            df = pd.DataFrame(rows)
            show = [c for c in ['edu_date','vendor','driver','subject','status'] if c in df.columns]
            st.dataframe(df[show] if show else df, use_container_width=True, hide_index=True)
            st.metric("교육 이수 건수", f"{len(rows)}건")
        else:
            st.info("해당 기간 안전교육 데이터가 없습니다.")
    else:
        st.info("안전교육 데이터가 없습니다.")

    st.divider()

    # 차량점검 체크리스트 현황
    st.markdown("#### 차량 점검 현황")
    check_data = db_get('safety_checklist')
    if check_data:
        rows2 = [r for r in check_data if str(r.get('check_date', '')).startswith(str(year))]
        if month != '전체':
            m_str = str(month).zfill(2)
            rows2 = [r for r in rows2 if f"-{m_str}-" in str(r.get('check_date', ''))]

        if rows2:
            df2 = pd.DataFrame(rows2)
            show2 = [c for c in ['check_date','vendor','driver','vehicle','result'] if c in df2.columns]
            st.dataframe(df2[show2] if show2 else df2, use_container_width=True, hide_index=True)
            st.metric("점검 건수", f"{len(rows2)}건")
        else:
            st.info("해당 기간 차량점검 데이터가 없습니다.")
    else:
        st.info("차량점검 데이터가 없습니다.")

    st.divider()

    # 사고 보고 현황
    st.markdown("#### 사고 보고 현황")
    accident_data = db_get('accident_report')
    if accident_data:
        rows3 = [r for r in accident_data if str(r.get('accident_date', '')).startswith(str(year))]
        if month != '전체':
            m_str = str(month).zfill(2)
            rows3 = [r for r in rows3 if f"-{m_str}-" in str(r.get('accident_date', ''))]

        if rows3:
            df3 = pd.DataFrame(rows3)
            show3 = [c for c in ['accident_date','vendor','driver','type','description','status']
                     if c in df3.columns]
            st.dataframe(df3[show3] if show3 else df3, use_container_width=True, hide_index=True)
            st.metric("사고 보고 건수", f"{len(rows3)}건")
        else:
            st.info("해당 기간 사고 보고 없음 ✅")
    else:
        st.info("사고 보고 데이터가 없습니다.")
