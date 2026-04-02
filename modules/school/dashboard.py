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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📊 월별 현황", "📋 수거 내역", "💰 정산 확인", "🌿 ESG 보고서", "🛡️ 안전관리보고서"])

    with tab1:
        _render_monthly(school)

    with tab2:
        _render_detail(school)

    with tab3:
        _render_settlement(school)

    with tab4:
        _render_esg(school)

    with tab5:
        _render_safety_report(school)


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


# ─────────────────────────────────────────────────────────────────────────────
# 안전관리보고서 탭 (FEAT: 학교 안전관리 현황 + PDF 다운로드)
# ─────────────────────────────────────────────────────────────────────────────

def _render_safety_report(school: str):
    """학교 안전관리보고서 탭 — 현황 조회 + PDF 다운로드"""
    st.markdown("### 🛡️ 안전관리 보고서")
    st.caption("중대재해예방점검 서류 기반 월간 안전관리 보고서를 조회·다운로드할 수 있습니다.")

    from database.db_manager import (db_get, get_safety_scores, get_violations,
                                     get_vendors_by_school, calculate_safety_score)

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("연도", [2024, 2025, 2026],
                            index=[2024,2025,2026].index(CURRENT_YEAR)
                            if CURRENT_YEAR in [2024,2025,2026] else 2,
                            key="sch_safety_year")
    with col2:
        month = st.selectbox("월", list(range(1, 13)),
                             index=CURRENT_MONTH - 1, key="sch_safety_month")

    year_month = f"{year}-{str(month).zfill(2)}"

    # ── 안전관리 등급 현황 ────────────────────────────────────────────────
    st.markdown("#### 📊 업체별 안전관리 등급")

    _GRADE_EMOJI = {'S': '⭐ S등급', 'A': '✅ A등급', 'B': '⚠️ B등급',
                    'C': '🔶 C등급', 'D': '🚨 D등급'}
    _GRADE_COLOR = {'S': '#1565C0', 'A': '#2D7D46', 'B': '#F9A825',
                    'C': '#E07B39', 'D': '#C0392B'}
    _GRADE_BG    = {'S': '#E3F2FD', 'A': '#E8F5E9', 'B': '#FFFDE7',
                    'C': '#FFF3E0', 'D': '#FFEBEE'}

    # 담당 수거업체만 조회
    my_vendors = get_vendors_by_school(school)

    scores = get_safety_scores(year_month=year_month)
    if not scores:
        for v in (my_vendors or []):
            calculate_safety_score(v, year_month)
        scores = get_safety_scores(year_month=year_month)

    # 담당 업체만 필터링
    if scores and my_vendors:
        scores = [s for s in scores if s.get('vendor') in my_vendors]

    if scores:
        cols = st.columns(min(len(scores), 4))
        for i, sc in enumerate(scores):
            grade = sc.get('grade', 'D')
            with cols[i % len(cols)]:
                st.markdown(
                    f"<div style='background:{_GRADE_BG.get(grade,'#f5f5f5')};"
                    f"border-left:5px solid {_GRADE_COLOR.get(grade,'#999')};"
                    f"padding:12px;border-radius:6px;margin-bottom:8px;'>"
                    f"<div style='font-size:13px;color:#555;'>{sc.get('vendor','')}</div>"
                    f"<div style='font-size:20px;font-weight:bold;"
                    f"color:{_GRADE_COLOR.get(grade,'#333')};'>"
                    f"{_GRADE_EMOJI.get(grade, grade)}</div>"
                    f"<div style='font-size:22px;font-weight:900;"
                    f"color:{_GRADE_COLOR.get(grade,'#333')};'>"
                    f"{sc.get('total_score',0):.0f}점</div>"
                    f"</div>", unsafe_allow_html=True
                )
    else:
        st.info("안전관리 평가 데이터가 없습니다.")

    st.divider()

    # ── 스쿨존 위반 이력 ──────────────────────────────────────────────────
    st.markdown("#### 🚨 스쿨존 위반 이력")
    violations = get_violations(year_month=year_month)
    # 담당 업체만 필터링
    if violations and my_vendors:
        violations = [v for v in violations if v.get('vendor') in my_vendors]
    if violations:
        df_v = pd.DataFrame(violations)
        show_v = [c for c in ['violation_date','vendor','driver','violation_type',
                               'location','fine_amount'] if c in df_v.columns]
        rename_v = {
            'violation_date': '위반일', 'vendor': '업체', 'driver': '기사',
            'violation_type': '유형', 'location': '장소', 'fine_amount': '과태료(원)',
        }
        st.dataframe(df_v[show_v].rename(columns=rename_v), use_container_width=True,
                     hide_index=True)
        st.metric("위반 건수", f"{len(violations)}건")
    else:
        st.info("해당 기간 스쿨존 위반 기록 없음")

    st.divider()

    # ── 안전교육 / 차량점검 요약 ──────────────────────────────────────────
    st.markdown("#### 📋 안전교육·차량점검 현황")
    m_str = str(month).zfill(2)

    edu_data = db_get('safety_education')
    edu_rows = [r for r in (edu_data or [])
                if str(r.get('edu_date', '')).startswith(f"{year}-{m_str}")
                and (not my_vendors or r.get('vendor') in my_vendors)]

    check_data = db_get('safety_checklist')
    check_rows = [r for r in (check_data or [])
                  if str(r.get('check_date', '')).startswith(f"{year}-{m_str}")
                  and (not my_vendors or r.get('vendor') in my_vendors)]

    accident_data = db_get('accident_report')
    accident_rows = [r for r in (accident_data or [])
                     if str(r.get('accident_date', '')).startswith(f"{year}-{m_str}")
                     and (not my_vendors or r.get('vendor') in my_vendors)]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("안전교육 이수", f"{len(edu_rows)}건")
    with c2:
        st.metric("차량점검 건수", f"{len(check_rows)}건")
    with c3:
        st.metric("사고 보고", f"{len(accident_rows)}건")

    st.divider()

    # ── 안전보건 점검 체크리스트 (HWP 기반) ──────────────────────────────
    st.markdown("#### ✅ 안전보건 점검 체크리스트")
    st.caption("중대재해예방점검 서류 기반 7개 항목입니다. PDF 보고서에 반영됩니다.")

    checklist_items = [
        "과업지시서(또는 계약서)에 '안전관리 및 예방조치 후 작업' 실시 내용 포함",
        "공사(용역)업체에서 근로자에 대한 안전보건교육 실시",
        "안전보호구(안전모, 안전대, 안전화 등) 착용 주지",
        "위험사항(위험성평가 등)과 기계·기구·설비 안전점검 안내",
        "학교 현장 이동 시 행정실(담당자) 안내 주지",
        "유해·위험 작업 시 안전보건 점검표 제출 여부",
        "안전·보건에 관한 종사자 의견청취 실시",
    ]

    checklist_results = []
    for idx, item in enumerate(checklist_items):
        result = st.radio(
            f"{idx+1}. {item}",
            ['예', '아니오'],
            horizontal=True,
            key=f"sch_safety_cl_{idx}",
        )
        checklist_results.append(result)

    st.divider()

    # ── PDF 다운로드 ──────────────────────────────────────────────────────
    st.markdown("#### 📄 안전관리보고서 PDF 다운로드")
    # 담당 업체명 자동 표시
    from database.db_manager import get_vendor_name
    default_vendor_name = "하영자원"
    if my_vendors:
        default_vendor_name = get_vendor_name(my_vendors[0])
    vendor_name = st.text_input("수거(용역) 업체명", value=default_vendor_name,
                                key="sch_safety_vendor")

    if st.button("📄 안전관리보고서 PDF 생성", key="sch_safety_pdf_btn", type="primary"):
        try:
            from services.pdf_generator import generate_safety_report_pdf
            pdf_bytes = generate_safety_report_pdf(
                org_name=school,
                org_type='school',
                year=year,
                month=month,
                vendor_scores=scores or [],
                violations=violations or [],
                education_records=edu_rows,
                checklist_records=check_rows,
                accident_records=accident_rows,
                vendor_name=vendor_name,
                checklist_results=checklist_results,
            )
            st.download_button(
                label="⬇️ PDF 다운로드",
                data=pdf_bytes,
                file_name=f"안전관리보고서_{school}_{year}년{month}월.pdf",
                mime="application/pdf",
                key="sch_safety_download",
            )
            st.success("✅ 안전관리보고서가 생성되었습니다.")
        except Exception as e:
            st.error(f"PDF 생성 오류: {e}")
