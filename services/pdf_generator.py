# zeroda_platform/services/pdf_generator.py
# 거래명세서 PDF 생성 - 한글 완벽 지원
from io import BytesIO
from datetime import datetime


# ── 잔반량 표준 데이터 (출처: 학교급식법 시행규칙 [별표 3], 2021.01.29 개정) ──
# 근거: 교육부 고시, 법제처 국가법령정보센터
# https://www.law.go.kr → 학교급식법 시행규칙 별표3
WASTE_STANDARD = {
    '남자고등': {
        'kcal': 900,        # 1끼 에너지 기준 (kcal)
        'supply_g': 780,    # 밥+국+반찬5종 총 제공량 (g)
        'waste_avg_g': 220, # 평균 잔반량 (g), 잔반율 약 28%
    },
    '여자고등': {
        'kcal': 670,
        'supply_g': 650,
        'waste_avg_g': 270, # 평균 잔반량 (g), 잔반율 약 42%
    },
    '혼합평균': {
        'kcal': 785,
        'supply_g': 715,
        'waste_avg_g': 245, # 남녀 혼합 평균 잔반량 (g)
    },
    '현장기준': {
        'kcal': 785,
        'supply_g': 750,
        'waste_avg_g': 300, # 현장 보수기준 (국물+채소 고잔반 시나리오)
    },
}
# 잔반 등급 기준 — 1인당 g 기준 (혼합평균 245g, 현장기준 300g 근거)
WASTE_GRADE = {
    'A': (0,   150),   # 우수: 150g 미만
    'B': (150, 245),   # 양호: 표준 이하 (245g 미만)
    'C': (245, 300),   # 주의: 표준 초과 (245~300g)
    'D': (300, 9999),  # 고잔반 경보: 300g 초과
}
# 구성별 제공량 및 잔반율 기준 (남자 고등학생 900kcal 기준)
MEAL_COMPOSITION = {
    '밥':       {'supply_g': 220, 'kcal': 330, 'waste_rate': 0.13},
    '국':       {'supply_g': 250, 'kcal':  50, 'waste_rate': 0.40},  # 국물 잔반 높음
    '육류반찬': {'supply_g':  80, 'kcal': 130, 'waste_rate': 0.15},
    '나물채소': {'supply_g':  60, 'kcal':  30, 'waste_rate': 0.50},  # 편식 잔반 높음
    '김치류':   {'supply_g':  60, 'kcal':  20, 'waste_rate': 0.40},
    '볶음류':   {'supply_g':  60, 'kcal':  80, 'waste_rate': 0.25},
    '기타반찬': {'supply_g':  50, 'kcal':  50, 'waste_rate': 0.28},
}
WASTE_SOURCE = (
    "출처: 학교급식법 시행규칙 [별표 3] (교육부, 2021.01.29 개정) | "
    "ZERODA 잔반 분석 표준 기준 v1.0"
)


def _get_korean_font():
    """한글 폰트 등록 - 우선순위로 시도"""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    # 1순위: 프로젝트 내 TTF 폰트 (한글 완벽 지원)
    import pathlib
    _base = pathlib.Path(__file__).resolve().parent.parent
    ttf_candidates = [
        str(_base / 'fonts' / 'NanumGothic.ttf'),
        'fonts/NanumGothic.ttf',
        'NanumGothic.ttf',
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        'C:/Windows/Fonts/malgun.ttf',
        'C:/Windows/Fonts/NanumGothic.ttf',
    ]
    for fp in ttf_candidates:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont('Korean', fp))
                return 'Korean'
            except Exception:
                continue

    # 2순위: reportlab 내장 CJK 폰트 (한국어 지원)
    # ※ CID 폰트는 PDF 뷰어에 한글 폰트가 설치된 환경에서 정상 표시됩니다.
    #    Windows: 맑은고딕(malgun.ttf) 자동 매핑 / Mac: Apple SD Gothic Neo
    #    완벽 임베딩을 원하면 fonts/NanumGothic.ttf 파일을 프로젝트에 추가하세요.
    cid_candidates = ['HYGothic-Medium', 'HYSMyeongJo-Medium', 'HeiseiKakuGo-W5']
    for fname in cid_candidates:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(fname))
            return fname
        except Exception:
            continue

    return 'Helvetica'


