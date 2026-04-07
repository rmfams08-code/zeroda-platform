# zeroda_reflex/utils/filters.py
# ══════════════════════════════════════════════════════════════
#  범용 필터링 유틸리티
#  - 각 state 파일에서 반복되는 "전체이면 전부, 아니면 특정 값 필터" 패턴을
#    공통 함수로 추출합니다.
#  - @rx.var computed var 내부에서 호출하여 사용합니다.
# ══════════════════════════════════════════════════════════════
from typing import Any


def filter_by_key(
    data: list[dict],
    filter_value: str,
    key: str,
    all_label: str = "전체",
) -> list[dict]:
    """단일 키 기준 필터링 — 가장 흔한 필터 패턴

    "전체"를 선택하면 전체 데이터를 반환하고,
    특정 값을 선택하면 해당 키의 값이 일치하는 항목만 반환합니다.

    Args:
        data: 필터링할 딕셔너리 리스트
        filter_value: 사용자가 선택한 필터 값
        key: 딕셔너리에서 비교할 키 이름
        all_label: "전체"에 해당하는 라벨 (기본: "전체")

    Returns:
        필터링된 딕셔너리 리스트

    사용 예:
        @rx.var
        def filtered_collections(self) -> list[dict]:
            return filter_by_key(self.monthly_collections,
                                 self.col_school_filter, "school_name")
    """
    if filter_value == all_label:
        return data
    return [r for r in data if r.get(key) == filter_value]


def filter_by_keys(
    data: list[dict],
    filters: dict[str, tuple[str, str]],
    all_label: str = "전체",
) -> list[dict]:
    """다중 키 기준 필터링 — 여러 필터를 동시에 적용할 때 사용

    Args:
        data: 필터링할 딕셔너리 리스트
        filters: {딕셔너리키: (필터값, 전체라벨)} 형식
                 예: {"vendor": ("하영자원", "전체"), "status": ("pending", "전체")}
        all_label: 기본 "전체" 라벨 (filters에서 개별 지정하지 않은 경우 사용)

    Returns:
        필터링된 딕셔너리 리스트

    사용 예:
        @rx.var
        def filtered_data(self) -> list[dict]:
            return filter_by_keys(self.raw_data, {
                "vendor": (self.vendor_filter, "전체"),
                "status": (self.status_filter, "전체"),
            })
    """
    result = data
    for key, (value, label) in filters.items():
        if value != label:
            result = [r for r in result if r.get(key) == value]
    return result


def build_options(
    data: list[dict],
    key: str,
    all_label: str = "전체",
    sort: bool = True,
) -> list[str]:
    """데이터에서 고유 값을 추출하여 "전체" 포함 옵션 리스트 생성

    필터 드롭다운에 사용할 옵션 목록을 자동으로 만듭니다.

    Args:
        data: 옵션을 추출할 딕셔너리 리스트
        key: 추출할 키 이름
        all_label: 첫 번째 항목으로 넣을 "전체" 라벨
        sort: 정렬 여부 (기본: True)

    Returns:
        ["전체", "값1", "값2", ...] 형태의 문자열 리스트

    사용 예:
        school_options = build_options(self.monthly_collections, "school_name")
        # → ["전체", "가나초등학교", "다라중학교", ...]
    """
    values = list(set(
        str(r.get(key, ""))
        for r in data
        if r.get(key)
    ))
    if sort:
        values.sort()
    return [all_label] + values


def safe_int(value: Any, default: int = 0) -> int:
    """안전한 정수 변환 — 문자열/None/빈 값을 안전하게 처리

    database.py가 문자열로 반환하는 경우가 많아, 비교 시 타입 혼동 방지용

    Args:
        value: 변환할 값
        default: 변환 실패 시 기본값

    Returns:
        정수값
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """안전한 실수 변환 — 문자열/None/빈 값을 안전하게 처리

    Args:
        value: 변환할 값
        default: 변환 실패 시 기본값

    Returns:
        실수값
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def parse_year_month(year_str: str, month_str: str) -> tuple[int, int] | None:
    """연/월 문자열을 안전하게 정수로 변환

    각 state 파일에서 int(self.selected_year), int(self.selected_month) 변환 시
    실패하면 silent하게 종료되는 문제를 개선하기 위한 헬퍼 함수입니다.

    Args:
        year_str: 연도 문자열 (예: "2026")
        month_str: 월 문자열 (예: "4")

    Returns:
        (year, month) 튜플, 변환 실패 시 None

    사용 예:
        result = parse_year_month(self.selected_year, self.selected_month)
        if result is None:
            rx.toast("연도와 월을 올바르게 선택해주세요.")
            return []
        year, month = result
        # year, month를 이용한 필터링 진행

    검증:
        - 연도: 2020 <= year <= 2099
        - 월: 1 <= month <= 12
    """
    try:
        y = int(year_str)
        m = int(month_str)
        if not (2020 <= y <= 2099):
            return None
        if not (1 <= m <= 12):
            return None
        return (y, m)
    except (ValueError, TypeError):
        return None
