# zeroda_platform/services/email_service.py
# ==========================================
# 이메일 발송 (네이버웍스 SMTP)
# ==========================================

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.mime.base      import MIMEBase
from email              import encoders
from datetime           import datetime
from config.settings    import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PW, COMPANY_NAME


def send_email(to_email: str, subject: str, body: str,
               attachments: list = None) -> tuple:
    """
    이메일 발송
    attachments: [{'filename': 'xxx.pdf', 'data': bytes}, ...]
    반환: (True, '성공') 또는 (False, '오류메시지')
    """
    if not SMTP_USER or not SMTP_PW:
        return False, "SMTP 설정이 없습니다. 환경변수를 확인하세요."

    try:
        msg = MIMEMultipart()
        msg['From']    = f"{COMPANY_NAME} <{SMTP_USER}>"
        msg['To']      = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        if attachments:
            for att in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(att['data'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f"attachment; filename*=UTF-8''{att['filename']}"
                )
                msg.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PW)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        return True, "발송 완료"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP 인증 실패 - 아이디/앱비밀번호 확인"
    except smtplib.SMTPException as e:
        return False, f"SMTP 오류: {str(e)}"
    except Exception as e:
        return False, f"발송 실패: {str(e)}"


def send_settlement_email(to_email: str, school_name: str,
                          year: int, month: int,
                          pdf_bytes: bytes = None,
                          excel_bytes: bytes = None) -> tuple:
    """정산서 이메일 발송 (PDF + 엑셀 첨부)"""

    subject = f"[{COMPANY_NAME}] {year}년 {month}월 음식물폐기물 수거 정산서 - {school_name}"

    body = f"""
    <div style="font-family: '맑은 고딕', sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a73e8; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h2 style="margin:0;">♻️ {COMPANY_NAME}</h2>
            <p style="margin:5px 0 0 0; opacity:0.8;">음식물폐기물 수거 정산서</p>
        </div>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px;">
            <p>안녕하세요, <strong>{school_name}</strong> 담당자님.</p>
            <p><strong>{year}년 {month}월</strong> 음식물폐기물 수거 정산서를 첨부 파일로 보내드립니다.</p>
            <hr style="border: none; border-top: 1px solid #dee2e6;">
            <table style="width:100%; border-collapse:collapse;">
                <tr>
                    <td style="padding:8px; color:#5f6368;">학교명</td>
                    <td style="padding:8px; font-weight:bold;">{school_name}</td>
                </tr>
                <tr style="background:#fff;">
                    <td style="padding:8px; color:#5f6368;">정산년월</td>
                    <td style="padding:8px; font-weight:bold;">{year}년 {month}월</td>
                </tr>
                <tr>
                    <td style="padding:8px; color:#5f6368;">발행일</td>
                    <td style="padding:8px;">{datetime.now().strftime('%Y년 %m월 %d일')}</td>
                </tr>
            </table>
            <hr style="border: none; border-top: 1px solid #dee2e6;">
            <p style="color:#5f6368; font-size:13px;">
                문의사항은 아래로 연락 주시기 바랍니다.<br>
                📧 {SMTP_USER} | 🏢 {COMPANY_NAME}
            </p>
        </div>
    </div>
    """

    attachments = []
    if pdf_bytes:
        attachments.append({
            'filename': f"{year}{month:02d}_{school_name}_정산서.pdf",
            'data': pdf_bytes
        })
    if excel_bytes:
        attachments.append({
            'filename': f"{year}{month:02d}_{school_name}_정산서.xlsx",
            'data': excel_bytes
        })

    return send_email(to_email, subject, body, attachments)


def send_bulk_settlement_emails(recipients: list) -> dict:
    """
    정산서 일괄 발송
    recipients: [{'email':..,'school':..,'year':..,'month':..,'pdf':..,'excel':..}, ...]
    반환: {'성공': [...], '실패': [...]}
    """
    result = {'성공': [], '실패': []}
    for r in recipients:
        ok, msg = send_settlement_email(
            to_email    = r['email'],
            school_name = r['school'],
            year        = r['year'],
            month       = r['month'],
            pdf_bytes   = r.get('pdf'),
            excel_bytes = r.get('excel'),
        )
        if ok:
            result['성공'].append(r['school'])
        else:
            result['실패'].append({'school': r['school'], 'error': msg})
    return result