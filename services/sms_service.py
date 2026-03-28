# services/sms_service.py
# CoolSMS(솔라피) API 연동 - 거래명세서 문자 발송
import hmac
import hashlib
import time
import uuid
import json
import os


def _get_coolsms_config():
    """CoolSMS API 인증정보 조회"""
    try:
        import streamlit as st
        api_key    = st.secrets.get("COOLSMS_API_KEY", "")
        api_secret = st.secrets.get("COOLSMS_API_SECRET", "")
    except Exception:
        api_key    = os.environ.get("COOLSMS_API_KEY", "")
        api_secret = os.environ.get("COOLSMS_API_SECRET", "")
    return api_key, api_secret


def _make_signature(api_key, api_secret):
    """CoolSMS API v4 HMAC-SHA256 서명 생성"""
    date = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    salt = str(uuid.uuid4())
    msg = date + salt
    signature = hmac.new(
        api_secret.encode('utf-8'),
        msg.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return {
        'Authorization': f'HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}',
        'Content-Type': 'application/json; charset=utf-8',
    }


def _normalize_phone(phone: str) -> str:
    """전화번호 정규화 (하이픈 제거, 공백 제거)"""
    if not phone:
        return ''
    cleaned = phone.replace('-', '').replace(' ', '').replace('.', '').strip()
    # 010-xxxx-xxxx, 02-xxx-xxxx 등 → 숫자만
    if cleaned and not cleaned.isdigit():
        cleaned = ''.join(c for c in cleaned if c.isdigit())
    return cleaned


def send_statement_sms(to_phone: str, message: str,
                       from_phone: str = '') -> tuple:
    """
    거래명세서 문자(LMS) 발송
    Args:
        to_phone:   수신 전화번호
        message:    메시지 본문 (2,000자 이내 → LMS 자동)
        from_phone: 발신 전화번호 (CoolSMS에 등록된 번호, 비어있으면 기본값)
    Returns: (success: bool, message: str)
    """
    import urllib.request

    api_key, api_secret = _get_coolsms_config()
    if not api_key or not api_secret:
        return False, "CoolSMS 설정 없음. Secrets에 COOLSMS_API_KEY, COOLSMS_API_SECRET을 등록하세요."

    to_clean = _normalize_phone(to_phone)
    if not to_clean or len(to_clean) < 10:
        return False, f"수신 전화번호가 올바르지 않습니다: {to_phone}"

    # 발신번호: 미지정 시 수신번호와 동일 (테스트), 실서비스에서는 등록된 번호 필수
    from_clean = _normalize_phone(from_phone) if from_phone else to_clean

    # 메시지 길이에 따라 SMS(90바이트) / LMS(2000자) 자동 결정
    msg_type = 'SMS' if len(message.encode('euc-kr', errors='replace')) <= 90 else 'LMS'

    headers = _make_signature(api_key, api_secret)

    payload = {
        "message": {
            "to": to_clean,
            "from": from_clean,
            "type": msg_type,
            "text": message,
        }
    }

    try:
        url = "https://api.coolsms.co.kr/messages/v4/send"
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            # 응답에서 상태 확인
            status_code = result.get('statusCode')
            if status_code and str(status_code).startswith('4'):
                return False, f"발송 실패: {result.get('statusMessage', '알 수 없는 오류')}"
            group_id = result.get('groupId', '')
            return True, f"✅ {to_phone} 으로 {msg_type} 발송 완료 (ID: {group_id})"

    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode()
            err_json = json.loads(err_body)
            err_msg = err_json.get('errorMessage', '') or err_json.get('statusMessage', str(e))
        except Exception:
            err_msg = str(e)
        return False, f"❌ CoolSMS 오류 (HTTP {e.code}): {err_msg}"
    except Exception as e:
        return False, f"❌ 발송 실패: {str(e)}"


def build_statement_sms_text(vendor_name: str, school: str,
                              year: int, month: int,
                              total_weight: float, total_amount: float,
                              contact: str = '') -> str:
    """거래명세서 안내 문자 본문 생성"""
    vat = total_amount * 0.1
    total_with_vat = total_amount + vat

    text = (
        f"[{vendor_name}] 거래명세서 안내\n"
        f"\n"
        f"■ {school} 님\n"
        f"■ {year}년 {month}월 수거 내역\n"
        f"\n"
        f"- 총 수거량: {total_weight:,.1f} kg\n"
        f"- 공급가액: {total_amount:,.0f}원\n"
        f"- VAT(10%): {vat:,.0f}원\n"
        f"- 합계: {total_with_vat:,.0f}원\n"
        f"\n"
        f"상세 명세서가 필요하시면 연락 주세요.\n"
    )
    if contact:
        text += f"연락처: {contact}\n"

    return text
