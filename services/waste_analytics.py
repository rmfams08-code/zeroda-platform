# services/waste_analytics.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 폐기물 수거 데이터 분석 모듈
# 일별/요일별/월별/계절별/거래처별/품목별/기사별 통계
# + 기상 데이터 상관분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict


# ── 계절 매핑 ──
SEASON_MAP = {
    1: '겨울', 2: '겨울', 3: '봄', 4: '봄', 5: '봄', 6: '여름',
    7: '여름', 8: '여름', 9: '가을', 10: '가을', 11: '가을', 12: '겨울'
}

# ── 학사일정 태그 (대략적 범위) ──
SCHOOL_PERIOD_MAP = {
    '방학(겨울)': [(1, 1), (2, 28)],
    '1학기':      [(3, 1), (7, 20)],
    '방학(여름)': [(7, 21), (8, 31)],
    '2학기':      [(9, 1), (12, 31)],
}


def _to_dataframe(rows):
    """수거 데이터(list of dict) → pandas DataFrame 변환 + 전처리"""
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # 날짜 파싱
    if 'collect_date' in df.columns:
        df['collect_date'] = pd.to_datetime(df['collect_date'], errors='coerce')
        df = df.dropna(subset=['collect_date'])
        df['year']    = df['collect_date'].dt.year
        df['month']   = df['collect_date'].dt.month
        df['day']     = df['collect_date'].dt.day
        df['weekday'] = df['collect_date'].dt.dayofweek          # 0=월 6=일
        df['weekday_name'] = df['collect_date'].dt.day_name()
        df['season']  = df['month'].map(SEASON_MAP)
        df['ym']      = df['collect_date'].dt.strftime('%Y-%m')   # 월별 집계용
        df['week']    = df['collect_date'].dt.isocalendar().week  # ISO 주차

    # 중량 숫자 변환
    if 'weight' in df.columns:
        df['weight'] = pd.to_numeric(df['weight'], errors='coerce').fillna(0)

    return df


# ──────────────────────────────────────────────
# 1. 기본 통계 함수
# ──────────────────────────────────────────────

def daily_stats(rows, year_month=None):
    """일별 수거량 집계
    Returns: DataFrame [collect_date, total_kg, food_kg, recycle_kg, general_kg, count]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year_month:
        df = df[df['ym'] == year_month]

    result = df.groupby(df['collect_date'].dt.date).agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
    ).reset_index()

    # 품목별 집계 추가
    for label, keyword in [('food_kg', '음식물'), ('recycle_kg', '재활용'), ('general_kg', '일반')]:
        sub = df[df['item_type'].str.contains(keyword, na=False)]
        sub_agg = sub.groupby(sub['collect_date'].dt.date)['weight'].sum().reset_index()
        sub_agg.columns = ['collect_date', label]
        result = result.merge(sub_agg, on='collect_date', how='left')
        result[label] = result[label].fillna(0)

    result = result.sort_values('collect_date')
    return result


def weekday_stats(rows, year_month=None):
    """요일별 평균 수거량
    Returns: DataFrame [weekday, weekday_name, avg_kg, total_kg, count]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year_month:
        df = df[df['ym'] == year_month]

    WEEKDAY_KR = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}

    result = df.groupby('weekday').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
    ).reset_index()

    # 해당 요일에 수거가 있었던 일수로 평균 계산
    day_counts = df.groupby('weekday')['collect_date'].apply(
        lambda x: x.dt.date.nunique()
    ).reset_index()
    day_counts.columns = ['weekday', 'day_count']
    result = result.merge(day_counts, on='weekday', how='left')
    result['avg_kg'] = (result['total_kg'] / result['day_count']).round(1)
    result['weekday_name'] = result['weekday'].map(WEEKDAY_KR)
    result = result.sort_values('weekday')
    return result


