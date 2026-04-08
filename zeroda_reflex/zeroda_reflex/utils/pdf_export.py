# zeroda_reflex/utils/pdf_export.py
# PDF 생성 래퍼 — 기존 services/pdf_generator.py 재사용
# Phase 5-A: Reflex에서 PDF 바이트를 생성하여 rx.download()로 전달
import logging
import sys
import pathlib

import uuid
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ── 거래명세서 저장소 ──
_STATEMENT_STORAGE_DIR = "/opt/zeroda-platform/storage/statements"
_STATEMENT_URL_BASE = "https://zeroda.co.kr/statements"
_STATEMENT_TTL_DAYS = 7


def save_statement_pdf_to_storage(pdf_bytes: bytes) -> tuple[str, str]:
    """PDF 바이트를 저장소에 UUID 파일명으로 저장.
    반환: (공개 URL, 파일시스템 경로). 실패 시 ("", "").
    """
    if not pdf_bytes:
        return "", ""
    try:
        os.makedirs(_STATEMENT_STORAGE_DIR, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.pdf"
        fpath = os.path.join(_STATEMENT_STORAGE_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(pdf_bytes)
        url = f"{_STATEMENT_URL_BASE}/{fname}"
        return url, fpath
    except Exception as e:
        logger.error(f"save_statement_pdf_to_storage 실패: {e}")
        return "", ""


def cleanup_old_statements(ttl_days: int = _STATEMENT_TTL_DAYS) -> int:
    """TTL 경과 파일 삭제. 반환: 삭제 건수."""
    if not os.path.isdir(_STATEMENT_STORAGE_DIR):
        return 0
    cutoff = datetime.now() - timedelta(days=ttl_days)
    deleted = 0
    for fname in os.listdir(_STATEMENT_STORAGE_DIR):
        fpath = os.path.join(_STATEMENT_STORAGE_DIR, fname)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            if mtime < cutoff:
                os.remove(fpath)
                deleted += 1
        except Exception as e:
            logger.warning(f"cleanup_old_statements: {fname} 실패 {e}")
    return deleted


# ── 기존 pdf_generator.py를 import 경로에 추가 ──
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent  # zeroda_platform/
_SERVICES_DIR = _PROJECT_ROOT / "services"
if str(_SERVICES_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVICES_DIR))


def _import_generator():
    """pdf_generator 모듈을 지연 import (reportlab 미설치 환경 대비)"""
    try:
        import pdf_generator
        return pdf_generator
    except ImportError as e:
        logger.error(f"pdf_generator import 실패: {e}")
        return None


# ══════════════════════════════════════════
#  1. 거래명세서 PDF (업체관리자 · 본사관리자)
# ══════════════════════════════════════════

def build_statement_pdf(
    vendor: str, school_name: str, year: int, month: int,
    rows: list, biz_info: dict, vendor_info: dict,
    cust_type: str = "", fixed_fee: float = 0,
) -> bytes | None:
    """거래명세서 PDF 바이트 반환. 실패 시 None."""
    gen = _import_generator()
    if not gen:
        return None
    try:
        return gen.generate_statement_pdf(
            vendor, school_name, year, month,
            rows, biz_info, vendor_info, cust_type, fixed_fee,
        )
    except Exception as e:
        logger.error(f"거래명세서 PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════
#  2. 스마트월말명세서 PDF (급식담당자)
# ══════════════════════════════════════════

def build_meal_statement_pdf(
    site_name: str, year: int, month: int,
    analysis_rows: list,
    menu_ranking: dict | None = None,
    ai_recommendation: list | None = None,
    school_standard: dict | None = None,
) -> bytes | None:
    """스마트월말명세서 PDF 바이트 반환."""
    gen = _import_generator()
    if not gen:
        return None
    try:
        return gen.generate_meal_statement_pdf(
            site_name, year, month, analysis_rows,
            menu_ranking, ai_recommendation, school_standard,
        )
    except Exception as e:
        logger.error(f"스마트월말명세서 PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════
#  3. AI 월말명세서 PDF (급식담당자)
# ══════════════════════════════════════════

def build_ai_meal_statement_pdf(
    site_name: str, year: int, month: int,
    analysis_rows: list, **kwargs,
) -> bytes | None:
    """AI 월말명세서 PDF 바이트 반환. kwargs로 선택 인자 전달."""
    gen = _import_generator()
    if not gen:
        return None
    try:
        return gen.generate_ai_meal_statement_pdf(
            site_name, year, month, analysis_rows, **kwargs,
        )
    except Exception as e:
        logger.error(f"AI 월말명세서 PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════
#  4. 학교 ESG 보고서 PDF
# ══════════════════════════════════════════

def build_school_esg_pdf(
    school_name: str, year: int, month_label: str,
    rows: list, vendor: str = "",
) -> bytes | None:
    """학교 ESG 보고서 PDF 바이트 반환."""
    gen = _import_generator()
    if not gen:
        return None
    try:
        return gen.generate_school_esg_pdf(
            school_name, year, month_label, rows, vendor,
        )
    except Exception as e:
        logger.error(f"학교 ESG PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════
#  5. 교육청 ESG 보고서 PDF
# ══════════════════════════════════════════

def build_edu_office_esg_pdf(
    edu_office_name: str, year: int, month_label: str,
    school_data: list, vendor: str = "",
) -> bytes | None:
    """교육청 ESG 보고서 PDF 바이트 반환."""
    gen = _import_generator()
    if not gen:
        return None
    try:
        return gen.generate_edu_office_esg_pdf(
            edu_office_name, year, month_label, school_data, vendor,
        )
    except Exception as e:
        logger.error(f"교육청 ESG PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════
#  6. 안전관리 보고서 PDF (학교 · 교육청 공용)
# ══════════════════════════════════════════

def build_safety_report_pdf(
    org_name: str, org_type: str, year: int, month: int,
    vendor_scores: list, violations: list,
    education_records: list, checklist_records: list,
    accident_records: list, vendor_name: str = "",
    checklist_results: list | None = None,
    daily_checks: list | None = None,
) -> bytes | None:
    """안전관리 보고서 PDF 바이트 반환."""
    gen = _import_generator()
    if not gen:
        return None
    try:
        return gen.generate_safety_report_pdf(
            org_name, org_type, year, month,
            vendor_scores, violations,
            education_records, checklist_records,
            accident_records, vendor_name,
            checklist_results, daily_checks,
        )
    except Exception as e:
        logger.error(f"안전관리 보고서 PDF 생성 실패: {e}")
        return None
