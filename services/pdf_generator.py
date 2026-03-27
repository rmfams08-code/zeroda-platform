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

    # customer_info에서 학교별 품목 단가 사전 로딩
    from database.db_manager import db_get
    price_cache = {}
    try:
        cust_rows = db_get(
            'customer_info',
            {'vendor': vendor, 'name': school_name}
        )
        if cust_rows:
            price_cache = {
                '음식물':       float(cust_rows[0].get('price_food', 0) or 0),
                '재활용':       float(cust_rows[0].get('price_recycle', 0) or 0),
                '일반':         float(cust_rows[0].get('price_general', 0) or 0),
                '사업장폐기물': float(cust_rows[0].get('price_general', 0) or 0),
            }
    except Exception:
        price_cache = {}

    total_weight = 0.0
    total_amount = 0.0

    for r in rows:
        weight     = float(r.get('weight') or r.get('음식물(kg)') or 0)
        # 1순위: customer_info 단가 (실시간 조회)
        # 2순위: real_collection에 저장된 단가
        # 3순위: 0
        item = str(r.get('item_type', '') or r.get('품목', ''))
        unit_price = price_cache.get(item, 0.0)
        if unit_price == 0.0:
            unit_price = float(r.get('unit_price') or r.get('단가(원)') or 0)
        amount     = round(weight * unit_price, 0)
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


# ─────────────────────────────────────────────────────────────────────────────
# ESG 보고서 PDF 생성 함수 (추가 - 기존 코드 유지)
# ─────────────────────────────────────────────────────────────────────────────

def _calc_esg_metrics(rows: list) -> dict:
    """ESG 지표 계산 공통 함수"""
    food_kg     = sum(float(r.get('weight', 0)) for r in rows
                      if str(r.get('item_type', r.get('재활용방법', ''))).startswith('음식물'))
    recycle_kg  = sum(float(r.get('weight', 0)) for r in rows
                      if '재활용' in str(r.get('item_type', r.get('재활용방법', ''))))
    general_kg  = sum(float(r.get('weight', 0)) for r in rows
                      if '사업장' in str(r.get('item_type', r.get('재활용방법', ''))) or
                         '일반' in str(r.get('item_type', r.get('재활용방법', ''))))
    total_kg    = sum(float(r.get('weight', 0)) for r in rows)

    # 탄소감축 계산 (음식물 0.47, 재활용 0.21, 일반 0.09 kgCO2/kg)
    carbon = food_kg * 0.47 + recycle_kg * 0.21 + general_kg * 0.09
    # 나무 1그루 = 연간 6.6kgCO2 흡수
    trees  = carbon / 6.6
    # 소나무 1그루 = 연간 4.6kgCO2 흡수
    pine   = carbon / 4.6

    return {
        'total_kg':    total_kg,
        'food_kg':     food_kg,
        'recycle_kg':  recycle_kg,
        'general_kg':  general_kg,
        'carbon':      carbon,
        'trees':       trees,
        'pine':        pine,
    }


