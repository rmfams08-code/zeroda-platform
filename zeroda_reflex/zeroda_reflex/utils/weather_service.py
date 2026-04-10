# zeroda_reflex/utils/weather_service.py
# 기상청 공공데이터포털 Open API (Reflex 전용)
# ① 지상관측 일자료 (ASOS) — 과거 데이터 분석용
# ② 초단기실황 조회 — 당일 실시간 날씨 (기사 알림용)
import json
import math
import os
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# ── 관측지점 코드 (ASOS 일자료용) ──
STATION_MAP = {
    "수원": 119,   # 화성·오산 인근 대표 관측소
    "서울": 108,
    "인천": 112,
    "이천": 203,
}
DEFAULT_STATION = 119  # 수원 (화성-오산 지역)

# ── 초단기실황 격자 좌표 ──
GRID_MAP = {
    "화성": (57, 119),
    "오산": (58, 118),
    "수원": (60, 121),
    "서울": (60, 127),
    "인천": (55, 124),
    "평택": (52, 110),
    "안양": (59, 124),
    "안산": (56, 122),
    "시흥": (57, 123),
    "광명": (58, 125),
    "군포": (59, 122),
    "의왕": (60, 122),
    "용인": (64, 119),
    "성남": (63, 124),
    "과천": (60, 124),
    "서초": (61, 125),
    "강남": (61, 126),
    "동작": (60, 126),
    "관악": (59, 125),
    "금천": (58, 125),
    "영등포": (58, 126),
    "구로": (58, 126),
}
DEFAULT_GRID = (57, 119)  # 화성시 기본


def grid_to_region(nx: int, ny: int) -> str:
    """격자 좌표 (nx, ny) → 가장 가까운 지역명 반환 (유클리드 거리)"""
    best_name = "화성"
    best_dist = float("inf")
    for name, (gx, gy) in GRID_MAP.items():
        dist = (nx - gx) ** 2 + (ny - gy) ** 2
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name

# ── 위경도 → 기상청 격자 변환 (Lambert Conformal Conic) ──

def latlon_to_grid(lat: float, lon: float) -> tuple:
    """위경도 → 기상청 초단기실황 격자 좌표 (nx, ny) 변환.
    기상청 공식 파라미터 사용.
    """
    RE = 6371.00877   # 지구반경 (km)
    GRID = 5.0        # 격자 간격 (km)
    SLAT1 = 30.0      # 표준위도 1
    SLAT2 = 60.0      # 표준위도 2
    OLON = 126.0      # 기준점 경도
    OLAT = 38.0       # 기준점 위도
    XO = 43.0         # 기준점 격자 X
    YO = 136.0        # 기준점 격자 Y

    DEGRAD = math.pi / 180.0

    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(ra * math.sin(theta) + XO + 0.5)
    ny = int(ro - ra * math.cos(theta) + YO + 0.5)
    return nx, ny


# ── 강수형태 코드 ──
RAIN_TYPE_NAMES = {
    1: "비", 2: "비/눈", 3: "눈",
    5: "빗방울", 6: "빗방울/눈", 7: "눈날림",
}


def _get_api_key() -> str | None:
    """기상청 API 키 조회 (환경변수)"""
    key = os.environ.get("KMA_API_KEY", "")
    return key if key else None


def _safe_float(val) -> float:
    """안전한 float 변환"""
    if val is None or val == "":
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# ══════════════════════════════════════════
#  ASOS 일자료 (과거 날씨)
# ══════════════════════════════════════════

