# zeroda_reflex/utils/excel_export.py
# ══════════════════════════════════════════════════════════════
#  Excel 다운로드 유틸리티 (Phase 3)
#  - openpyxl로 Excel 파일을 메모리에서 생성하여 bytes로 반환
#  - 각 역할별 state에서 호출하여 rx.download()로 전달
# ══════════════════════════════════════════════════════════════
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False
    logger.warning("openpyxl 미설치 — Excel 다운로드 기능 비활성화")


# ══════════════════════════════════════════
#  공통 스타일 정의
# ══════════════════════════════════════════

# 헤더 스타일 — 진한 파란 배경 + 흰 글자
HEADER_FONT = Font(name="맑은 고딕", size=11, bold=True, color="FFFFFF") if HAS_OPENPYXL else None
HEADER_FILL = PatternFill(start_color="1A73E8", end_color="1A73E8", fill_type="solid") if HAS_OPENPYXL else None
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True) if HAS_OPENPYXL else None

# 데이터 셀 스타일
DATA_FONT = Font(name="맑은 고딕", size=10) if HAS_OPENPYXL else None
DATA_ALIGN_LEFT = Alignment(horizontal="left", vertical="center") if HAS_OPENPYXL else None
DATA_ALIGN_RIGHT = Alignment(horizontal="right", vertical="center") if HAS_OPENPYXL else None
DATA_ALIGN_CENTER = Alignment(horizontal="center", vertical="center") if HAS_OPENPYXL else None

# 테두리
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
) if HAS_OPENPYXL else None

# 제목 스타일 — 큰 제목 행
TITLE_FONT = Font(name="맑은 고딕", size=14, bold=True, color="1A73E8") if HAS_OPENPYXL else None

# 소계/합계 행 스타일
TOTAL_FONT = Font(name="맑은 고딕", size=10, bold=True) if HAS_OPENPYXL else None
TOTAL_FILL = PatternFill(start_color="F0F4FF", end_color="F0F4FF", fill_type="solid") if HAS_OPENPYXL else None


def _apply_header_style(ws, row: int, col_count: int):
    """헤더 행에 스타일 적용"""
    for c in range(1, col_count + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGN
        cell.border = THIN_BORDER


def _apply_data_style(ws, row: int, col_count: int, aligns: list[str] | None = None):
    """데이터 행에 스타일 적용

    Args:
        aligns: 각 컬럼별 정렬 ("L"=왼쪽, "R"=오른쪽, "C"=가운데)
    """
    align_map = {"L": DATA_ALIGN_LEFT, "R": DATA_ALIGN_RIGHT, "C": DATA_ALIGN_CENTER}
    for c in range(1, col_count + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = DATA_FONT
        cell.border = THIN_BORDER
        if aligns and c <= len(aligns):
            cell.alignment = align_map.get(aligns[c - 1], DATA_ALIGN_LEFT)
        else:
            cell.alignment = DATA_ALIGN_LEFT


def _auto_width(ws, col_count: int, min_width: int = 10, max_width: int = 40):
    """컬럼 너비 자동 조절 — 한글 폭 고려"""
    for c in range(1, col_count + 1):
        letter = get_column_letter(c)
        max_len = min_width
        for row in ws.iter_rows(min_col=c, max_col=c, values_only=False):
            cell = row[0]
            if cell.value:
                # 한글은 약 2칸, 영문/숫자는 1칸으로 계산
                val = str(cell.value)
                char_len = sum(2 if ord(ch) > 127 else 1 for ch in val)
                max_len = max(max_len, char_len + 2)
        ws.column_dimensions[letter].width = min(max_len, max_width)


def _create_workbook_with_title(title: str, subtitle: str = "") -> tuple:
    """제목이 포함된 워크북 생성

    Returns:
        (workbook, worksheet, 데이터 시작 행 번호)
    """
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]  # Excel 시트명 31자 제한

    # 제목 행
    ws.cell(row=1, column=1, value=f"ZERODA — {title}")
    ws.cell(row=1, column=1).font = TITLE_FONT
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=6)

    # 부제목/생성일시
    if not subtitle:
        subtitle = f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ws.cell(row=2, column=1, value=subtitle)
    ws.cell(row=2, column=1).font = Font(name="맑은 고딕", size=9, color="666666")

    return wb, ws, 4  # 4행부터 데이터 시작