def generate_school_esg_pdf(school_name: str, year: int, month_label: str,
                             rows: list, vendor: str = '') -> bytes:
    """
    학교 ESG 보고서 PDF 생성
    month_label: 예) '2024년 1~6월', '2024년 7월'
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle

    font  = _get_korean_font()
    W, _H = A4

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    def P(text, size=10, bold=False, align=0, color=colors.black):
        style = ParagraphStyle('s', fontName=font, fontSize=size,
                               alignment=align, textColor=color,
                               leading=size * 1.5)
        return Paragraph(str(text), style)

    GREEN1 = colors.HexColor('#2d7d46')   # 진초록
    GREEN2 = colors.HexColor('#4caf50')   # 중간초록
    GREEN3 = colors.HexColor('#e8f5e9')   # 연초록 배경
    GRAY   = colors.HexColor('#757575')
    LGRAY  = colors.HexColor('#f5f5f5')
    DGRAY  = colors.HexColor('#e0e0e0')

    m = _calc_esg_metrics(rows)
    story = []

    # ── 헤더 ──────────────────────────────────────────────────────────────────
    story.append(P(f"{school_name}", size=13, align=1, color=GREEN1))
    story.append(P(f"ESG 폐기물 수거 실적보고서", size=20, align=1, color=GREEN1))
    story.append(Spacer(1, 2*mm))
    story.append(P(f"대상 기간: {month_label}　　발행일: {datetime.now().strftime('%Y년 %m월 %d일')}",
                   size=9, align=1, color=GRAY))
    story.append(HRFlowable(width="100%", thickness=2.5, color=GREEN1))
    story.append(Spacer(1, 5*mm))

    # ── 핵심 성과 4개 카드 ─────────────────────────────────────────────────
    story.append(P("■ 핵심 환경 성과", size=12, color=GREEN1))
    story.append(Spacer(1, 2*mm))

    card_data = [
        [P('총 수거량', size=9, align=1, color=colors.white),
         P('탄소 감축량', size=9, align=1, color=colors.white),
         P('소나무 환산', size=9, align=1, color=colors.white),
         P('나무 환산', size=9, align=1, color=colors.white)],
        [P(f"{m['total_kg']:,.0f} kg", size=14, align=1, color=GREEN1),
         P(f"{m['carbon']:,.1f} kg", size=14, align=1, color=GREEN1),
         P(f"{m['pine']:,.1f} 그루", size=14, align=1, color=GREEN1),
         P(f"{m['trees']:,.1f} 그루", size=14, align=1, color=GREEN1)],
        [P('이 기간 수거 총량', size=8, align=1, color=GRAY),
         P('CO\u2082 기준', size=8, align=1, color=GRAY),
         P('소나무 4.6 kgCO\u2082/그루\u00b7년', size=8, align=1, color=GRAY),
         P('일반 나무 6.6 kgCO\u2082/그루\u00b7년', size=8, align=1, color=GRAY)],
    ]
    cw4 = [42*mm] * 4
    card_tbl = Table(card_data, colWidths=cw4)
    card_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  GREEN2),
        ('BACKGROUND', (0,1), (-1,2),  GREEN3),
        ('BOX',        (0,0), (-1,-1), 1, GREEN2),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.white),
        ('PADDING',    (0,0), (-1,-1), 7),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(card_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 품목별 수거 실적 ──────────────────────────────────────────────────
    story.append(P("■ 품목별 수거 실적 (E - 녹색 행정)", size=12, color=GREEN1))
    story.append(Spacer(1, 2*mm))

    item_data = [
        [P(h, size=9, align=1, color=colors.white) for h in
         ['품목', '수거량 (kg)', '비율 (%)', '탄소 감축 (kgCO\u2082)', '소나무 환산 (그루)']],
    ]
    items = [
        ('음식물폐기물', m['food_kg'],    0.47),
        ('재활용 폐기물', m['recycle_kg'], 0.21),
        ('사업장 일반폐기물', m['general_kg'], 0.09),
    ]
    for name, kg, factor in items:
        pct   = (kg / m['total_kg'] * 100) if m['total_kg'] > 0 else 0
        c_red = kg * factor
        pine  = c_red / 4.6
        item_data.append([
            P(name, size=9),
            P(f"{kg:,.1f}", size=9, align=2),
            P(f"{pct:.1f}%", size=9, align=2),
            P(f"{c_red:,.1f}", size=9, align=2),
            P(f"{pine:,.1f}", size=9, align=2),
        ])
    # 합계
    item_data.append([
        P('합  계', size=9, align=1, color=colors.white),
        P(f"{m['total_kg']:,.1f}", size=9, align=2, color=colors.white),
        P('100.0%', size=9, align=2, color=colors.white),
        P(f"{m['carbon']:,.1f}", size=9, align=2, color=colors.white),
        P(f"{m['pine']:,.1f}", size=9, align=2, color=colors.white),
    ])
    cw5 = [44*mm, 30*mm, 22*mm, 36*mm, 36*mm]
    item_tbl = Table(item_data, colWidths=cw5)
    item_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), font),
        ('BACKGROUND',  (0,0), (-1,0),  GREEN2),
        ('BACKGROUND',  (0,-1),(-1,-1), GREEN1),
        ('BACKGROUND',  (0,1), (-1,-2), LGRAY),
        ('BOX',         (0,0), (-1,-1), 0.8, GREEN2),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',     (0,0), (-1,-1), 5),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(item_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 소나무 환경 효과 강조 박스 ─────────────────────────────────────────
    story.append(P("■ 환경 기여 효과 (소나무 기준)", size=12, color=GREEN1))
    story.append(Spacer(1, 2*mm))

    pine_effect = [
        [P('🌲 소나무 환산 효과', size=11, align=1, color=GREEN1)],
        [P(f"이 기간 폐기물 분리수거로 대기 중 CO\u2082 {m['carbon']:,.1f}kg 감축",
           size=10, align=1)],
        [P(f"이는 소나무 {m['pine']:,.1f}그루가 1년간 흡수하는 CO\u2082와 동일한 양입니다.",
           size=10, align=1, color=GREEN1)],
        [P(f"(소나무 1그루 = 연간 4.6 kgCO\u2082 흡수 기준 / 출처: 국립산림과학원)",
           size=8, align=1, color=GRAY)],
    ]
    pine_tbl = Table(pine_effect, colWidths=[168*mm])
    pine_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,-1), GREEN3),
        ('BOX',        (0,0), (-1,-1), 1.5, GREEN2),
        ('PADDING',    (0,0), (-1,-1), 8),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(pine_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 수거 일정 요약 ────────────────────────────────────────────────────
    if rows:
        story.append(P("■ 수거 이행 현황 (G - 투명 행정)", size=12, color=GREEN1))
        story.append(Spacer(1, 2*mm))
        dates = sorted(set(str(r.get('collect_date', ''))[:10] for r in rows if r.get('collect_date')))
        count = len(dates)
        g_data = [
            [P('총 수거 횟수', size=9, align=1, color=colors.white),
             P('최초 수거일', size=9, align=1, color=colors.white),
             P('최근 수거일', size=9, align=1, color=colors.white),
             P('수거 업체', size=9, align=1, color=colors.white)],
            [P(f"{count}회", size=12, align=1, color=GREEN1),
             P(dates[0] if dates else '-', size=10, align=1),
             P(dates[-1] if dates else '-', size=10, align=1),
             P(vendor or '하영자원', size=10, align=1)],
        ]
        g_tbl = Table(g_data, colWidths=[42*mm]*4)
        g_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  GREEN2),
            ('BACKGROUND', (0,1), (-1,-1), GREEN3),
            ('BOX',        (0,0), (-1,-1), 0.8, GREEN2),
            ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.white),
            ('PADDING',    (0,0), (-1,-1), 7),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(g_tbl)
        story.append(Spacer(1, 5*mm))

    # ── 푸터 ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN2))
    story.append(Spacer(1, 2*mm))
    story.append(P("본 보고서는 zeroda 폐기물 데이터 플랫폼(zeroda2026.streamlit.app)에서 자동 생성되었습니다.",
                   size=8, align=1, color=GRAY))
    story.append(P(f"수거 업체: {vendor or '하영자원'}  |  발행: {datetime.now().strftime('%Y-%m-%d')}",
                   size=8, align=1, color=GRAY))

    doc.build(story)
    return buffer.getvalue()


def generate_edu_office_esg_pdf(edu_office_name: str, year: int, month_label: str,
                                 school_data: list, vendor: str = '') -> bytes:
    """
    교육청 ESG 보고서 PDF 생성
    school_data: [{'school': 학교명, 'rows': [...수거데이터]}, ...]
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable, PageBreak)
    from reportlab.lib.styles import ParagraphStyle

    font  = _get_korean_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=18*mm, leftMargin=18*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    def P(text, size=10, align=0, color=colors.black):
        style = ParagraphStyle('s', fontName=font, fontSize=size,
                               alignment=align, textColor=color,
                               leading=size * 1.5)
        return Paragraph(str(text), style)

    GREEN1 = colors.HexColor('#2d7d46')
    GREEN2 = colors.HexColor('#4caf50')
    GREEN3 = colors.HexColor('#e8f5e9')
    BLUE1  = colors.HexColor('#1565c0')
    GRAY   = colors.HexColor('#757575')
    LGRAY  = colors.HexColor('#f5f5f5')
    DGRAY  = colors.HexColor('#e0e0e0')

    story = []

    # 전체 합산
    all_rows = [r for sd in school_data for r in sd.get('rows', [])]
    total_m  = _calc_esg_metrics(all_rows)
    school_count = len(school_data)

    # ── 표지 헤더 ─────────────────────────────────────────────────────────
    story.append(P(f"{edu_office_name}", size=13, align=1, color=BLUE1))
    story.append(P("ESG 학교 폐기물 수거 종합 실적보고서", size=19, align=1, color=GREEN1))
    story.append(Spacer(1, 2*mm))
    story.append(P(f"대상 기간: {month_label}　　관할 학교 수: {school_count}개교　　발행일: {datetime.now().strftime('%Y년 %m월 %d일')}",
                   size=9, align=1, color=GRAY))
    story.append(HRFlowable(width="100%", thickness=2.5, color=GREEN1))
    story.append(Spacer(1, 5*mm))

    # ── 전체 핵심 지표 ────────────────────────────────────────────────────
    story.append(P("■ 관할 전체 핵심 성과", size=12, color=GREEN1))
    story.append(Spacer(1, 2*mm))

    summary_data = [
        [P(h, size=9, align=1, color=colors.white) for h in
         ['관할 학교 수', '총 수거량', '탄소 감축량', '소나무 환산', '나무 환산']],
        [P(f"{school_count}개교", size=13, align=1, color=BLUE1),
         P(f"{total_m['total_kg']:,.0f} kg", size=13, align=1, color=GREEN1),
         P(f"{total_m['carbon']:,.1f} kg", size=13, align=1, color=GREEN1),
         P(f"{total_m['pine']:,.1f} 그루", size=13, align=1, color=GREEN1),
         P(f"{total_m['trees']:,.1f} 그루", size=13, align=1, color=GREEN1)],
        [P('', size=8, align=1),
         P('전체 수거 합산', size=8, align=1, color=GRAY),
         P('CO\u2082 기준', size=8, align=1, color=GRAY),
         P('4.6 kgCO\u2082/그루\u00b7년', size=8, align=1, color=GRAY),
         P('6.6 kgCO\u2082/그루\u00b7년', size=8, align=1, color=GRAY)],
    ]
    cw5 = [30*mm, 35*mm, 35*mm, 35*mm, 35*mm]
    sum_tbl = Table(summary_data, colWidths=cw5)
    sum_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  GREEN2),
        ('BACKGROUND', (0,1), (-1,2),  GREEN3),
        ('BOX',        (0,0), (-1,-1), 1, GREEN2),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, colors.white),
        ('PADDING',    (0,0), (-1,-1), 7),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 5*mm))

    # ── 소나무 환경 효과 강조 박스 ─────────────────────────────────────────
    pine_box = [
        [P(f"🌲  관할 {school_count}개 학교의 분리수거로 소나무 {total_m['pine']:,.1f}그루 효과",
           size=12, align=1, color=GREEN1)],
        [P(f"탄소 감축 총량 {total_m['carbon']:,.1f} kgCO\u2082  =  소나무 {total_m['pine']:,.1f}그루 × 연간 흡수량 4.6 kgCO\u2082",
           size=9, align=1)],
        [P("(출처: 국립산림과학원 / 소나무 1그루 연간 4.6 kgCO\u2082, 일반 나무 6.6 kgCO\u2082 흡수 기준)",
           size=8, align=1, color=GRAY)],
    ]
    pb_tbl = Table(pine_box, colWidths=[168*mm])
    pb_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,-1), GREEN3),
        ('BOX',        (0,0), (-1,-1), 2, GREEN2),
        ('PADDING',    (0,0), (-1,-1), 8),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(pb_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 학교별 순위표 ─────────────────────────────────────────────────────
    story.append(P("■ 학교별 수거 실적 순위 (E - 녹색 행정)", size=12, color=GREEN1))
    story.append(Spacer(1, 2*mm))

    ranking = []
    for sd in school_data:
        m = _calc_esg_metrics(sd.get('rows', []))
        ranking.append((sd['school'], m))
    ranking.sort(key=lambda x: x[1]['total_kg'], reverse=True)

    rank_header = [P(h, size=9, align=1, color=colors.white) for h in
                   ['순위', '학교명', '수거량(kg)', '탄소감축(kgCO\u2082)', '소나무(그루)', '수거횟수']]
    rank_data = [rank_header]
    for i, (sch, m) in enumerate(ranking, 1):
        cnt = len(sd['rows']) if any(sd['school'] == sch for sd in school_data) else 0
        for sd in school_data:
            if sd['school'] == sch:
                cnt = len(sd['rows'])
                break
        bg = GREEN3 if i % 2 == 0 else colors.white
        rank_data.append([
            P(f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else str(i)}", size=9, align=1),
            P(sch, size=9),
            P(f"{m['total_kg']:,.1f}", size=9, align=2),
            P(f"{m['carbon']:,.1f}", size=9, align=2),
            P(f"{m['pine']:,.1f}", size=9, align=2),
            P(f"{cnt}회", size=9, align=2),
        ])

    cw6 = [14*mm, 52*mm, 28*mm, 32*mm, 26*mm, 16*mm]
    rank_tbl = Table(rank_data, colWidths=cw6)
    rank_tbl.setStyle(TableStyle([
        ('FONTNAME',    (0,0), (-1,-1), font),
        ('BACKGROUND',  (0,0), (-1,0),  GREEN1),
        ('BOX',         (0,0), (-1,-1), 0.8, GREEN2),
        ('INNERGRID',   (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',     (0,0), (-1,-1), 5),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, GREEN3]),
    ]))
    story.append(rank_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 품목별 전체 집계 ──────────────────────────────────────────────────
    story.append(P("■ 품목별 수거 집계", size=12, color=GREEN1))
    story.append(Spacer(1, 2*mm))

    total_m2 = _calc_esg_metrics(all_rows)
    items = [
        ('음식물폐기물',      total_m2['food_kg'],    0.47),
        ('재활용 폐기물',     total_m2['recycle_kg'], 0.21),
        ('사업장 일반폐기물', total_m2['general_kg'], 0.09),
    ]
    cat_header = [P(h, size=9, align=1, color=colors.white) for h in
                  ['품목', '수거량(kg)', '비율(%)', '탄소감축(kgCO\u2082)', '소나무 환산(그루)']]
    cat_data = [cat_header]
    for name, kg, factor in items:
        pct  = (kg / total_m2['total_kg'] * 100) if total_m2['total_kg'] > 0 else 0
        cred = kg * factor
        pine = cred / 4.6
        cat_data.append([
            P(name, size=9),
            P(f"{kg:,.1f}", size=9, align=2),
            P(f"{pct:.1f}%", size=9, align=2),
            P(f"{cred:,.1f}", size=9, align=2),
            P(f"{pine:,.1f}", size=9, align=2),
        ])
    cat_data.append([
        P('합  계', size=9, align=1, color=colors.white),
        P(f"{total_m2['total_kg']:,.1f}", size=9, align=2, color=colors.white),
        P('100.0%', size=9, align=2, color=colors.white),
        P(f"{total_m2['carbon']:,.1f}", size=9, align=2, color=colors.white),
        P(f"{total_m2['pine']:,.1f}", size=9, align=2, color=colors.white),
    ])
    cat_tbl = Table(cat_data, colWidths=[44*mm, 30*mm, 22*mm, 36*mm, 36*mm])
    cat_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  GREEN2),
        ('BACKGROUND', (0,-1),(-1,-1), GREEN1),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, GREEN3]),
        ('BOX',        (0,0), (-1,-1), 0.8, GREEN2),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(cat_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 푸터 ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN2))
    story.append(Spacer(1, 2*mm))
    story.append(P("본 보고서는 zeroda 폐기물 데이터 플랫폼(zeroda2026.streamlit.app)에서 자동 생성되었습니다.",
                   size=8, align=1, color=GRAY))
    story.append(P(f"수거 업체: {vendor or '하영자원'}  |  발행: {datetime.now().strftime('%Y-%m-%d')}",
                   size=8, align=1, color=GRAY))

    doc.build(story)
    return buffer.getvalue()
