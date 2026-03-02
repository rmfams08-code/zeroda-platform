# zeroda_platform/services/pdf_generator.py
# 거래명세서 PDF 생성 - 한글 완벽 지원
from io import BytesIO
from datetime import datetime


def _get_korean_font():
    """한글 폰트 등록 - 우선순위로 시도"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    # 1순위: 프로젝트 내 TTF 폰트
    ttf_candidates = [
        'fonts/NanumGothic.ttf',
        'NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/malgun.ttf',
    ]
    for fp in ttf_candidates:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont('Korean', fp))
                return 'Korean'
            except Exception:
                continue

    # 2순위: reportlab 내장 CJK 폰트 (한국어 지원)
    cid_candidates = ['HYSMyeongJo-Medium', 'HYGoThic-Medium', 'HeiseiKakuGo-W5']
    for fname in cid_candidates:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(fname))
            return fname
        except Exception:
            continue

    return 'Helvetica'


def generate_statement_pdf(vendor: str, school_name: str, year: int, month: int,
                            rows: list, biz_info: dict, vendor_info: dict) -> bytes:
    """
    거래명세서 PDF 생성
    rows: 수거 데이터 리스트
    biz_info: 수급자(학교) 사업자 정보
    vendor_info: 공급자(업체) 정보
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle

    font = _get_korean_font()

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    def P(text, size=10, bold=False, align=0, color=colors.black):
        style = ParagraphStyle('s', fontName=font, fontSize=size,
                               alignment=align, textColor=color,
                               leading=size * 1.4)
        return Paragraph(str(text), style)

    BLUE   = colors.HexColor('#1a73e8')
    GREEN  = colors.HexColor('#34a853')
    LGRAY  = colors.HexColor('#f5f5f5')
    DGRAY  = colors.HexColor('#e0e0e0')

    story = []

    # ── 제목 ──────────────────────────────
    story.append(P("거  래  명  세  서", size=22, align=1, color=BLUE))
    story.append(Spacer(1, 3*mm))
    today = datetime.now().strftime('%Y년 %m월 %d일')
    story.append(P(f"발행일: {today}　　정산기간: {year}년 {month}월", size=9, align=2))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    story.append(Spacer(1, 4*mm))

    # ── 공급자 / 수급자 정보 ──────────────
    sup = vendor_info
    rec = biz_info
    info_data = [
        [P('공  급  자', size=10, align=1, color=colors.white),
         P('수  급  자', size=10, align=1, color=colors.white)],
        [P(f"상호: {sup.get('biz_name', vendor)}", size=9),
         P(f"상호: {rec.get('상호', school_name)}", size=9)],
        [P(f"대표자: {sup.get('rep', '')}", size=9),
         P(f"대표자: {rec.get('대표자', '')}", size=9)],
        [P(f"사업자번호: {sup.get('biz_no', '')}", size=9),
         P(f"사업자번호: {rec.get('사업자번호', '')}", size=9)],
        [P(f"주소: {sup.get('address', '')}", size=9),
         P(f"주소: {rec.get('주소', '')}", size=9)],
        [P(f"연락처: {sup.get('contact', '')}", size=9),
         P(f"이메일: {rec.get('이메일', '')}", size=9)],
    ]
    info_tbl = Table(info_data, colWidths=[90*mm, 90*mm])
    info_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  BLUE),
        ('BACKGROUND', (0,1), (-1,-1), LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('LINEAFTER',  (0,0), (0,-1),  0.8, colors.grey),
        ('INNERGRID',  (0,1), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 수거 내역 ─────────────────────────
    story.append(P("■ 수거 내역", size=11, color=BLUE))
    story.append(Spacer(1, 2*mm))

    header = ['날짜', '학교명', '품목', '수거량(kg)', '단가(원)', '금액(원)']
    tdata = [[P(h, size=9, align=1, color=colors.white) for h in header]]

    total_weight = 0.0
    total_amount = 0.0

    for r in rows:
        weight     = float(r.get('weight') or r.get('음식물(kg)') or 0)
        unit_price = float(r.get('unit_price') or r.get('단가(원)') or 0)
        amount     = weight * unit_price
        total_weight += weight
        total_amount += amount
        tdata.append([
            P(str(r.get('collect_date', r.get('날짜', ''))), size=8),
            P(str(r.get('school_name', r.get('학교명', school_name))), size=8),
            P(str(r.get('item_type', r.get('재활용방법', ''))), size=8),
            P(f"{weight:,.1f}", size=8, align=2),
            P(f"{unit_price:,.0f}", size=8, align=2),
            P(f"{amount:,.0f}", size=8, align=2),
        ])

    # 합계 행
    tdata.append([
        P('', size=9), P('합  계', size=9, align=1),
        P('', size=9),
        P(f"{total_weight:,.1f}", size=9, align=2),
        P('', size=9),
        P(f"{total_amount:,.0f}", size=9, align=2),
    ])

    cw = [28*mm, 42*mm, 28*mm, 24*mm, 22*mm, 26*mm]
    detail_tbl = Table(tdata, colWidths=cw)
    detail_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  GREEN),
        ('BACKGROUND', (0,-1),(-1,-1), LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 4),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(detail_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 합계 요약 ─────────────────────────
    vat   = total_amount * 0.1
    total = total_amount + vat
    sum_data = [
        [P('공급가액', size=10, color=colors.white),
         P(f"{total_amount:,.0f} 원", size=10, align=2, color=colors.white)],
        [P('부가세 (10%)', size=10),
         P(f"{vat:,.0f} 원", size=10, align=2)],
        [P('합계금액', size=11, color=colors.white),
         P(f"{total:,.0f} 원", size=11, align=2, color=colors.white)],
    ]
    sum_tbl = Table(sum_data, colWidths=[60*mm, 60*mm])
    sum_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  BLUE),
        ('BACKGROUND', (0,2), (-1,2),  colors.HexColor('#ea4335')),
        ('BACKGROUND', (0,1), (-1,1),  LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 6),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 8*mm))
    story.append(P("* 본 거래명세서는 전자 발행된 문서입니다.", size=8, color=colors.grey))

    doc.build(story)
    return buffer.getvalue()
