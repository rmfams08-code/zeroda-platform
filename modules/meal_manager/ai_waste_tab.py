# modules/meal_manager/ai_waste_tab.py
# 단체급식 담당 — AI잔반분석 (4탭: 잔반요약 / 메뉴별상세 / AI분석생성 / AI월말명세서)
# Claude API 기반 잔반 패턴 분석 + 추천식단 생성 + AI 월말명세서
# v2.0 — 비용절감 효과, 이상치 탐지, 요일패턴, 메뉴조합, 배식인원 대비 분석 추가
import streamlit as st
import json
import re
import os
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from database.db_manager import (
    analyze_meal_waste, get_meal_menus, get_meal_analysis,
    save_meal_menu, get_school_student_count,
    get_unit_price, db_get,
)
from services.pdf_generator import (
    generate_meal_statement_pdf,
    generate_ai_meal_statement_pdf,
)
from config.settings import COMMON_CSS


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 요일 / 계절 상수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEEKDAY_KR = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}


def render_ai_waste_tab(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.title("🤖 AI잔반분석")

    site_name = _get_site_name(user)
    if not site_name:
        st.warning("담당 거래처가 설정되지 않았습니다.")
        return

    st.caption(f"📍 {site_name}")

    # ── 4탭 구성 ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 잔반요약", "📋 메뉴별상세", "🤖 AI분석생성", "📄 AI월말명세서"
    ])

    now = datetime.now(ZoneInfo('Asia/Seoul'))

    # ── 과거 6개월 데이터 수집 (공통) ──
    past_months = []
    for delta in range(-6, 0):
        m = now.month + delta
        y = now.year
        if m < 1:
            m += 12
            y -= 1
        past_months.append(f"{y}-{m:02d}")
    past_months.reverse()

    all_analysis = []
    months_with_data = []
    for pm in past_months:
        rows = analyze_meal_waste(site_name, pm)
        if rows and any(float(r.get('waste_kg', 0) or 0) > 0 for r in rows):
            all_analysis.extend(rows)
            months_with_data.append(pm)

    with tab1:
        _render_summary_tab(all_analysis, months_with_data, site_name, user)

    with tab2:
        _render_detail_tab(all_analysis, site_name, user)

    with tab3:
        _render_ai_analysis_tab(user, site_name, all_analysis, months_with_data)

    with tab4:
        _render_ai_statement_tab(user, site_name, all_analysis, months_with_data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: 잔반요약 + AI 인사이트 + 비용절감 + 이상치 + 요일패턴
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_summary_tab(all_analysis, months_with_data, site_name, user):
    if not all_analysis:
        st.info("아직 잔반 분석 데이터가 없습니다.\n"
                "식단을 등록하고 기사가 수거량을 입력하면 자동으로 데이터가 쌓입니다.")
        return

    st.subheader("📊 잔반 데이터 요약")
    st.caption(f"데이터 기간: {months_with_data[0]} ~ {months_with_data[-1]} ({len(months_with_data)}개월)")

    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in all_analysis)
    valid = [r for r in all_analysis if float(r.get('waste_per_person', 0) or 0) > 0]
    avg_pp = sum(float(r['waste_per_person']) for r in valid) / len(valid) if valid else 0
    total_days = len(all_analysis)
    matched = len([r for r in all_analysis if float(r.get('waste_kg', 0) or 0) > 0])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("총 잔반량", f"{total_waste:.1f} kg")
    with c2:
        st.metric("1인당 평균", f"{avg_pp:.1f} g")
    with c3:
        st.metric("분석 일수", f"{matched} / {total_days}일")
    with c4:
        data_score = "충분" if len(months_with_data) >= 3 else ("보통" if len(months_with_data) >= 2 else "부족")
        st.metric("데이터 충분도", data_score)

    # ── 비용 절감 효과 (신규) ──
    cost_info = _calc_cost_savings(site_name, user, all_analysis, months_with_data)
    if cost_info and cost_info.get('unit_price', 0) > 0:
        st.divider()
        st.markdown("""
        <div style="background:linear-gradient(135deg,#00c853,#00bfa5);
                    padding:14px;border-radius:10px;color:white;">
            <div style="font-size:14px;font-weight:700;">💰 비용 절감 효과</div>
        </div>
        """, unsafe_allow_html=True)

        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            st.metric("처리 단가", f"{cost_info['unit_price']:,.0f} 원/kg")
        with cc2:
            st.metric("이번 기간 처리비", f"{cost_info['current_cost']:,.0f} 원")
        with cc3:
            if cost_info.get('prev_cost', 0) > 0:
                delta_val = cost_info['mom_save']
                st.metric("전월 대비", f"{abs(delta_val):,.0f} 원",
                          delta=f"{'절감' if delta_val > 0 else '증가'}",
                          delta_color="normal" if delta_val > 0 else "inverse")
            else:
                st.metric("전월 대비", "데이터 없음")
        with cc4:
            st.metric("10% 감소 시 절감", f"{cost_info.get('save_amount', 0):,.0f} 원/월")

        if cost_info.get('save_amount', 0) > 0:
            yearly = cost_info['save_amount'] * 12
            st.info(f"💡 잔반량을 10% 줄이면 **연간 약 {yearly:,.0f}원** 절감이 가능합니다.")

    # ── 월별 추이 차트 ──
    if len(months_with_data) >= 2:
        st.subheader("📈 월별 잔반량 추이")
        monthly = {}
        for r in all_analysis:
            ym = r.get('year_month', '') or r.get('meal_date', '')[:7]
            if ym:
                monthly[ym] = monthly.get(ym, 0) + float(r.get('waste_kg', 0) or 0)
        if monthly:
            chart_df = pd.DataFrame(
                [{'월': k, '잔반량(kg)': v} for k, v in sorted(monthly.items())]
            )
            st.bar_chart(chart_df.set_index('월'), use_container_width=True)

    # 등급 분포
    grade_counts = {}
    for r in all_analysis:
        g = r.get('grade', '-')
        if g != '-':
            grade_counts[g] = grade_counts.get(g, 0) + 1
    if grade_counts:
        st.subheader("📊 등급 분포")
        grade_df = pd.DataFrame(
            [{'등급': k, '일수': v} for k, v in sorted(grade_counts.items())]
        )
        st.bar_chart(grade_df.set_index('등급'), use_container_width=True)

    # ── 요일별 잔반 패턴 (신규) ──
    weekday_data = _build_weekday_pattern(all_analysis)
    if weekday_data and weekday_data.get('data'):
        st.subheader("📅 요일별 잔반 패턴")
        wd_rows = []
        for wd in weekday_data['data']:
            wd_rows.append({
                '요일': wd['weekday_name'] + '요일',
                '평균 잔반(kg)': round(wd['avg_kg'], 1),
                '평균 1인당(g)': round(wd['avg_pp'], 1),
                '수거 일수': wd['count'],
                '주요 메뉴': wd.get('top_menus', '-'),
            })
        wd_df = pd.DataFrame(wd_rows)
        st.dataframe(wd_df, use_container_width=True, hide_index=True)

        if weekday_data.get('insight'):
            st.info(weekday_data['insight'])

    # ── 이상치 탐지 (신규) ──
    anomalies = _detect_anomalies(all_analysis)
    if anomalies:
        st.subheader("🚨 이상치 탐지")
        st.caption("평소 대비 잔반량이 급증/급감한 날을 감지합니다.")
        for a in anomalies[:5]:
            z = a['z_score']
            icon = "🔴" if z > 0 else "🟢"
            direction = "급증" if z > 0 else "급감"
            st.markdown(
                f"{icon} **{a['date']}** — 잔반 {a['waste_kg']:.1f}kg "
                f"({direction}, Z={z:.2f}) | 메뉴: {a.get('menus', '-')}"
            )

    # ── AI 인사이트 (규칙기반 + 강화) ──
    if len(months_with_data) >= 2:
        st.divider()
        st.markdown("""
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);
                    padding:16px;border-radius:10px;color:white;">
            <div style="font-size:15px;font-weight:700;">🤖 AI 인사이트</div>
            <div style="font-size:13px;margin-top:8px;opacity:0.95;">
                더 상세한 AI 분석은 <b>'AI분석생성'</b> 탭에서 Claude API를 통해 확인할 수 있습니다.
            </div>
        </div>
        """, unsafe_allow_html=True)

        insights = []
        if avg_pp > 300:
            insights.append("⚠️ 1인당 평균 잔반량이 300g 이상입니다. 메뉴 구성 재검토가 필요합니다.")
        elif avg_pp > 245:
            insights.append("📌 1인당 평균 잔반량이 245g 이상입니다. 개선 여지가 있습니다.")
        elif avg_pp < 150:
            insights.append("✅ 1인당 평균 잔반량이 150g 미만으로 우수한 수준입니다.")

        if grade_counts.get('D', 0) > grade_counts.get('A', 0):
            insights.append("⚠️ D등급 일수가 A등급보다 많습니다. 잔반 많은 메뉴 교체를 권장합니다.")

        # 배식인원 대비 분석 (신규)
        servings_waste = _analyze_servings_efficiency(all_analysis)
        if servings_waste:
            insights.append(servings_waste)

        # 요일 패턴 인사이트
        if weekday_data and weekday_data.get('insight'):
            insights.append(weekday_data['insight'])

        if insights:
            for ins in insights:
                st.markdown(f"- {ins}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: 메뉴별 상세 + AI 원인분석 + 메뉴조합 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_detail_tab(all_analysis, site_name, user):
    if not all_analysis:
        st.info("분석 데이터가 없습니다.")
        return

    st.subheader("📋 메뉴별 잔반 분석")

    menu_stats = _build_menu_stats(all_analysis)

    # 잔반 적은 메뉴 TOP 10
    st.markdown("### ✅ 잔반 적은 메뉴 (추천 유지)")
    good = menu_stats.get('good', [])[:10]
    if good:
        df_good = pd.DataFrame([
            {'메뉴': m['menu'], '평균 잔반(g/인)': round(m['avg_waste'], 1),
             '등장 횟수': m['count']}
            for m in good
        ])
        st.dataframe(df_good, use_container_width=True, hide_index=True)
    else:
        st.info("데이터 부족")

    # 잔반 많은 메뉴 TOP 10
    st.markdown("### ⚠️ 잔반 많은 메뉴 (개선 필요)")
    bad = menu_stats.get('bad', [])[:10]
    if bad:
        df_bad = pd.DataFrame([
            {'메뉴': m['menu'], '평균 잔반(g/인)': round(m['avg_waste'], 1),
             '등장 횟수': m['count']}
            for m in bad
        ])
        st.dataframe(df_bad, use_container_width=True, hide_index=True)
    else:
        st.info("데이터 부족")

    # ── 메뉴 조합 분석 (신규) ──
    combo = _build_combo_analysis(all_analysis)
    if combo:
        st.divider()
        st.markdown("### 🔗 메뉴 조합 효과 분석")
        st.caption("같은 날 함께 제공된 메뉴 세트 단위로 잔반량을 분석합니다.")

        combo_good = [c for c in combo if c['avg_waste'] < 200][:5]
        combo_bad = [c for c in combo if c['avg_waste'] >= 245][:5]

        if combo_good:
            st.markdown("**✅ 잔반 적은 조합 TOP 5**")
            df_cg = pd.DataFrame([
                {'메뉴 조합': c['combo'], '평균 잔반(g/인)': round(c['avg_waste'], 1),
                 '등장 횟수': c['count']}
                for c in combo_good
            ])
            st.dataframe(df_cg, use_container_width=True, hide_index=True)

        if combo_bad:
            st.markdown("**⚠️ 잔반 많은 조합 TOP 5**")
            df_cb = pd.DataFrame([
                {'메뉴 조합': c['combo'], '평균 잔반(g/인)': round(c['avg_waste'], 1),
                 '등장 횟수': c['count']}
                for c in combo_bad
            ])
            st.dataframe(df_cb, use_container_width=True, hide_index=True)

    # ── 배식인원 대비 효율 분석 (신규) ──
    srv_analysis = _build_servings_analysis(all_analysis)
    if srv_analysis:
        st.divider()
        st.markdown("### 👥 배식인원 대비 잔반 효율")
        st.caption("배식인원 구간별 1인당 잔반량을 비교합니다.")
        df_srv = pd.DataFrame(srv_analysis)
        st.dataframe(df_srv, use_container_width=True, hide_index=True)

    # AI 원인분석 버튼
    st.divider()
    api_key = _get_api_key()
    if api_key and bad:
        st.markdown("#### 🤖 AI 원인분석")
        st.caption("잔반 많은 메뉴에 대해 AI가 원인을 분석하고 대체 메뉴를 제안합니다.")

        if st.button("🤖 잔반 원인 분석 요청", key="ai_cause_btn"):
            bad_list = "\n".join(
                f"- {m['menu']} (평균 잔반 {m['avg_waste']:.1f}g/인, {m['count']}회)"
                for m in bad[:10]
            )

            # 요일별 메뉴 패턴 추가 (신규 강화)
            weekday_info = _build_weekday_menu_text(all_analysis)

            # 메뉴 조합 정보 추가 (신규 강화)
            combo_text = ""
            if combo:
                combo_bad_items = [c for c in combo if c['avg_waste'] >= 245][:5]
                if combo_bad_items:
                    combo_text = "\n## 잔반 많은 메뉴 조합\n" + "\n".join(
                        f"- {c['combo']} (평균 {c['avg_waste']:.1f}g/인, {c['count']}회)"
                        for c in combo_bad_items
                    )

            prompt = f"""당신은 단체급식 영양전문가입니다.
아래 메뉴들은 잔반량이 많은 메뉴입니다. 각 메뉴에 대해:
1. 잔반이 많은 원인을 추정하세요
2. 개선 방안 또는 대체 메뉴를 제안하세요
3. 어떤 메뉴와 조합하면 잔반이 줄어들지 제안하세요

## 잔반 많은 메뉴 (기관: {site_name})
{bad_list}
{weekday_info}
{combo_text}

간결하게 메뉴별로 2~3줄씩 답변하세요. 마크다운 형식으로."""

            with st.spinner("🤖 AI가 원인을 분석하고 있습니다..."):
                try:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    message = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=2000,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.session_state['_ai_cause_result'] = message.content[0].text
                    st.rerun()
                except Exception as e:
                    st.error(f"API 호출 오류: {str(e)}")

        cause_result = st.session_state.get('_ai_cause_result', '')
        if cause_result:
            st.markdown(cause_result)

    # 전체 메뉴 통계
    all_menus = menu_stats.get('good', []) + menu_stats.get('bad', [])
    seen = set()
    unique = []
    for m in all_menus:
        if m['menu'] not in seen:
            seen.add(m['menu'])
            unique.append(m)

    if unique:
        with st.expander(f"📊 전체 메뉴 통계 ({len(unique)}종)", expanded=False):
            df_all = pd.DataFrame([
                {'메뉴': m['menu'], '평균 잔반(g/인)': round(m['avg_waste'], 1),
                 '등장 횟수': m['count']}
                for m in sorted(unique, key=lambda x: x['avg_waste'])
            ])
            st.dataframe(df_all, use_container_width=True, hide_index=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3: AI 분석생성 (종합분석 + 추천식단) — 프롬프트 강화
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_ai_analysis_tab(user, site_name, all_analysis, months_with_data):
    # 데이터 충분도 안내
    if len(months_with_data) < 1:
        st.warning("📊 잔반 데이터가 아직 없습니다.\n\n"
                   "식단을 등록하고 수거 데이터가 1개월 이상 쌓이면 AI 분석이 가능합니다.")
        st.progress(0.0, text="데이터 수집 중...")
        return
    elif len(months_with_data) < 3:
        st.info(f"📊 현재 {len(months_with_data)}개월 데이터가 있습니다. "
                f"3개월 이상 쌓이면 더 정확한 분석이 가능합니다.")
        st.progress(len(months_with_data) / 3, text=f"데이터 수집 {len(months_with_data)}/3개월")

    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a73e8,#34a853);
                padding:16px;border-radius:10px;margin-bottom:16px;color:white;">
        <div style="font-size:16px;font-weight:700;">🤖 ZERODA AI 잔반분석</div>
        <div style="font-size:13px;margin-top:4px;opacity:0.9;">
            과거 잔반 데이터를 AI가 종합 분석하고, 다음달 최적 식단을 자동 생성합니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # API 키 확인
    api_key = _get_api_key()
    if not api_key:
        st.error("Claude API 키가 설정되지 않았습니다.")
        st.info("Streamlit secrets에 `ANTHROPIC_API_KEY`를 추가하거나, "
                "환경변수 `ANTHROPIC_API_KEY`를 설정하세요.")
        return

    # ── 2개 서브탭: 종합분석 / 추천식단 ──
    sub1, sub2 = st.tabs(["📊 AI 종합분석", "🍽️ AI 추천식단"])

    with sub1:
        _render_ai_comprehensive(api_key, site_name, all_analysis, months_with_data, user)

    with sub2:
        _render_ai_recommend(api_key, site_name, all_analysis, months_with_data, user)


def _render_ai_comprehensive(api_key, site_name, all_analysis, months_with_data, user):
    """AI 종합 잔반분석 리포트 생성 — 프롬프트 강화 (요일, 배식인원, 비용, 조합)"""
    st.markdown("#### 📊 AI 종합 잔반분석")
    st.caption("Claude AI가 잔반 데이터를 종합 분석하여 인사이트를 제공합니다.")

    menu_stats = _build_menu_stats(all_analysis)

    # 요약 데이터 표시
    with st.expander("📊 분석 데이터 요약", expanded=False):
        st.write(f"분석 기간: {months_with_data}")
        st.write(f"총 분석 일수: {len(all_analysis)}일")
        st.write(f"전체 평균 1인당 잔반: {menu_stats.get('overall_avg', 0):.1f}g")

    if st.button("🤖 AI 종합분석 실행", type="primary", key="ai_comprehensive_btn"):
        # 월별 잔반 데이터
        monthly_data = {}
        for r in all_analysis:
            ym = r.get('year_month', '') or r.get('meal_date', '')[:7]
            if ym:
                if ym not in monthly_data:
                    monthly_data[ym] = {'total_kg': 0, 'count': 0, 'grades': []}
                monthly_data[ym]['total_kg'] += float(r.get('waste_kg', 0) or 0)
                monthly_data[ym]['count'] += 1
                g = r.get('grade', '-')
                if g != '-':
                    monthly_data[ym]['grades'].append(g)

        monthly_summary = "\n".join(
            f"- {ym}: 총 {d['total_kg']:.1f}kg, {d['count']}일, "
            f"등급분포 {dict((g, d['grades'].count(g)) for g in set(d['grades']))}"
            for ym, d in sorted(monthly_data.items())
        )

        good_list = "\n".join(
            f"- {m['menu']} ({m['avg_waste']:.1f}g/인, {m['count']}회)"
            for m in menu_stats['good'][:10]
        ) or "- 데이터 없음"

        bad_list = "\n".join(
            f"- {m['menu']} ({m['avg_waste']:.1f}g/인, {m['count']}회)"
            for m in menu_stats['bad'][:10]
        ) or "- 데이터 없음"

        # ── 신규: 요일별 패턴 데이터 ──
        weekday_text = _build_weekday_menu_text(all_analysis)

        # ── 신규: 배식인원 대비 효율 ──
        srv_text = _build_servings_text(all_analysis)

        # ── 신규: 비용 데이터 ──
        cost_info = _calc_cost_savings(site_name, user, all_analysis, months_with_data)
        cost_text = ""
        if cost_info and cost_info.get('unit_price', 0) > 0:
            cost_text = f"""
## 비용 정보
- 음식물 처리 단가: {cost_info['unit_price']:,.0f}원/kg
- 분석 기간 처리비용: {cost_info['current_cost']:,.0f}원
- 10% 감소 시 절감 예상: 월 {cost_info.get('save_amount', 0):,.0f}원, 연간 {cost_info.get('save_amount', 0) * 12:,.0f}원"""

        # ── 신규: 이상치 데이터 ──
        anomalies = _detect_anomalies(all_analysis)
        anomaly_text = ""
        if anomalies:
            anomaly_text = "\n## 이상치 (평소 대비 급증/급감일)\n" + "\n".join(
                f"- {a['date']}: {a['waste_kg']:.1f}kg (Z={a['z_score']:.2f}, {'급증' if a['z_score'] > 0 else '급감'}) 메뉴: {a.get('menus', '-')}"
                for a in anomalies[:5]
            )

        # ── 신규: 메뉴 조합 데이터 ──
        combo = _build_combo_analysis(all_analysis)
        combo_text = ""
        if combo:
            combo_good = [c for c in combo if c['avg_waste'] < 200][:3]
            combo_bad = [c for c in combo if c['avg_waste'] >= 245][:3]
            parts = []
            if combo_good:
                parts.append("잔반 적은 조합:\n" + "\n".join(
                    f"- {c['combo']} ({c['avg_waste']:.1f}g/인, {c['count']}회)" for c in combo_good))
            if combo_bad:
                parts.append("잔반 많은 조합:\n" + "\n".join(
                    f"- {c['combo']} ({c['avg_waste']:.1f}g/인, {c['count']}회)" for c in combo_bad))
            if parts:
                combo_text = "\n## 메뉴 조합 분석\n" + "\n".join(parts)

        prompt = f"""당신은 단체급식 잔반 분석 전문가입니다.
아래 데이터를 기반으로 종합 분석 리포트를 작성하세요.

## 기관: {site_name}
## 분석 기간: {months_with_data[0]} ~ {months_with_data[-1]}
## 전체 평균 1인당 잔반: {menu_stats.get('overall_avg', 0):.1f}g

## 월별 추이
{monthly_summary}

## 잔반 적은 메뉴 TOP 10
{good_list}

## 잔반 많은 메뉴 TOP 10
{bad_list}
{weekday_text}
{srv_text}
{cost_text}
{anomaly_text}
{combo_text}

## 작성 항목 (반드시 모두 포함)
1. **종합 평가**: 전체적인 잔반 관리 수준 평가 (A~D 등급 기준)
2. **월별 트렌드 분석**: 증감 패턴 및 원인 추정
3. **요일별 패턴 분석**: 요일별 잔반 차이의 원인 추정과 대응 방안
4. **메뉴 분석**: 잔반 많은 메뉴의 원인 추정과 개선 방안 (조합 효과 포함)
5. **배식인원 대비 효율**: 인원수와 잔반의 관계, 조리량 조절 권고
6. **비용 절감 방안**: 구체적인 비용 절감 목표와 실행 방안
7. **이상치 분석**: 급증/급감일 원인 추정
8. **개선 권고사항**: 5가지 구체적이고 즉시 실행 가능한 방안
9. **목표 설정**: 다음 분기 잔반 감소 목표 (kg, g/인, 원 단위 모두)

마크다운 형식으로 간결하게 작성하세요."""

        with st.spinner("🤖 AI가 종합분석을 수행하고 있습니다..."):
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}]
                )
                st.session_state['_ai_comprehensive_result'] = message.content[0].text
                st.rerun()
            except ImportError:
                st.error("anthropic 패키지가 설치되지 않았습니다.")
            except Exception as e:
                st.error(f"API 호출 오류: {str(e)}")

    result = st.session_state.get('_ai_comprehensive_result', '')
    if result:
        st.divider()
        st.markdown(result)


