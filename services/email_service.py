# zeroda_platform/services/email_service.py
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header


def _get_smtp_config():
    try:
        import streamlit as st
        user = st.secrets.get("WORKS_SMTP_USER", "") or st.secrets.get("NAVER_SMTP_USER", "")
        pw   = st.secrets.get("WORKS_SMTP_APP_PW", "") or st.secrets.get("NAVER_SMTP_APP_PW", "")
    except Exception:
        user = os.environ.get("WORKS_SMTP_USER", "") or os.environ.get("NAVER_SMTP_USER", "")
        pw   = os.environ.get("WORKS_SMTP_APP_PW", "") or os.environ.get("NAVER_SMTP_APP_PW", "")
    return user, pw


def send_statement_email(to_email: str, subject: str, body: str,
                          pdf_bytes: bytes, filename: str) -> tuple:
    """
    거래명세서 PDF 이메일 발송
    Returns: (success: bool, message: str)
    """
    smtp_user, smtp_pw = _get_smtp_config()

    if not smtp_user or not smtp_pw:
        return False, "SMTP 설정 없음. Secrets에 NAVER_SMTP_USER, NAVER_SMTP_APP_PW를 등록하세요."
    if not to_email:
        return False, "수신 이메일 주소가 없습니다."

    try:
        msg = MIMEMultipart('mixed')
        msg['From']    = smtp_user
        msg['To']      = to_email
        # 한글 제목 깨짐 방지 - Header 인코딩
        msg['Subject'] = Header(subject, 'utf-8')

        # 본문 - utf-8 명시
        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)

        # 첨부파일 - 파일명 한글 깨짐 방지
        pdf_part = MIMEApplication(pdf_bytes, _subtype='pdf')
        # RFC2231 방식으로 한글 파일명 인코딩
        encoded_filename = Header(filename, 'utf-8').encode()
        pdf_part.add_header('Content-Disposition', 'attachment',
                            filename=('utf-8', '', filename))
        msg.attach(pdf_part)

        # 네이버웍스 SMTP 발송 (SSL 465)
        with smtplib.SMTP_SSL('smtp.worksmobile.com', 465) as server:
            server.ehlo()
            server.login(smtp_user, smtp_pw)
            server.sendmail(smtp_user, [to_email], msg.as_string())

        return True, f"✅ {to_email} 으로 발송 완료"

    except smtplib.SMTPAuthenticationError:
        return False, "❌ SMTP 인증 실패 - 네이버웍스 앱 비밀번호와 이메일 주소를 확인하세요."
    except smtplib.SMTPRecipientsRefused:
        return False, f"❌ 수신 이메일 오류: {to_email}"
    except smtplib.SMTPException as e:
        return False, f"❌ SMTP 오류: {str(e)}"
    except Exception as e:
        return False, f"❌ 발송 실패: {str(e)}"
