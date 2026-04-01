# modules/meal_manager/statement_tab.py
# 단체급식 담당 — 월말명세서 생성/다운로드
import streamlit as st
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from database.db_manager import (
    analyze_meal_waste, get_meal_menus, get_meal_analysis,
)
from services.pdf_generator import generate_meal_statement_pdf
from config.settings import COMMON_CSS


def render_statement_tab(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.title("📄 월말명세서")

    site_name = _get_site_name(user)
    if not site_name:
        st.warning("담당 거래처가 설정되지 않았습니다.")
        return

    st.caption(f"📍 {site_name}")

    # ── 월 선택 ──
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    month_options = []
    for delta in range(-6, 1):
        m = now.month + delta
        y = now.year
        if m < 1:
            m += 12
            y -= 1
        month_options.append(f"{y}-{m:02d}")
    month_options.reverse()

    sel_month = st.selectbox("명세서 월 선택", month_options, index=0,
                             key="stmt_month")

    year = int(sel_month[:4])
    month = int(sel_month[5:7])

    # ── 데이터 확인 ──
    menus = get_meal_menus(site_name, sel_month)
    if not menus:
        st.warning(f"{sel_month} 등록된 식단이 없습니다. '식단 등록'에서 먼저 식단을 등록하세요.")
        return

    # 실시간 분석 (기사 수거량 즉시 반영)
    analysis = analyze_meal_waste(site_name, sel_month)

    if not analysis:
        st.info("아직 수거 데이터가 없습니다. 기사가 수거량을 입력하면 자동 반영됩니다.")
        return

    # ── 간략 요약 ──
    matched = len([r for r in analysis if float(r.get('waste_kg', 0) or 0) > 0])
    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in analysis)
    st.success(f"✅ {sel_month}: 식단 {len(menus)}일 / 수거매칭 {matched}일 / 총 잔반 {total_waste:.1f}kg")

    # ── 메뉴별 순위 계산 ──
    menu_ranking = _build_menu_ranking(analysis)

    # ── AI 추천식단 (이전에 생성한 것이 있으면) ──
    ai_rec = st.session_state.get('_ai_recommendation', None)
    ai_meals = None
    if ai_rec and ai_rec.get('meals'):
        ai_meals = ai_rec['meals']
        st.info(f"💡 AI 추천식단이 포함됩니다 ({len(ai_meals)}일)")

    st.divider()

    # ── PDF 생성/다운로드 버튼 ──
    bc1, bc2 = st.columns(2)

    with bc1:
        if st.button("📄 명세서 생성 (잔반분석만)", type="primary",
                     key="stmt_gen_basic", use_container_width=True):
            with st.spinner("PDF 생성 중..."):
                pdf_bytes = generate_meal_statement_pdf(
                    site_name=site_name,
                    year=year, month=month,
                    analysis_rows=analysis,
                    menu_ranking=menu_ranking,
                    ai_recommendation=None,
                )
                st.session_state['_stmt_pdf'] = pdf_bytes
                st.session_state['_stmt_filename'] = f"급식명세서_{site_name}_{sel_month}.pdf"
                st.success("✅ 명세서 생성 완료!")

    with bc2:
        if ai_meals:
            if st.button("📄 명세서 생성 (AI추천 포함)", key="stmt_gen_ai",
                         use_container_width=True):
                with st.spinner("PDF 생성 중..."):
                    pdf_bytes = generate_meal_statement_pdf(
                        site_name=site_name,
                        year=year, month=month,
                        analysis_rows=analysis,
                        menu_ranking=menu_ranking,
                        ai_recommendation=ai_meals,
                    )
                    st.session_state['_stmt_pdf'] = pdf_bytes
                    st.session_state['_stmt_filename'] = f"급식명세서_{site_name}_{sel_month}_AI추천포함.pdf"
                    st.success("✅ 명세서 생성 완료 (AI 추천 포함)!")
        else:
            st.info("AI 추천식단을 먼저 생성하면\n여기에 포함할 수 있습니다.")

    # ── 다운로드 버튼 ──
    pdf_bytes = st.session_state.get('_stmt_pdf', None)
    filename = st.session_state.get('_stmt_filename', '')
    if pdf_bytes:
        st.divider()
        st.download_button(
            label="⬇️ PDF 다운로드",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key="stmt_download",
            use_container_width=True,
        )


def _build_menu_ranking(analysis_rows):
    """분석 데이터에서 메뉴별 통계"""
    menu_waste = {}
    for r in analysis_rows:
        wpp = float(r.get('waste_per_person', 0) or 0)
        if wpp <= 0:
            continue
        try:
            menus = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menus = []
        for m in menus:
            if m not in menu_waste:
                menu_waste[m] = []
            menu_waste[m].append(wpp)

    ranking = []
    for menu, wastes in menu_waste.items():
        avg = sum(wastes) / len(wastes)
        ranking.append({'menu': menu, 'avg_waste': avg, 'count': len(wastes)})

    ranking.sort(key=lambda x: x['avg_waste'])
    return {
        'good': ranking[:20],
        'bad': list(reversed(ranking))[:20],
    }


def _get_site_name(user: dict) -> str:
    schools = user.get('schools', '')
    if schools:
        return schools.split(',')[0].strip()
    vendor = user.get('vendor', '')
    if vendor:
        return vendor
    return ''
