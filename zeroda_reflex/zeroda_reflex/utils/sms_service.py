# zeroda_reflex/utils/sms_service.py
# SOLAPI REST API 직접 연동 - 거래명세서 문자 발송 (Reflex 전용)
import os
import hmac
import hashlib
import uuid
import datetime
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


def _get_coolsms_config() -> tuple[str, str, str]:
    """CoolSMS/SOLAPI API 인증정보 + 대표 발신번호 조회 (환경변수)"""
    api_key = os.environ.get("COOLSMS_API_KEY", "").strip()
    api_secret = os.environ.get("COOLSMS_API_SECRET", "").strip()
    main_phone = os.environ.get("COOLSMS_SENDER_PHONE", "").strip()
    return api_key, api_secret, main_phone


def _normalize_phone(phone: str) -> str:
    """전화번호 정규화 (하이픈·공백·점 제거)"""
    if not phone:
        return ""
    cleaned = phone.replace("-", "").replace(" ", "").replace(".", "").strip()
    if cleaned and not cleaned.isdigit():
        cleaned = "".join(c for c in cleaned if c.isdigit())
    return cleaned


def _make_auth_header(api_key: str, api_secret: str) -> str:
    """SOLAPI HMAC-SHA256 인증 헤더 생성 (UTC 기준)"""
    date_str = (
        datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        + "Z"
    )
    salt = uuid.uuid4().hex
    data = date_str + salt
    signature = hmac.new(
        api_secret.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return (
        f"HMAC-SHA256 apiKey={api_key}, "
        f"date={date_str}, salt={salt}, signature={signature}"
    )


# ══════════════════════════════════════════
#  SMS 발송
# ══════════════════════════════════════════

def send_statement_sms(
    to_phone: str,
    message: str,
    from_phone: str = "",
    vendor_name: str = "",
    vendor_contact: str = "",
) -> tuple[bool, str]:
    """
    거래명세서 문자 발송 - SOLAPI REST API (urllib 사용)
    ※ 발신번호는 항상 대표번호(COOLSMS_SENDER_PHONE)로 고정
    """
    api_key, api_secret, main_phone = _get_coolsms_config()
    if not api_key or not api_secret:
        return (
            False,
            "CoolSMS 설정 없음. 환경변수에 COOLSMS_API_KEY, COOLSMS_API_SECRET을 등록하세요.",
        )

    to_clean = _normalize_phone(to_phone)
    if not to_clean or len(to_clean) < 10:
        return False, f"수신 전화번호가 올바르지 않습니다: {to_phone}"

    from_clean = _normalize_phone(main_phone)
    if not from_clean or len(from_clean) < 10:
        return False, "대표 발신번호가 없습니다. 환경변수에 COOLSMS_SENDER_PHONE을 등록하세요."

    # 본문 하단에 외주업체 정보 추가
    if vendor_name:
        footer = f"\n\n─────────────\n담당: {vendor_name}"
        if vendor_contact:
            footer += f" ({vendor_contact})"
        message = message + footer

    try:
        auth_header = _make_auth_header(api_key, api_secret)
        payload = json.dumps({
            "messages": [
                {
                    "to": to_clean,
                    "from": from_clean,
                    "text": message,
                }
            ]
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.solapi.com/messages/v4/send-many/detail",
            data=payload,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        group_id = (
            result.get("groupId", "")
            or result.get("groupInfo", {}).get("groupId", "")
        )
        return True, f"✅ {to_phone} 으로 문자 발송 완료 (GroupID: {group_id})"

    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            err_code = err_body.get("errorCode", "")
            err_msg = err_body.get("errorMessage", "알 수 없는 오류")
            return False, f"❌ SOLAPI 오류 ({err_code}): {err_msg}"
        except Exception:
            return False, f"❌ SOLAPI HTTP 오류: {e.code}"
    except Exception as e:
        logger.warning(f"SMS 발송 실패: {e}")
        return False, f"❌ 문자 발송 실패: {e}"


# ══════════════════════════════════════════
#  문자 본문 생성 헬퍼
# ══════════════════════════════════════════

def build_summary_sms_text(
    vendor_name: str,
    school: str,
    year: int,
    month: int,
    total_weight: float,
    total_amount: float,
    contact: str = "",
    overdue_amount: float = 0,
    overdue_months: str = "",
    cust_type: str = "",
) -> str:
    """요약 정산 문자 본문 생성 (SMS 단문용)"""
    if cust_type == "기타":
        text = (
            f"[{vendor_name}] {year}년{month}월 정산\n"
            f"{school}\n"
            f"합계 {total_amount:,.0f}원"
        )
    elif cust_type in ("학교", "기타1(면세사업장)"):
        text = (
            f"[{vendor_name}] {year}년{month}월 정산\n"
            f"{school} {total_weight:,.1f}kg\n"
            f"합계 {total_amount:,.0f}원(면세)"
        )
    elif cust_type == "기타2(부가세포함)":
        vat = total_amount * 0.1
        total_with_vat = total_amount + vat
        text = (
            f"[{vendor_name}] {year}년{month}월 정산\n"
            f"{school}\n"
            f"합계 {total_with_vat:,.0f}원(VAT포함)"
        )
    else:
        vat = total_amount * 0.1
        total_with_vat = total_amount + vat
        text = (
            f"[{vendor_name}] {year}년{month}월 정산\n"
            f"{school} {total_weight:,.1f}kg\n"
            f"합계 {total_with_vat:,.0f}원(VAT포함)"
        )

    if overdue_amount > 0:
        text += f"\n※미납 {overdue_amount:,.0f}원"
        if overdue_months:
            text += f"({overdue_months})"
    if contact:
        text += f"\n문의:{contact}"
    return text


def build_detail_sms_text(
    vendor_name: str,
    school: str,
    year: int,
    month: int,
    rows: list,
    total_weight: float,
    total_amount: float,
    contact: str = "",
    overdue_amount: float = 0,
    overdue_months: str = "",
    cust_type: str = "",
) -> str:
    """상세 정산 문자 본문 생성 (LMS 장문용, 일별 수거 내역 포함)"""
    text = (
        f"[{vendor_name}] 거래명세서\n"
        f"\n"
        f"■ {school}\n"
        f"■ {year}년 {month}월 수거 내역\n"
        f"\n"
    )

    # 기타(고정비용)가 아닌 경우에만 일별 수거 내역 표시
    if cust_type not in ("기타", "기타2(부가세포함)"):
        sorted_rows = sorted(rows, key=lambda r: r.get("collect_date", ""))
        for r in sorted_rows:
            rdate = r.get("collect_date", "")
            try:
                parts = rdate.split("-")
                short_date = f"{int(parts[1])}/{int(parts[2])}"
            except (IndexError, ValueError):
                short_date = rdate
            itype = r.get("item_type", "")
            w = float(r.get("weight", 0))
            text += f"{short_date} {itype} {w:,.1f}kg\n"

        text += f"\n총 수거량: {total_weight:,.1f}kg\n"

    # 구분별 금액 표시
    if cust_type == "기타":
        text += (
            f"월 고정비용: {total_amount:,.0f}원\n"
            f"합계: {total_amount:,.0f}원\n"
        )
    elif cust_type in ("학교", "기타1(면세사업장)"):
        text += (
            f"공급가액: {total_amount:,.0f}원\n"
            f"(면세)\n"
            f"합계: {total_amount:,.0f}원\n"
        )
    elif cust_type == "기타2(부가세포함)":
        vat = total_amount * 0.1
        total_with_vat = total_amount + vat
        text += (
            f"월 고정비용: {total_amount:,.0f}원\n"
            f"VAT(10%): {vat:,.0f}원\n"
            f"합계: {total_with_vat:,.0f}원\n"
        )
    else:
        vat = total_amount * 0.1
        total_with_vat = total_amount + vat
        text += (
            f"공급가액: {total_amount:,.0f}원\n"
            f"VAT(10%): {vat:,.0f}원\n"
            f"합계: {total_with_vat:,.0f}원\n"
        )

    if overdue_amount > 0:
        text += f"\n※ 미납 안내: {overdue_amount:,.0f}원"
        if overdue_months:
            text += f" ({overdue_months})"
        text += "\n조속한 납부 부탁드립니다.\n"
    if contact:
        text += f"\n문의: {contact}"

    return text
