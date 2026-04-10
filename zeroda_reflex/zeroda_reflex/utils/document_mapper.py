# zeroda_reflex/utils/document_mapper.py
# 2026-04-10 신규: 문서 태그 ↔ DB 컬럼 자동 매핑 테이블
#
# 사용처: hwpx_engine.fill_template() 에 data 딕셔너리 전달 시
#        build_template_data(template_category, customer_id, vendor, issuer)
#        호출로 자동 생성
#
# 설계 원칙
#   - 태그명은 한글로 통일 (사장님이 hwpx 양식 편집 시 직관적)
#   - 공통 태그 + 카테고리별 고유 태그 분리
#   - 빈 값은 빈 문자열로 처리 (None 금지 — hwpx에 'None' 출력되면 안 됨)
#   - 단가는 천 단위 콤마 포맷
#   - 날짜는 YYYY-MM-DD 또는 "YYYY년 MM월 DD일" 포맷 선택 가능

from __future__ import annotations

from datetime import datetime
from typing import Any

# ══════════════════════════════════════════
#  카테고리 정의
# ══════════════════════════════════════════
CATEGORY_CONTRACT_2 = "2자계약서"      # 배출자 ↔ 수집운반업체
CATEGORY_CONTRACT_3 = "3자계약서"      # 배출자 ↔ 수집운반업체 ↔ 처리업체
CATEGORY_QUOTE = "견적서"
CATEGORY_CONFIRM = "처리확인서"

ALL_CATEGORIES = [
    CATEGORY_CONTRACT_2,
    CATEGORY_CONTRACT_3,
    CATEGORY_QUOTE,
    CATEGORY_CONFIRM,
]


# ══════════════════════════════════════════
#  공통 태그 (4종 모두 사용)
# ══════════════════════════════════════════
COMMON_TAGS = [
    "발급일",
    "발급번호",
    "수집운반업체_상호",
    "수집운반업체_사업자번호",
    "수집운반업체_대표자",
    "수집운반업체_주소",
    "수집운반업체_연락처",
    "수집운반업체_허가번호",
    "거래처_상호",
    "거래처_사업자번호",
    "거래처_대표자",
    "거래처_주소",
    "거래처_연락처",
]

# ══════════════════════════════════════════
#  카테고리별 고유 태그
# ══════════════════════════════════════════
CATEGORY_TAGS: dict[str, list[str]] = {
    CATEGORY_CONTRACT_2: [
        "계약명",
        "계약기간_시작",
        "계약기간_종료",
        "폐기물_종류",
        "단가_음식물",
        "단가_재활용",
        "단가_일반",
        "수거주기",
        "결제조건",
    ],
    CATEGORY_CONTRACT_3: [
        "계약명",
        "계약기간_시작",
        "계약기간_종료",
        "폐기물_종류",
        "단가_음식물",
        "단가_재활용",
        "단가_일반",
        "수거주기",
        "결제조건",
        "처리업체_상호",
        "처리업체_사업자번호",
        "처리업체_대표자",
        "처리업체_주소",
        "처리시설_소재지",
        "처리업체_허가번호",
    ],
    CATEGORY_QUOTE: [
        "견적유효기간",
        "예상월수거량",
        "예상월금액",
        "부가세별도여부",
        "단가_음식물",
        "단가_재활용",
        "단가_일반",
        "특약사항",
    ],
    CATEGORY_CONFIRM: [
        "확인기간_시작",
        "확인기간_종료",
        "총수거량_음식물",
        "총수거량_재활용",
        "총수거량_일반",
        "총금액",
        "처리방법",
        "처리결과",
    ],
}


def get_expected_tags(category: str) -> list[str]:
    """카테고리별 사용 가능한 전체 태그 목록 (공통 + 고유)."""
    return COMMON_TAGS + CATEGORY_TAGS.get(category, [])


# ══════════════════════════════════════════
#  포맷터
# ══════════════════════════════════════════

def _fmt_money(v: Any) -> str:
    """금액 천 단위 콤마. None/0/빈값은 '0'."""
    if v is None or v == "":
        return "0"
    try:
        return f"{int(float(v)):,}"
    except (ValueError, TypeError):
        return str(v)


def _fmt_date(v: Any, style: str = "dash") -> str:
    """날짜 포맷. style='dash' → 2026-04-10, style='kr' → 2026년 4월 10일."""
    if not v:
        return ""
    try:
        if isinstance(v, str):
            dt = datetime.fromisoformat(v.replace("/", "-"))
        elif isinstance(v, datetime):
            dt = v
        else:
            return str(v)
        if style == "kr":
            return f"{dt.year}년 {dt.month}월 {dt.day}일"
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(v)


def _s(v: Any) -> str:
    """None → 빈 문자열, 그 외 str()."""
    return "" if v is None else str(v)


# ══════════════════════════════════════════
#  메인 빌더
# ══════════════════════════════════════════

