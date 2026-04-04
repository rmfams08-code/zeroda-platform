# services/weather_api.py
# 기상청 공공데이터포털 Open API — 지상관측 일자료 조회
import streamlit as st
import json
import os
from datetime import datetime, date
from zoneinfo import ZoneInfo


# ── 관측지점 코드 (화성·오산·서울 인근 주요 AWS 지점) ──
STATION_MAP = {
    '수원': 119,   # 화성·오산 인근 대표 관측소
    '서울': 108,
    '인천': 112,
    '이천': 203,
}
DEFAULT_STATION = 119  # 수원 (화성-오산 지역)


def _get_api_key():
    """기상청 API 키 조회 (Streamlit secrets → 환경변수)"""
    try:
        if hasattr(st, 'secrets') and 'KMA_API_KEY' in st.secrets:
            return st.secrets['KMA_API_KEY']
    except Exception:
        pass
    key = os.environ.get('KMA_API_KEY', '')
    return key if key else None


def fetch_daily_weather(start_date: str, end_date: str,
                        station_id: int = DEFAULT_STATION):
    """
    기상청 지상관측 일자료 조회.
    start_date, end_date: 'YYYY-MM-DD' 형식
    반환: dict {
        'success': bool,
        'message': str,
        'data': [
            {'date': 'YYYY-MM-DD', 'temp_avg': float, 'temp_max': float,
             'temp_min': float, 'rain': float, 'humidity': float},
            ...
        ]
    }
    """
    api_key = _get_api_key()
    if not api_key:
        return {
            'success': False,
            'message': 'KMA_API_KEY가 설정되지 않았습니다. '
                       'Streamlit Secrets에 KMA_API_KEY를 추가하세요.',
            'data': []
        }

    # 날짜 포맷 변환 (YYYY-MM-DD → YYYYMMDD)
    try:
        sd = start_date.replace('-', '')
        ed = end_date.replace('-', '')
    except Exception:
        return {'success': False, 'message': '날짜 형식 오류', 'data': []}

    import urllib.request
    import urllib.parse

    # 기상청 ASOS 일자료 API (공공데이터포털 경유)
    base_url = 'https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList'
    params = {
        'serviceKey': api_key,
        'numOfRows': '100',
        'pageNo': '1',
        'dataType': 'JSON',
        'dataCd': 'ASOS',
        'dateCd': 'DAY',
        'startDt': sd,
        'endDt': ed,
        'stnIds': str(station_id),
    }

    url = base_url + '?' + urllib.parse.urlencode(params, safe='=+/')

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
            result = json.loads(raw)
    except Exception as e:
        return {
            'success': False,
            'message': f'API 호출 실패: {e}',
            'data': []
        }

    # 응답 파싱
    try:
        header = result.get('response', {}).get('header', {})
        result_code = header.get('resultCode', '')
        if result_code != '00':
            return {
                'success': False,
                'message': f"API 오류: {header.get('resultMsg', result_code)}",
                'data': []
            }

        items = (result.get('response', {})
                       .get('body', {})
                       .get('items', {})
                       .get('item', []))
        if not isinstance(items, list):
            items = [items] if items else []

        weather_data = []
        for item in items:
            dt_str = str(item.get('tm', ''))
            if len(dt_str) == 8:
                dt_fmt = f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]}"
            else:
                dt_fmt = dt_str

            weather_data.append({
                'date':     dt_fmt,
                'temp_avg': _safe_float(item.get('avgTa')),    # 평균기온
                'temp_max': _safe_float(item.get('maxTa')),    # 최고기온
                'temp_min': _safe_float(item.get('minTa')),    # 최저기온
                'rain':     _safe_float(item.get('sumRn')),    # 일강수량
                'humidity': _safe_float(item.get('avgRhm')),   # 평균습도
                'wind':     _safe_float(item.get('avgWs')),    # 평균풍속
            })

        return {
            'success': True,
            'message': f'{len(weather_data)}일 날씨 데이터 조회 완료',
            'data': weather_data
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'응답 파싱 오류: {e}',
            'data': []
        }


