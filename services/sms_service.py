# services/sms_service.py
# SOLAPI(CoolSMS) 공식 SDK 연동 - 거래명세서 문자 발송
import os


def _get_coolsms_config():
    """CoolSMS/SOLAPI API 인증정보 조회"""
    try:
        import streamlit as st
        api_key    = st.secrets.get("COOLSMS_API_KEY", "")
        api_secret = st.secrets.get("COOLSMS_API_SECRET", "")
    except Exception:
        api_key    = os.environ.get("COOLSMS_API_KEY", "")
        api_secret = os.environ.get("COOLSMS_API_SECRET", "")
    return api_key, api_secret


def _normalize_phone(phone: str) -> str:
    """전화번호 정규화 (하이픈 제거, 공백 제거)"""
    if not phone:
        return ''
    cleaned = phone.replace('-', '').replace(' ', '').replace('.', '').strip()
    if cleaned and not cleaned.isdigit():
        cleaned = ''.join(c for c in cleaned if c.isdigit())
    return cleaned


def send_statement_sms(to_phone: str, message: str,
                       from_phone: str = '') -> tuple:
    """
    거래명세서 문자(LMS) 발송 - SOLAPI 공식 SDK 사용
    Args:
        to_phone:   수신 전화번호
        message:    메시지 본문 (2,000자 이내 → LMS 자동)
        from_phone: 발신 전화번호 (CoolSMS에 등록된 번호)
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
        return False, "발신 전화번호가 없습니다. CoolSMS에 등록된 발신번호를 입력하세요."

    try:
        from solapi import SolapiMessageService
        from solapi.model.request.message import Message

        message_service = SolapiMessageService(api_key, api_secret)

        # 90바이트 이하 → SMS(단문), 초과 → LMS(장문) 자동 판별
        msg = Message(
            to=to_clean,
            **{'from': from_clean},
            text=message,
            auto_type_detect=True,
        )
        result = message_service.send(msg)

        # 응답 확인
        if hasattr(result, 'count') and hasattr(result.count, 'registered_failed'):
            if result.count.registered_failed and result.count.registered_failed > 0:
                return False, f"❌ 발송 실패: {result.count.registered_failed}건 실패"
        group_id = getattr(result, 'group_id', '') or ''
        return True, f"✅ {to_phone} 으로 문자 발송 완료 (GroupID: {group_id})"

    except ImportError:
        return False, "❌ solapi 패키지 미설치. requirements.txt에 solapi를 추가하세요."
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