def fetch_daily_weather(
    start_date: str,
    end_date: str,
    station_id: int = DEFAULT_STATION,
) -> dict:
    """
    기상청 지상관측 일자료 조회.
    start_date, end_date: 'YYYY-MM-DD' 형식
    """
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "message": "KMA_API_KEY 미설정", "data": []}

    try:
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")
    except Exception:
        return {"success": False, "message": "날짜 형식 오류", "data": []}

    base_url = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
    params = {
        "serviceKey": api_key,
        "numOfRows": "100",
        "pageNo": "1",
        "dataType": "JSON",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": sd,
        "endDt": ed,
        "stnIds": str(station_id),
    }
    url = base_url + "?" + urllib.parse.urlencode(params, safe="=+/")

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw)
    except Exception as e:
        logger.warning(f"ASOS API 호출 실패: {e}")
        return {"success": False, "message": f"API 호출 실패: {e}", "data": []}

    try:
        header = result.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            return {
                "success": False,
                "message": f"API 오류: {header.get('resultMsg', '')}",
                "data": [],
            }

        items = (
            result.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if not isinstance(items, list):
            items = [items] if items else []

        weather_data = []
        for item in items:
            dt_str = str(item.get("tm", ""))
            dt_fmt = (
                f"{dt_str[:4]}-{dt_str[4:6]}-{dt_str[6:8]}"
                if len(dt_str) == 8
                else dt_str
            )
            weather_data.append({
                "date": dt_fmt,
                "temp_avg": _safe_float(item.get("avgTa")),
                "temp_max": _safe_float(item.get("maxTa")),
                "temp_min": _safe_float(item.get("minTa")),
                "rain": _safe_float(item.get("sumRn")),
                "humidity": _safe_float(item.get("avgRhm")),
                "wind": _safe_float(item.get("avgWs")),
            })

        return {
            "success": True,
            "message": f"{len(weather_data)}일 날씨 데이터 조회 완료",
            "data": weather_data,
        }
    except Exception as e:
        logger.warning(f"ASOS 파싱 오류: {e}")
        return {"success": False, "message": f"파싱 오류: {e}", "data": []}


# ══════════════════════════════════════════
#  초단기실황 (실시간 날씨)
# ══════════════════════════════════════════

def fetch_ultra_srt_ncst(
    nx: int | None = None,
    ny: int | None = None,
) -> dict:
    """초단기실황 조회 — 현재 시각 기준 실시간 날씨"""
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "message": "KMA_API_KEY 미설정", "data": {}}

    if nx is None or ny is None:
        nx, ny = DEFAULT_GRID

    now = datetime.now(ZoneInfo("Asia/Seoul"))
    # 매시 정각 발표, 40분 이후 조회 가능
    if now.minute < 40:
        base = now - timedelta(hours=1)
    else:
        base = now

    base_date = base.strftime("%Y%m%d")
    base_time = base.strftime("%H00")

    url_base = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    params = {
        "serviceKey": api_key,
        "numOfRows": "10",
        "pageNo": "1",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny),
    }
    url = url_base + "?" + urllib.parse.urlencode(params, safe="=+/")

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            result = json.loads(raw)
    except Exception as e:
        logger.warning(f"초단기실황 API 호출 실패: {e}")
        return {"success": False, "message": f"초단기실황 호출 실패: {e}", "data": {}}

    try:
        header = result.get("response", {}).get("header", {})
        if header.get("resultCode") != "00":
            return {
                "success": False,
                "message": f"초단기실황 오류: {header.get('resultMsg', '')}",
                "data": {},
            }

        items = (
            result.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )
        if not isinstance(items, list):
            items = [items] if items else []

        data = {
            "temp": 0.0,
            "rain_1h": 0.0,
            "humidity": 0.0,
            "wind": 0.0,
            "rain_type": 0,
            "base_time": base_time,
        }
        CAT_MAP = {
            "T1H": "temp",
            "RN1": "rain_1h",
            "REH": "humidity",
            "WSD": "wind",
            "PTY": "rain_type",
        }
        for item in items:
            cat = item.get("category", "")
            if cat in CAT_MAP:
                data[CAT_MAP[cat]] = _safe_float(item.get("obsrValue", 0))

        return {
            "success": True,
            "message": f"초단기실황 조회 완료 ({base_date} {base_time})",
            "data": data,
        }
    except Exception as e:
        logger.warning(f"초단기실황 파싱 오류: {e}")
        return {"success": False, "message": f"파싱 오류: {e}", "data": {}}


# ══════════════════════════════════════════
#  기사모드용 날씨 알림 생성
# ══════════════════════════════════════════

