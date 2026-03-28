# services/sms_service.py
# SOLAPI REST API 직접 연동 - 거래명세서 문자 발송
import os
import hmac
import hashlib
import uuid
import datetime
import json


def _get_coolsms_config():
    """CoolSMS/SOLAPI API 인증정보 조회"""
    try:
        import streamlit as st
        api_key    = st.secrets.get("COOLSMS_API_KEY", "")
        api_secret = st.secrets.get("COOLSMS_API_SECRET", "")
    except Exception:
        api_key    = os.environ.get("COOLSMS_API_KEY", "")
        api_secret = os.environ.get("COOLSMS_API_SECRET", "")
    return api_key.strip(), api_secret.strip()


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
                       from_phone: str = '') -> tuple:
    """
    거래명세서 문자 발송 - SOLAPI REST API 직접 호출
    Args:
        to_phone:   수신 전화번호
        message:    메시지 본문
        from_phone: 발신 전화번호 (SOLAPI에 등록된 번호)
    Returns: (success: bool, message: str)
    """
    api_key, api_secret = _get_coolsms_config()
    if not api_key or not api_secret:
        return False, "CoolSMS 설정 없음. Secrets에 COOLSMS_API_KEY, COOLSMS_API_SECRET을 등록하세요."

    to_clean = _normalize_phone(to_phone)
    if not to_clean or len(to_clean) < 10:
        return False, f"수신 전화번호가 올바르지 않습니다: {to_phone}"

    from_clean = _normalize_phone(from_phone)
    if not from_clean or len(from_clean) < 10:
        return False, "발신 전화번호가 없습니다. SOLAPI에 등록된 발신번호를 입력하세요."

    try:
        import httpx

        # --- 먼저 잔액 조회로 인증 테스트 ---
        auth_header = _make_auth_header(api_key, api_secret)
        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
        }

        # 디버그: API Key 앞 8자리만 표시
        debug_key = api_key[:8] + "..." if len(api_key) > 8 else api_key
        debug_secret_len = len(api_secret)

        with httpx.Client(timeout=10) as client:
            # 1단계: 잔액 조회로 인증 확인
            test_resp = client.get(
                "https://api.solapi.com/cash/v1/balance",
                headers=headers,
            )
            if test_resp.status_code >= 400:
                test_result = test_resp.json()
                err_code = test_result.get('errorCode', '')
                err_msg = test_result.get('errorMessage', '')
                return False, (
                    f"❌ 인증 실패 ({err_code}): {err_msg}\n"
                    f"[디버그] Key: {debug_key}, Secret길이: {debug_secret_len}자, "
                    f"Auth 앞부분: {auth_header[:60]}..."
                )

            # 2단계: 인증 성공 → 문자 발송
            # 발송 시 새 인증 헤더 생성 (시간 갱신)
            auth_header2 = _make_auth_header(api_key, api_secret)
            send_headers = {
                "Authorization": auth_header2,
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

            resp = client.post(
                "https://api.solapi.com/messages/v4/send-many/detail",
                headers=send_headers,
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