def build_excel(
    title: str,
    headers: list[str],
    rows: list[list],
    aligns: list[str] | None = None,
    subtitle: str = "",
    totals: list | None = None,
) -> bytes:
    """범용 Excel 생성 함수 — bytes로 반환

    모든 Excel 다운로드의 핵심 함수입니다.

    Args:
        title: 시트 제목 (예: "수거데이터")
        headers: 컬럼 헤더 리스트 (예: ["날짜", "학교명", "품목", "수거량(kg)"])
        rows: 데이터 행 리스트 (예: [["2026-04-01", "가나초등", "음식물", 12.5], ...])
        aligns: 컬럼별 정렬 ("L","R","C") 리스트. None이면 전부 왼쪽
        subtitle: 부제목 (비워두면 생성일시 자동)
        totals: 합계 행 리스트 (예: ["합계", "", "", 125.0])

    Returns:
        Excel 파일의 bytes 데이터

    사용 예 (state 메서드 내):
        data = build_excel("수거데이터", headers, rows, aligns=["C","L","C","R"])
        return rx.download(data=data, filename="수거데이터_2026-04.xlsx")
    """
    if not HAS_OPENPYXL:
        logger.error("openpyxl 미설치 — Excel 생성 불가")
        return b""

    wb, ws, start_row = _create_workbook_with_title(title, subtitle)
    col_count = len(headers)

    # 헤더 작성
    for c, h in enumerate(headers, 1):
        ws.cell(row=start_row, column=c, value=h)
    _apply_header_style(ws, start_row, col_count)

    # 데이터 행 작성
    for r_idx, row_data in enumerate(rows, start_row + 1):
        for c_idx, val in enumerate(row_data, 1):
            ws.cell(row=r_idx, column=c_idx, value=val)
        _apply_data_style(ws, r_idx, col_count, aligns)

    # 합계 행 (있으면)
    if totals:
        total_row = start_row + 1 + len(rows)
        for c_idx, val in enumerate(totals, 1):
            cell = ws.cell(row=total_row, column=c_idx, value=val)
            cell.font = TOTAL_FONT
            cell.fill = TOTAL_FILL
            cell.border = THIN_BORDER
            if aligns and c_idx <= len(aligns):
                align_map = {"L": DATA_ALIGN_LEFT, "R": DATA_ALIGN_RIGHT, "C": DATA_ALIGN_CENTER}
                cell.alignment = align_map.get(aligns[c_idx - 1], DATA_ALIGN_LEFT)

    # 컬럼 너비 자동 조절
    _auto_width(ws, col_count)

    # bytes로 변환
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


# ══════════════════════════════════════════
#  역할별 Excel 생성 함수 (7종)
# ══════════════════════════════════════════

def export_collection_data(data: list[dict], year: str, month: str) -> bytes:
    """3-1. 수거데이터 Excel (본사/업체 공용)

    Args:
        data: 수거 기록 딕셔너리 리스트
        year, month: 필터링된 연/월
    """
    headers = ["수거일자", "업체", "학교명", "품목", "수거량(kg)", "기사", "상태"]
    aligns = ["C", "L", "L", "C", "R", "L", "C"]
    rows = []
    total_weight = 0.0
    for r in data:
        w = float(r.get("weight", 0) or 0)
        total_weight += w
        rows.append([
            r.get("collect_date", ""),
            r.get("vendor", ""),
            r.get("school_name", ""),
            r.get("item_type", ""),
            round(w, 1),
            r.get("driver", ""),
            r.get("status", ""),
        ])
    totals = ["합계", "", "", "", round(total_weight, 1), f"{len(rows)}건", ""]
    return build_excel(
        title="수거데이터",
        headers=headers,
        rows=rows,
        aligns=aligns,
        subtitle=f"{year}년 {month}월 수거 데이터",
        totals=totals,
    )


def export_settlement(data: list[dict], summary: dict, year: str, month: str) -> bytes:
    """3-2. 정산내역 Excel (본사/업체 공용)

    Args:
        data: 정산 상세 내역
        summary: 정산 요약 (total_amount, vat, grand_total 등)
        year, month: 정산 기간
    """
    headers = ["학교명", "품목", "수거량(kg)", "단가(원)", "공급가액(원)", "수거건수"]
    aligns = ["L", "C", "R", "R", "R", "C"]
    rows = []
    for r in data:
        rows.append([
            r.get("school_name", r.get("name", "")),
            r.get("item_type", ""),
            float(r.get("weight", 0) or 0),
            int(float(r.get("unit_price", 0) or 0)),
            int(float(r.get("amount", 0) or 0)),
            int(r.get("count", 0) or 0),
        ])

    total_amt = summary.get("total_amount", "0")
    vat = summary.get("vat", "0")
    grand = summary.get("grand_total", "0")
    totals = [
        "합계", "",
        summary.get("total_weight", ""),
        "",
        int(float(total_amt)),
        "",
    ]
    return build_excel(
        title="정산내역",
        headers=headers,
        rows=rows,
        aligns=aligns,
        subtitle=f"{year}년 {month}월 정산 | 공급가 {total_amt}원 + VAT {vat}원 = 합계 {grand}원",
        totals=totals,
    )