def _render_ai_recommend(api_key, site_name, all_analysis, months_with_data, user):
    """AI 추천식단 생성 (기존 ai_recommend.py 기능 통합)"""
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    past_months = []
    for delta in range(-6, 0):
        m = now.month + delta
        y = now.year
        if m < 1:
            m += 12
            y -= 1
        past_months.append(f"{y}-{m:02d}")
    past_months.reverse()

    next_m = now.month + 1
    next_y = now.year
    if next_m > 12:
        next_m = 1
        next_y += 1
    target_month = f"{next_y}-{next_m:02d}"

    st.subheader(f"📅 추천 대상: {target_month}")

    ref_months = st.multiselect("참고할 분석 월 (최대 3개월)",
                                past_months, default=past_months[:2],
                                max_selections=3,
                                key="aiwt_ref_months")

    if not ref_months:
        st.info("참고할 분석 월을 1개 이상 선택하세요.")
        return

    ref_analysis = []
    for rm in ref_months:
        rows = get_meal_analysis(site_name, rm)
        ref_analysis.extend(rows)

    if not ref_analysis:
        st.warning("선택한 월의 잔반 분석 데이터가 없습니다.")
        return

    menu_stats = _build_menu_stats(ref_analysis)

    with st.expander("📊 참고 데이터 요약", expanded=False):
        st.write(f"분석 기간: {ref_months}")
        st.write(f"총 분석 일수: {len(ref_analysis)}일")
        if menu_stats['good']:
            st.write("**✅ 잔반 적은 메뉴 TOP 5:**")
            for i, m in enumerate(menu_stats['good'][:5], 1):
                st.write(f"  {i}. {m['menu']} (평균 {m['avg_waste']:.1f}g/인, {m['count']}회)")
        if menu_stats['bad']:
            st.write("**⚠️ 잔반 많은 메뉴 TOP 5:**")
            for i, m in enumerate(menu_stats['bad'][:5], 1):
                st.write(f"  {i}. {m['menu']} (평균 {m['avg_waste']:.1f}g/인, {m['count']}회)")

    extra_request = st.text_area("추가 요청사항 (선택)",
                                 placeholder="예: 매주 수요일은 한식으로, 알레르기 식품 제외 등",
                                 key="aiwt_extra", height=80)

    st.info("💡 추천 생성 시 Claude API를 호출합니다. "
            "예상 토큰: 약 2,000~4,000 토큰 (프롬프트 + 응답)")

    if st.button("🤖 추천식단 생성", type="primary", key="aiwt_generate"):
        _generate_recommendation(api_key, site_name, target_month,
                                 menu_stats, extra_request, user)

    rec = st.session_state.get('_ai_recommendation', None)
    if rec and rec.get('month') == target_month:
        _render_recommendation(rec, site_name, user)