def fetch_today_weather_alert(station_id: int = DEFAULT_STATION):
    """
    기사모드용: 오늘(또는 전일) 날씨 조회 → 주의 알림 생성.
    Returns: dict {
        'available': bool,        # 날씨 데이터 사용 가능 여부
        'weather': dict or None,  # {date, temp_avg, temp_max, temp_min, rain, humidity, wind}
        'alerts': list[str],      # 주의 알림 메시지 목록
        'summary': str,           # 한 줄 요약 ("맑음 12°C" 등)
        'icon': str,              # 대표 아이콘
        'level': str,             # 'normal', 'caution', 'warning'
    }
    """
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    today_str = now.strftime('%Y-%m-%d')
    yesterday = (now.date() - __import__('datetime').timedelta(days=1))
    yesterday_str = yesterday.strftime('%Y-%m-%d')

    # 오늘 + 어제 2일치 조회 (오늘 데이터 미등록 시 어제 사용)
    result = fetch_daily_weather(yesterday_str, today_str, station_id)

    if not result.get('success') or not result.get('data'):
        return {
            'available': False, 'weather': None,
            'alerts': [], 'summary': '날씨 정보 없음',
            'icon': '🌐', 'level': 'normal'
        }

    # 오늘 데이터 우선, 없으면 어제
    data_list = result['data']
    weather = None
    for d in reversed(data_list):
        if d.get('date') == today_str:
            weather = d
            break
    if weather is None:
        weather = data_list[-1]  # 가장 최근

    # ── 알림 생성 로직 ──
    alerts = []
    level = 'normal'
    icon = '☀️'

    temp_avg = weather.get('temp_avg', 0)
    temp_max = weather.get('temp_max', 0)
    temp_min = weather.get('temp_min', 0)
    rain = weather.get('rain', 0)
    humidity = weather.get('humidity', 0)
    wind = weather.get('wind', 0)

    # 강수 알림
    if rain > 30:
        alerts.append(f"🌧️ 강수량 {rain}mm — 폭우 주의! 안전운행 필수, 미끄러움 주의")
        level = 'warning'
        icon = '🌧️'
    elif rain > 10:
        alerts.append(f"🌧️ 강수량 {rain}mm — 비 주의. 우비/장화 준비")
        level = 'caution'
        icon = '🌧️'
    elif rain > 0.5:
        alerts.append(f"🌂 강수량 {rain}mm — 약한 비. 우의 준비")
        if level == 'normal':
            level = 'caution'
            icon = '🌂'

    # 폭염 알림
    if temp_max >= 35:
        alerts.append(f"🔥 최고 {temp_max}°C 폭염 — 온열질환 주의! 충분한 수분 섭취")
        level = 'warning'
        icon = '🔥'
    elif temp_max >= 30:
        alerts.append(f"☀️ 최고 {temp_max}°C — 더위 주의. 수분 보충 권장")
        if level == 'normal':
            level = 'caution'

    # 한파 알림
    if temp_min <= -10:
        alerts.append(f"🥶 최저 {temp_min}°C 한파 — 노면 결빙 주의! 서행 운전")
        level = 'warning'
        icon = '🥶'
    elif temp_min <= 0:
        alerts.append(f"❄️ 최저 {temp_min}°C — 결빙 가능. 출발 전 워밍업")
        if level == 'normal':
            level = 'caution'
            icon = '❄️'

    # 강풍 알림
    if wind >= 10:
        alerts.append(f"💨 평균풍속 {wind}m/s 강풍 — 적재물 고정 확인!")
        level = 'warning'
        icon = '💨'
    elif wind >= 7:
        alerts.append(f"🌬️ 풍속 {wind}m/s — 바람 주의. 적재물 확인")
        if level == 'normal':
            level = 'caution'

    # 고습도 알림
    if humidity >= 90:
        alerts.append(f"💧 습도 {humidity}% — 안개/시야 불량 가능. 전조등 사용")
        if level == 'normal':
            level = 'caution'

    # 알림 없으면 좋은 날씨
    if not alerts:
        alerts.append("수거 작업에 좋은 날씨입니다. 안전 운행하세요!")

    # 한 줄 요약 생성
    if rain > 0.5:
        weather_desc = f"비 {rain}mm"
    elif temp_max >= 30:
        weather_desc = "맑음(더위)"
    elif temp_min <= 0:
        weather_desc = "추움"
    else:
        weather_desc = "맑음"

    summary = f"{weather_desc} {temp_avg:.0f}°C (최저 {temp_min:.0f}° / 최고 {temp_max:.0f}°)"

    return {
        'available': True,
        'weather': weather,
        'alerts': alerts,
        'summary': summary,
        'icon': icon,
        'level': level,
    }


def _safe_float(val):
    """안전한 float 변환 (None, 빈문자열 → 0.0)"""
    if val is None or val == '':
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