def generate_statement_pdf(vendor: str, school_name: str, year: int, month: int,
                            rows: list, biz_info: dict, vendor_info: dict,
                            cust_type: str = '') -> bytes:
    """
    거래명세서 PDF 생성
    cust_type: '학교'면 면세(부가세 없음), 그 외('기업','관공서','기타')면 부가세 10% 포함
    rows: 수거 데이터 리스트
    biz_info: 수급자(학교) 사업자 정보
    vendor_info: 공급자(업체) 정보
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    import os, pathlib

    font = _get_korean_font()

    # ── 직인 경로 탐색 ─────────────────────
    _base = pathlib.Path(__file__).resolve().parent.parent
    _stamp_candidates = [
        _base / 'assets' / 'stamp.png',
        pathlib.Path('assets') / 'stamp.png',
        pathlib.Path('assets/stamp.png'),
    ]
    _stamp_path = None
    for _p in _stamp_candidates:
        if _p.exists():
            _stamp_path = str(_p)
            break

    class _StampDoc(SimpleDocTemplate):
        """afterPage에서 직인을 그려서 테이블 위에 오버레이"""
        def afterPage(self):
            if not _stamp_path or self.page != 1:
                return
            try:
                stamp_size = 14 * mm
                # 공급자 컬럼 우측, 대표자 행 높이에 맞춤
                x = 15*mm + 90*mm - stamp_size - 3*mm
                y = A4[1] - 15*mm - 23*mm - 16*mm - stamp_size + 3*mm
                self.canv.saveState()
                self.canv.setFillAlpha(0.85)
                self.canv.drawImage(_stamp_path, x, y,
                                    width=stamp_size, height=stamp_size,
                                    mask='auto', preserveAspectRatio=True)
                self.canv.restoreState()
            except Exception as e:
                import logging
                logging.warning(f"직인 이미지 렌더링 실패: {e}")

    buffer = BytesIO()
    doc = _StampDoc(buffer, pagesize=A4,
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

    header = ['날짜', '품목', '수거량\n(kg)', '단가\n(원)', '금액\n(원)',
              '재활용방법', '재활용자\n(처리자)', '수집운반자', '비고']
    tdata = [[P(h, size=7, align=1, color=colors.white) for h in header]]

    # customer_info에서 학교별 품목 단가 조회 (load_customers_from_db 방식)
    try:
        from database.db_manager import load_customers_from_db
        _all_cust = load_customers_from_db(vendor)
        _cust_info = _all_cust.get(school_name, {})
        if not _cust_info:
            for _ck, _cv in _all_cust.items():
                if _cv.get('상호') == school_name:
                    _cust_info = _cv
                    break
        _price_cache = {}
        if _cust_info:
            _price_cache = {
                '음식물':       float(_cust_info.get('price_food', 0) or 0),
                '재활용':       float(_cust_info.get('price_recycle', 0) or 0),
                '일반':         float(_cust_info.get('price_general', 0) or 0),
                '사업장폐기물': float(_cust_info.get('price_general', 0) or 0),
                '음식물쓰레기': float(_cust_info.get('price_food', 0) or 0),
            }
    except Exception:
        _price_cache = {}

    # 재활용방법 매핑 (품목 → 재활용방법)
    _recycle_method_map = {
        '음식물': '퇴비화및비료생산', '음식물쓰레기': '퇴비화및비료생산',
        '재활용': '선별 후 재활용', '일반': '소각/매립', '사업장폐기물': '소각/매립',
    }

    total_weight = 0.0
    total_amount = 0.0

    for r in rows:
        weight     = float(r.get('weight') or r.get('음식물(kg)') or 0)
        _item = str(
            r.get('item_type', '')
            or r.get('품목', '')
        ).strip()
        unit_price = _price_cache.get(_item, 0.0)
        if unit_price == 0.0:
            unit_price = float(
                r.get('unit_price')
                or r.get('단가(원)')
                or 0
            )
        amount     = round(weight * unit_price, 0)
        total_weight += weight
        total_amount += amount

        # 재활용방법: row에 직접 있으면 사용, 없으면 품목별 기본값
        _r_method = str(r.get('recycle_method', r.get('재활용방법', '')) or '')
        if not _r_method:
            _r_method = _recycle_method_map.get(_item, '')
        # 재활용자(처리자): row에 직접 있으면 사용, 없으면 customer_info에서 조회
        _r_recycler = str(r.get('recycler', r.get('재활용자', '')) or '')
        if not _r_recycler and _cust_info:
            _r_recycler = str(_cust_info.get('재활용자', '') or '')
        # 수집운반자: row에 직접 있으면 사용, 없으면 공급자(업체)
        _r_collector = str(r.get('collector', r.get('수집운반자', '')) or '')
        if not _r_collector:
            _r_collector = vendor_info.get('biz_name', vendor)
        # 비고: 기사 특이사항 메모
        _r_memo = str(r.get('memo', r.get('비고', '')) or '')

        tdata.append([
            P(str(r.get('collect_date', r.get('날짜', ''))), size=7),
            P(_item, size=7, align=1),
            P(f"{weight:,.1f}", size=7, align=2),
            P(f"{unit_price:,.0f}", size=7, align=2),
            P(f"{amount:,.0f}", size=7, align=2),
            P(_r_method, size=6, align=1),
            P(_r_recycler, size=6, align=1),
            P(_r_collector, size=6, align=1),
            P(_r_memo, size=6),
        ])

    # 합계 행
    tdata.append([
        P('총  계', size=8, align=1), P('', size=8),
        P(f"{total_weight:,.1f}", size=8, align=2),
        P('', size=8),
        P(f"{total_amount:,.0f}", size=8, align=2),
        P('-', size=8, align=1), P('-', size=8, align=1),
        P('-', size=8, align=1), P('', size=8),
    ])

    # A4 가로 폭(210mm) - 좌우마진(30mm) = 180mm
    cw = [30*mm, 14*mm, 14*mm, 14*mm, 18*mm, 26*mm, 22*mm, 20*mm, 22*mm]
    detail_tbl = Table(tdata, colWidths=cw, repeatRows=1)
    detail_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  GREEN),
        ('BACKGROUND', (0,-1),(-1,-1), LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 3),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(detail_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 합계 요약 ─────────────────────────
    _is_tax_free = (cust_type in ('학교', ''))
    if _is_tax_free:
        # 학교: 면세 — 부가세 없음
        sum_data = [
            [P('공급가액', size=10, color=colors.white),
             P(f"{total_amount:,.0f} 원", size=10, align=2, color=colors.white)],
            [P('부가세', size=10),
             P('면세', size=10, align=2, color=colors.HexColor('#1a73e8'))],
            [P('합계금액', size=11, color=colors.white),
             P(f"{total_amount:,.0f} 원", size=11, align=2, color=colors.white)],
        ]
    else:
        # 기업/관공서/기타: 부가세 10% 포함
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
    pdf_bytes_result = buffer.getvalue()
    return pdf_bytes_result


# ─────────────────────────────────────────────────────────────────────────────
# 스마트월말명세서 PDF 생성 (단체급식 담당용)
# ─────────────────────────────────────────────────────────────────────────────

def generate_meal_statement_pdf(site_name: str, year: int, month: int,
                                 analysis_rows: list, menu_ranking: dict = None,
                                 ai_recommendation: list = None) -> bytes:
    """
    스마트월말명세서 PDF 생성
    - 1페이지: 기관정보 + 일별 식단↔잔반량 테이블 + 월간 요약
    - 2페이지(선택): AI 추천식단 (ai_recommendation이 있을 때만)
    """
    import json
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, HRFlowable, PageBreak)
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
    ORANGE = colors.HexColor('#fbbc05')
    RED    = colors.HexColor('#ea4335')
    LGRAY  = colors.HexColor('#f5f5f5')
    DGRAY  = colors.HexColor('#e0e0e0')

    story = []

    # ── 1페이지: 제목 ──
    story.append(P("스마트 월말명세서", size=20, align=1, color=BLUE))
    story.append(Spacer(1, 3*mm))
    today = datetime.now().strftime('%Y년 %m월 %d일')
    story.append(P(f"발행일: {today}　　분석기간: {year}년 {month}월", size=9, align=2))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    story.append(Spacer(1, 4*mm))

    # ── 기관 정보 ──
    info_data = [
        [P('기관명', size=9, align=1, color=colors.white),
         P(site_name, size=10)],
        [P('분석기간', size=9, align=1, color=colors.white),
         P(f"{year}년 {month}월", size=10)],
    ]
    info_tbl = Table(info_data, colWidths=[35*mm, 145*mm])
    info_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (0,-1),  BLUE),
        ('BACKGROUND', (1,0), (1,-1),  LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5*mm))

    # ── 월간 요약 ──
    story.append(P("■ 월간 요약", size=11, color=BLUE))
    story.append(Spacer(1, 2*mm))

    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in analysis_rows)
    valid_days = [r for r in analysis_rows if float(r.get('waste_per_person', 0) or 0) > 0]
    avg_pp = sum(float(r['waste_per_person']) for r in valid_days) / len(valid_days) if valid_days else 0
    matched_cnt = len([r for r in analysis_rows if float(r.get('waste_kg', 0) or 0) > 0])

    grade_counts = {}
    for r in analysis_rows:
        g = r.get('grade', '-')
        grade_counts[g] = grade_counts.get(g, 0) + 1
    main_grade = max(grade_counts, key=grade_counts.get) if grade_counts else '-'

    sum_data = [
        [P('총 잔반량', size=8, align=1, color=colors.white),
         P('1인당 평균', size=8, align=1, color=colors.white),
         P('매칭 일수', size=8, align=1, color=colors.white),
         P('주요 등급', size=8, align=1, color=colors.white)],
        [P(f"{total_waste:.1f} kg", size=11, align=1),
         P(f"{avg_pp:.1f} g", size=11, align=1),
         P(f"{matched_cnt} / {len(analysis_rows)}일", size=11, align=1),
         P(main_grade, size=14, align=1,
           color=GREEN if main_grade == 'A' else (ORANGE if main_grade == 'B' else RED))],
    ]
    sum_tbl = Table(sum_data, colWidths=[45*mm]*4)
    sum_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  BLUE),
        ('BACKGROUND', (0,1), (-1,1),  LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 5*mm))

    # ── 일별 상세 ──
    story.append(P("■ 일별 식단 × 잔반량", size=11, color=BLUE))
    story.append(Spacer(1, 2*mm))

    header = ['날짜', '메뉴', '잔반량(kg)', '1인당(g)', '등급']
    tdata = [[P(h, size=7, align=1, color=colors.white) for h in header]]

    for r in analysis_rows:
        try:
            menus = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menus = []
        menu_str = ", ".join(menus[:3])
        if len(menus) > 3:
            menu_str += f" 외 {len(menus)-3}"

        wkg = float(r.get('waste_kg', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        grade = r.get('grade', '-')
        grade_color = GREEN if grade == 'A' else (ORANGE if grade == 'B' else (RED if grade == 'D' else colors.black))

        tdata.append([
            P(r.get('meal_date', '')[-5:], size=7, align=1),
            P(menu_str, size=6),
            P(f"{wkg:.1f}", size=7, align=2),
            P(f"{wpp:.1f}", size=7, align=2),
            P(grade, size=8, align=1, color=grade_color),
        ])

    detail_tbl = Table(tdata, colWidths=[20*mm, 85*mm, 22*mm, 22*mm, 16*mm])
    detail_style = [
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  BLUE),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 3),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]
    for i in range(1, len(tdata)):
        bg = LGRAY if i % 2 == 0 else colors.white
        detail_style.append(('BACKGROUND', (0, i), (-1, i), bg))
    detail_tbl.setStyle(TableStyle(detail_style))
    story.append(detail_tbl)
    story.append(Spacer(1, 5*mm))

    # ── 메뉴별 순위 (잔반 적은 TOP 5 / 많은 TOP 5) ──
    if menu_ranking:
        story.append(P("■ 메뉴별 잔반 순위", size=11, color=BLUE))
        story.append(Spacer(1, 2*mm))

        good = menu_ranking.get('good', [])[:5]
        bad = menu_ranking.get('bad', [])[:5]

        rank_header = [P('순위', size=7, align=1, color=colors.white),
                       P('메뉴 (잔반 적은)', size=7, align=1, color=colors.white),
                       P('평균(g)', size=7, align=1, color=colors.white),
                       P('', size=7),
                       P('메뉴 (잔반 많은)', size=7, align=1, color=colors.white),
                       P('평균(g)', size=7, align=1, color=colors.white)]
        rank_data = [rank_header]
        for i in range(5):
            g = good[i] if i < len(good) else {}
            b = bad[i] if i < len(bad) else {}
            rank_data.append([
                P(str(i+1), size=7, align=1),
                P(g.get('menu', '-'), size=7),
                P(f"{g.get('avg_waste', 0):.1f}" if g else '-', size=7, align=2, color=GREEN),
                P('', size=7),
                P(b.get('menu', '-'), size=7),
                P(f"{b.get('avg_waste', 0):.1f}" if b else '-', size=7, align=2, color=RED),
            ])

        rank_tbl = Table(rank_data, colWidths=[12*mm, 50*mm, 18*mm, 5*mm, 50*mm, 18*mm])
        rank_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  BLUE),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(rank_tbl)

    story.append(Spacer(1, 6*mm))
    story.append(P(
        "* 본 명세서는 ZERODA 폐기물데이터플랫폼에서 자동 생성되었습니다. | "
        + WASTE_SOURCE,
        size=7, color=colors.grey))

    # ── 2페이지: AI 추천식단 (선택) ──
    if ai_recommendation:
        story.append(PageBreak())
        story.append(P("AI 추천식단", size=18, align=1, color=BLUE))
        story.append(Spacer(1, 2*mm))
        story.append(P(f"분석 기반 다음달 추천 메뉴 (ZERODA AI)", size=9, align=1, color=colors.grey))
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE))
        story.append(Spacer(1, 4*mm))

        ai_header = ['날짜', '요일', '추천 메뉴', 'kcal']
        ai_data = [[P(h, size=7, align=1, color=colors.white) for h in ai_header]]

        for m in ai_recommendation:
            menus = m.get('menu_items', [])
            menu_str = " / ".join(menus)
            ai_data.append([
                P(str(m.get('date', ''))[-5:], size=7, align=1),
                P(m.get('weekday', ''), size=7, align=1),
                P(menu_str, size=6),
                P(str(int(m.get('calories', 0))), size=7, align=2),
            ])

        ai_tbl = Table(ai_data, colWidths=[20*mm, 12*mm, 120*mm, 15*mm])
        ai_style = [
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  BLUE),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]
        for i in range(1, len(ai_data)):
            bg = LGRAY if i % 2 == 0 else colors.white
            ai_style.append(('BACKGROUND', (0, i), (-1, i), bg))
        ai_tbl.setStyle(TableStyle(ai_style))
        story.append(ai_tbl)

        story.append(Spacer(1, 5*mm))
        story.append(P("* AI 추천식단은 과거 잔반 데이터와 영양균형을 기반으로 생성되었습니다.",
                       size=8, color=colors.grey))
        story.append(P("* ZERODA Premium 서비스", size=8, color=BLUE))

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


# ─────────────────────────────────────────────────────────────────────────────
# 안전관리보고서 PDF 생성 (FEAT: 학교·교육청 안전관리 현황 리포트)
# ─────────────────────────────────────────────────────────────────────────────

# HWP 원본 기반 안전보건 점검 7개 항목
_SAFETY_CHECKLIST_ITEMS = [
    "과업지시서(또는 계약서)에 '안전관리 및 예방조치 후 작업' 실시 내용 포함",
    "공사(용역)업체에서 근로자에 대한 안전보건교육 실시",
    "안전보호구(안전모, 안전대, 안전화 등) 착용 주지",
    "위험사항(위험성평가 등)과 기계·기구·설비 안전점검 안내",
    "학교 현장 이동 시 행정실(담당자) 안내 주지",
    "유해·위험 작업 시 안전보건 점검표 제출 여부",
    "안전·보건에 관한 종사자 의견청취 실시",
]

_GRADE_EMOJI_PDF = {'S': 'S등급(최우수)', 'A': 'A등급(우수)', 'B': 'B등급(보통)',
                    'C': 'C등급(주의)', 'D': 'D등급(불량)'}
_GRADE_COLOR_PDF = {'S': '#1565C0', 'A': '#2D7D46', 'B': '#F9A825',
                    'C': '#E07B39', 'D': '#C0392B'}


def generate_safety_report_pdf(
    org_name: str,
    org_type: str,
    year: int,
    month: int,
    vendor_scores: list,
    violations: list,
    education_records: list,
    checklist_records: list,
    accident_records: list,
    vendor_name: str = '',
    checklist_results: list = None,
) -> bytes:
    """
    안전관리보고서 PDF 생성 (학교·교육청 공용)
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle

    font = _get_korean_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=15*mm, leftMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    def P(text, size=10, align=0, color=colors.black):
        style = ParagraphStyle('s', fontName=font, fontSize=size,
                               alignment=align, textColor=color,
                               leading=size * 1.5)
        return Paragraph(str(text), style)

    NAVY   = colors.HexColor('#1a237e')
    BLUE   = colors.HexColor('#1565c0')
    RED    = colors.HexColor('#c62828')
    GREEN  = colors.HexColor('#2d7d46')
    ORANGE = colors.HexColor('#e65100')
    GRAY   = colors.HexColor('#757575')
    LGRAY  = colors.HexColor('#f5f5f5')
    DGRAY  = colors.HexColor('#e0e0e0')
    LBLUE  = colors.HexColor('#e3f2fd')

    story = []
    today = datetime.now().strftime('%Y년 %m월 %d일')

    # ── 1. 헤더 ──────────────────────────────────────────────────────────────
    story.append(P(org_name, size=13, align=1, color=NAVY))
    story.append(P("월간 안전관리 보고서", size=20, align=1, color=NAVY))
    story.append(Spacer(1, 2*mm))
    story.append(P(f"보고 기간: {year}년 {month}월          작성일: {today}",
                   size=9, align=1, color=GRAY))
    if vendor_name:
        story.append(P(f"수거(용역) 업체: {vendor_name}", size=9, align=1, color=GRAY))
    story.append(HRFlowable(width="100%", thickness=2.5, color=NAVY))
    story.append(Spacer(1, 5*mm))

    # ── 2. 안전관리 평가 등급 ────────────────────────────────────────────────
    story.append(P("1. 안전관리 평가 등급", size=12, color=NAVY))
    story.append(Spacer(1, 2*mm))

    if vendor_scores:
        grade_header = [P(h, size=9, align=1, color=colors.white) for h in
                        ['업체', '평가월', '스쿨존위반(40)', '차량점검(30)',
                         '교육이수(30)', '총점', '등급']]
        grade_data = [grade_header]
        for sc in vendor_scores:
            grade = sc.get('grade', 'D')
            g_color = colors.HexColor(_GRADE_COLOR_PDF.get(grade, '#333'))
            grade_data.append([
                P(sc.get('vendor', ''), size=9),
                P(sc.get('year_month', ''), size=9, align=1),
                P(f"{sc.get('violation_score', 0):.0f}", size=9, align=2),
                P(f"{sc.get('checklist_score', 0):.1f}", size=9, align=2),
                P(f"{sc.get('education_score', 0):.1f}", size=9, align=2),
                P(f"{sc.get('total_score', 0):.0f}", size=10, align=2, color=g_color),
                P(_GRADE_EMOJI_PDF.get(grade, grade), size=9, align=1, color=g_color),
            ])
        cw_g = [30*mm, 22*mm, 24*mm, 22*mm, 22*mm, 18*mm, 30*mm]
        grade_tbl = Table(grade_data, colWidths=cw_g)
        grade_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  BLUE),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
            ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(grade_tbl)
    else:
        story.append(P("평가 데이터 없음", size=10, color=GRAY))
    story.append(Spacer(1, 6*mm))

    # ── 3. 안전보건 점검 현황 (HWP 기반 7항목) ──────────────────────────────
    story.append(P("2. 공사(용역) 안전보건 점검 현황", size=12, color=NAVY))
    story.append(Spacer(1, 1*mm))
    story.append(P("[학교(기관), 교육(지원)청에서 확인하여 자체 보관]",
                   size=8, color=GRAY))
    story.append(Spacer(1, 2*mm))

    check_results = checklist_results or ['예'] * 7
    cl_header = [P('번호', size=9, align=1, color=colors.white),
                 P('점 검 내 용', size=9, align=1, color=colors.white),
                 P('예', size=9, align=1, color=colors.white),
                 P('아니오', size=9, align=1, color=colors.white)]
    cl_data = [cl_header]
    for i, item_text in enumerate(_SAFETY_CHECKLIST_ITEMS):
        result = check_results[i] if i < len(check_results) else '예'
        cl_data.append([
            P(str(i+1), size=8, align=1),
            P(item_text, size=8),
            P('O' if result == '예' else '', size=9, align=1,
              color=GREEN if result == '예' else colors.black),
            P('O' if result != '예' else '', size=9, align=1,
              color=RED if result != '예' else colors.black),
        ])
    cw_cl = [12*mm, 120*mm, 18*mm, 18*mm]
    cl_tbl = Table(cl_data, colWidths=cw_cl)
    cl_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  NAVY),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LGRAY]),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 4),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(cl_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 4. 스쿨존 위반 이력 ──────────────────────────────────────────────────
    story.append(P("3. 스쿨존 위반 이력", size=12, color=NAVY))
    story.append(Spacer(1, 2*mm))

    if violations:
        v_header = [P(h, size=9, align=1, color=colors.white) for h in
                    ['위반일', '업체', '기사', '유형', '장소', '과태료(원)']]
        v_data = [v_header]
        total_fine = 0
        for v in violations:
            fine = int(v.get('fine_amount', 0) or 0)
            total_fine += fine
            v_data.append([
                P(str(v.get('violation_date', '')), size=8),
                P(str(v.get('vendor', '')), size=8),
                P(str(v.get('driver', '')), size=8),
                P(str(v.get('violation_type', '')), size=8),
                P(str(v.get('location', '')), size=8),
                P(f"{fine:,}", size=8, align=2),
            ])
        v_data.append([
            P('', size=9), P('합 계', size=9, align=1),
            P(f"{len(violations)}건", size=9, align=1, color=RED),
            P('', size=9), P('', size=9),
            P(f"{total_fine:,}", size=9, align=2, color=RED),
        ])
        cw_v = [24*mm, 24*mm, 22*mm, 22*mm, 44*mm, 28*mm]
        v_tbl = Table(v_data, colWidths=cw_v)
        v_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  RED),
            ('BACKGROUND', (0,-1),(-1,-1), colors.HexColor('#ffebee')),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, LGRAY]),
            ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(v_tbl)
    else:
        story.append(P("해당 기간 스쿨존 위반 기록 없음", size=10, color=GREEN))
    story.append(Spacer(1, 6*mm))

    # ── 5. 안전교육 이수 현황 ────────────────────────────────────────────────
    story.append(P("4. 안전교육 이수 현황", size=12, color=NAVY))
    story.append(Spacer(1, 2*mm))

    if education_records:
        e_header = [P(h, size=9, align=1, color=colors.white) for h in
                    ['교육일', '업체', '기사', '교육내용', '이수여부']]
        e_data = [e_header]
        for ed in education_records[:20]:
            e_data.append([
                P(str(ed.get('edu_date', '')), size=8),
                P(str(ed.get('vendor', '')), size=8),
                P(str(ed.get('driver', '')), size=8),
                P(str(ed.get('subject', '')), size=8),
                P(str(ed.get('status', '')), size=8, align=1),
            ])
        cw_e = [26*mm, 26*mm, 24*mm, 58*mm, 26*mm]
        e_tbl = Table(e_data, colWidths=cw_e)
        e_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  GREEN),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LGRAY]),
            ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(e_tbl)
        story.append(P(f"교육 이수 건수: {len(education_records)}건",
                       size=9, color=GREEN))
    else:
        story.append(P("해당 기간 안전교육 기록 없음", size=10, color=GRAY))
    story.append(Spacer(1, 6*mm))

    # ── 6. 차량점검 현황 ─────────────────────────────────────────────────────
    story.append(P("5. 차량 안전점검 현황", size=12, color=NAVY))
    story.append(Spacer(1, 2*mm))

    if checklist_records:
        ck_header = [P(h, size=9, align=1, color=colors.white) for h in
                     ['점검일', '업체', '기사', '차량번호', '점검결과']]
        ck_data = [ck_header]
        for ck in checklist_records[:20]:
            ck_data.append([
                P(str(ck.get('check_date', '')), size=8),
                P(str(ck.get('vendor', '')), size=8),
                P(str(ck.get('driver', '')), size=8),
                P(str(ck.get('vehicle', '')), size=8),
                P(str(ck.get('result', '')), size=8, align=1),
            ])
        cw_ck = [26*mm, 28*mm, 24*mm, 40*mm, 42*mm]
        ck_tbl = Table(ck_data, colWidths=cw_ck)
        ck_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  BLUE),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LBLUE]),
            ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(ck_tbl)
        story.append(P(f"점검 건수: {len(checklist_records)}건",
                       size=9, color=BLUE))
    else:
        story.append(P("해당 기간 차량점검 기록 없음", size=10, color=GRAY))
    story.append(Spacer(1, 6*mm))

    # ── 7. 사고 보고 현황 ────────────────────────────────────────────────────
    story.append(P("6. 사고 보고 현황", size=12, color=NAVY))
    story.append(Spacer(1, 2*mm))

    if accident_records:
        a_header = [P(h, size=9, align=1, color=colors.white) for h in
                    ['사고일', '업체', '기사', '사고유형', '상태']]
        a_data = [a_header]
        for ac in accident_records[:20]:
            a_data.append([
                P(str(ac.get('accident_date', '')), size=8),
                P(str(ac.get('vendor', '')), size=8),
                P(str(ac.get('driver', '')), size=8),
                P(str(ac.get('type', '')), size=8),
                P(str(ac.get('status', '')), size=8, align=1),
            ])
        cw_a = [26*mm, 28*mm, 24*mm, 46*mm, 36*mm]
        a_tbl = Table(a_data, colWidths=cw_a)
        a_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  ORANGE),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, LGRAY]),
            ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(a_tbl)
        story.append(P(f"사고 보고 건수: {len(accident_records)}건",
                       size=9, color=ORANGE))
    else:
        story.append(P("해당 기간 사고 보고 없음", size=10, color=GREEN))
    story.append(Spacer(1, 6*mm))

    # ── 8. 공사업체 확인서 ───────────────────────────────────────────────────
    story.append(P("7. 공사업체 확인서", size=12, color=NAVY))
    story.append(Spacer(1, 2*mm))

    confirm_text = (
        "위 점검사항에 대해 안내를 받았으며 산업안전보건법규에 따라 "
        "작업자에게 안전보건보호구 지급 및 안전수칙을 준수하여 "
        "작업할 것을 확인합니다."
    )
    confirm_data = [
        [P(confirm_text, size=9)],
        [P(f"소속(회사): {vendor_name or '하영자원'}          "
           f"공사(용역)업체 책임자:                    (서명)",
           size=9)],
    ]
    conf_tbl = Table(confirm_data, colWidths=[168*mm])
    conf_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,-1), LGRAY),
        ('BOX',        (0,0), (-1,-1), 1, NAVY),
        ('PADDING',    (0,0), (-1,-1), 10),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(conf_tbl)
    story.append(Spacer(1, 3*mm))

    # ── 결재란 ────────────────────────────────────────────────────────────
    if org_type == 'school':
        sign_headers = ['담당', '행정실장', '학교장']
    else:
        sign_headers = ['담당', '과장', '국장']
    sign_data = [
        [P(h, size=9, align=1, color=colors.white) for h in ['결재'] + sign_headers],
        [P('', size=9)] + [P('', size=9)] * len(sign_headers),
    ]
    cw_sign = [20*mm] + [30*mm] * len(sign_headers)
    sign_tbl = Table(sign_data, colWidths=cw_sign, rowHeights=[16, 30])
    sign_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  NAVY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.5, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 4),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sign_tbl)
    story.append(Spacer(1, 6*mm))

    # ── 푸터 ──────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    story.append(Spacer(1, 2*mm))
    story.append(P("본 보고서는 zeroda 폐기물 데이터 플랫폼(zeroda2026.streamlit.app)에서 자동 생성되었습니다.",
                   size=8, align=1, color=GRAY))
    story.append(P(f"수거(용역) 업체: {vendor_name or '하영자원'}  |  발행: {datetime.now().strftime('%Y-%m-%d')}",
                   size=8, align=1, color=GRAY))
    story.append(P("※ 작성대상: 금액에 상관없이 1회성 소규모 수선 등 모든 공사, 용역 포함",
                   size=7, align=1, color=GRAY))

    doc.build(story)
    return buffer.getvalue()
