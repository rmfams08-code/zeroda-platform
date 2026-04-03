# services/neis_api.py
# 나이스(NEIS) 교육정보 Open API 연동 — 급식식단정보 조회
import json
import urllib.request
import urllib.parse
import streamlit as st
from datetime import datetime


# ── API 설정 ──────────────────────────────────────────────────────────────────
NEIS_BASE_URL = "https://open.neis.go.kr/hub"
MEAL_ENDPOINT = "/mealServiceDietInfo"


def _get_api_key() -> str:
    """API 인증키 조회 (st.secrets → 환경변수 → SAMPLE 순)"""
    # 1) Streamlit secrets
    try:
        key = st.secrets.get("NEIS_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    # 2) 환경변수
    import os
    key = os.environ.get("NEIS_API_KEY", "")
    if key:
        return key
    # 3) 샘플키 (테스트용, 일 호출 제한 있음)
    return "SAMPLE"


def fetch_meal_dates(edu_office_code: str, school_code: str,
                     year: int, month: int) -> dict:
    """
    NEIS 급식식단정보 API 조회 — 해당 월의 급식일 목록 반환.

    Args:
        edu_office_code: 시도교육청코드 (예: 'J10' = 경기도)
        school_code:     학교표준코드 (예: '7530560')
        year:            연도
        month:           월

    Returns:
        {
            'success': True/False,
            'message': '성공' 또는 에러 메시지,
            'school_name': '학교명',
            'meal_dates': ['2026-04-07', '2026-04-08', ...],  # 급식일 리스트
            'meal_details': {
                '2026-04-07': {'menu': '...', 'cal': '...'},
                ...
            },
            'total_count': 20,
        }
    """
    api_key = _get_api_key()
    month_str = str(month).zfill(2)
    from_date = f"{year}{month_str}01"

    # 월 마지막 날 계산
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    to_date = f"{year}{month_str}{last_day}"

    params = {
        'KEY':                api_key,
        'Type':               'json',
        'pIndex':             1,
        'pSize':              100,
        'ATPT_OFCDC_SC_CODE': edu_office_code,
        'SD_SCHUL_CODE':      school_code,
        'MLSV_FROM_YMD':      from_date,
        'MLSV_TO_YMD':        to_date,
    }

    url = NEIS_BASE_URL + MEAL_ENDPOINT + '?' + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            data = json.loads(raw)
    except Exception as e:
        return {
            'success': False,
            'message': f'API 호출 실패: {e}',
            'school_name': '',
            'meal_dates': [],
            'meal_details': {},
            'total_count': 0,
        }

    return _parse_meal_response(data, year, month)


def _parse_meal_response(data: dict, year: int, month: int) -> dict:
    """NEIS API JSON 응답 파싱"""
    result = {
        'success': False,
        'message': '',
        'school_name': '',
        'meal_dates': [],
        'meal_details': {},
        'total_count': 0,
    }

    # 에러 체크
    if 'RESULT' in data:
        code = data['RESULT'].get('CODE', '')
        msg = data['RESULT'].get('MESSAGE', '')
        if code == 'INFO-200':
            result['message'] = '해당 월에 급식 데이터가 없습니다.'
        else:
            result['message'] = f'API 오류: {code} - {msg}'
        return result

    # 정상 응답 파싱
    try:
        meal_info = data.get('mealServiceDietInfo', [])
        if not meal_info or len(meal_info) < 2:
            result['message'] = 'API 응답 형식 오류'
            return result

        # [0] = head (총 건수), [1] = row (실제 데이터)
        head = meal_info[0].get('head', [{}])
        rows = meal_info[1].get('row', [])

        total = 0
        for h in head:
            if 'list_totalCount' in h:
                total = int(h['list_totalCount'])

        meal_dates = []
        meal_details = {}
        school_name = ''

        for row in rows:
            # 학교명 추출
            if not school_name:
                school_name = row.get('SCHUL_NM', '')

            # 급식일자: YYYYMMDD → YYYY-MM-DD
            raw_date = str(row.get('MLSV_YMD', ''))
            if len(raw_date) == 8:
                fmt_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
            else:
                continue

            if fmt_date not in meal_dates:
                meal_dates.append(fmt_date)

            # 메뉴 정보 (<br/> 태그 → 줄바꿈)
            menu_raw = row.get('DDISH_NM', '')
            menu_clean = menu_raw.replace('<br/>', '\n').strip()
            # 알레르기 정보 번호 제거 (예: "카레라이스(1.2.5)" → "카레라이스")
            import re
            menu_clean = re.sub(r'\([0-9.]+\)', '', menu_clean).strip()

            cal_info = row.get('CAL_INFO', '')
            meal_code = row.get('MMEAL_SC_CODE', '')  # 1:조식, 2:중식, 3:석식

            meal_details[fmt_date] = {
                'menu': menu_clean,
                'cal': cal_info,
                'meal_code': meal_code,
            }

        result['success'] = True
        result['message'] = f'{school_name} {year}년 {month}월 급식일 {len(meal_dates)}일 조회 완료'
        result['school_name'] = school_name
        result['meal_dates'] = sorted(meal_dates)
        result['meal_details'] = meal_details
        result['total_count'] = len(meal_dates)

    except Exception as e:
        result['message'] = f'응답 파싱 오류: {e}'

    return result


# ── 시도교육청 코드 상수 ──────────────────────────────────────────────────────
EDU_OFFICE_CODES = {
    'B10': '서울특별시교육청',
    'C10': '부산광역시교육청',
    'D10': '대구광역시교육청',
    'E10': '인천광역시교육청',
    'F10': '광주광역시교육청',
    'G10': '대전광역시교육청',
    'H10': '울산광역시교육청',
    'I10': '세종특별자치시교육청',
    'J10': '경기도교육청',
    'K10': '강원특별자치도교육청',
    'M10': '충청북도교육청',
    'N10': '충청남도교육청',
    'P10': '전북특별자치도교육청',
    'Q10': '전라남도교육청',
    'R10': '경상북도교육청',
    'S10': '경상남도교육청',
    'T10': '제주특별자치도교육청',
}

# 코드 → 이름 / 이름 → 코드 변환
EDU_OFFICE_NAMES = {v: k for k, v in EDU_OFFICE_CODES.items()}


def get_edu_office_list() -> list:
    """시도교육청 목록 반환 [('J10', '경기도교육청'), ...]"""
    return [(k, v) for k, v in EDU_OFFICE_CODES.items()]