def export_carbon_data(data: dict, ranking: list[dict], year: str) -> bytes:
    """3-3. 탄소감축 Excel (본사/교육청 공용)

    Args:
        data: 탄소감축 요약 (food_kg, recycle_kg, carbon_reduced 등)
        ranking: 학교별 탄소감축 순위
        year: 연도
    """
    # 요약 시트
    headers = ["항목", "값", "단위"]
    aligns = ["L", "R", "L"]
    summary_rows = [
        ["음식물 수거량", float(data.get("food_kg", 0) or 0), "kg"],
        ["재활용 수거량", float(data.get("recycle_kg", 0) or 0), "kg"],
        ["일반 수거량", float(data.get("general_kg", 0) or 0), "kg"],
        ["총 수거량", float(data.get("total_kg", 0) or 0), "kg"],
        ["탄소 감축량", float(data.get("carbon_reduced", 0) or 0), "kg CO₂"],
        ["나무 환산", int(float(data.get("tree_equivalent", 0) or 0)), "그루"],
    ]

    if not HAS_OPENPYXL:
        return b""

    wb, ws, start = _create_workbook_with_title("탄소감축 현황", f"{year}년 탄소감축 분석")
    col_count = 3

    # 요약 테이블
    for c, h in enumerate(headers, 1):
        ws.cell(row=start, column=c, value=h)
    _apply_header_style(ws, start, col_count)
    for r_idx, row_data in enumerate(summary_rows, start + 1):
        for c_idx, val in enumerate(row_data, 1):
            ws.cell(row=r_idx, column=c_idx, value=val)
        _apply_data_style(ws, r_idx, col_count, aligns)

    # 학교별 순위 테이블
    rank_start = start + len(summary_rows) + 3
    ws.cell(row=rank_start - 1, column=1, value="학교별 탄소감축 순위")
    ws.cell(row=rank_start - 1, column=1).font = Font(name="맑은 고딕", size=12, bold=True)
    rank_headers = ["순위", "학교명", "수거량(kg)", "탄소감축(kg CO₂)"]
    for c, h in enumerate(rank_headers, 1):
        ws.cell(row=rank_start, column=c, value=h)
    _apply_header_style(ws, rank_start, 4)

    for idx, r in enumerate(ranking, 1):
        row_num = rank_start + idx
        ws.cell(row=row_num, column=1, value=idx)
        ws.cell(row=row_num, column=2, value=r.get("school_name", ""))
        ws.cell(row=row_num, column=3, value=float(r.get("total_weight", 0) or 0))
        ws.cell(row=row_num, column=4, value=float(r.get("carbon", 0) or 0))
        _apply_data_style(ws, row_num, 4, ["C", "L", "R", "R"])

    _auto_width(ws, 4)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_safety_data(
    edu_data: list[dict],
    check_data: list[dict],
    accident_data: list[dict],
    vendor: str = "",
) -> bytes:
    """3-4. 안전관리 Excel (본사/업체 공용)

    3개 시트: 안전교육, 차량점검, 사고이력
    """
    if not HAS_OPENPYXL:
        return b""

    wb = Workbook()

    # ── 시트1: 안전교육 ──
    ws1 = wb.active
    ws1.title = "안전교육"
    edu_headers = ["교육일", "교육유형", "참석자", "이수시간", "결과"]
    for c, h in enumerate(edu_headers, 1):
        ws1.cell(row=1, column=c, value=h)
    _apply_header_style(ws1, 1, len(edu_headers))
    for r_idx, r in enumerate(edu_data, 2):
        ws1.cell(row=r_idx, column=1, value=r.get("edu_date", ""))
        ws1.cell(row=r_idx, column=2, value=r.get("edu_type", ""))
        ws1.cell(row=r_idx, column=3, value=r.get("attendee", ""))
        ws1.cell(row=r_idx, column=4, value=r.get("hours", ""))
        ws1.cell(row=r_idx, column=5, value=r.get("result", ""))
        _apply_data_style(ws1, r_idx, len(edu_headers), ["C", "L", "L", "C", "C"])
    _auto_width(ws1, len(edu_headers))

    # ── 시트2: 차량점검 ──
    ws2 = wb.create_sheet("차량점검")
    chk_headers = ["점검일", "기사", "차량번호", "결과", "비고"]
    for c, h in enumerate(chk_headers, 1):
        ws2.cell(row=1, column=c, value=h)
    _apply_header_style(ws2, 1, len(chk_headers))
    for r_idx, r in enumerate(check_data, 2):
        ws2.cell(row=r_idx, column=1, value=r.get("check_date", ""))
        ws2.cell(row=r_idx, column=2, value=r.get("driver", ""))
        ws2.cell(row=r_idx, column=3, value=r.get("vehicle_no", ""))
        ws2.cell(row=r_idx, column=4, value=r.get("result", ""))
        ws2.cell(row=r_idx, column=5, value=r.get("memo", ""))
        _apply_data_style(ws2, r_idx, len(chk_headers), ["C", "L", "L", "C", "L"])
    _auto_width(ws2, len(chk_headers))

    # ── 시트3: 사고이력 ──
    ws3 = wb.create_sheet("사고이력")
    acc_headers = ["발생일", "유형", "심각도", "기사", "장소", "내용"]
    for c, h in enumerate(acc_headers, 1):
        ws3.cell(row=1, column=c, value=h)
    _apply_header_style(ws3, 1, len(acc_headers))
    for r_idx, r in enumerate(accident_data, 2):
        ws3.cell(row=r_idx, column=1, value=r.get("accident_date", ""))
        ws3.cell(row=r_idx, column=2, value=r.get("accident_type", ""))
        ws3.cell(row=r_idx, column=3, value=r.get("severity", ""))
        ws3.cell(row=r_idx, column=4, value=r.get("driver", ""))
        ws3.cell(row=r_idx, column=5, value=r.get("location", ""))
        ws3.cell(row=r_idx, column=6, value=r.get("description", ""))
        _apply_data_style(ws3, r_idx, len(acc_headers), ["C", "C", "C", "L", "L", "L"])
    _auto_width(ws3, len(acc_headers))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_school_collections(data: list[dict], school: str, year: str, month: str) -> bytes:
    """3-5. 수거내역 Excel (학교용)"""
    headers = ["수거일자", "품목", "수거량(kg)", "기사", "상태"]
    aligns = ["C", "C", "R", "L", "C"]
    rows = []
    total_weight = 0.0
    for r in data:
        w = float(r.get("weight", 0) or 0)
        total_weight += w
        rows.append([
            r.get("collect_date", ""),
            r.get("item_type", ""),
            round(w, 1),
            r.get("driver", ""),
            r.get("status", ""),
        ])
    totals = ["합계", "", round(total_weight, 1), f"{len(rows)}건", ""]
    return build_excel(
        title=f"{school} 수거내역",
        headers=headers,
        rows=rows,
        aligns=aligns,
        subtitle=f"{year}년 {month}월 | {school}",
        totals=totals,
    )