def monthly_stats(rows, year=None):
    """월별 수거량 집계
    Returns: DataFrame [ym, total_kg, food_kg, recycle_kg, general_kg, count, days]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year:
        df = df[df['year'] == year]

    result = df.groupby('ym').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
        days=('collect_date', lambda x: x.dt.date.nunique()),
    ).reset_index()

    for label, keyword in [('food_kg', '음식물'), ('recycle_kg', '재활용'), ('general_kg', '일반')]:
        sub = df[df['item_type'].str.contains(keyword, na=False)]
        sub_agg = sub.groupby('ym')['weight'].sum().reset_index()
        sub_agg.columns = ['ym', label]
        result = result.merge(sub_agg, on='ym', how='left')
        result[label] = result[label].fillna(0)

    result = result.sort_values('ym')
    return result


def seasonal_stats(rows):
    """계절별 수거량
    Returns: DataFrame [season, total_kg, avg_daily_kg, count]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    result = df.groupby('season').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
        days=('collect_date', lambda x: x.dt.date.nunique()),
    ).reset_index()
    result['avg_daily_kg'] = (result['total_kg'] / result['days']).round(1)

    season_order = {'봄': 0, '여름': 1, '가을': 2, '겨울': 3}
    result['_order'] = result['season'].map(season_order)
    result = result.sort_values('_order').drop(columns='_order')
    return result


def school_period_stats(rows):
    """학사일정별 수거량 (방학/학기 비교)
    Returns: DataFrame [period, total_kg, avg_daily_kg, count]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    def _get_period(dt):
        md = (dt.month, dt.day)
        for period_name, (start, end) in SCHOOL_PERIOD_MAP.items():
            if start <= md <= end:
                return period_name
        return '기타'

    df['period'] = df['collect_date'].apply(_get_period)

    result = df.groupby('period').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
        days=('collect_date', lambda x: x.dt.date.nunique()),
    ).reset_index()
    result['avg_daily_kg'] = (result['total_kg'] / result['days']).round(1)
    return result


# ──────────────────────────────────────────────
# 2. 차원별 분석 (거래처/품목/기사)
# ──────────────────────────────────────────────

def by_school_stats(rows, year_month=None, top_n=20):
    """거래처(학교)별 수거량 랭킹
    Returns: DataFrame [school_name, total_kg, food_kg, recycle_kg, count] (상위 top_n)
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year_month:
        df = df[df['ym'] == year_month]

    result = df.groupby('school_name').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
    ).reset_index()

    for label, keyword in [('food_kg', '음식물'), ('recycle_kg', '재활용')]:
        sub = df[df['item_type'].str.contains(keyword, na=False)]
        sub_agg = sub.groupby('school_name')['weight'].sum().reset_index()
        sub_agg.columns = ['school_name', label]
        result = result.merge(sub_agg, on='school_name', how='left')
        result[label] = result[label].fillna(0)

    result = result.sort_values('total_kg', ascending=False).head(top_n)
    return result


def by_item_stats(rows, year_month=None):
    """품목별 수거량
    Returns: DataFrame [item_type, total_kg, pct, count]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year_month:
        df = df[df['ym'] == year_month]

    result = df.groupby('item_type').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
    ).reset_index()

    total = result['total_kg'].sum()
    result['pct'] = ((result['total_kg'] / total) * 100).round(1) if total > 0 else 0
    result = result.sort_values('total_kg', ascending=False)
    return result


def by_driver_stats(rows, year_month=None):
    """기사별 수거량
    Returns: DataFrame [driver, total_kg, count, schools]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year_month:
        df = df[df['ym'] == year_month]

    if 'driver' not in df.columns:
        return pd.DataFrame()

    result = df.groupby('driver').agg(
        total_kg=('weight', 'sum'),
        count=('weight', 'count'),
        schools=('school_name', 'nunique'),
    ).reset_index()
    result = result.sort_values('total_kg', ascending=False)
    return result


# ──────────────────────────────────────────────
# 3. 추세 분석
# ──────────────────────────────────────────────

