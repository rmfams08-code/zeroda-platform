# modules/meal_manager/waste_analysis.py
# 단체급식 담당 — 잔반량 분석 (식단↔수거량 매칭)
import streamlit as st
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from database.db_manager import (
    analyze_meal_waste, get_meal_menus, get_meal_analysis,
)
from config.settings import COMMON_CSS


def render_waste_analysis(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.title("📊 잔반 분석")

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

    sel_month = st.selectbox("분석 월 선택", month_options, index=0,
                             key="waste_month")

    # ── 등록된 식단 확인 ──
    menus = get_meal_menus(site_name, sel_month)
    if not menus:
        st.info(f"{sel_month} 등록된 식단이 없습니다. '식단 등록' 메뉴에서 먼저 식단을 등록하세요.")
        return

    st.success(f"{sel_month}: {len(menus)}일 식단 등록됨")

    # ── 등급 기준 안내 ──
    with st.expander("📏 잔반 등급 기준 (학교급식법 시행규칙 [별표 3])", expanded=False):
        st.markdown("""
| 등급 | 1인당 잔반량 | 판정 | 설명 |
|:---:|:---:|:---:|:---|
| **A** | 150g 미만 | 우수 | 잔반 최소화 달성 |
| **B** | 150~245g | 양호 | 혼합평균(245g) 이하 |
| **C** | 245~300g | 주의 | 표준 초과, 메뉴 조정 권장 |
| **D** | 300g 이상 | 경보 | 고잔반, 메뉴 구성 재검토 필요 |

*출처: 학교급식법 시행규칙 [별표 3] (교육부, 2021.01.29 개정)*
        """)

    # ── 실시간 자동 매칭 (페이지 진입 시 바로 실행) ──
    results = analyze_meal_waste(site_name, sel_month)

    # 수동 새로고침 버튼도 유지 (기사가 방금 입력한 경우)
    if st.button("🔄 새로고침", key="waste_refresh"):
        results = analyze_meal_waste(site_name, sel_month)

    if not results:
        st.info("아직 수거 데이터가 없습니다. 기사가 수거량을 입력하면 자동으로 반영됩니다.")
        return

    # ── 요약 카드 ──
    _render_summary(results)

    st.divider()

    # ── 일별 상세 테이블 ──
    _render_daily_table(results)

    st.divider()

    # ── 메뉴별 잔반 순위 ──
    _render_menu_ranking(results)


def _render_summary(results):
    """월간 요약 카드"""
    total_waste = sum(r.get('waste_kg', 0) for r in results)
    avg_per_person = 0
    valid_days = [r for r in results if r.get('waste_per_person', 0) > 0]
    if valid_days:
        avg_per_person = sum(r['waste_per_person'] for r in valid_days) / len(valid_days)

    grade_counts = {}
    for r in results:
        g = r.get('grade', '-')
        grade_counts[g] = grade_counts.get(g, 0) + 1

    matched_days = len([r for r in results if r.get('waste_kg', 0) > 0])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 잔반량", f"{total_waste:.1f} kg")
    with c2:
        st.metric("1인당 평균", f"{avg_per_person:.1f} g")
    with c3:
        st.metric("매칭 일수", f"{matched_days} / {len(results)}일")
    with c4:
        # 가장 많은 등급
        best_grade = max(grade_counts, key=grade_counts.get) if grade_counts else '-'
        st.metric("주요 등급", best_grade)


def _render_daily_table(results):
    """일별 상세 테이블"""
    st.subheader("📋 일별 상세")

    rows = []
    for r in results:
        try:
            menus = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menus = []
        menu_str = ", ".join(menus) if menus else "-"

        rows.append({
            '날짜': r.get('meal_date', ''),
            '메뉴': menu_str,
            '잔반량(kg)': round(r.get('waste_kg', 0), 1),
            '1인당(g)': round(r.get('waste_per_person', 0), 1),
            '등급': r.get('grade', '-'),
            '특이사항': r.get('remark', ''),
        })

    if rows:
        df = pd.DataFrame(rows)
        # 등급별 색상
        def _grade_color(val):
            colors = {'A': 'background-color: #e8f5e9',
                      'B': 'background-color: #fff3e0',
                      'C': 'background-color: #fff9c4',
                      'D': 'background-color: #ffebee',
                      '-': ''}
            return colors.get(val, '')

        st.dataframe(df.style.map(_grade_color, subset=['등급']),
                     use_container_width=True, hide_index=True)

        # 차트: 일별 잔반량 추이
        if any(r.get('waste_kg', 0) > 0 for r in results):
            chart_df = pd.DataFrame({
                '날짜': [r['meal_date'] for r in results],
                '잔반량(kg)': [r.get('waste_kg', 0) for r in results],
            })
            st.line_chart(chart_df.set_index('날짜'), use_container_width=True)


def _render_menu_ranking(results):
    """메뉴별 잔반 순위 (TOP 10)"""
    st.subheader("🏆 메뉴별 잔반 순위")

    menu_waste = {}  # {메뉴명: [waste_per_person 리스트]}
    for r in results:
        wpp = r.get('waste_per_person', 0)
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

    if not menu_waste:
        st.info("잔반 데이터가 부족하여 메뉴 순위를 표시할 수 없습니다.")
        return

    # 평균 잔반량 계산 + 정렬
    ranking = []
    for menu, wastes in menu_waste.items():
        avg = sum(wastes) / len(wastes)
        ranking.append({'메뉴': menu, '평균 1인당 잔반(g)': round(avg, 1),
                        '등장 횟수': len(wastes)})

    ranking.sort(key=lambda x: x['평균 1인당 잔반(g)'])

    t1, t2 = st.tabs(["✅ 잔반 적은 메뉴 (추천)", "⚠️ 잔반 많은 메뉴 (개선)"])

    with t1:
        good = ranking[:10]
        if good:
            st.dataframe(pd.DataFrame(good), use_container_width=True,
                         hide_index=True)
        else:
            st.info("데이터 없음")

    with t2:
        bad = list(reversed(ranking))[:10]
        if bad:
            st.dataframe(pd.DataFrame(bad), use_container_width=True,
                         hide_index=True)
        else:
            st.info("데이터 없음")


def _get_site_name(user: dict) -> str:
    schools = user.get('schools', '')
    if schools:
        return schools.split(',')[0].strip()
    vendor = user.get('vendor', '')
    if vendor:
        return vendor
    return ''
