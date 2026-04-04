# modules/vendor_admin/analytics_tab.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 업체관리자 — 폐기물 발생 분석 대시보드
# (본사 화면과 유사하되, 자기 업체 데이터만 표시)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import streamlit as st
import pandas as pd
from datetime import datetime

from database.db_manager import db_get
from services.waste_analytics import (
    summary_kpis, daily_stats, weekday_stats, monthly_stats,
    seasonal_stats, school_period_stats,
    by_school_stats, by_item_stats, by_driver_stats,
    trend_analysis, detect_anomalies, weather_correlation,
)


def _get_vendor():
    """현재 로그인한 업체관리자의 vendor 값"""
    user = st.session_state.get('current_user', {})
    return user.get('vendor', '')


def render_analytics_tab():
    """업체관리자 폐기물 발생 분석 화면"""
    st.markdown("## 📊 수거 데이터 분석")

    vendor = _get_vendor()
    if not vendor:
        st.warning("업체 정보를 확인할 수 없습니다.")
        return

    # ── 데이터 로드 (자기 업체만) ──
    all_rows = db_get('real_collection', {'vendor': vendor}) or []
    if not all_rows:
        st.info("수거 데이터가 없습니다. 수거 데이터가 등록되면 분석이 표시됩니다.")
        return

    # ── 필터 ──
    col_f1, col_f2 = st.columns(2)
    dates = [str(r.get('collect_date', ''))[:7] for r in all_rows if r.get('collect_date')]
    ym_set = sorted(set(d for d in dates if len(d) == 7), reverse=True)
    years = sorted(set(d[:4] for d in ym_set), reverse=True)

    with col_f1:
        sel_year = st.selectbox("연도", ['전체'] + years, key='va_ana_year')
    with col_f2:
        if sel_year != '전체':
            months_in_year = [ym for ym in ym_set if ym.startswith(sel_year)]
            sel_ym = st.selectbox("월", ['전체'] + months_in_year, key='va_ana_ym')
        else:
            sel_ym = st.selectbox("월", ['전체'] + ym_set, key='va_ana_ym')

    year_val = int(sel_year) if sel_year != '전체' else None
    ym_val = sel_ym if sel_ym != '전체' else None

    # ── 탭 구성 ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 종합 현황", "📅 일별·요일별", "🏫 거래처·기사별", "🌤️ 기상 상관분석"
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 1: 종합 현황
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab1:
        kpi = summary_kpis(all_rows, year_month=ym_val)
        if not kpi:
            st.info("선택한 기간의 데이터가 없습니다.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                delta_str = f"{kpi['mom_change_pct']:+.1f}%" if kpi.get('mom_change_pct') is not None else None
                st.metric("총 수거량", f"{kpi['total_kg']:,.1f} kg", delta=delta_str)
            with c2:
                st.metric("일평균", f"{kpi['avg_daily_kg']:,.1f} kg/일")
            with c3:
                st.metric("수거일수", f"{kpi['collection_days']}일")
            with c4:
                st.metric("거래처 수", f"{kpi['school_count']}개소")

            c5, c6, c7, c8 = st.columns(4)
            with c5:
                st.metric("음식물", f"{kpi['food_kg']:,.1f} kg")
            with c6:
                st.metric("재활용", f"{kpi['recycle_kg']:,.1f} kg")
            with c7:
                st.metric("일반", f"{kpi['general_kg']:,.1f} kg")
            with c8:
                st.metric("Top 거래처", kpi['top_school'],
                          delta=f"{kpi['top_school_kg']:,.1f} kg")

            st.divider()

            # 품목별 + 월별 추세
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("#### 품목별 비율")
                item_df = by_item_stats(all_rows, year_month=ym_val)
                if not item_df.empty:
                    st.bar_chart(item_df.set_index('item_type')['total_kg'],
                                 use_container_width=True)

            with col_b:
                st.markdown("#### 월별 추세")
                t_df = trend_analysis(all_rows, period='monthly')
                if not t_df.empty:
                    st.line_chart(t_df.set_index('period')['total_kg'],
                                  use_container_width=True)

            # 이상치
            st.divider()
            st.markdown("#### ⚠️ 이상치 탐지")
            anomaly_df = detect_anomalies(all_rows, year_month=ym_val)
            if not anomaly_df.empty:
                anomalies = anomaly_df[anomaly_df['is_anomaly'] == True]
                if len(anomalies) > 0:
                    st.warning(f"이상 수거량이 감지된 날: {len(anomalies)}일")
                    st.dataframe(
                        anomalies[['collect_date', 'total_kg', 'z_score']].rename(columns={
                            'collect_date': '날짜', 'total_kg': '수거량(kg)', 'z_score': 'Z-Score'
                        }),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.success("이상치 없음")
            else:
                st.info("분석할 데이터 부족")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 2: 일별·요일별
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab2:
        st.markdown("### 📅 일별 수거량")
        d_df = daily_stats(all_rows, year_month=ym_val)
        if not d_df.empty:
            d_df['collect_date'] = pd.to_datetime(d_df['collect_date'])
            chart_df = d_df.set_index('collect_date')[['food_kg', 'recycle_kg', 'general_kg']]
            chart_df.columns = ['음식물', '재활용', '일반']
            st.area_chart(chart_df, use_container_width=True)

            with st.expander("일별 상세", expanded=False):
                show_df = d_df.copy()
                show_df['collect_date'] = show_df['collect_date'].dt.strftime('%Y-%m-%d')
                st.dataframe(
                    show_df.rename(columns={
                        'collect_date': '날짜', 'total_kg': '합계',
                        'food_kg': '음식물', 'recycle_kg': '재활용',
                        'general_kg': '일반', 'count': '건수'
                    }),
                    use_container_width=True, hide_index=True
                )
        else:
            st.info("데이터 없음")

        st.divider()
        st.markdown("### 📊 요일별 평균")
        w_df = weekday_stats(all_rows, year_month=ym_val)
        if not w_df.empty:
            st.bar_chart(w_df.set_index('weekday_name')['avg_kg'], use_container_width=True)
            st.dataframe(
                w_df[['weekday_name', 'avg_kg', 'total_kg', 'count']].rename(columns={
                    'weekday_name': '요일', 'avg_kg': '평균(kg)',
                    'total_kg': '합계(kg)', 'count': '건수'
                }),
                use_container_width=True, hide_index=True
            )

        # 계절별 + 학사일정
        st.divider()
        col_s, col_p = st.columns(2)
        with col_s:
            st.markdown("### 🌸 계절별")
            s_df = seasonal_stats(all_rows)
            if not s_df.empty:
                st.bar_chart(s_df.set_index('season')['avg_daily_kg'], use_container_width=True)
                st.dataframe(
                    s_df[['season', 'total_kg', 'avg_daily_kg']].rename(columns={
                        'season': '계절', 'total_kg': '합계(kg)', 'avg_daily_kg': '일평균(kg)'
                    }),
                    use_container_width=True, hide_index=True
                )

        with col_p:
            st.markdown("### 🎓 학사일정별")
            p_df = school_period_stats(all_rows)
            if not p_df.empty:
                st.bar_chart(p_df.set_index('period')['avg_daily_kg'], use_container_width=True)
                st.dataframe(
                    p_df[['period', 'total_kg', 'avg_daily_kg']].rename(columns={
                        'period': '기간', 'total_kg': '합계(kg)', 'avg_daily_kg': '일평균(kg)'
                    }),
                    use_container_width=True, hide_index=True
                )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 3: 거래처·기사별
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab3:
        st.markdown("### 🏫 거래처별 수거량")
        sch_df = by_school_stats(all_rows, year_month=ym_val, top_n=20)
        if not sch_df.empty:
            st.bar_chart(sch_df.set_index('school_name')[['food_kg', 'recycle_kg']],
                         use_container_width=True)
            st.dataframe(
                sch_df.rename(columns={
                    'school_name': '거래처', 'total_kg': '합계(kg)',
                    'food_kg': '음식물(kg)', 'recycle_kg': '재활용(kg)', 'count': '건수'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("데이터 없음")

        st.divider()
        st.markdown("### 🚛 기사별 수거 실적")
        drv_df = by_driver_stats(all_rows, year_month=ym_val)
        if not drv_df.empty:
            st.bar_chart(drv_df.set_index('driver')['total_kg'], use_container_width=True)
            st.dataframe(
                drv_df.rename(columns={
                    'driver': '기사', 'total_kg': '합계(kg)',
                    'count': '건수', 'schools': '담당 거래처수'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("데이터 없음")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB 4: 기상 상관분석
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab4:
        st.markdown("### 🌤️ 기상 데이터 × 수거량 상관분석")
        st.caption("기상청 API 키(KMA_API_KEY)가 Streamlit Secrets에 설정되어 있어야 합니다.")

        col_w1, col_w2 = st.columns(2)
        with col_w1:
            w_start = st.date_input("시작일", key='va_w_start',
                                     value=datetime(datetime.now().year, datetime.now().month, 1))
        with col_w2:
            w_end = st.date_input("종료일", key='va_w_end',
                                   value=datetime.now())

        if st.button("기상 상관분석 실행", key='va_run_weather'):
            with st.spinner("기상 데이터 조회 중..."):
                try:
                    from services.weather_api import fetch_daily_weather
                    weather_result = fetch_daily_weather(
                        w_start.strftime('%Y-%m-%d'),
                        w_end.strftime('%Y-%m-%d')
                    )
                except ImportError:
                    weather_result = {'success': False, 'message': 'weather_api 모듈 없음', 'data': []}

                if not weather_result.get('success'):
                    st.error(f"기상 데이터 조회 실패: {weather_result.get('message')}")
                else:
                    st.success(weather_result.get('message', ''))
                    start_str = w_start.strftime('%Y-%m-%d')
                    end_str = w_end.strftime('%Y-%m-%d')
                    period_rows = [r for r in all_rows
                                   if start_str <= str(r.get('collect_date', ''))[:10] <= end_str]

                    result = weather_correlation(period_rows, weather_result['data'])
                    if result is None:
                        st.warning("병합할 데이터가 없습니다.")
                    else:
                        # 상관계수
                        st.markdown("#### 상관계수")
                        corr = result['correlations']
                        LABELS = {'temp_avg': '평균기온', 'rain': '강수량',
                                  'humidity': '습도', 'wind': '풍속'}
                        cols = st.columns(len(corr))
                        for idx, (k, v) in enumerate(corr.items()):
                            with cols[idx]:
                                color = "🔴" if abs(v) > 0.5 else "🟡" if abs(v) > 0.3 else "🟢"
                                st.metric(f"{color} {LABELS.get(k, k)}", f"{v:+.3f}")

                        st.divider()

                        # 비/맑음 비교
                        st.markdown("#### 비 오는 날 vs 맑은 날")
                        rv = result['rainy_vs_clear']
                        rc1, rc2, rc3 = st.columns(3)
                        with rc1:
                            st.metric("비 오는 날 평균", f"{rv['rainy_avg']:,.1f} kg")
                        with rc2:
                            st.metric("맑은 날 평균", f"{rv['clear_avg']:,.1f} kg")
                        with rc3:
                            st.metric("차이", f"{rv['diff_pct']:+.1f}%")

                        # 기온 구간별
                        if not result['temp_bins'].empty:
                            st.markdown("#### 기온 구간별 평균 수거량")
                            st.bar_chart(
                                result['temp_bins'].set_index('temp_range')['avg_kg'],
                                use_container_width=True
                            )

                        with st.expander("상세 데이터", expanded=False):
                            show_cols = ['date_key', 'total_kg', 'temp_avg', 'rain', 'humidity', 'wind']
                            avail = [c for c in show_cols if c in result['merged_df'].columns]
                            st.dataframe(
                                result['merged_df'][avail].rename(columns={
                                    'date_key': '날짜', 'total_kg': '수거량(kg)',
                                    'temp_avg': '기온(°C)', 'rain': '강수(mm)',
                                    'humidity': '습도(%)', 'wind': '풍속(m/s)'
                                }),
                                use_container_width=True, hide_index=True
                            )