def fetch_today_weather_alert(
    nx: int | None = None,
    ny: int | None = None,
    station_id: int = DEFAULT_STATION,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """
    기사모드용 날씨 알림.
    lat/lon 제공 시 GPS 좌표를 격자로 변환 (nx/ny 우선).
    초단기실황(실시간) 우선 → ASOS(전일) 폴백 → 알림 생성.
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
    # GPS 좌표 → 격자 변환 (lat/lon 제공 시, nx/ny 미지정인 경우)
    if lat is not None and lon is not None and nx is None and ny is None:
        try:
            nx, ny = latlon_to_grid(lat, lon)
        except Exception as e:
            logger.warning(f"위경도→격자 변환 실패: {e}")

    # 격자 좌표 → 지역명 결정
    _used_nx = nx if nx is not None else DEFAULT_GRID[0]
    _used_ny = ny if ny is not None else DEFAULT_GRID[1]
    location = grid_to_region(_used_nx, _used_ny)

    # ── 1차: 초단기실황 (실시간) ──
    rt = fetch_ultra_srt_ncst(nx, ny)
    if rt.get("success") and rt.get("data"):
        alert = _build_realtime_alert(rt["data"])
        alert["location"] = location
        return alert

    # ── 2차 폴백: ASOS 전일 데이터 ──
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    yesterday_str = (now.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    result = fetch_daily_weather(yesterday_str, yesterday_str, station_id)

    if not result.get("success") or not result.get("data"):
        return {
            "available": False,
            "weather": None,
            "alerts": [],
            "summary": "날씨 정보를 조회할 수 없습니다",
            "icon": "🌐",
            "level": "normal",
            "source": "none",
            "location": location,
        }

    alert = _build_yesterday_alert(result["data"][-1])
    alert["location"] = location
    return alert


def _build_realtime_alert(d: dict) -> dict:
    """실시간 날씨 기반 알림 생성"""
    temp = d.get("temp", 0)
    rain_1h = d.get("rain_1h", 0)
    humidity = d.get("humidity", 0)
    wind = d.get("wind", 0)
    rain_type = int(d.get("rain_type", 0))

    alerts: list[str] = []
    level = "normal"
    icon = "☀️"

    # 강수형태 알림
    if rain_type > 0:
        rname = RAIN_TYPE_NAMES.get(rain_type, "강수")
        if rain_1h > 30:
            alerts.append(f"🌧️ {rname} — 시간당 {rain_1h}mm 폭우! 안전운행 필수")
            level = "warning"
            icon = "🌧️"
        elif rain_1h > 5:
            alerts.append(f"🌧️ {rname} — 시간당 {rain_1h}mm. 우비/장화 준비")
            level = "caution"
            icon = "🌧️"
        else:
            alerts.append(f"🌂 {rname} — 약한 강수. 우의 준비")
            level = "caution"
            icon = "🌂" if rain_type <= 2 else "❄️"

    # 기온 알림
    if temp >= 35:
        alerts.append(f"🔥 현재 {temp}°C 폭염 — 온열질환 주의! 수분 섭취 필수")
        level = "warning"
        icon = "🔥"
    elif temp >= 30:
        alerts.append(f"☀️ 현재 {temp}°C — 더위 주의. 수분 보충 권장")
        if level == "normal":
            level = "caution"
    elif temp <= -10:
        alerts.append(f"🥶 현재 {temp}°C 한파 — 노면 결빙 주의! 서행 운전")
        level = "warning"
        icon = "🥶"
    elif temp <= 0:
        alerts.append(f"❄️ 현재 {temp}°C — 결빙 가능. 출발 전 워밍업")
        if level == "normal":
            level = "caution"
            icon = "❄️"

    # 강풍 알림
    if wind >= 10:
        alerts.append(f"💨 풍속 {wind}m/s 강풍 — 적재물 고정 확인!")
        level = "warning"
        icon = "💨"
    elif wind >= 7:
        alerts.append(f"🌬️ 풍속 {wind}m/s — 바람 주의. 적재물 확인")
        if level == "normal":
            level = "caution"

    # 고습도
    if humidity >= 90:
        alerts.append(f"💧 습도 {humidity}% — 안개/시야 불량 가능. 전조등 사용")
        if level == "normal":
            level = "caution"

    if not alerts:
        alerts.append("수거 작업에 좋은 날씨입니다. 안전 운행하세요!")

    # 요약
    if rain_type > 0:
        rname = RAIN_TYPE_NAMES.get(rain_type, "강수")
        weather_desc = f"{rname} {rain_1h}mm/h"
    elif temp >= 30:
        weather_desc = "맑음(더위)"
    elif temp <= 0:
        weather_desc = "추움"
    else:
        weather_desc = "맑음"

    base_t = d.get("base_time", "")
    time_label = f"{base_t[:2]}:{base_t[2:]}" if len(base_t) == 4 else base_t
    summary = f"{weather_desc} {temp:.0f}°C | 습도 {humidity:.0f}% | 풍속 {wind:.0f}m/s ({time_label} 기준)"

    return {
        "available": True,
        "weather": d,
        "alerts": alerts,
        "summary": summary,
        "icon": icon,
        "level": level,
        "source": "realtime",
    }


def _build_yesterday_alert(weather: dict) -> dict:
    """전일 데이터 기반 알림 생성 (폴백)"""
    temp_avg = weather.get("temp_avg", 0)
    rain = weather.get("rain", 0)
    humidity = weather.get("humidity", 0)
    wind = weather.get("wind", 0)

    alerts: list[str] = []
    level = "normal"
    icon = "☀️"

    if rain > 10:
        alerts.append(f"🌧️ 어제 강수 {rain}mm — 오늘도 비 가능성. 우의 준비")
        level = "caution"
        icon = "🌧️"
    if temp_avg >= 28:
        alerts.append(f"☀️ 어제 평균 {temp_avg}°C — 오늘도 더위 예상. 수분 보충")
        if level == "normal":
            level = "caution"
    if temp_avg <= 2:
        alerts.append(f"❄️ 어제 평균 {temp_avg}°C — 노면 결빙 가능. 서행 운전")
        if level == "normal":
            level = "caution"
            icon = "❄️"
    if wind >= 7:
        alerts.append(f"🌬️ 어제 풍속 {wind}m/s — 바람 주의")
        if level == "normal":
            level = "caution"

    if not alerts:
        alerts.append("수거 작업에 좋은 날씨입니다. 안전 운행하세요!")

    summary = f"(어제 기준) {temp_avg:.0f}°C | 강수 {rain}mm | 풍속 {wind}m/s"

    return {
        "available": True,
        "weather": weather,
        "alerts": alerts,
        "summary": summary,
        "icon": icon,
        "level": level,
        "source": "yesterday",
    }