def _generate_recommendation(api_key, site_name, target_month,
                             menu_stats, extra_request, user):
    """Claude API 호출하여 추천식단 생성"""
    nutrition_summary = _build_nutrition_summary(site_name)
    prompt = _build_recommend_prompt(site_name, target_month, menu_stats,
                                     extra_request, nutrition_summary)

    with st.spinner("🤖 AI가 추천식단을 생성하고 있습니다..."):
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text
            recommendation = _parse_recommendation(response_text, target_month)

            if recommendation:
                st.session_state['_ai_recommendation'] = recommendation
                st.success("✅ 추천식단이 생성되었습니다!")
                st.rerun()
            else:
                st.error("추천 결과 파싱에 실패했습니다.")
                with st.expander("원본 응답 확인"):
                    st.text(response_text)
        except ImportError:
            st.error("anthropic 패키지가 설치되지 않았습니다.")
        except Exception as e:
            st.error(f"API 호출 오류: {str(e)}")


def _render_recommendation(rec, site_name, user):
    """생성된 추천 결과 렌더링"""
    st.divider()
    st.subheader(f"📋 {rec['month']} 추천식단")

    meals = rec.get('meals', [])
    if not meals:
        st.warning("추천 결과가 비어있습니다.")
        return

    for m in meals:
        date_str = m.get('date', '')
        weekday = m.get('weekday', '')
        menus = m.get('menu_items', [])
        cal = m.get('calories', 0)
        reason = m.get('reason', '')
        menu_text = " / ".join(menus)
        st.markdown(
            f"**{date_str} ({weekday})** &nbsp; "
            f"`{cal}kcal` &nbsp; {menu_text}"
        )
        if reason:
            st.caption(f"💡 {reason}")

    st.divider()
    st.subheader("💾 추천식단 일괄 등록")
    st.caption("아래 버튼을 누르면 추천식단이 '식단 등록'에 저장됩니다.")

    site_type = user.get('site_type', '학교')
    student_count = get_school_student_count(site_name)
    servings = student_count if student_count > 0 else 0

    if st.button("✅ 추천식단 전체 등록", type="primary", key="aiwt_save_all"):
        saved = 0
        for m in meals:
            ok = save_meal_menu(
                site_name=site_name,
                meal_date=m.get('date', ''),
                meal_type='중식',
                menu_items=m.get('menu_items', []),
                calories=float(m.get('calories', 0)),
                nutrition_info={},
                servings=servings,
                site_type=site_type,
            )
            if ok:
                saved += 1
        st.success(f"✅ {saved}/{len(meals)}일 식단이 등록되었습니다!")
        st.session_state['_ai_recommendation'] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4: AI월말명세서 — 차별화된 AI 전용 PDF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_ai_statement_tab(user, site_name, all_analysis, months_with_data):
    st.subheader("📄 AI월말명세서")
    st.caption("AI 분석 코멘트 + 비용절감 + 요일패턴 + 이상치가 포함된 차별화된 보고서입니다.")

    # ── 스마트명세서와의 차이 안내 ──
    with st.expander("📌 스마트월말명세서와 무엇이 다른가요?", expanded=False):
        st.markdown("""
**스마트월말명세서**는 수치 데이터만 나열합니다.
**AI월말명세서**는 아래 5가지를 추가로 제공합니다:

| 항목 | 스마트 | AI |
|---|:---:|:---:|
| 일별 잔반 테이블 | ✅ | ✅ |
| 메뉴별 순위 | ✅ | ✅ |
| **AI 종합 코멘트** | ❌ | ✅ |
| **비용 절감 효과** | ❌ | ✅ |
| **요일별 잔반 패턴** | ❌ | ✅ |
| **이상치 탐지 결과** | ❌ | ✅ |
| **메뉴 조합 분석** | ❌ | ✅ |
| AI 추천식단 | 선택 | 선택 |
        """)

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
                             key="aiwt_stmt_month")

    year = int(sel_month[:4])
    month = int(sel_month[5:7])

    menus = get_meal_menus(site_name, sel_month)
    if not menus:
        st.warning(f"{sel_month} 등록된 식단이 없습니다.")
        return

    analysis = analyze_meal_waste(site_name, sel_month)
    if not analysis:
        st.info("아직 수거 데이터가 없습니다.")
        return

    matched = len([r for r in analysis if float(r.get('waste_kg', 0) or 0) > 0])
    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in analysis)
    st.success(f"✅ {sel_month}: 식단 {len(menus)}일 / 수거매칭 {matched}일 / 총 잔반 {total_waste:.1f}kg")

    menu_ranking = _build_menu_ranking(analysis)

    # AI 추천식단 (이전에 생성한 것이 있으면)
    ai_rec = st.session_state.get('_ai_recommendation', None)
    ai_meals = None
    if ai_rec and ai_rec.get('meals'):
        ai_meals = ai_rec['meals']
        st.info(f"💡 AI 추천식단이 포함됩니다 ({len(ai_meals)}일)")

    # AI 종합분석 결과 (이전에 생성한 것이 있으면)
    ai_comment = st.session_state.get('_ai_comprehensive_result', '')
    if ai_comment:
        st.info("💡 AI 종합분석 코멘트가 포함됩니다.")

    st.divider()

    # ── AI 전용 데이터 준비 ──
    cost_info = _calc_cost_savings(site_name, user, analysis, [sel_month])
    weekday_pattern = _build_weekday_pattern(analysis)
    anomalies_raw = _detect_anomalies(analysis)
    combo_data = _build_combo_analysis(analysis)

    bc1, bc2 = st.columns(2)

    with bc1:
        if st.button("📄 AI월말명세서 생성", type="primary",
                     key="aiwt_stmt_basic", use_container_width=True):
            with st.spinner("AI월말명세서 PDF 생성 중..."):
                pdf_bytes = generate_ai_meal_statement_pdf(
                    site_name=site_name,
                    year=year, month=month,
                    analysis_rows=analysis,
                    menu_ranking=menu_ranking,
                    ai_recommendation=None,
                    ai_comment=ai_comment,
                    cost_savings=cost_info,
                    weekday_pattern=weekday_pattern,
                    anomalies=anomalies_raw,
                    combo_analysis=combo_data,
                )
                st.session_state['_aiwt_stmt_pdf'] = pdf_bytes
                st.session_state['_aiwt_stmt_filename'] = f"AI월말명세서_{site_name}_{sel_month}.pdf"
                st.success("✅ AI월말명세서 생성 완료!")

    with bc2:
        if ai_meals:
            if st.button("📄 AI월말명세서 생성 (추천 포함)",
                         key="aiwt_stmt_ai", use_container_width=True):
                with st.spinner("AI월말명세서 PDF 생성 중 (추천 포함)..."):
                    pdf_bytes = generate_ai_meal_statement_pdf(
                        site_name=site_name,
                        year=year, month=month,
                        analysis_rows=analysis,
                        menu_ranking=menu_ranking,
                        ai_recommendation=ai_meals,
                        ai_comment=ai_comment,
                        cost_savings=cost_info,
                        weekday_pattern=weekday_pattern,
                        anomalies=anomalies_raw,
                        combo_analysis=combo_data,
                    )
                    st.session_state['_aiwt_stmt_pdf'] = pdf_bytes
                    st.session_state['_aiwt_stmt_filename'] = f"AI월말명세서_{site_name}_{sel_month}_AI추천포함.pdf"
                    st.success("✅ AI월말명세서 생성 완료 (AI 추천 포함)!")
        else:
            st.info("AI 추천식단을 먼저 생성하면\n여기에 포함할 수 있습니다.")

    pdf_bytes = st.session_state.get('_aiwt_stmt_pdf', None)
    filename = st.session_state.get('_aiwt_stmt_filename', '')
    if pdf_bytes:
        st.divider()
        st.download_button(
            label="⬇️ PDF 다운로드",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key="aiwt_stmt_download",
            use_container_width=True,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 헬퍼 함수 (기존 유지 + 신규 추가)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_menu_stats(analysis_rows):
    """분석 데이터에서 메뉴별 통계 생성"""
    menu_waste = {}
    total_wpp = []
    for r in analysis_rows:
        wpp = float(r.get('waste_per_person', 0) or 0)
        if wpp <= 0:
            continue
        total_wpp.append(wpp)
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
        'overall_avg': sum(total_wpp) / len(total_wpp) if total_wpp else 0,
    }


