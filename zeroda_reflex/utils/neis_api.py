# zeroda_reflex/utils/neis_api.py
# 나이스(NEIS) 교육정보 Open API 연동 — Reflex용 (Streamlit 의존성 제거)
import json
import os
import re
import calendar
import urllib.request
import urllib.parse
from datetime import datetime


# ── API 설정 ──
NEIS_BASE_URL = "https://open.neis.go.kr/hub"
MEAL_ENDPOINT = "/mealServiceDietInfo"


def _get_api_key() -> str:
    """API 인증키 조회 (환경변수 → SAMPLE 순)"""
    key = os.environ.get("NEIS_API_KEY", "")
    if key:
        return key
    return "SAMPLE"


def fetch_meal_dates(
    edu_office_code: str,
    school_code: str,
    year: int,
    month: int,
) -> dict:
    """
    NEIS 급식식단정보 API 조회 — 해당 월의 급식일 목록 반환.

    Returns:
        {
            'success': True/False,
            'message': str,
            'school_name': str,
            'meal_dates': ['2026-04-07', ...],
            'meal_details': {'2026-04-07': {'menu': '...', 'cal': '...'}},
            'total_count': int,
        }
    """
    api_key = _get_api_key()
    month_str = str(month).zfill(2)
    from_date = f"{year}{month_str}01"
    last_day = calendar.monthrange(year, month)[1]
    to_date = f"{year}{month_str}{last_day}"

    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": edu_office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": from_date,
        "MLSV_TO_YMD": to_date,
    }

    url = NEIS_BASE_URL + MEAL_ENDPOINT + "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
    except Exception as e:
        return {
            "success": False,
            "message": f"API 호출 실패: {e}",
            "school_name": "",
            "meal_dates": [],
            "meal_details": {},
            "total_count": 0,
        }

    return _parse_meal_response(data, year, month)


def _parse_meal_response(data: dict, year: int, month: int) -> dict:
    """NEIS API JSON 응답 파싱"""
    result = {
        "success": False,
        "message": "",
        "school_name": "",
        "meal_dates": [],
        "meal_details": {},
        "total_count": 0,
    }

    if "RESULT" in data:
        code = data["RESULT"].get("CODE", "")
        msg = data["RESULT"].get("MESSAGE", "")
        if code == "INFO-200":
            result["message"] = "해당 월에 급식 데이터가 없습니다."
        else:
            result["message"] = f"API 오류: {code} - {msg}"
        return result

    try:
        meal_info = data.get("mealServiceDietInfo", [])
        if not meal_info or len(meal_info) < 2:
            result["message"] = "API 응답 형식 오류"
            return result

        rows = meal_info[1].get("row", [])
        meal_dates = []
        meal_details = {}
        school_name = ""

        for row in rows:
            if not school_name:
                school_name = row.get("SCHUL_NM", "")

            raw_date = str(row.get("MLSV_YMD", ""))
            if len(raw_date) == 8:
                fmt_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            else:
                continue

            if fmt_date not in meal_dates:
                meal_dates.append(fmt_date)

            menu_raw = row.get("DDISH_NM", "")
            menu_clean = menu_raw.replace("<br/>", "\n").strip()
            menu_clean = re.sub(r"\([0-9.]+\)", "", menu_clean).strip()

            cal_info = row.get("CAL_INFO", "")
            meal_code = row.get("MMEAL_SC_CODE", "")

            meal_details[fmt_date] = {
                "menu": menu_clean,
                "cal": cal_info,
                "meal_code": meal_code,
            }

        result["success"] = True
        result["message"] = (
            f"{school_name} {year}년 {month}월 급식일 {len(meal_dates)}일 조회 완료"
        )
        result["school_name"] = school_name
        result["meal_dates"] = sorted(meal_dates)
        result["meal_details"] = meal_details
        result["total_count"] = len(meal_dates)

    except Exception as e:
        result["message"] = f"응답 파싱 오류: {e}"

    return result


# ── 시도교육청 코드 상수 ──
EDU_OFFICE_CODES = {
    "B10": "서울특별시교육청",
    "C10": "부산광역시교육청",
    "D10": "대구광역시교육청",
    "E10": "인천광역시교육청",
    "F10": "광주광역시교육청",
    "G10": "대전광역시교육청",
    "H10": "울산광역시교육청",
    "I10": "세종특별자치시교육청",
    "J10": "경기도교육청",
    "K10": "강원특별자치도교육청",
    "M10": "충청북도교육청",
    "N10": "충청남도교육청",
    "P10": "전북특별자치도교육청",
    "Q10": "전라남도교육청",
    "R10": "경상북도교육청",
    "S10": "경상남도교육청",
    "T10": "제주특별자치도교육청",
}

EDU_CODE_LIST = list(EDU_OFFICE_CODES.keys())
EDU_NAME_LIST = [f"{v} ({k})" for k, v in EDU_OFFICE_CODES.items()]
