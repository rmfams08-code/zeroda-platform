# modules/meal_manager/ai_recommend.py
# 단체급식 담당 — Claude API 기반 추천식단 생성
import streamlit as st
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from database.db_manager import (
    get_meal_analysis, get_meal_menus, save_meal_menu,
    get_school_student_count, analyze_meal_waste,
)
from config.settings import COMMON_CSS


def render_ai_recommend(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.title("🤖 AI 추천식단")

    site_name = _get_site_name(user)
    if not site_name:
        st.warning("담당 거래처가 설정되지 않았습니다.")
        return

    st.caption(f"📍 {site_name}")

    # ── 3탭 구성: 요약 / 상세 분석 / AI 추천 ──
    tab1, tab2, tab3 = st.tabs(["📊 잔반 요약", "📋 메뉴별 상세", "🤖 AI 추천 생성"])

    now = datetime.now(ZoneInfo('Asia/Seoul'))

    # ── 과거 데이터 수집 (최대 6개월) ──
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

    # ── TAB 1: 요약 ──
    with tab1:
        _render_summary_tab(all_analysis, months_with_data, site_name)

    # ── TAB 2: 메뉴별 상세 ──
    with tab2:
        _render_detail_tab(all_analysis)

    # ── TAB 3: AI 추천 (유료 전환 대비 분리) ──
    with tab3:
        _render_ai_tab(user, site_name, all_analysis, months_with_data)


def _render_summary_tab(all_analysis, months_with_data, site_name):
    """잔반 데이터 요약"""
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
        data_score = "충분" if len(months_with_data) >= 3 else ("부족" if len(months_with_data) < 2 else "보통")
        st.metric("데이터 충분도", data_score)

    # 월별 추이 차트
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


def _render_detail_tab(all_analysis):
    """메뉴별 상세 분석"""
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

    # 전체 메뉴 통계
    all_menus = menu_stats.get('good', []) + menu_stats.get('bad', [])
    # 중복 제거
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


def _render_ai_tab(user, site_name, all_analysis, months_with_data):
    """AI 추천식단 생성 (유료 전환 대비 분리)"""

    # 데이터 충분도 안내
    if len(months_with_data) < 1:
        st.warning("📊 잔반 데이터가 아직 없습니다.\n\n"
                   "식단을 등록하고 수거 데이터가 1개월 이상 쌓이면 AI 추천이 가능합니다.")
        st.progress(0.0, text="데이터 수집 중...")
        return
    elif len(months_with_data) < 3:
        st.info(f"📊 현재 {len(months_with_data)}개월 데이터가 있습니다. "
                f"3개월 이상 쌓이면 더 정확한 추천이 가능합니다.")
        st.progress(len(months_with_data) / 3, text=f"데이터 수집 {len(months_with_data)}/3개월")

    # 유료 전환 안내 영역 (추후 여기에 결제 게이트 추가 가능)
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1a73e8,#34a853);
                padding:16px;border-radius:10px;margin-bottom:16px;color:white;">
        <div style="font-size:16px;font-weight:700;">🤖 ZERODA AI 추천식단</div>
        <div style="font-size:13px;margin-top:4px;opacity:0.9;">
            과거 잔반 데이터 + 영양균형을 고려하여 다음달 최적 식단을 자동 생성합니다.
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

    # 이하 기존 추천 생성 로직 호출
    _render_ai_generate(api_key, site_name, all_analysis, months_with_data, user)


def _render_ai_generate(api_key, site_name, all_analysis, months_with_data, user):
    """AI 추천 생성 UI (기존 로직 유지)"""
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

    # 다음달 계산
    next_m = now.month + 1
    next_y = now.year
    if next_m > 12:
        next_m = 1
        next_y += 1
    target_month = f"{next_y}-{next_m:02d}"

    st.subheader(f"📅 추천 대상: {target_month}")

    # ── 참고 데이터 선택 ──
    ref_months = st.multiselect("참고할 분석 월 (최대 3개월)",
                                past_months, default=past_months[:2],
                                max_selections=3,
                                key="ai_ref_months")

    if not ref_months:
        st.info("참고할 분석 월을 1개 이상 선택하세요.")
        return

    # ── 분석 데이터 수집 ──
    all_analysis = []
    for rm in ref_months:
        rows = get_meal_analysis(site_name, rm)
        all_analysis.extend(rows)

    if not all_analysis:
        st.warning("선택한 월의 잔반 분석 데이터가 없습니다. '잔반 분석'에서 먼저 분석을 실행하세요.")
        return

    # ── 메뉴별 통계 요약 ──
    menu_stats = _build_menu_stats(all_analysis)

    with st.expander("📊 참고 데이터 요약", expanded=False):
        st.write(f"분석 기간: {ref_months}")
        st.write(f"총 분석 일수: {len(all_analysis)}일")

        if menu_stats['good']:
            st.write("**✅ 잔반 적은 메뉴 TOP 5:**")
            for i, m in enumerate(menu_stats['good'][:5], 1):
                st.write(f"  {i}. {m['menu']} (평균 {m['avg_waste']:.1f}g/인, {m['count']}회)")

        if menu_stats['bad']:
            st.write("**⚠️ 잔반 많은 메뉴 TOP 5:**")
            for i, m in enumerate(menu_stats['bad'][:5], 1):
                st.write(f"  {i}. {m['menu']} (평균 {m['avg_waste']:.1f}g/인, {m['count']}회)")

    # ── 추가 요청사항 ──
    extra_request = st.text_area("추가 요청사항 (선택)",
                                 placeholder="예: 매주 수요일은 한식으로, 알레르기 식품 제외 등",
                                 key="ai_extra", height=80)

    # ── 예상 비용 안내 ──
    st.info("💡 추천 생성 시 Claude API를 호출합니다. "
            "예상 토큰: 약 2,000~4,000 토큰 (프롬프트 + 응답)")

    # ── 추천 생성 버튼 ──
    if st.button("🤖 추천식단 생성", type="primary", key="ai_generate"):
        _generate_recommendation(
            api_key, site_name, target_month,
            menu_stats, extra_request, user
        )

    # ── 생성된 추천 결과 표시 ──
    rec = st.session_state.get('_ai_recommendation', None)
    if rec and rec.get('month') == target_month:
        _render_recommendation(rec, site_name, user)


def _generate_recommendation(api_key, site_name, target_month,
                             menu_stats, extra_request, user):
    """Claude API 호출하여 추천식단 생성"""
    prompt = _build_prompt(site_name, target_month, menu_stats, extra_request)

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

            # JSON 파싱 시도
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
            st.error("anthropic 패키지가 설치되지 않았습니다. "
                     "`pip install anthropic`을 실행하세요.")
        except Exception as e:
            st.error(f"API 호출 오류: {str(e)}")


def _build_prompt(site_name, target_month, menu_stats, extra_request):
    """Claude API 프롬프트 구성"""
    good_list = "\n".join(
        f"- {m['menu']} (평균 잔반 {m['avg_waste']:.1f}g/인, {m['count']}회 제공)"
        for m in menu_stats['good'][:10]
    ) or "- 데이터 없음"

    bad_list = "\n".join(
        f"- {m['menu']} (평균 잔반 {m['avg_waste']:.1f}g/인, {m['count']}회 제공)"
        for m in menu_stats['bad'][:10]
    ) or "- 데이터 없음"

    avg_waste = menu_stats.get('overall_avg', 0)

    prompt = f"""당신은 단체급식 영양사 AI입니다.
아래 잔반 분석 데이터를 참고하여 {target_month} 한 달간의 추천 식단표를 작성해주세요.

## 기관 정보
- 기관명: {site_name}
- 대상월: {target_month}
- 전체 평균 1인당 잔반량: {avg_waste:.1f}g

## 잔반 적은 메뉴 (선호 → 자주 배치)
{good_list}

## 잔반 많은 메뉴 (비선호 → 빈도 줄이거나 개선 조합)
{bad_list}

## 작성 규칙
1. 평일(월~금)만 작성 (주말 제외)
2. 잔반 적은 메뉴를 우선 배치하되, 영양 균형을 고려
3. 잔반 많은 메뉴는 빈도를 줄이거나 인기 메뉴와 조합
4. 메뉴는 밥, 국/찌개, 주찬, 부찬, 김치 5가지 구성
5. 칼로리는 700~900kcal 범위로 추정
{f"6. 추가 요청: {extra_request}" if extra_request else ""}

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

    return prompt


def _parse_recommendation(text, target_month):
    """API 응답에서 JSON 추출"""
    # JSON 블록 추출
    import re
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # 전체 텍스트가 JSON일 수 있음
        json_str = text.strip()

    try:
        data = json.loads(json_str)
        if 'meals' in data:
            data['month'] = target_month
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    return None


def _render_recommendation(rec, site_name, user):
    """생성된 추천 결과 렌더링"""
    st.divider()
    st.subheader(f"📋 {rec['month']} 추천식단")

    meals = rec.get('meals', [])
    if not meals:
        st.warning("추천 결과가 비어있습니다.")
        return

    # 테이블 형태로 표시
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

    # ── 일괄 등록 버튼 ──
    st.subheader("💾 추천식단 일괄 등록")
    st.caption("아래 버튼을 누르면 추천식단이 '식단 등록'에 저장됩니다.")

    site_type = user.get('site_type', '학교')
    student_count = get_school_student_count(site_name)
    servings = student_count if student_count > 0 else 0

    if st.button("✅ 추천식단 전체 등록", type="primary", key="ai_save_all"):
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


def _get_api_key():
    """Anthropic API 키 조회"""
    import os
    # 1. Streamlit secrets
    try:
        if hasattr(st, 'secrets') and 'ANTHROPIC_API_KEY' in st.secrets:
            return st.secrets['ANTHROPIC_API_KEY']
    except Exception:
        pass
    # 2. 환경변수
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