def _build_menu_ranking(analysis_rows):
    """PDF용 메뉴 순위"""
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
    return {'good': ranking[:20], 'bad': list(reversed(ranking))[:20]}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 신규: 비용 절감 효과 계산
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _calc_cost_savings(site_name, user, analysis_rows, months_with_data):
    """음식물 처리 단가를 기반으로 비용 절감 효과 계산"""
    vendor = user.get('vendor', '')
    if not vendor:
        return None

    unit_price = get_unit_price(vendor, site_name, '음식물')
    if unit_price <= 0:
        # 기본 단가 (업계 평균)
        unit_price = 0

    if unit_price <= 0:
        return None

    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in analysis_rows)
    current_cost = total_waste * unit_price

    # 10% 감소 시 절감 (월 기준)
    months_count = max(len(months_with_data), 1)
    monthly_avg = total_waste / months_count
    save_amount = monthly_avg * 0.1 * unit_price

    # 전월 대비 (최근 2개월 비교)
    prev_cost = 0
    mom_save = 0
    if len(months_with_data) >= 2:
        latest_ym = months_with_data[-1]
        prev_ym = months_with_data[-2]
        latest_kg = sum(float(r.get('waste_kg', 0) or 0) for r in analysis_rows
                        if (r.get('year_month', '') or r.get('meal_date', '')[:7]) == latest_ym)
        prev_kg = sum(float(r.get('waste_kg', 0) or 0) for r in analysis_rows
                      if (r.get('year_month', '') or r.get('meal_date', '')[:7]) == prev_ym)
        prev_cost = prev_kg * unit_price
        mom_save = (prev_kg - latest_kg) * unit_price

    target_cost = current_cost * 0.9

    return {
        'unit_price': unit_price,
        'current_cost': current_cost,
        'target_cost': target_cost,
        'save_amount': round(save_amount),
        'save_pct': 10,
        'prev_cost': prev_cost,
        'mom_save': round(mom_save),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 신규: 요일별 잔반 패턴 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_weekday_pattern(analysis_rows):
    """요일별 잔반량 + 주요 메뉴 키워드 분석"""
    weekday_data = {}

    for r in analysis_rows:
        meal_date = r.get('meal_date', '')
        waste_kg = float(r.get('waste_kg', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        if not meal_date or waste_kg <= 0:
            continue
        try:
            dt = datetime.strptime(meal_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue

        wd = dt.weekday()
        if wd not in weekday_data:
            weekday_data[wd] = {'kg_list': [], 'pp_list': [], 'menus': []}
        weekday_data[wd]['kg_list'].append(waste_kg)
        weekday_data[wd]['pp_list'].append(wpp)

        try:
            menu_items = json.loads(r.get('menu_items', '[]'))
            weekday_data[wd]['menus'].extend(menu_items)
        except (json.JSONDecodeError, TypeError):
            pass

    if not weekday_data:
        return None

    result = []
    for wd in sorted(weekday_data.keys()):
        d = weekday_data[wd]
        avg_kg = sum(d['kg_list']) / len(d['kg_list'])
        avg_pp = sum(d['pp_list']) / len(d['pp_list']) if d['pp_list'] else 0

        # 주요 메뉴 키워드 (빈도 상위 3개)
        from collections import Counter
        menu_counter = Counter(d['menus'])
        top_menus = ", ".join(m for m, _ in menu_counter.most_common(3))

        result.append({
            'weekday': wd,
            'weekday_name': WEEKDAY_KR.get(wd, ''),
            'avg_kg': avg_kg,
            'avg_pp': avg_pp,
            'count': len(d['kg_list']),
            'top_menus': top_menus or '-',
        })

    # 인사이트 생성
    insight = ""
    if len(result) >= 2:
        worst = max(result, key=lambda x: x['avg_kg'])
        best = min(result, key=lambda x: x['avg_kg'])
        insight = (f"💡 **{worst['weekday_name']}요일**에 잔반이 가장 많고 "
                   f"(평균 {worst['avg_kg']:.1f}kg, 주요메뉴: {worst['top_menus']}), "
                   f"**{best['weekday_name']}요일**에 가장 적습니다 "
                   f"(평균 {best['avg_kg']:.1f}kg).")

    return {'data': result, 'insight': insight}


def _build_weekday_menu_text(analysis_rows):
    """AI 프롬프트용 요일별 메뉴-잔반 텍스트"""
    pattern = _build_weekday_pattern(analysis_rows)
    if not pattern or not pattern.get('data'):
        return ""

    lines = ["## 요일별 잔반 패턴"]
    for wd in pattern['data']:
        lines.append(
            f"- {wd['weekday_name']}요일: 평균 {wd['avg_kg']:.1f}kg, "
            f"1인당 {wd['avg_pp']:.1f}g, {wd['count']}일, "
            f"주요메뉴: {wd['top_menus']}"
        )
    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 신규: 이상치 탐지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _detect_anomalies(analysis_rows, threshold=1.8):
    """잔반 이상치 (평소 대비 급증/급감) 탐지"""
    valid = []
    for r in analysis_rows:
        waste_kg = float(r.get('waste_kg', 0) or 0)
        if waste_kg <= 0:
            continue
        try:
            menu_items = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menu_items = []
        valid.append({
            'date': r.get('meal_date', ''),
            'waste_kg': waste_kg,
            'menus': ", ".join(menu_items[:3]) if menu_items else '-',
        })

    if len(valid) < 5:
        return []

    kg_values = [v['waste_kg'] for v in valid]
    mean_kg = sum(kg_values) / len(kg_values)
    std_kg = (sum((x - mean_kg) ** 2 for x in kg_values) / len(kg_values)) ** 0.5

    if std_kg == 0:
        return []

    anomalies = []
    for v in valid:
        z = (v['waste_kg'] - mean_kg) / std_kg
        if abs(z) > threshold:
            v['z_score'] = round(z, 2)
            anomalies.append(v)

    anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)
    return anomalies


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 신규: 메뉴 조합 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_combo_analysis(analysis_rows):
    """같은 날 제공된 메뉴 세트 단위로 잔반량 분석"""
    combo_waste = {}

    for r in analysis_rows:
        wpp = float(r.get('waste_per_person', 0) or 0)
        if wpp <= 0:
            continue
        try:
            menu_items = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menu_items = []

        if len(menu_items) < 2:
            continue

        # 메뉴를 정렬하여 조합 키 생성 (밥/김치 제외하고 주반찬 위주)
        filtered = [m for m in menu_items
                    if not any(k in m for k in ['밥', '김치', '공기'])]
        if len(filtered) < 2:
            filtered = menu_items[:3]
        else:
            filtered = filtered[:3]

        combo_key = " + ".join(sorted(filtered))
        if combo_key not in combo_waste:
            combo_waste[combo_key] = []
        combo_waste[combo_key].append(wpp)

    if not combo_waste:
        return []

    result = []
    for combo, wastes in combo_waste.items():
        if len(wastes) >= 2:  # 최소 2회 이상 등장한 조합만
            avg = sum(wastes) / len(wastes)
            result.append({
                'combo': combo,
                'avg_waste': avg,
                'count': len(wastes),
            })

    result.sort(key=lambda x: x['avg_waste'])
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 신규: 배식인원 대비 효율 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _analyze_servings_efficiency(analysis_rows):
    """배식인원과 잔반의 관계 분석 → 인사이트 텍스트"""
    high_srv = []
    low_srv = []

    for r in analysis_rows:
        srv = int(r.get('servings', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        if srv <= 0 or wpp <= 0:
            continue
        if srv >= 300:
            high_srv.append(wpp)
        elif srv < 200:
            low_srv.append(wpp)

    if high_srv and low_srv:
        avg_high = sum(high_srv) / len(high_srv)
        avg_low = sum(low_srv) / len(low_srv)
        if avg_low > avg_high * 1.15:
            return (f"📌 배식인원이 적은 날({len(low_srv)}일) 1인당 잔반이 "
                    f"{avg_low:.0f}g으로, 인원 많은 날({len(high_srv)}일) "
                    f"{avg_high:.0f}g보다 높습니다. 소인원 시 조리량 조절을 권장합니다.")
    return None


def _build_servings_analysis(analysis_rows):
    """배식인원 구간별 1인당 잔반 통계"""
    bins = {'~100명': [], '100~200명': [], '200~300명': [], '300명~': []}

    for r in analysis_rows:
        srv = int(r.get('servings', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        if srv <= 0 or wpp <= 0:
            continue
        if srv < 100:
            bins['~100명'].append(wpp)
        elif srv < 200:
            bins['100~200명'].append(wpp)
        elif srv < 300:
            bins['200~300명'].append(wpp)
        else:
            bins['300명~'].append(wpp)

    result = []
    for label, values in bins.items():
        if values:
            result.append({
                '배식인원 구간': label,
                '평균 1인당 잔반(g)': round(sum(values) / len(values), 1),
                '데이터 수': len(values),
            })

    return result if result else None


def _build_servings_text(analysis_rows):
    """AI 프롬프트용 배식인원 대비 텍스트"""
    stats = _build_servings_analysis(analysis_rows)
    if not stats:
        return ""

    lines = ["## 배식인원 대비 1인당 잔반"]
    for s in stats:
        lines.append(
            f"- {s['배식인원 구간']}: 평균 {s['평균 1인당 잔반(g)']}g/인 ({s['데이터 수']}일)"
        )
    return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 기존 헬퍼 (유지)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _build_recommend_prompt(site_name, target_month, menu_stats, extra_request,
                            nutrition_summary=None):
    good_list = "\n".join(
        f"- {m['menu']} (평균 잔반 {m['avg_waste']:.1f}g/인, {m['count']}회 제공)"
        for m in menu_stats['good'][:10]
    ) or "- 데이터 없음"

    bad_list = "\n".join(
        f"- {m['menu']} (평균 잔반 {m['avg_waste']:.1f}g/인, {m['count']}회 제공)"
        for m in menu_stats['bad'][:10]
    ) or "- 데이터 없음"

    avg_waste = menu_stats.get('overall_avg', 0)

    nut_section = ""
    if nutrition_summary:
        nut_section = "\n## 기존 식단 영양정보 평균 (참고)\n" + nutrition_summary + "\n"

    extra_line = ""
    if extra_request:
        extra_line = "7. 추가 요청: " + extra_request

    return f"""당신은 단체급식 영양사 AI입니다.
아래 잔반 분석 데이터를 참고하여 {target_month} 한 달간의 추천 식단표를 작성해주세요.

## 기관 정보
- 기관명: {site_name}
- 대상월: {target_month}
- 전체 평균 1인당 잔반량: {avg_waste:.1f}g

## 잔반 적은 메뉴 (선호 → 자주 배치)
{good_list}

## 잔반 많은 메뉴 (비선호 → 빈도 줄이거나 개선 조합)
{bad_list}
{nut_section}
## 작성 규칙
1. 평일(월~금)만 작성 (주말 제외)
2. 잔반 적은 메뉴를 우선 배치하되, 영양 균형을 고려
3. 잔반 많은 메뉴는 빈도를 줄이거나 인기 메뉴와 조합
4. 메뉴는 밥, 국/찌개, 주찬, 부찬, 김치 5가지 구성
5. 칼로리는 700~900kcal 범위로 추정
6. 비타민·미네랄이 균형 잡히도록 구성
{extra_line}

## 출력 형식 (반드시 아래 JSON 형식으로)
```json
{{
  "month": "{target_month}",
  "meals": [
    {{
      "date": "YYYY-MM-DD",
      "weekday": "월",
      "menu_items": ["잡곡밥", "김치찌개", "제육볶음", "시금치나물", "배추김치"],
      "calories": 780,
      "reason": "제육볶음과 시금치나물은 잔반율이 낮은 조합"
    }}
  ]
}}
```
JSON만 출력하세요. 다른 설명은 불필요합니다."""


def _parse_recommendation(text, target_month):
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = text.strip()
    try:
        data = json.loads(json_str)
        if 'meals' in data:
            data['month'] = target_month
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def _build_nutrition_summary(site_name: str) -> str:
    menus = get_meal_menus(site_name, '')
    if not menus:
        return ""

    nut_keys = ['탄수화물', '단백질', '지방', '비타민A', '티아민',
                '리보플라빈', '비타민C', '칼슘', '철분']
    sums = {k: 0.0 for k in nut_keys}
    cal_sum = 0.0
    count = 0

    for m in menus:
        try:
            nut = json.loads(m.get('nutrition_info', '{}'))
        except (json.JSONDecodeError, TypeError):
            continue
        if not nut:
            continue
        has_data = any(float(nut.get(k, 0) or 0) > 0 for k in nut_keys)
        if not has_data:
            continue
        count += 1
        cal_sum += float(m.get('calories', 0) or 0)
        for k in nut_keys:
            sums[k] += float(nut.get(k, 0) or 0)

    if count == 0:
        return ""

    lines = [f"- 분석 대상: {count}일"]
    lines.append(f"- 평균 칼로리: {cal_sum/count:.0f} kcal")
    units = {'탄수화물': 'g', '단백질': 'g', '지방': 'g',
             '비타민A': 'R.E', '티아민': 'mg', '리보플라빈': 'mg',
             '비타민C': 'mg', '칼슘': 'mg', '철분': 'mg'}
    for k in nut_keys:
        avg = sums[k] / count
        lines.append(f"- {k}: {avg:.1f} {units[k]}")
    return "\n".join(lines)


def _get_api_key():
    try:
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
    except Exception:
        pass
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    return key if key else None


def _get_site_name(user: dict) -> str:
    schools = user.get('schools', '')
    if schools:
        return schools.split(',')[0].strip()
    vendor = user.get('vendor', '')
    if vendor:
        return vendor
    return ''
