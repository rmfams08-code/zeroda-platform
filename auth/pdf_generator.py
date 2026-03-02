# zeroda_platform/services/pdf_generator.py
# ==========================================
# PDF 생성 (수거일보, 정산서, 계약서)
# ==========================================

import io
import os
from datetime import datetime
from config.settings import (
    PLATFORM_NAME, COMPANY_NAME, CO2_FACTOR, TREE_FACTOR, FONT_CANDIDATES
)

# ──────────────────────────────────────────
# 한글 폰트 설정
# ──────────────────────────────────────────

def get_korean_font():
    """사용 가능한 한글 폰트 경로 반환"""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        for path, index in FONT_CANDIDATES:
            if not os.path.exists(path):
                continue
            try:
                if index is not None:
                    from reportlab.pdfbase.ttfonts import TTFont as TF
                    pdfmetrics.registerFont(TF('KoreanFont', path, subfontIndex=index))
                else:
                    pdfmetrics.registerFont(TTFont('KoreanFont', path))
                return 'KoreanFont'
            except Exception:
                continue
    except ImportError:
        pass
    return 'Helvetica'


FONT_NAME = get_korean_font()


# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────

def _fmt_num(val):
    """숫자 → 천단위 콤마 문자열"""
    try:
        return f"{int(float(val)):,}"
    except Exception:
        return str(val)


def _safe(val, default=''):
    return val if val is not None else default


# ──────────────────────────────────────────
# 수거일보 PDF
# ──────────────────────────────────────────