def export_customers(data: list[dict], vendor: str = "") -> bytes:
    """3-6. 거래처 목록 Excel (업체용)"""
    headers = ["거래처명", "유형", "대표자", "사업자번호", "연락처", "이메일",
               "음식물 단가", "재활용 단가", "일반 단가"]
    aligns = ["L", "C", "L", "C", "C", "L", "R", "R", "R"]
    rows = []
    for r in data:
        rows.append([
            r.get("name", ""),
            r.get("cust_type", ""),
            r.get("ceo", ""),
            r.get("biz_no", ""),
            r.get("phone", ""),
            r.get("email", ""),
            int(float(r.get("price_food", 0) or 0)),
            int(float(r.get("price_recycle", 0) or 0)),
            int(float(r.get("price_general", 0) or 0)),
        ])
    return build_excel(
        title="거래처 목록",
        headers=headers,
        rows=rows,
        aligns=aligns,
        subtitle=f"업체: {vendor}" if vendor else "",
    )


def export_meal_data(data: list[dict], site: str, year: str, month: str) -> bytes:
    """3-7. 식단 데이터 Excel (급식용)"""
    headers = ["날짜", "식단명", "메뉴", "칼로리(kcal)", "인원수", "알레르기", "잔반등급"]
    aligns = ["C", "L", "L", "R", "R", "L", "C"]
    rows = []
    for r in data:
        rows.append([
            r.get("meal_date", ""),
            r.get("meal_name", ""),
            r.get("menu", ""),
            int(float(r.get("calories", 0) or 0)),
            int(float(r.get("servings", 0) or 0)),
            r.get("allergens", ""),
            r.get("waste_grade", "-"),
        ])
    return build_excel(
        title="식단 데이터",
        headers=headers,
        rows=rows,
        aligns=aligns,
        subtitle=f"{year}년 {month}월 | {site}",
    )
