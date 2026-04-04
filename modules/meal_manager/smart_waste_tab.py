# modules/meal_manager/smart_waste_tab.py
# 단체급식 담당 — 스마트잔반분석 (4탭: 잔반요약 / 메뉴별상세 / 잔반트렌드 / 스마트월말명세서)
import streamlit as st
import json
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from database.db_manager import (
    analyze_meal_waste, get_meal_menus, db_get,
)
from services.pdf_generator import generate_meal_statement_pdf
from config.settings import (
    COMMON_CSS, get_school_standard, detect_school_level,
    OFFICIAL_REFERENCES,
)


def render_smart_waste_tab(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.title("📊 스마트잔반분석")

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
                             key="swt_month")

    # ── 4탭 구성 ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 잔반요약", "📋 메뉴별상세", "📈 잔반트렌드", "📄 스마트월말명세서"
    ])

    # ── 데이터 로드 (공통) ──
    menus = get_meal_menus(site_name, sel_month)
    analysis = analyze_meal_waste(site_name, sel_month) if menus else []

    # ── 과거 6개월 데이터 (트렌드용) ──
    all_analysis = []
    months_with_data = []
    for delta in range(-6, 1):
        m = now.month + delta
        y = now.year
        if m < 1:
            m += 12
            y -= 1
        ym = f"{y}-{m:02d}"
        rows = analyze_meal_waste(site_name, ym)
        if rows and any(float(r.get('waste_kg', 0) or 0) > 0 for r in rows):
            all_analysis.extend(rows)
            months_with_data.append(ym)

    with tab1:
        _render_summary_tab(analysis, menus, sel_month, site_name)

    with tab2:
        _render_detail_tab(analysis, site_name)

    with tab3:
        _render_trend_tab(all_analysis, months_with_data, site_name)

    with tab4:
        _render_statement_tab(user, site_name, sel_month, analysis, menus)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: 잔반요약
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_summary_tab(results, menus, sel_month, site_name=''):
    if not menus:
        st.info(f"{sel_month} 등록된 식단이 없습니다. '식단 등록' 메뉴에서 먼저 식단을 등록하세요.")
        return

    st.success(f"{sel_month}: {len(menus)}일 식단 등록됨")

    # ── 공식기준 안내 (학교급 자동 판별) ──
    std = get_school_standard(site_name)
    level = std['level']
    nut = std['nutrition']
    comp = std['composition']

    with st.expander(f"📏 공식기준: {nut['label']} (학교급식법 시행규칙 [별표 3])", expanded=False):
        st.markdown(f"""
**학교급:** {nut['label']} | **1끼 에너지 기준:** {nut['energy_kcal']} kcal (±10%)

| 등급 | 1인당 잔반량 | 판정 | 설명 |
|:---:|:---:|:---:|:---|
| **A** | 150g 미만 | 우수 | 잔반 최소화 달성 |
| **B** | 150~245g | 양호 | 혼합평균(245g) 이하 |
| **C** | 245~300g | 주의 | 표준 초과, 메뉴 조정 권장 |
| **D** | 300g 이상 | 경보 | 고잔반, 메뉴 구성 재검토 필요 |

**1끼 구성별 제공량 기준:**

| 구성 | 제공량(g) | 칼로리(kcal) |
|:---|:---:|:---:|
| 밥 | {comp.get('밥', {}).get('supply_g', '-')}g | {comp.get('밥', {}).get('kcal', '-')} |
| 국 | {comp.get('국', {}).get('supply_g', '-')}g | {comp.get('국', {}).get('kcal', '-')} |
| 주반찬 | {comp.get('주반찬', {}).get('supply_g', '-')}g | {comp.get('주반찬', {}).get('kcal', '-')} |
| 부반찬 | {comp.get('부반찬', {}).get('supply_g', '-')}g | {comp.get('부반찬', {}).get('kcal', '-')} |
| 김치 | {comp.get('김치', {}).get('supply_g', '-')}g | {comp.get('김치', {}).get('kcal', '-')} |
| **합계** | **{comp.get('total_g', '-')}g** | **{comp.get('total_kcal', '-')} kcal** |

*조리 시 폐기율(10~35%) + 조리손실(~10%) 감안 → 제공량 대비 약 20% 추가 조리 필요*

**분석 근거:**
{"".join(chr(10) + '- ' + r for r in OFFICIAL_REFERENCES[:4])}
        """)

    if not results:
        st.info("아직 수거 데이터가 없습니다. 기사가 수거량을 입력하면 자동으로 반영됩니다.")
        return

    # 요약 KPI
    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in results)
    valid = [r for r in results if float(r.get('waste_per_person', 0) or 0) > 0]
    avg_pp = sum(float(r['waste_per_person']) for r in valid) / len(valid) if valid else 0
    matched = len([r for r in results if float(r.get('waste_kg', 0) or 0) > 0])

    grade_counts = {}
    for r in results:
        g = r.get('grade', '-')
        if g != '-':
            grade_counts[g] = grade_counts.get(g, 0) + 1

    srv_list = [int(r.get('servings', 0) or 0) for r in results if int(r.get('servings', 0) or 0) > 0]
    avg_srv = round(sum(srv_list) / len(srv_list)) if srv_list else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("평균 배식인원", f"{avg_srv:,}명" if avg_srv > 0 else '-')
    with c2:
        st.metric("총 잔반량", f"{total_waste:.1f} kg")
    with c3:
        st.metric("1인당 평균", f"{avg_pp:.1f} g")
    with c4:
        st.metric("매칭 일수", f"{matched} / {len(results)}일")
    with c5:
        best_grade = max(grade_counts, key=grade_counts.get) if grade_counts else '-'
        st.metric("주요 등급", best_grade)

    # ── 공식기준 대비 실적 비교 ──
    std_supply_g = comp.get('total_g', 670)
    std_kcal = nut['energy_kcal']
    waste_ratio = (avg_pp / std_supply_g * 100) if std_supply_g > 0 and avg_pp > 0 else 0

    st.divider()
    st.subheader(f"📏 공식기준 대비 실적 ({nut['label']})")
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        st.metric("1끼 제공량 기준", f"{std_supply_g}g",
                  help=f"밥+국+반찬+김치 합계 ({level})")
    with sc2:
        st.metric("1인당 잔반 비율", f"{waste_ratio:.1f}%",
                  help=f"1인당 잔반 {avg_pp:.0f}g ÷ 제공량 {std_supply_g}g")
    with sc3:
        overhead = std_supply_g * 1.2  # 약 20% 추가 조리
        st.metric("예상 조리량/인", f"{overhead:.0f}g",
                  help="폐기율+조리손실 약 20% 감안")

    if waste_ratio > 40:
        st.warning(f"⚠️ 잔반율 {waste_ratio:.1f}%: 제공량의 40%를 초과합니다. 메뉴 구성 재검토를 권장합니다.")
    elif waste_ratio > 30:
        st.info(f"📌 잔반율 {waste_ratio:.1f}%: 제공량의 30% 이상입니다. 개선 여지가 있습니다.")
    elif waste_ratio < 20 and avg_pp > 0:
        st.success(f"✅ 잔반율 {waste_ratio:.1f}%: 양호한 수준입니다.")

    # 등급 분포 차트
    if grade_counts:
        st.subheader("📊 등급 분포")
        grade_df = pd.DataFrame(
            [{'등급': k, '일수': v} for k, v in sorted(grade_counts.items())]
        )
        st.bar_chart(grade_df.set_index('등급'), use_container_width=True)

    # 일별 상세 테이블
    st.subheader("📋 일별 상세")
    rows_table = []
    for r in results:
        try:
            menu_items = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menu_items = []
        menu_str = ", ".join(menu_items) if menu_items else "-"
        srv = int(r.get('servings', 0) or 0)
        rows_table.append({
            '날짜': r.get('meal_date', ''),
            '메뉴': menu_str,
            '배식인원': f"{srv:,}" if srv > 0 else '-',
            '잔반량(kg)': round(float(r.get('waste_kg', 0) or 0), 1),
            '1인당(g)': round(float(r.get('waste_per_person', 0) or 0), 1),
            '등급': r.get('grade', '-'),
        })

    if rows_table:
        df = pd.DataFrame(rows_table)

        def _grade_color(val):
            colors = {'A': 'background-color: #e8f5e9',
                      'B': 'background-color: #fff3e0',
                      'C': 'background-color: #fff9c4',
                      'D': 'background-color: #ffebee',
                      '-': ''}
            return colors.get(val, '')

        st.dataframe(df.style.map(_grade_color, subset=['등급']),
                     use_container_width=True, hide_index=True)

    # 일별 추이 차트
    if any(float(r.get('waste_kg', 0) or 0) > 0 for r in results):
        chart_df = pd.DataFrame({
            '날짜': [r['meal_date'] for r in results],
            '잔반량(kg)': [float(r.get('waste_kg', 0) or 0) for r in results],
        })
        st.line_chart(chart_df.set_index('날짜'), use_container_width=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: 메뉴별 상세
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_detail_tab(results, site_name=''):
    if not results:
        st.info("분석 데이터가 없습니다.")
        return

    st.subheader("📋 메뉴별 잔반 분석")

    # 공식기준 메뉴 유형별 잔반 순위 안내
    std = get_school_standard(site_name)
    menu_rank = std['menu_rank']
    with st.expander("📏 메뉴 유형별 잔반 발생 순위 (논문 근거)", expanded=False):
        rank_rows = []
        for name, info in sorted(menu_rank.items(), key=lambda x: x[1]['rank']):
            rank_rows.append({
                '순위': info['rank'],
                '메뉴 유형': name,
                '잔반 비율': f"{info['waste_pct']}%",
                '비고': info['note'],
            })
        st.dataframe(pd.DataFrame(rank_rows), use_container_width=True, hide_index=True)
        st.caption("출처: 한국식품영양과학회(2019), 한국식품영양학회지 KCI, RISS 학위논문 종합")

    menu_stats = _build_menu_stats(results)

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
# TAB 3: 잔반트렌드 (요일별 / 월별 / 계절별)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WEEKDAY_KR = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}
SEASON_MAP = {1: '겨울', 2: '겨울', 3: '봄', 4: '봄', 5: '봄', 6: '여름',
              7: '여름', 8: '여름', 9: '가을', 10: '가을', 11: '가을', 12: '겨울'}


def _render_trend_tab(all_analysis, months_with_data, site_name):
    if not all_analysis:
        st.info("트렌드 분석에 필요한 데이터가 부족합니다. 최소 1개월 이상 데이터가 필요합니다.")
        return

    st.subheader("📈 잔반 트렌드 분석")
    st.caption(f"분석 기간: {months_with_data[0]} ~ {months_with_data[-1]} ({len(months_with_data)}개월)")

    # 데이터 변환
    df = _analysis_to_dataframe(all_analysis)
    if df.empty:
        st.info("분석 가능한 데이터가 없습니다.")
        return

    # ── 3개 서브탭 ──
    sub1, sub2, sub3 = st.tabs(["📅 요일별 패턴", "📊 월별 추이", "🌸 계절별 비교"])

    with sub1:
        _render_weekday_pattern(df)

    with sub2:
        _render_monthly_trend(df)

    with sub3:
        _render_seasonal_compare(df)


def _analysis_to_dataframe(all_analysis):
    """잔반분석 결과를 DataFrame으로 변환"""
    rows = []
    for r in all_analysis:
        waste_kg = float(r.get('waste_kg', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        meal_date = r.get('meal_date', '')
        if not meal_date or waste_kg <= 0:
            continue
        try:
            dt = datetime.strptime(meal_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            continue
        rows.append({
            'date': dt,
            'waste_kg': waste_kg,
            'waste_per_person': wpp,
            'grade': r.get('grade', '-'),
            'servings': int(r.get('servings', 0) or 0),
            'weekday': dt.weekday(),
            'weekday_name': WEEKDAY_KR.get(dt.weekday(), ''),
            'month': dt.month,
            'ym': dt.strftime('%Y-%m'),
            'season': SEASON_MAP.get(dt.month, ''),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _render_weekday_pattern(df):
    """요일별 잔반 패턴"""
    st.markdown("#### 요일별 평균 잔반량")

    weekday_agg = df.groupby(['weekday', 'weekday_name']).agg(
        avg_kg=('waste_kg', 'mean'),
        avg_pp=('waste_per_person', 'mean'),
        count=('waste_kg', 'count'),
    ).reset_index().sort_values('weekday')

    if weekday_agg.empty:
        st.info("요일별 데이터가 없습니다.")
        return

    # 차트
    chart_df = weekday_agg[['weekday_name', 'avg_kg']].copy()
    chart_df.columns = ['요일', '평균 잔반량(kg)']
    chart_df['평균 잔반량(kg)'] = chart_df['평균 잔반량(kg)'].round(1)
    st.bar_chart(chart_df.set_index('요일'), use_container_width=True)

    # 테이블
    display_df = weekday_agg[['weekday_name', 'avg_kg', 'avg_pp', 'count']].copy()
    display_df.columns = ['요일', '평균 잔반(kg)', '평균 1인당(g)', '데이터 수']
    display_df['평균 잔반(kg)'] = display_df['평균 잔반(kg)'].round(1)
    display_df['평균 1인당(g)'] = display_df['평균 1인당(g)'].round(1)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 인사이트
    if len(weekday_agg) >= 2:
        worst = weekday_agg.loc[weekday_agg['avg_kg'].idxmax()]
        best = weekday_agg.loc[weekday_agg['avg_kg'].idxmin()]
        st.info(f"💡 **{worst['weekday_name']}요일**에 잔반이 가장 많고 "
                f"(평균 {worst['avg_kg']:.1f}kg), "
                f"**{best['weekday_name']}요일**에 가장 적습니다 "
                f"(평균 {best['avg_kg']:.1f}kg).")


def _render_monthly_trend(df):
    """월별 잔반 추이"""
    st.markdown("#### 월별 잔반량 추이")

    monthly = df.groupby('ym').agg(
        total_kg=('waste_kg', 'sum'),
        avg_kg=('waste_kg', 'mean'),
        avg_pp=('waste_per_person', 'mean'),
        days=('date', 'nunique'),
    ).reset_index().sort_values('ym')

    if monthly.empty:
        st.info("월별 데이터가 없습니다.")
        return

    # 차트: 총 잔반량
    chart_df = monthly[['ym', 'total_kg']].copy()
    chart_df.columns = ['월', '총 잔반량(kg)']
    chart_df['총 잔반량(kg)'] = chart_df['총 잔반량(kg)'].round(1)
    st.bar_chart(chart_df.set_index('월'), use_container_width=True)

    # 테이블
    display_df = monthly[['ym', 'total_kg', 'avg_kg', 'avg_pp', 'days']].copy()
    display_df.columns = ['월', '총 잔반(kg)', '일평균(kg)', '1인당 평균(g)', '수거일수']
    display_df['총 잔반(kg)'] = display_df['총 잔반(kg)'].round(1)
    display_df['일평균(kg)'] = display_df['일평균(kg)'].round(1)
    display_df['1인당 평균(g)'] = display_df['1인당 평균(g)'].round(1)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 전월 대비 증감
    if len(monthly) >= 2:
        latest = monthly.iloc[-1]
        prev = monthly.iloc[-2]
        if prev['total_kg'] > 0:
            change = ((latest['total_kg'] - prev['total_kg']) / prev['total_kg']) * 100
            arrow = "🔺" if change > 0 else "🔻"
            color = "red" if change > 0 else "green"
            st.markdown(
                f"**전월 대비:** {arrow} <span style='color:{color}'>"
                f"{abs(change):.1f}%</span> "
                f"({'증가' if change > 0 else '감소'})",
                unsafe_allow_html=True
            )


def _render_seasonal_compare(df):
    """계절별 잔반 비교"""
    st.markdown("#### 계절별 평균 잔반량")

    seasonal = df.groupby('season').agg(
        avg_kg=('waste_kg', 'mean'),
        total_kg=('waste_kg', 'sum'),
        avg_pp=('waste_per_person', 'mean'),
        count=('waste_kg', 'count'),
    ).reset_index()

    season_order = {'봄': 0, '여름': 1, '가을': 2, '겨울': 3}
    seasonal['_order'] = seasonal['season'].map(season_order)
    seasonal = seasonal.sort_values('_order').drop(columns='_order')

    if seasonal.empty:
        st.info("계절별 데이터가 없습니다.")
        return

    # 차트
    chart_df = seasonal[['season', 'avg_kg']].copy()
    chart_df.columns = ['계절', '평균 잔반량(kg)']
    chart_df['평균 잔반량(kg)'] = chart_df['평균 잔반량(kg)'].round(1)
    st.bar_chart(chart_df.set_index('계절'), use_container_width=True)

    # 테이블
    display_df = seasonal[['season', 'avg_kg', 'total_kg', 'avg_pp', 'count']].copy()
    display_df.columns = ['계절', '일평균(kg)', '총합(kg)', '1인당(g)', '데이터 수']
    display_df['일평균(kg)'] = display_df['일평균(kg)'].round(1)
    display_df['총합(kg)'] = display_df['총합(kg)'].round(1)
    display_df['1인당(g)'] = display_df['1인당(g)'].round(1)
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    if len(seasonal) >= 2:
        worst = seasonal.loc[seasonal['avg_kg'].idxmax()]
        best = seasonal.loc[seasonal['avg_kg'].idxmin()]
        st.info(f"💡 **{worst['season']}**에 잔반이 가장 많고 "
                f"(일평균 {worst['avg_kg']:.1f}kg), "
                f"**{best['season']}**에 가장 적습니다 "
                f"(일평균 {best['avg_kg']:.1f}kg).")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4: 스마트월말명세서
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _render_statement_tab(user, site_name, sel_month, analysis, menus):
    st.subheader("📄 스마트월말명세서")

    if not menus:
        st.warning(f"{sel_month} 등록된 식단이 없습니다.")
        return

    if not analysis:
        st.info("아직 수거 데이터가 없습니다. 기사가 수거량을 입력하면 자동 반영됩니다.")
        return

    year = int(sel_month[:4])
    month = int(sel_month[5:7])

    matched = len([r for r in analysis if float(r.get('waste_kg', 0) or 0) > 0])
    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in analysis)
    st.success(f"✅ {sel_month}: 식단 {len(menus)}일 / 수거매칭 {matched}일 / 총 잔반 {total_waste:.1f}kg")

    menu_ranking = _build_menu_ranking(analysis)

    st.divider()

    # 공식기준 데이터 로드 (PDF에 전달)
    school_std = get_school_standard(site_name)

    if st.button("📄 스마트월말명세서 생성", type="primary",
                 key="swt_stmt_gen", use_container_width=True):
        with st.spinner("PDF 생성 중..."):
            pdf_bytes = generate_meal_statement_pdf(
                site_name=site_name,
                year=year, month=month,
                analysis_rows=analysis,
                menu_ranking=menu_ranking,
                ai_recommendation=None,
                school_standard=school_std,
            )
            st.session_state['_swt_stmt_pdf'] = pdf_bytes
            st.session_state['_swt_stmt_filename'] = f"스마트월말명세서_{site_name}_{sel_month}.pdf"
            st.success("✅ 명세서 생성 완료!")

    pdf_bytes = st.session_state.get('_swt_stmt_pdf', None)
    filename = st.session_state.get('_swt_stmt_filename', '')
    if pdf_bytes:
        st.download_button(
            label="⬇️ PDF 다운로드",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            key="swt_stmt_download",
            use_container_width=True,
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 헬퍼 함수
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