def generate_collection_report_pdf(school_name, year, month,
                                   collection_data, contract_price=162):
    """
    학교별 월간 수거일보 PDF 생성
    반환: bytes (PDF 바이너리)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer
        )
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    style_title = ParagraphStyle('title', fontName=FONT_NAME,
                                 fontSize=16, leading=20, alignment=1)
    style_sub   = ParagraphStyle('sub',   fontName=FONT_NAME,
                                 fontSize=10, leading=14, alignment=1)
    style_body  = ParagraphStyle('body',  fontName=FONT_NAME,
                                 fontSize=9,  leading=13)

    elements = []

    # 제목
    elements.append(Paragraph(f"{year}년 {month}월 음식물폐기물 수거일보", style_title))
    elements.append(Paragraph(f"{school_name}", style_sub))
    elements.append(Spacer(1, 0.5*cm))

    # 집계
    total_kg    = sum(float(r.get('음식물(kg)', 0) or 0) for r in collection_data)
    total_price = int(total_kg * contract_price)
    supply      = int(total_price / 1.1)
    vat         = total_price - supply
    co2_saved   = round(total_kg * CO2_FACTOR, 1)
    trees       = round(co2_saved / TREE_FACTOR, 1)

    # 요약 테이블
    summary = [
        ['항목', '내용'],
        ['학교명',     school_name],
        ['정산년월',   f"{year}년 {month}월"],
        ['총 수거량',  f"{total_kg:,.1f} kg"],
        ['계약단가',   f"{contract_price:,} 원/kg"],
        ['공급가액',   f"{supply:,} 원"],
        ['부가세(10%)', f"{vat:,} 원"],
        ['합계금액',   f"{total_price:,} 원"],
        ['CO₂ 감축',   f"{co2_saved:,} kg"],
        ['동등 식수',  f"소나무 {trees:,} 그루"],
    ]
    t = Table(summary, colWidths=[5*cm, 10*cm])
    t.setStyle(TableStyle([
        ('FONTNAME',    (0,0),(-1,-1), FONT_NAME),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('BACKGROUND',  (0,0),(-1,0),  colors.HexColor('#1a73e8')),
        ('TEXTCOLOR',   (0,0),(-1,0),  colors.white),
        ('FONTNAME',    (0,0),(-1,0),  FONT_NAME),
        ('FONTSIZE',    (0,0),(-1,0),  10),
        ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID',        (0,0),(-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('FONTNAME',    (0,7),(1,7), FONT_NAME),
        ('TEXTCOLOR',   (0,7),(1,7), colors.HexColor('#1a73e8')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))

    # 일별 수거 상세
    if collection_data:
        elements.append(Paragraph("▶ 일별 수거 내역", style_body))
        elements.append(Spacer(1, 0.2*cm))

        detail_header = ['날짜', '수거량(kg)', '단가(원)', '금액(원)', '수거업체']
        detail_rows   = [detail_header]
        for r in sorted(collection_data, key=lambda x: x.get('날짜', '')):
            kg    = float(r.get('음식물(kg)', 0) or 0)
            price = float(r.get('단가(원)', contract_price) or contract_price)
            amt   = int(kg * price)
            detail_rows.append([
                _safe(r.get('날짜'), '-'),
                f"{kg:.1f}",
                f"{int(price):,}",
                f"{amt:,}",
                _safe(r.get('수거업체'), '-'),
            ])

        dt = Table(detail_rows, colWidths=[3*cm, 3*cm, 3*cm, 3.5*cm, 4.5*cm])
        dt.setStyle(TableStyle([
            ('FONTNAME',    (0,0),(-1,-1), FONT_NAME),
            ('FONTSIZE',    (0,0),(-1,-1), 8),
            ('BACKGROUND',  (0,0),(-1,0),  colors.HexColor('#34a853')),
            ('TEXTCOLOR',   (0,0),(-1,0),  colors.white),
            ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
            ('ROWBACKGROUNDS', (0,1),(-1,-1), [colors.white, colors.HexColor('#f0f9f2')]),
            ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#dee2e6')),
        ]))
        elements.append(dt)

    # 하단 서명란
    elements.append(Spacer(1, 1*cm))
    sign_data = [
        ['발행기관', COMPANY_NAME, '발행일', datetime.now().strftime('%Y년 %m월 %d일')],
        ['담당자', '',            '서명',   ''],
    ]
    st = Table(sign_data, colWidths=[3*cm, 5*cm, 3*cm, 6*cm])
    st.setStyle(TableStyle([
        ('FONTNAME', (0,0),(-1,-1), FONT_NAME),
        ('FONTSIZE', (0,0),(-1,-1), 9),
        ('GRID',     (0,0),(-1,-1), 0.5, colors.HexColor('#dee2e6')),
        ('ALIGN',    (0,0),(-1,-1), 'CENTER'),
        ('BACKGROUND',(0,0),(0,-1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND',(2,0),(2,-1), colors.HexColor('#f8f9fa')),
    ]))
    elements.append(st)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()


# ──────────────────────────────────────────
# 정산서 PDF
# ──────────────────────────────────────────

def generate_settlement_pdf(vendor, year, month, settlement_data):
    """
    월별 정산서 PDF
    settlement_data: [{'학교명':..,'수거량':..,'단가':..,'금액':..}, ...]
    반환: bytes
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer
        )
        from reportlab.lib.styles import ParagraphStyle
    except ImportError:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    style_title = ParagraphStyle('t', fontName=FONT_NAME, fontSize=16,
                                 leading=20, alignment=1)
    style_body  = ParagraphStyle('b', fontName=FONT_NAME, fontSize=9, leading=13)

    elements = []
    elements.append(Paragraph(f"{year}년 {month}월 수거 정산서", style_title))
    elements.append(Paragraph(f"외주업체: {vendor}", style_body))
    elements.append(Spacer(1, 0.5*cm))

    total_kg  = sum(float(r.get('수거량', 0) or 0) for r in settlement_data)
    total_amt = sum(int(r.get('금액', 0)   or 0) for r in settlement_data)
    supply    = int(total_amt / 1.1)
    vat       = total_amt - supply

    # 상세 테이블
    header = ['학교명', '수거량(kg)', '단가(원/kg)', '공급가액', '부가세', '합계']
    rows   = [header]
    for r in settlement_data:
        kg  = float(r.get('수거량', 0) or 0)
        amt = int(r.get('금액', 0) or 0)
        sup = int(amt / 1.1)
        vt  = amt - sup
        rows.append([
            r.get('학교명', ''),
            f"{kg:,.1f}",
            f"{int(r.get('단가', 0) or 0):,}",
            f"{sup:,}",
            f"{vt:,}",
            f"{amt:,}",
        ])

    # 합계 행
    rows.append([
        '합 계',
        f"{total_kg:,.1f}",
        '-',
        f"{supply:,}",
        f"{vat:,}",
        f"{total_amt:,}",
    ])

    t = Table(rows, colWidths=[4.5*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm, 3*cm])
    t.setStyle(TableStyle([
        ('FONTNAME',    (0,0),(-1,-1), FONT_NAME),
        ('FONTSIZE',    (0,0),(-1,-1), 8),
        ('BACKGROUND',  (0,0),(-1,0),  colors.HexColor('#1a73e8')),
        ('TEXTCOLOR',   (0,0),(-1,0),  colors.white),
        ('BACKGROUND',  (0,-1),(-1,-1),colors.HexColor('#e8f4fd')),
        ('FONTNAME',    (0,-1),(-1,-1),FONT_NAME),
        ('ALIGN',       (0,0),(-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),[colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID',        (0,0),(-1,-1), 0.3, colors.HexColor('#dee2e6')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(
        f"발행일: {datetime.now().strftime('%Y년 %m월 %d일')}  |  발행: {COMPANY_NAME}",
        style_body))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()