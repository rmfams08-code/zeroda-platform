# services/weather_api.py
# 기상청 공공데이터포털 Open API
# ① 지상관측 일자료 (ASOS) — 과거 데이터 분석용
# ② 초단기실황 조회 — 당일 실시간 날씨 (기사 알림용)
import streamlit as st
import json
import os
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


# ── 관측지점 코드 (ASOS 일자료용) ──
STATION_MAP = {
    '수원': 119,   # 화성·오산 인근 대표 관측소
    '서울': 108,
    '인천': 112,
    '이천': 203,
}
DEFAULT_STATION = 119  # 수원 (화성-오산 지역)

# ── 초단기실황 격자 좌표 (단기예보용 nx, ny) ──
# 기상청 격자 변환표 기준
GRID_MAP = {
    '화성': (57, 119),   # 화성시
    '오산': (58, 118),   # 오산시
    '수원': (60, 121),   # 수원시
    '서울': (60, 127),   # 서울 중구
    '인천': (55, 124),   # 인천
}
DEFAULT_GRID = (57, 119)  # 화성시 기본


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


def fetch_ultra_srt_ncst(nx: int = None, ny: int = None):
    """
    초단기실황 조회 — 현재 시각 기준 실시간 날씨.
    기상청 단기예보 조회서비스 > getUltraSrtNcst
    Returns: dict {
        'success': bool,
        'message': str,
        'data': {
            'temp': float,       # 기온 (T1H)
            'rain_1h': float,    # 1시간 강수량 (RN1)
            'humidity': float,   # 습도 (REH)
            'wind': float,       # 풍속 (WSD)
            'rain_type': int,    # 강수형태 (PTY) 0없음 1비 2비/눈 3눈 5빗방울 6빗방울/눈날림 7눈날림
            'base_time': str,    # 발표시각
        }
    }
    """
    api_key = _get_api_key()
    if not api_key:
        return {'success': False, 'message': 'KMA_API_KEY 미설정', 'data': {}}

    if nx is None or ny is None:
        nx, ny = DEFAULT_GRID

    import urllib.request
    import urllib.parse

    now = datetime.now(ZoneInfo('Asia/Seoul'))

    # 초단기실황은 매시 정각 발표, 40분 이후 조회 가능
    # 예: 13시 실황 → 13:40 이후 조회 가능
    # 현재 시각이 40분 이전이면 1시간 전 발표 데이터 사용
    if now.minute < 40:
        base = now - timedelta(hours=1)
    else:
        base = now

    base_date = base.strftime('%Y%m%d')
    base_time = base.strftime('%H00')

    url_base = 'https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
    params = {
        'serviceKey': api_key,
        'numOfRows': '10',
        'pageNo': '1',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': str(nx),
        'ny': str(ny),
    }

    url = url_base + '?' + urllib.parse.urlencode(params, safe='=+/')

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            result = json.loads(raw)
    except Exception as e:
        return {'success': False, 'message': f'초단기실황 API 호출 실패: {e}', 'data': {}}

    try:
        header = result.get('response', {}).get('header', {})
        if header.get('resultCode') != '00':
            return {
                'success': False,
                'message': f"초단기실황 오류: {header.get('resultMsg', '')}",
                'data': {}
            }

        items = (result.get('response', {})
                       .get('body', {})
                       .get('items', {})
                       .get('item', []))
        if not isinstance(items, list):
            items = [items] if items else []

        # 카테고리별 파싱
        data = {
            'temp': 0.0, 'rain_1h': 0.0, 'humidity': 0.0,
            'wind': 0.0, 'rain_type': 0, 'base_time': base_time,
        }
        CAT_MAP = {
            'T1H': 'temp',       # 기온
            'RN1': 'rain_1h',    # 1시간 강수량
            'REH': 'humidity',   # 습도
            'WSD': 'wind',       # 풍속
            'PTY': 'rain_type',  # 강수형태
        }
        for item in items:
            cat = item.get('category', '')
            if cat in CAT_MAP:
                val = _safe_float(item.get('obsrValue', 0))
                data[CAT_MAP[cat]] = val

        return {
            'success': True,
            'message': f'초단기실황 조회 완료 ({base_date} {base_time})',
            'data': data
        }

    except Exception as e:
        return {'success': False, 'message': f'초단기실황 파싱 오류: {e}', 'data': {}}