def build_template_data(
    category: str,
    customer_row: dict[str, Any] | None,
    vendor_row: dict[str, Any] | None,
    issuer: str = "",
    extra: dict[str, Any] | None = None,
    issue_number: str = "",
    date_style: str = "kr",
) -> dict[str, str]:
    """hwpx 양식에 넣을 태그 데이터 딕셔너리 생성.

    customer_row : customer_info 테이블 한 행 (dict) — 거래처 정보
    vendor_row   : 수집운반업체 정보 (users 또는 company_info 기반)
    issuer       : 발급자 아이디
    extra        : 수동입력 필드 (계약기간, 특약사항 등) — UI에서 입력받은 값
    issue_number : 발급번호 (자동 채번)
    date_style   : 'kr' 또는 'dash'

    반환: hwpx_engine.fill_template(data=...) 에 그대로 넘길 수 있는 dict
    """
    extra = extra or {}
    customer_row = customer_row or {}
    vendor_row = vendor_row or {}

    data: dict[str, str] = {}

    # 발급 메타
    data["발급일"] = _fmt_date(datetime.now(), style=date_style)
    data["발급번호"] = _s(issue_number)

    # 수집운반업체 (우리 회사)
    data["수집운반업체_상호"] = _s(
        vendor_row.get("company_name")
        or vendor_row.get("vendor")
        or vendor_row.get("상호")
    )
    data["수집운반업체_사업자번호"] = _s(
        vendor_row.get("business_no") or vendor_row.get("사업자번호")
    )
    data["수집운반업체_대표자"] = _s(
        vendor_row.get("representative") or vendor_row.get("대표자")
    )
    data["수집운반업체_주소"] = _s(
        vendor_row.get("address") or vendor_row.get("주소")
    )
    data["수집운반업체_연락처"] = _s(
        vendor_row.get("phone") or vendor_row.get("연락처")
    )
    data["수집운반업체_허가번호"] = _s(
        vendor_row.get("license_no") or vendor_row.get("허가번호")
    )

    # 거래처
    data["거래처_상호"] = _s(
        customer_row.get("customer_name")
        or customer_row.get("상호")
        or customer_row.get("school_name")
    )
    data["거래처_사업자번호"] = _s(
        customer_row.get("business_no") or customer_row.get("사업자번호")
    )
    data["거래처_대표자"] = _s(
        customer_row.get("representative") or customer_row.get("대표자")
    )
    data["거래처_주소"] = _s(
        customer_row.get("address") or customer_row.get("주소")
    )
    data["거래처_연락처"] = _s(
        customer_row.get("phone") or customer_row.get("연락처")
    )

    # 단가 (customer_info 의 price_food / price_recycle / price_general)
    data["단가_음식물"] = _fmt_money(
        customer_row.get("price_food") or customer_row.get("단가_음식물")
    )
    data["단가_재활용"] = _fmt_money(
        customer_row.get("price_recycle") or customer_row.get("단가_재활용")
    )
    data["단가_일반"] = _fmt_money(
        customer_row.get("price_general") or customer_row.get("단가_일반")
    )

    # 카테고리별 고유 태그 — extra 에서 받거나 customer/vendor에서 자동 추출
    if category in (CATEGORY_CONTRACT_2, CATEGORY_CONTRACT_3):
        data["계약명"] = _s(extra.get("계약명"))
        data["계약기간_시작"] = _fmt_date(extra.get("계약기간_시작"), date_style)
        data["계약기간_종료"] = _fmt_date(extra.get("계약기간_종료"), date_style)
        data["폐기물_종류"] = _s(extra.get("폐기물_종류") or "음식물")
        data["수거주기"] = _s(extra.get("수거주기") or "주 5회")
        data["결제조건"] = _s(extra.get("결제조건") or "월말 정산")

    if category == CATEGORY_CONTRACT_3:
        data["처리업체_상호"] = _s(extra.get("처리업체_상호"))
        data["처리업체_사업자번호"] = _s(extra.get("처리업체_사업자번호"))
        data["처리업체_대표자"] = _s(extra.get("처리업체_대표자"))
        data["처리업체_주소"] = _s(extra.get("처리업체_주소"))
        data["처리시설_소재지"] = _s(extra.get("처리시설_소재지"))
        data["처리업체_허가번호"] = _s(extra.get("처리업체_허가번호"))

    if category == CATEGORY_QUOTE:
        data["견적유효기간"] = _s(extra.get("견적유효기간") or "발급일로부터 30일")
        data["예상월수거량"] = _s(extra.get("예상월수거량"))
        data["예상월금액"] = _fmt_money(extra.get("예상월금액"))
        data["부가세별도여부"] = _s(extra.get("부가세별도여부") or "별도")
        data["특약사항"] = _s(extra.get("특약사항"))

    if category == CATEGORY_CONFIRM:
        data["확인기간_시작"] = _fmt_date(extra.get("확인기간_시작"), date_style)
        data["확인기간_종료"] = _fmt_date(extra.get("확인기간_종료"), date_style)
        data["총수거량_음식물"] = _s(extra.get("총수거량_음식물") or "0")
        data["총수거량_재활용"] = _s(extra.get("총수거량_재활용") or "0")
        data["총수거량_일반"] = _s(extra.get("총수거량_일반") or "0")
        data["총금액"] = _fmt_money(extra.get("총금액"))
        data["처리방법"] = _s(extra.get("처리방법") or "위탁처리")
        data["처리결과"] = _s(extra.get("처리결과") or "정상 처리 완료")

    return data


def generate_issue_number(category: str, seq: int) -> str:
    """발급번호 자동 채번. 형식: ZRD-YYYYMMDD-카테고리약어-0001."""
    code = {
        CATEGORY_CONTRACT_2: "C2",
        CATEGORY_CONTRACT_3: "C3",
        CATEGORY_QUOTE: "QT",
        CATEGORY_CONFIRM: "CF",
    }.get(category, "DC")
    today = datetime.now().strftime("%Y%m%d")
    return f"ZRD-{today}-{code}-{seq:04d}"
