# zeroda_reflex/utils/pdf_export.py
# PDF 생성 래퍼 — zeroda_reflex 내부 pdf_generator 직접 import
# sys.path 해킹 제거: services/pdf_generator.py 의존성 없음
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
#  2. 스마트월말명세서 PDF (급식담당자)
#     → zeroda_reflex/utils/pdf_generator.py 직접 import
# ══════════════════════════════════════════════════════════════════════

def build_meal_statement_pdf(
    site_name: str,
    year: int,
    month: int,
    analysis_rows: list,
    menu_ranking: dict | None = None,
    ai_comment: str = "",
    **kwargs,
) -> bytes | None:
    """
    스마트월말명세서 PDF 바이트 반환.
    ai_comment: AI 추천 텍스트 (있으면 기관정보 다음, 분석표 이전에 배치)
    """
    try:
        from zeroda_reflex.utils.pdf_generator import generate_meal_statement_pdf
        return generate_meal_statement_pdf(
            site_name=site_name,
            year_month=f"{year}-{str(month).zfill(2)}",
            analysis_rows=analysis_rows,
            ai_comment=ai_comment,
            menu_ranking=menu_ranking,
        )
    except FileNotFoundError as e:
        # 폰트 없음 — 사용자가 조치해야 하므로 경고 로그 출력
        logger.error(f"스마트월말명세서 PDF 생성 실패 (폰트 없음):\n{e}")
        return None
    except Exception as e:
        logger.error(f"스마트월말명세서 PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
#  3. AI 월말명세서 PDF (급식담당자)
#     → zeroda_reflex/utils/pdf_generator.py 직접 import
# ══════════════════════════════════════════════════════════════════════

def build_ai_meal_statement_pdf(
    site_name: str,
    year: int,
    month: int,
    analysis_rows: list,
    ai_comment: str = "",
    menu_ranking: dict | None = None,
    cost_savings: dict | None = None,
    weekday_pattern: list | None = None,
    price_food: int = 0,
    **kwargs,
) -> bytes | None:
    """
    AI 월말명세서 PDF 바이트 반환.
    ai_comment: Paragraph + wordWrap='CJK' 로 자동 줄바꿈, 최상단 배치.
    """
    try:
        from zeroda_reflex.utils.pdf_generator import generate_ai_meal_statement_pdf
        return generate_ai_meal_statement_pdf(
            site_name=site_name,
            year_month=f"{year}-{str(month).zfill(2)}",
            analysis_rows=analysis_rows,
            ai_comment=ai_comment,
            menu_ranking=menu_ranking,
            cost_savings=cost_savings,
            weekday_pattern=weekday_pattern,
            price_food=price_food,
        )
    except FileNotFoundError as e:
        logger.error(f"AI 월말명세서 PDF 생성 실패 (폰트 없음):\n{e}")
        return None
    except Exception as e:
        logger.error(f"AI 월말명세서 PDF 생성 실패: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
#  1 / 4 / 5 / 6. 레거시 PDF 함수 — services/pdf_generator.py 삭제로
#  현재 사용 불가. 각 함수는 None 을 반환하고 경고 로그를 남깁니다.
#  향후 zeroda_reflex/utils/pdf_generator.py 에 이전 예정.
# ══════════════════════════════════════════════════════════════════════

def build_statement_pdf(*args, **kwargs) -> bytes | None:
    """거래명세서 PDF — 미이전 (services/ 삭제됨). None 반환."""
    logger.warning("build_statement_pdf: services/pdf_generator.py 삭제로 사용 불가.")
    return None


def build_school_esg_pdf(*args, **kwargs) -> bytes | None:
    """학교 ESG 보고서 PDF — 미이전. None 반환."""
    logger.warning("build_school_esg_pdf: services/pdf_generator.py 삭제로 사용 불가.")
    return None


def build_edu_office_esg_pdf(*args, **kwargs) -> bytes | None:
    """교육청 ESG 보고서 PDF — 미이전. None 반환."""
    logger.warning("build_edu_office_esg_pdf: services/pdf_generator.py 삭제로 사용 불가.")
    return None


def build_safety_report_pdf(*args, **kwargs) -> bytes | None:
    """안전관리 보고서 PDF — 미이전. None 반환."""
    logger.warning("build_safety_report_pdf: services/pdf_generator.py 삭제로 사용 불가.")
    return None