def fetch_today_weather_alert(nx: int = None, ny: int = None,
                              station_id: int = DEFAULT_STATION):
    """
    기사모드용: 초단기실황(실시간) 우선 → ASOS(전일) 폴백 → 알림 생성.
    Returns: dict {
        'available': bool,
        'weather': dict or None,
        'alerts': list[str],
        'summary': str,
        'icon': str,
        'level': str,     # 'normal', 'caution', 'warning'
        'source': str,    # 'realtime' 또는 'yesterday'
    }
    """
    # ── 1차: 초단기실황 (실시간) ──
    rt = fetch_ultra_srt_ncst(nx, ny)
    if rt.get('success') and rt.get('data'):
        d = rt['data']
        temp = d.get('temp', 0)
        rain_1h = d.get('rain_1h', 0)
        humidity = d.get('humidity', 0)
        wind = d.get('wind', 0)
        rain_type = int(d.get('rain_type', 0))

        alerts = []
        level = 'normal'
        icon = '☀️'

        # 강수형태 알림
        RAIN_TYPE_NAMES = {1: '비', 2: '비/눈', 3: '눈', 5: '빗방울', 6: '빗방울/눈', 7: '눈날림'}
        if rain_type > 0:
            rname = RAIN_TYPE_NAMES.get(rain_type, '강수')
            if rain_1h > 30:
                alerts.append(f"🌧️ {rname} — 시간당 {rain_1h}mm 폭우! 안전운행 필수")
                level = 'warning'
                icon = '🌧️'
            elif rain_1h > 5:
                alerts.append(f"🌧️ {rname} — 시간당 {rain_1h}mm. 우비/장화 준비")
                level = 'caution'
                icon = '🌧️'
            else:
                alerts.append(f"🌂 {rname} — 약한 강수. 우의 준비")
                level = 'caution'
                icon = '🌂' if rain_type <= 2 else '❄️'

        # 기온 알림
        if temp >= 35:
            alerts.append(f"🔥 현재 {temp}°C 폭염 — 온열질환 주의! 수분 섭취 필수")
            level = 'warning'
            icon = '🔥'
        elif temp >= 30:
            alerts.append(f"☀️ 현재 {temp}°C — 더위 주의. 수분 보충 권장")
            if level == 'normal':
                level = 'caution'
        elif temp <= -10:
            alerts.append(f"🥶 현재 {temp}°C 한파 — 노면 결빙 주의! 서행 운전")
            level = 'warning'
            icon = '🥶'
        elif temp <= 0:
            alerts.append(f"❄️ 현재 {temp}°C — 결빙 가능. 출발 전 워밍업")
            if level == 'normal':
                level = 'caution'
                icon = '❄️'

        # 강풍 알림
        if wind >= 10:
            alerts.append(f"💨 풍속 {wind}m/s 강풍 — 적재물 고정 확인!")
            level = 'warning'
            icon = '💨'
        elif wind >= 7:
            alerts.append(f"🌬️ 풍속 {wind}m/s — 바람 주의. 적재물 확인")
            if level == 'normal':
                level = 'caution'

        # 고습도
        if humidity >= 90:
            alerts.append(f"💧 습도 {humidity}% — 안개/시야 불량 가능. 전조등 사용")
            if level == 'normal':
                level = 'caution'

        if not alerts:
            alerts.append("수거 작업에 좋은 날씨입니다. 안전 운행하세요!")

        # 요약
        if rain_type > 0:
            rname = RAIN_TYPE_NAMES.get(rain_type, '강수')
            weather_desc = f"{rname} {rain_1h}mm/h"
        elif temp >= 30:
            weather_desc = "맑음(더위)"
        elif temp <= 0:
            weather_desc = "추움"
        else:
            weather_desc = "맑음"

        base_t = d.get('base_time', '')
        time_label = f"{base_t[:2]}:{base_t[2:]}" if len(base_t) == 4 else base_t
        summary = f"{weather_desc} {temp:.0f}°C | 습도 {humidity:.0f}% | 풍속 {wind:.0f}m/s ({time_label} 기준)"

        return {
            'available': True,
            'weather': d,
            'alerts': alerts,
            'summary': summary,
            'icon': icon,
            'level': level,
            'source': 'realtime',
        }

    # ── 2차 폴백: ASOS 전일 데이터 ──
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    yesterday_str = (now.date() - timedelta(days=1)).strftime('%Y-%m-%d')
    result = fetch_daily_weather(yesterday_str, yesterday_str, station_id)

    if not result.get('success') or not result.get('data'):
        return {
            'available': False, 'weather': None,
            'alerts': [], 'summary': '날씨 정보를 조회할 수 없습니다',
            'icon': '🌐', 'level': 'normal', 'source': 'none',
        }

    weather = result['data'][-1]
    temp_avg = weather.get('temp_avg', 0)
    rain = weather.get('rain', 0)
    humidity = weather.get('humidity', 0)
    wind = weather.get('wind', 0)

    alerts = []
    level = 'normal'
    icon = '☀️'

    if rain > 10:
        alerts.append(f"🌧️ 어제 강수 {rain}mm — 오늘도 비 가능성. 우의 준비")
        level = 'caution'
        icon = '🌧️'
    if temp_avg >= 28:
        alerts.append(f"☀️ 어제 평균 {temp_avg}°C — 오늘도 더위 예상. 수분 보충")
        if level == 'normal':
            level = 'caution'
    if temp_avg <= 2:
        alerts.append(f"❄️ 어제 평균 {temp_avg}°C — 노면 결빙 가능. 서행 운전")
        if level == 'normal':
            level = 'caution'
            icon = '❄️'
    if wind >= 7:
        alerts.append(f"🌬️ 어제 풍속 {wind}m/s — 바람 주의")
        if level == 'normal':
            level = 'caution'

    if not alerts:
        alerts.append("수거 작업에 좋은 날씨입니다. 안전 운행하세요!")

    summary = f"(어제 기준) {temp_avg:.0f}°C | 강수 {rain}mm | 풍속 {wind}m/s"

    return {
        'available': True,
        'weather': weather,
        'alerts': alerts,
        'summary': summary,
        'icon': icon,
        'level': level,
        'source': 'yesterday',
    }


def _safe_float(val):
    """안전한 float 변환 (None, 빈문자열 → 0.0)"""
    if val is None or val == '':
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
