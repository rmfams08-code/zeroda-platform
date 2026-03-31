# services/sms_service.py
# SOLAPI REST API 직접 연동 - 거래명세서 문자 발송
import os
import hmac
import hashlib
import uuid
import datetime
import json


def _get_coolsms_config():
    """CoolSMS/SOLAPI API 인증정보 + 대표 발신번호 조회"""
    try:
        import streamlit as st
        api_key    = st.secrets.get("COOLSMS_API_KEY", "")
        api_secret = st.secrets.get("COOLSMS_API_SECRET", "")
        main_phone = st.secrets.get("COOLSMS_SENDER_PHONE", "")
    except Exception:
        api_key    = os.environ.get("COOLSMS_API_KEY", "")
        api_secret = os.environ.get("COOLSMS_API_SECRET", "")
        main_phone = os.environ.get("COOLSMS_SENDER_PHONE", "")
    return api_key.strip(), api_secret.strip(), main_phone.strip()


def _normalize_phone(phone: str) -> str:
    """전화번호 정규화 (하이픈 제거, 공백 제거)"""
    if not phone:
        return ''
    cleaned = phone.replace('-', '').replace(' ', '').replace('.', '').strip()
    if cleaned and not cleaned.isdigit():
        cleaned = ''.join(c for c in cleaned if c.isdigit())
    return cleaned


def _make_auth_header(api_key: str, api_secret: str) -> str:
    """SOLAPI HMAC-SHA256 인증 헤더 생성 (UTC 기준)"""
    date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    salt = uuid.uuid4().hex
    data = date + salt
    signature = hmac.new(
        api_secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"


def send_statement_sms(to_phone: str, message: str,
                       from_phone: str = '',
                       vendor_name: str = '',
                       vendor_contact: str = '') -> tuple:
    """
    거래명세서 문자 발송 - SOLAPI REST API 직접 호출
    ※ 발신번호는 항상 하영자원 대표번호(COOLSMS_SENDER_PHONE)로 고정
    Args:
        to_phone:       수신 전화번호
        message:        메시지 본문
        from_phone:     (무시됨, 하위호환용) → 대표번호로 대체
        vendor_name:    외주업체명 (본문 하단에 표시)
        vendor_contact: 외주업체 연락처 (본문 하단에 표시)
    Returns: (success: bool, message: str)
    """
    api_key, api_secret, main_phone = _get_coolsms_config()
    if not api_key or not api_secret:
        return False, "CoolSMS 설정 없음. Secrets에 COOLSMS_API_KEY, COOLSMS_API_SECRET을 등록하세요."

    to_clean = _normalize_phone(to_phone)
    if not to_clean or len(to_clean) < 10:
        return False, f"수신 전화번호가 올바르지 않습니다: {to_phone}"

    # 발신번호: 항상 하영자원 대표번호 (Secrets에 등록된 COOLSMS_SENDER_PHONE)
    from_clean = _normalize_phone(main_phone)
    if not from_clean or len(from_clean) < 10:
        return False, "대표 발신번호가 없습니다. Secrets에 COOLSMS_SENDER_PHONE을 등록하세요."

    # 본문 하단에 실제 외주업체 정보 추가
    if vendor_name:
        footer = f"\n\n─────────────\n담당: {vendor_name}"
        if vendor_contact:
            footer += f" ({vendor_contact})"
        message = message + footer

    try:
        import httpx

        auth_header = _make_auth_header(api_key, api_secret)
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }
        payload = {
            "messages": [
                {
                    "to": to_clean,
                    "from": from_clean,
                    "text": message,
                }
            ]
        }

        with httpx.Client(timeout=10) as client:
            resp = client.post(
                "https://api.solapi.com/messages/v4/send-many/detail",
                headers=headers,
                json=payload,
            )

        result = resp.json()

        if resp.status_code >= 400:
            err_code = result.get('errorCode', '')
            err_msg = result.get('errorMessage', '알 수 없는 오류')
            return False, f"❌ SOLAPI 오류 ({err_code}): {err_msg}"

        # 성공 응답
        group_id = result.get('groupId', '') or result.get('groupInfo', {}).get('groupId', '')
        return True, f"✅ {to_phone} 으로 문자 발송 완료 (GroupID: {group_id})"

    except ImportError:
        return False, "❌ httpx 패키지 미설치. requirements.txt에 httpx를 추가하세요."
    except Exception as e:
        err_str = str(e)
        return False, f"❌ 문자 발송 실패: {err_str}"


def build_summary_sms_text(vendor_name: str, school: str,
                            year: int, month: int,
                            total_weight: float, total_amount: float,
                            contact: str = '') -> str:
    """요약 정산 문자 본문 생성 (SMS 단문용, 90바이트 이내)"""
    vat = total_amount * 0.1
    total_with_vat = total_amount + vat
    text = (
        f"[{vendor_name}] {year}년{month}월 정산\n"
        f"{school} {total_weight:,.1f}kg\n"
        f"합계 {total_with_vat:,.0f}원(VAT포함)"
    )
    if contact:
        text += f"\n문의:{contact}"
    return text


def build_detail_sms_text(vendor_name: str, school: str,
                           year: int, month: int,
                           rows: list,
                           total_weight: float, total_amount: float,
                           contact: str = '') -> str:
    """상세 정산 문자 본문 생성 (LMS 장문용, 일별 수거 내역 포함)
    Args:
        rows: 수거 데이터 리스트 [{'collect_date': '2026-03-05', 'item_type': '음식물', 'weight': 50.0, ...}, ...]
    """
    vat = total_amount * 0.1
    total_with_vat = total_amount + vat

    text = (
        f"[{vendor_name}] 거래명세서\n"
        f"\n"
        f"■ {school}\n"
        f"■ {year}년 {month}월 수거 내역\n"
        f"\n"
    )

    # 일별 수거 내역 (날짜순 정렬)
    sorted_rows = sorted(rows, key=lambda r: r.get('collect_date', ''))
    for r in sorted_rows:
        rdate = r.get('collect_date', '')
        # 날짜에서 월-일만 표시 (2026-03-05 → 3/5)
        try:
            parts = rdate.split('-')
            short_date = f"{int(parts[1])}/{int(parts[2])}"
        except (IndexError, ValueError):
            short_date = rdate
        itype = r.get('item_type', '')
        w = float(r.get('weight', 0))
        text += f"{short_date} {itype} {w:,.1f}kg\n"

    text += (
        f"\n"
        f"총 수거량: {total_weight:,.1f}kg\n"
        f"공급가액: {total_amount:,.0f}원\n"
        f"VAT(10%): {vat:,.0f}원\n"
        f"합계: {total_with_vat:,.0f}원\n"
    )
    if contact:
        text += f"\n문의: {contact}"

    return text


# 하위 호환용 (기존 코드에서 호출 시)
def build_statement_sms_text(vendor_name: str, school: str,
                              year: int, month: int,
                              total_weight: float, total_amount: float,
                              contact: str = '') -> str:
    """거래명세서 안내 문자 본문 생성 (하위 호환)"""
    return build_summary_sms_text(
        vendor_name, school, year, month,
        total_weight, total_amount, contact
    )