def trend_analysis(rows, period='monthly'):
    """전월/전주 대비 증감률 계산
    period: 'monthly' 또는 'weekly'
    Returns: DataFrame [..., change_kg, change_pct]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if period == 'monthly':
        grouped = df.groupby('ym')['weight'].sum().reset_index()
        grouped.columns = ['period', 'total_kg']
        grouped = grouped.sort_values('period')
    else:  # weekly
        df['yw'] = df['collect_date'].dt.strftime('%Y-W%V')
        grouped = df.groupby('yw')['weight'].sum().reset_index()
        grouped.columns = ['period', 'total_kg']
        grouped = grouped.sort_values('period')

    grouped['prev_kg'] = grouped['total_kg'].shift(1)
    grouped['change_kg'] = grouped['total_kg'] - grouped['prev_kg']
    grouped['change_pct'] = (
        (grouped['change_kg'] / grouped['prev_kg']) * 100
    ).round(1)

    return grouped


# ──────────────────────────────────────────────
# 4. 기상 상관분석
# ──────────────────────────────────────────────

def weather_correlation(collection_rows, weather_data):
    """수거량 × 날씨 상관분석
    collection_rows: real_collection 데이터
    weather_data: weather_api.fetch_daily_weather()['data'] 결과
    Returns: dict {
        'merged_df': DataFrame,
        'correlations': {temp_avg: r, rain: r, humidity: r, wind: r},
        'rainy_vs_clear': {rainy_avg: float, clear_avg: float, diff_pct: float},
        'temp_bins': DataFrame [temp_range, avg_kg],
    }
    """
    cdf = _to_dataframe(collection_rows)
    if cdf.empty or not weather_data:
        return None

    wdf = pd.DataFrame(weather_data)
    if wdf.empty:
        return None

    # 날짜 키 통일
    cdf['date_key'] = cdf['collect_date'].dt.strftime('%Y-%m-%d')
    wdf['date_key'] = wdf['date'].astype(str)

    # 일별 수거량 합산
    daily = cdf.groupby('date_key')['weight'].sum().reset_index()
    daily.columns = ['date_key', 'total_kg']

    # 병합
    merged = daily.merge(wdf, on='date_key', how='inner')
    if merged.empty:
        return None

    # 숫자 컬럼 확인
    for col in ['temp_avg', 'temp_max', 'temp_min', 'rain', 'humidity', 'wind']:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)

    # 상관계수 계산
    weather_cols = [c for c in ['temp_avg', 'rain', 'humidity', 'wind'] if c in merged.columns]
    correlations = {}
    for col in weather_cols:
        corr = merged['total_kg'].corr(merged[col])
        correlations[col] = round(corr, 3) if pd.notna(corr) else 0

    # 비 오는 날 vs 맑은 날 비교
    rainy = merged[merged['rain'] > 0.5]['total_kg']
    clear = merged[merged['rain'] <= 0.5]['total_kg']
    rainy_avg = round(rainy.mean(), 1) if len(rainy) > 0 else 0
    clear_avg = round(clear.mean(), 1) if len(clear) > 0 else 0
    diff_pct = round(((rainy_avg - clear_avg) / clear_avg) * 100, 1) if clear_avg > 0 else 0

    # 기온 구간별 수거량
    if 'temp_avg' in merged.columns and len(merged) > 5:
        bins = [-100, 0, 10, 20, 30, 50]
        labels = ['영하', '0~10°C', '10~20°C', '20~30°C', '30°C+']
        merged['temp_range'] = pd.cut(merged['temp_avg'], bins=bins, labels=labels)
        temp_bins = merged.groupby('temp_range', observed=True)['total_kg'].mean().reset_index()
        temp_bins.columns = ['temp_range', 'avg_kg']
        temp_bins['avg_kg'] = temp_bins['avg_kg'].round(1)
    else:
        temp_bins = pd.DataFrame()

    return {
        'merged_df': merged,
        'correlations': correlations,
        'rainy_vs_clear': {
            'rainy_avg': rainy_avg,
            'clear_avg': clear_avg,
            'diff_pct': diff_pct
        },
        'temp_bins': temp_bins,
    }


# ──────────────────────────────────────────────
# 5. 이상치 탐지
# ──────────────────────────────────────────────

def detect_anomalies(rows, year_month=None, threshold=2.0):
    """일별 수거량에서 이상치(평균 ± threshold×σ 벗어남) 탐지
    Returns: DataFrame [collect_date, total_kg, z_score, is_anomaly]
    """
    df = _to_dataframe(rows)
    if df.empty:
        return pd.DataFrame()

    if year_month:
        df = df[df['ym'] == year_month]

    daily = df.groupby(df['collect_date'].dt.date)['weight'].sum().reset_index()
    daily.columns = ['collect_date', 'total_kg']

    if len(daily) < 3:
        return pd.DataFrame()

    mean_kg = daily['total_kg'].mean()
    std_kg = daily['total_kg'].std()

    if std_kg == 0:
        daily['z_score'] = 0
    else:
        daily['z_score'] = ((daily['total_kg'] - mean_kg) / std_kg).round(2)

    daily['is_anomaly'] = daily['z_score'].abs() > threshold
    daily = daily.sort_values('collect_date')
    return daily


# ──────────────────────────────────────────────
# 6. 요약 대시보드용 KPI 생성
# ──────────────────────────────────────────────

def summary_kpis(rows, year_month=None):
    """한 눈에 보는 KPI 딕셔너리
    Returns: dict {
        total_kg, food_kg, recycle_kg, general_kg,
        avg_daily_kg, collection_days, school_count, driver_count,
        top_school, top_school_kg,
        mom_change_pct (전월대비),
    }
    """
    df = _to_dataframe(rows)
    if df.empty:
        return {}

    # 현재 월 필터
    if year_month:
        curr = df[df['ym'] == year_month]
    else:
        curr = df

    if curr.empty:
        return {}

    total_kg = round(curr['weight'].sum(), 1)
    food_kg = round(curr[curr['item_type'].str.contains('음식물', na=False)]['weight'].sum(), 1)
    recycle_kg = round(curr[curr['item_type'].str.contains('재활용', na=False)]['weight'].sum(), 1)
    general_kg = round(total_kg - food_kg - recycle_kg, 1)

    days = curr['collect_date'].dt.date.nunique()
    avg_daily = round(total_kg / days, 1) if days > 0 else 0

    school_count = curr['school_name'].nunique() if 'school_name' in curr.columns else 0
    driver_count = curr['driver'].nunique() if 'driver' in curr.columns else 0

    # Top 거래처
    top_school = ''
    top_school_kg = 0
    if 'school_name' in curr.columns:
        school_sum = curr.groupby('school_name')['weight'].sum()
        if len(school_sum) > 0:
            top_school = school_sum.idxmax()
            top_school_kg = round(school_sum.max(), 1)

    # 전월 대비 변화율
    mom_change_pct = None
    if year_month:
        try:
            ym_dt = datetime.strptime(year_month, '%Y-%m')
            prev_ym = (ym_dt.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
            prev = df[df['ym'] == prev_ym]
            prev_total = prev['weight'].sum()
            if prev_total > 0:
                mom_change_pct = round(((total_kg - prev_total) / prev_total) * 100, 1)
        except Exception:
            pass

    return {
        'total_kg': total_kg,
        'food_kg': food_kg,
        'recycle_kg': recycle_kg,
        'general_kg': general_kg,
        'avg_daily_kg': avg_daily,
        'collection_days': days,
        'school_count': school_count,
        'driver_count': driver_count,
        'top_school': top_school,
        'top_school_kg': top_school_kg,
        'mom_change_pct': mom_change_pct,
    }
