# zeroda_reflex/utils/email_service.py
# 이메일 발송 서비스 — 네이버웍스 SMTP (SSL 465)
# Phase 6: PDF 첨부 이메일 발송 기능
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header

logger = logging.getLogger(__name__)


def _get_smtp_config() -> tuple[str, str]:
    """SMTP 계정 정보 조회 (환경변수 → .env)"""
    user = os.environ.get("WORKS_SMTP_USER", "") or os.environ.get("NAVER_SMTP_USER", "")
    pw = os.environ.get("WORKS_SMTP_APP_PW", "") or os.environ.get("NAVER_SMTP_APP_PW", "")
    if user and pw:
        return user, pw
    # .env 파일에서 읽기
    try:
        import pathlib
        env_path = pathlib.Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line.startswith("WORKS_SMTP_USER=") or line.startswith("NAVER_SMTP_USER="):
                    user = user or line.split("=", 1)[1].strip().strip('"').strip("'")
                elif line.startswith("WORKS_SMTP_APP_PW=") or line.startswith("NAVER_SMTP_APP_PW="):
                    pw = pw or line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return user, pw


def send_email_with_pdf(
    to_email: str,
    subject: str,
    body: str,
    pdf_bytes: bytes,
    filename: str,
) -> tuple[bool, str]:
    """
    PDF 첨부 이메일 발송 (네이버웍스 SMTP)

    Returns: (성공 여부, 메시지)
    """
    smtp_user, smtp_pw = _get_smtp_config()

    if not smtp_user or not smtp_pw:
        return False, "SMTP 설정이 없습니다. 환경변수 NAVER_SMTP_USER, NAVER_SMTP_APP_PW를 설정하세요."
    if not to_email or "@" not in to_email:
        return False, "유효한 수신 이메일 주소가 필요합니다."
    if not pdf_bytes:
        return False, "첨부할 PDF 파일이 없습니다."

    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = smtp_user
        msg["To"] = to_email
        # 한글 제목 깨짐 방지
        msg["Subject"] = Header(subject, "utf-8")

        # 본문
        text_part = MIMEText(body, "plain", "utf-8")
        msg.attach(text_part)

        # PDF 첨부
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition", "attachment",
            filename=("utf-8", "", filename),
        )
        msg.attach(pdf_part)

        # 네이버웍스 SMTP 발송 (SSL 465)
        with smtplib.SMTP_SSL("smtp.worksmobile.com", 465) as server:
            server.ehlo()
            server.login(smtp_user, smtp_pw)
            server.sendmail(smtp_user, [to_email], msg.as_string())

        logger.info(f"이메일 발송 완료: {to_email}")
        return True, f"{to_email} 으로 발송 완료"

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP 인증 실패")
        return False, "SMTP 인증 실패 — 네이버웍스 앱 비밀번호를 확인하세요."
    except smtplib.SMTPRecipientsRefused:
        logger.error(f"수신 이메일 오류: {to_email}")
        return False, f"수신 이메일 오류: {to_email}"
    except smtplib.SMTPException as e:
        logger.error(f"SMTP 오류: {e}")
        return False, f"SMTP 오류: {str(e)}"
    except Exception as e:
        logger.error(f"이메일 발송 실패: {e}")
        return False, f"발송 실패: {str(e)}"
