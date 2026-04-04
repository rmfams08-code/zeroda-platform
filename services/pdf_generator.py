# zeroda_platform/services/pdf_generator.py
# 거래명세서 PDF 생성 - 한글 완벽 지원
from io import BytesIO
from datetime import datetime


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ── ZERODA 잔반 분석 표준 기준 v2.0 ──
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# [근거 1] 학교급식법 시행규칙 [별표 3] (교육부, 2021.01.29 개정)
#   - 법제처 국가법령정보센터 https://www.law.go.kr
#   - 학교급별 영양 기준(kcal) 및 1끼 제공량
#
# [근거 2] 경기도교육청, 「2023학년도 학교급식 정책추진 기본계획」, 2023.02
#   - https://www.goe.go.kr
#   - 2021년 경기도 급식학교 음식물쓰레기: 45,627톤/년, 처리비용 85억 원/년
#   - 폐기물 유형: 전처리(과일껍질·채소껍질·다시마·멸치),
#                   일반(뼈·조개껍질), 순수잔반(배식 후 학생 남긴 잔반)
#
# [근거 3] 한국식품영양과학회 (2019), JAKO201908662572910
#   - 「경기도 학교급식 음식물쓰레기 발생 실태 및 잔반 감량화 방안」
#   - 경기도 영양교사 622명 대상
#   - 잔반 발생 순위: 채소찬 57.4% > 국·찌개류 22.7% > 생선찬 13.5%
#
# [근거 4] 한국식품영양학회지, KCI 등재 (ART001424254)
#   - 「고등학생의 학교급식 만족도와 메뉴 선호도」
#   - 전북 익산시 고등학생 692명 대상
#   - 잔식 순위: 채소·나물 41.3% > 생선 17.6% > 국 16.9% > 밥 10.3%
#   - 육류·과일: 잔반 매우 적음
#
# [근거 5] RISS 학위논문 — 서울 광진구 중학생 300명 대상
#   - 성별 차이: 국·찌개 여학생 42.0% > 남학생 28.7%
#                채소류 남학생 36.7% > 여학생 18.0%
#   - 잔반 이유: ①맛 ②향·질감·식감 ③습관
#
# [근거 6] 환경부 / 한국환경공단 / 한국폐기물협회
#   - 「2023년 전국폐기물 발생 및 처리현황」 http://www.kwaste.or.kr
#   - 전국 음식물쓰레기 일일 발생량: 약 14,000톤
#   - 전체 쓰레기 중 음식물 비중: 28.7%
#   - 연간 온실가스 배출량: 885만 톤 CO₂e
#   - 2023년 총 폐기물: 17,619만 톤/년 (전년 대비 5.5% 감소), 재활용 86.0%
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── 1인당 제공량 및 잔반 기준 [근거 1] ──
WASTE_STANDARD = {
    '남자고등': {
        'kcal': 900,        # 1끼 에너지 기준 (kcal)
        'supply_g': 780,    # 밥+국+반찬5종 총 제공량 (g)
        'waste_avg_g': 220, # 평균 잔반량 (g)
    },
    '여자고등': {
        'kcal': 670,
        'supply_g': 650,
        'waste_avg_g': 270,
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

# ── 잔반 등급 기준 — 1인당 g [근거 1,2,3 종합] ──
WASTE_GRADE = {
    'A': (0,   150),   # 우수: 150g 미만
    'B': (150, 245),   # 양호: 혼합평균(245g) 이하
    'C': (245, 300),   # 주의: 표준 초과, 현장기준(300g) 이하
    'D': (300, 9999),  # 고잔반 경보: 300g 초과
}

# ── 메뉴 유형별 잔반 발생 순위 [근거 3,4,5] ──
# 잔반 발생 빈도 순위 기반 (복수 논문 종합)
# rank: 잔반 빈도 순위 (1=가장 많이 남김)
# category: 폐기물 유형 분류 [근거 2]
MENU_WASTE_RANK = {
    '채소·나물': {
        'rank': 1,
        'category': '순수잔반',
        'note': '편식 요인 최다 — 학교급별 무관',
    },
    '국·찌개류': {
        'rank': 2,
        'category': '순수잔반',
        'note': '국물 잔반 — 학교급 높을수록 감소 경향',
    },
    '생선류': {
        'rank': 3,
        'category': '순수잔반+일반(뼈·가시)',
        'note': '학교급 높을수록 증가 — 뼈·가시 전처리 발생',
    },
    '밥': {
        'rank': 4,
        'category': '순수잔반',
        'note': '상대적 저잔반',
    },
    '육류': {
        'rank': 5,
        'category': '순수잔반+일반(뼈)',
        'note': '잔반 매우 적음 — 뼈류 전처리 발생',
    },
    '과일': {
        'rank': 6,
        'category': '전처리(껍질·씨)',
        'note': '순수잔반 매우 적음 — 껍질·씨 전처리 잔여물 발생',
    },
}

# ── 구성별 제공량 기준 (남자 고등학생 900kcal 기준) [근거 1] ──
MEAL_COMPOSITION = {
    '밥':       {'supply_g': 220, 'kcal': 330},
    '국':       {'supply_g': 250, 'kcal':  50},
    '육류반찬': {'supply_g':  80, 'kcal': 130},
    '나물채소': {'supply_g':  60, 'kcal':  30},
    '김치류':   {'supply_g':  60, 'kcal':  20},
    '볶음류':   {'supply_g':  60, 'kcal':  80},
    '기타반찬': {'supply_g':  50, 'kcal':  50},
}

# ── 출처 표기 (PDF 푸터용) ──
WASTE_SOURCE = (
    "출처: 학교급식법 시행규칙 [별표 3](교육부, 2021) | "
    "경기도교육청 급식정책 기본계획(2023) | "
    "한국식품영양과학회(2019, JAKO201908662572910) | "
    "환경부 전국폐기물 발생현황(2023)"
)

# ── 연구 출처 상세 (PDF 보고서 본문 참조용) ──
WASTE_REFERENCES = [
    "[1] 학교급식법 시행규칙 [별표 3] (교육부, 2021.01.29 개정) — law.go.kr",
    "[2] 경기도교육청, 2023학년도 학교급식 정책추진 기본계획 (2023.02) — goe.go.kr",
    "[3] 경기도 학교급식 음식물쓰레기 발생 실태 연구, 한국식품영양과학회 (2019)",
    "[4] 고등학생 학교급식 만족도와 메뉴 선호도, 한국식품영양학회지 KCI",
    "[5] 중학생 편식·급식 식단기호도 조사, RISS 학위논문",
    "[6] 환경부/한국폐기물협회, 2023년 전국폐기물 발생 및 처리현황",
]


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
                            cust_type: str = '', fixed_fee: float = 0) -> bytes:
    """
    거래명세서 PDF 생성
    cust_type: '학교','기타1(면세사업장)'=면세, '기타'=월고정비용(세금없음), 그 외=부가세 10%
    fixed_fee: 기타 구분 월 고정비용 (0이면 수거량×단가 정산)
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
    # 기타/기타2 구분: 월 고정비용 → 수거량 합계 대신 고정비용 표기
    if fixed_fee > 0 and cust_type == '기타2(부가세포함)':
        # 기타2: 고정비용 + 부가세 10%
        _vat = round(fixed_fee * 0.1)
        _total_fee = round(fixed_fee + _vat)
        sum_data = [
            [P('월 고정비용 (계약금액)', size=10, color=colors.white),
             P(f"{fixed_fee:,.0f} 원", size=10, align=2, color=colors.white)],
            [P('부가세 (10%)', size=10),
             P(f"{_vat:,.0f} 원", size=10, align=2)],
            [P('합계금액', size=11, color=colors.white),
             P(f"{_total_fee:,.0f} 원", size=11, align=2, color=colors.white)],
        ]
    elif fixed_fee > 0 and cust_type == '기타':
        # 기타: 고정비용 단순 표기 (부가세 없음)
        sum_data = [
            [P('월 고정비용 (계약금액)', size=10, color=colors.white),
             P(f"{fixed_fee:,.0f} 원", size=10, align=2, color=colors.white)],
            [P('부가세', size=10),
             P('해당없음', size=10, align=2, color=colors.grey)],
            [P('합계금액', size=11, color=colors.white),
             P(f"{fixed_fee:,.0f} 원", size=11, align=2, color=colors.white)],
        ]
    elif cust_type in ('학교', '기타1(면세사업장)', ''):
        # 학교·기타1(면세사업장): 면세 — 부가세 없음
        sum_data = [
            [P('공급가액', size=10, color=colors.white),
             P(f"{total_amount:,.0f} 원", size=10, align=2, color=colors.white)],
            [P('부가세', size=10),
             P('면세', size=10, align=2, color=colors.HexColor('#1a73e8'))],
            [P('합계금액', size=11, color=colors.white),
             P(f"{total_amount:,.0f} 원", size=11, align=2, color=colors.white)],
        ]
    else:
        # 기업/관공서/일반업장: 부가세 10% 포함
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
                                 ai_recommendation: list = None,
                                 school_standard: dict = None) -> bytes:
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
    # 배식인원 통계
    servings_list = [int(r.get('servings', 0) or 0) for r in analysis_rows if int(r.get('servings', 0) or 0) > 0]
    avg_servings = round(sum(servings_list) / len(servings_list)) if servings_list else 0

    grade_counts = {}
    for r in analysis_rows:
        g = r.get('grade', '-')
        grade_counts[g] = grade_counts.get(g, 0) + 1
    main_grade = max(grade_counts, key=grade_counts.get) if grade_counts else '-'

    sum_data = [
        [P('평균 배식인원', size=8, align=1, color=colors.white),
         P('총 잔반량', size=8, align=1, color=colors.white),
         P('1인당 평균', size=8, align=1, color=colors.white),
         P('매칭 일수', size=8, align=1, color=colors.white),
         P('주요 등급', size=8, align=1, color=colors.white)],
        [P(f"{avg_servings:,}명", size=11, align=1),
         P(f"{total_waste:.1f} kg", size=11, align=1),
         P(f"{avg_pp:.1f} g", size=11, align=1),
         P(f"{matched_cnt} / {len(analysis_rows)}일", size=11, align=1),
         P(main_grade, size=14, align=1,
           color=GREEN if main_grade == 'A' else (ORANGE if main_grade == 'B' else RED))],
    ]
    sum_tbl = Table(sum_data, colWidths=[36*mm]*5)
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
    story.append(Spacer(1, 3*mm))

    # ── 등급 기준 안내 ──
    story.append(P("■ 등급 기준 (학교급식법 시행규칙 [별표 3])", size=9, color=colors.grey))
    story.append(Spacer(1, 1*mm))
    grade_info = [
        [P('등급', size=6, align=1, color=colors.white),
         P('A (우수)', size=6, align=1, color=colors.white),
         P('B (양호)', size=6, align=1, color=colors.white),
         P('C (주의)', size=6, align=1, color=colors.white),
         P('D (경보)', size=6, align=1, color=colors.white)],
        [P('1인당', size=6, align=1),
         P('~150g', size=6, align=1, color=GREEN),
         P('150~245g', size=6, align=1, color=ORANGE),
         P('245~300g', size=6, align=1, color=colors.HexColor('#ff8f00')),
         P('300g~', size=6, align=1, color=RED)],
    ]
    grade_tbl = Table(grade_info, colWidths=[20*mm, 35*mm, 35*mm, 35*mm, 35*mm])
    grade_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  colors.HexColor('#607d8b')),
        ('BACKGROUND', (0,1), (-1,1),  LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 3),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(grade_tbl)
    story.append(Spacer(1, 4*mm))

    # ── 공식기준: 영양·구성·조리량 (school_standard 전달 시) ──
    if school_standard:
        _nut = school_standard.get('nutrition', {})
        _comp = school_standard.get('composition', {})
        _proc = school_standard.get('procurement', {})
        _level = school_standard.get('level', '혼합평균')
        _label = _nut.get('label', _level)

        story.append(P(f"■ 공식기준: {_label} (학교급식법 시행규칙 [별표 3])", size=10, color=BLUE))
        story.append(Spacer(1, 2*mm))

        # 영양기준 요약
        nutr_data = [
            [P('항목', size=7, align=1, color=colors.white),
             P('1끼 에너지', size=7, align=1, color=colors.white),
             P('단백질', size=7, align=1, color=colors.white),
             P('칼슘', size=7, align=1, color=colors.white),
             P('철분', size=7, align=1, color=colors.white),
             P('비타민C', size=7, align=1, color=colors.white)],
            [P(_label, size=7, align=1),
             P(f"{_nut.get('energy_kcal', '-')} kcal", size=7, align=1),
             P(f"{_nut.get('protein_g', '-')} g", size=7, align=1),
             P(f"{_nut.get('calcium_mg', '-')} mg", size=7, align=1),
             P(f"{_nut.get('iron_mg', '-')} mg", size=7, align=1),
             P(f"{_nut.get('vitC_mg', '-')} mg", size=7, align=1)],
        ]
        nutr_tbl = Table(nutr_data, colWidths=[30*mm, 30*mm, 22*mm, 22*mm, 22*mm, 22*mm])
        nutr_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  colors.HexColor('#607d8b')),
            ('BACKGROUND', (0,1), (-1,1),  LGRAY),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(nutr_tbl)
        story.append(Spacer(1, 2*mm))

        # 구성별 제공량 테이블
        comp_header = [P(h, size=7, align=1, color=colors.white)
                       for h in ['구성', '제공량(g)', '칼로리(kcal)', '조리량(g)', '비고']]
        comp_data = [comp_header]
        _overhead_pct = _proc.get('total_overhead_pct', 20)
        for _cname in ['밥', '국', '주반찬', '부반찬', '김치']:
            _ci = _comp.get(_cname, {})
            _sg = _ci.get('supply_g', 0)
            _ck = _ci.get('kcal', 0)
            _cook = round(_sg * (1 + _overhead_pct / 100))
            comp_data.append([
                P(_cname, size=7, align=1),
                P(f"{_sg}g", size=7, align=2),
                P(f"{_ck}", size=7, align=2),
                P(f"{_cook}g", size=7, align=2),
                P(f"+{_overhead_pct}% 조리손실 포함", size=6, color=colors.grey),
            ])
        # 합계
        _tot_g = _comp.get('total_g', 0)
        _tot_k = _comp.get('total_kcal', 0)
        _tot_cook = round(_tot_g * (1 + _overhead_pct / 100))
        comp_data.append([
            P('합계', size=7, align=1),
            P(f"{_tot_g}g", size=7, align=2),
            P(f"{_tot_k}", size=7, align=2),
            P(f"{_tot_cook}g", size=7, align=2),
            P('', size=6),
        ])
        comp_tbl = Table(comp_data, colWidths=[22*mm, 24*mm, 24*mm, 24*mm, 54*mm])
        comp_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  colors.HexColor('#607d8b')),
            ('BACKGROUND', (0,-1),(-1,-1), LGRAY),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(comp_tbl)
        story.append(Spacer(1, 2*mm))

        # 공식기준 대비 잔반율 요약
        _std_supply = _tot_g if _tot_g > 0 else 670
        _waste_ratio = (avg_pp / _std_supply * 100) if _std_supply > 0 and avg_pp > 0 else 0
        _wr_color = GREEN if _waste_ratio < 20 else (ORANGE if _waste_ratio < 30 else RED)
        story.append(P(
            f"공식기준 대비 잔반율: {avg_pp:.0f}g / {_std_supply}g = {_waste_ratio:.1f}%",
            size=8, color=_wr_color))
        story.append(Spacer(1, 4*mm))

    # ── 일별 상세 ──
    story.append(P("■ 일별 식단 × 잔반량", size=11, color=BLUE))
    story.append(Spacer(1, 2*mm))

    header = ['날짜', '메뉴', '인원', '잔반(kg)', '1인당(g)', '등급', '특이사항']
    tdata = [[P(h, size=9, align=1, color=colors.white) for h in header]]

    for r in analysis_rows:
        try:
            menus = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menus = []
        menu_str = ", ".join(menus[:3])
        if len(menus) > 3:
            menu_str += f" 외 {len(menus)-3}"

        srv = int(r.get('servings', 0) or 0)
        wkg = float(r.get('waste_kg', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        grade = r.get('grade', '-')
        grade_color = GREEN if grade == 'A' else (ORANGE if grade == 'B' else (RED if grade == 'D' else colors.black))
        remark = r.get('remark', '')

        tdata.append([
            P(r.get('meal_date', '')[-5:], size=9, align=1),
            P(menu_str, size=8),
            P(f"{srv:,}" if srv > 0 else '-', size=9, align=2),
            P(f"{wkg:.1f}", size=9, align=2),
            P(f"{wpp:.1f}", size=9, align=2),
            P(grade, size=10, align=1, color=grade_color),
            P(remark, size=7),
        ])

    detail_tbl = Table(tdata, colWidths=[16*mm, 48*mm, 14*mm, 14*mm, 14*mm, 10*mm, 49*mm])
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

    # ── 분석 근거 출처 ──
    story.append(P("■ 분석 근거", size=8, color=colors.grey))
    story.append(Spacer(1, 1*mm))
    # school_standard가 전달되면 OFFICIAL_REFERENCES 사용 (더 포괄적)
    _refs_to_use = (school_standard or {}).get('references', WASTE_REFERENCES)
    for ref in _refs_to_use:
        story.append(P(ref, size=5, color=colors.grey))
    story.append(Spacer(1, 3*mm))
    story.append(P(
        "* 본 명세서는 ZERODA 폐기물데이터플랫폼에서 자동 생성되었습니다.",
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
# AI 월말명세서 PDF 생성 함수 (AI 분석 코멘트 + 비용절감 + 요일패턴 + 이상치)
# ─────────────────────────────────────────────────────────────────────────────

def generate_ai_meal_statement_pdf(
    site_name: str, year: int, month: int,
    analysis_rows: list,
    menu_ranking: dict = None,
    ai_recommendation: list = None,
    ai_comment: str = '',
    cost_savings: dict = None,
    weekday_pattern: dict = None,
    anomalies: list = None,
    combo_analysis: list = None,
    school_standard: dict = None,
) -> bytes:
    """
    AI 월말명세서 PDF — 스마트월말명세서와 차별화된 AI 전용 보고서
    추가 섹션:
      - AI 종합 코멘트 (Claude API 분석 결과)
      - 비용 절감 효과 (처리비용 기반)
      - 요일별 잔반 패턴 분석
      - 이상치 탐지 결과
      - 메뉴 조합 분석
      - AI 추천식단 (선택)
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

    def P(text, size=10, bold=False, align=0, color=colors.black, leading=None):
        ld = leading if leading else size * 1.4
        style = ParagraphStyle('s', fontName=font, fontSize=size,
                               alignment=align, textColor=color,
                               leading=ld)
        return Paragraph(str(text), style)

    BLUE   = colors.HexColor('#1a73e8')
    GREEN  = colors.HexColor('#34a853')
    ORANGE = colors.HexColor('#fbbc05')
    RED    = colors.HexColor('#ea4335')
    PURPLE = colors.HexColor('#7c4dff')
    LGRAY  = colors.HexColor('#f5f5f5')
    DGRAY  = colors.HexColor('#e0e0e0')

    story = []

    # ══════════════════════════════════════════
    # 1페이지: AI 월말명세서 헤더 + 요약 + AI 코멘트
    # ══════════════════════════════════════════
    story.append(P("AI 월말명세서", size=22, align=1, color=PURPLE))
    story.append(Spacer(1, 2*mm))
    story.append(P("ZERODA AI Analytics Report", size=9, align=1, color=colors.grey))
    story.append(Spacer(1, 2*mm))
    today = datetime.now().strftime('%Y년 %m월 %d일')
    story.append(P(f"발행일: {today}　　분석기간: {year}년 {month}월", size=9, align=2))
    story.append(HRFlowable(width="100%", thickness=2, color=PURPLE))
    story.append(Spacer(1, 4*mm))

    # ── 기관 정보 ──
    info_data = [
        [P('기관명', size=9, align=1, color=colors.white),
         P(site_name, size=10)],
        [P('분석기간', size=9, align=1, color=colors.white),
         P(f"{year}년 {month}월", size=10)],
        [P('보고서 유형', size=9, align=1, color=colors.white),
         P("AI 분석 보고서 (Claude API 기반)", size=10, color=PURPLE)],
    ]
    info_tbl = Table(info_data, colWidths=[35*mm, 145*mm])
    info_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (0,-1),  PURPLE),
        ('BACKGROUND', (1,0), (1,-1),  LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5*mm))

    # ── 월간 요약 KPI ──
    story.append(P("■ 월간 핵심 지표", size=11, color=PURPLE))
    story.append(Spacer(1, 2*mm))

    total_waste = sum(float(r.get('waste_kg', 0) or 0) for r in analysis_rows)
    valid_days = [r for r in analysis_rows if float(r.get('waste_per_person', 0) or 0) > 0]
    avg_pp = sum(float(r['waste_per_person']) for r in valid_days) / len(valid_days) if valid_days else 0
    matched_cnt = len([r for r in analysis_rows if float(r.get('waste_kg', 0) or 0) > 0])
    servings_list = [int(r.get('servings', 0) or 0) for r in analysis_rows if int(r.get('servings', 0) or 0) > 0]
    avg_servings = round(sum(servings_list) / len(servings_list)) if servings_list else 0

    grade_counts = {}
    for r in analysis_rows:
        g = r.get('grade', '-')
        grade_counts[g] = grade_counts.get(g, 0) + 1
    main_grade = max(grade_counts, key=grade_counts.get) if grade_counts else '-'

    sum_data = [
        [P('배식인원', size=8, align=1, color=colors.white),
         P('총 잔반량', size=8, align=1, color=colors.white),
         P('1인당 평균', size=8, align=1, color=colors.white),
         P('매칭 일수', size=8, align=1, color=colors.white),
         P('주요 등급', size=8, align=1, color=colors.white)],
        [P(f"{avg_servings:,}명", size=11, align=1),
         P(f"{total_waste:.1f} kg", size=11, align=1),
         P(f"{avg_pp:.1f} g", size=11, align=1),
         P(f"{matched_cnt}/{len(analysis_rows)}일", size=11, align=1),
         P(main_grade, size=14, align=1,
           color=GREEN if main_grade == 'A' else (ORANGE if main_grade == 'B' else RED))],
    ]
    sum_tbl = Table(sum_data, colWidths=[36*mm]*5)
    sum_tbl.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  PURPLE),
        ('BACKGROUND', (0,1), (-1,1),  LGRAY),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.grey),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, DGRAY),
        ('PADDING',    (0,0), (-1,-1), 5),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════
    # 공식기준 섹션 (school_standard 전달 시)
    # ══════════════════════════════════════════
    if school_standard:
        _nut = school_standard.get('nutrition', {})
        _comp = school_standard.get('composition', {})
        _proc = school_standard.get('procurement', {})
        _level = school_standard.get('level', '혼합평균')
        _label = _nut.get('label', _level)

        story.append(P(f"■ 공식기준: {_label} (학교급식법 시행규칙 [별표 3])", size=10, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        # 영양기준 + 구성별 제공량 (1개 테이블)
        std_header = [P(h, size=7, align=1, color=colors.white)
                      for h in ['구성', '제공량(g)', '칼로리', '조리량(g)', '비고']]
        std_data = [std_header]
        _overhead_pct = _proc.get('total_overhead_pct', 20)
        for _cname in ['밥', '국', '주반찬', '부반찬', '김치']:
            _ci = _comp.get(_cname, {})
            _sg = _ci.get('supply_g', 0)
            _ck = _ci.get('kcal', 0)
            _cook = round(_sg * (1 + _overhead_pct / 100))
            std_data.append([
                P(_cname, size=7, align=1),
                P(f"{_sg}g", size=7, align=2),
                P(f"{_ck}kcal", size=7, align=2),
                P(f"{_cook}g", size=7, align=2),
                P(f"+{_overhead_pct}%", size=6, color=colors.grey),
            ])
        _tot_g = _comp.get('total_g', 0)
        _tot_k = _comp.get('total_kcal', 0)
        _tot_cook = round(_tot_g * (1 + _overhead_pct / 100))
        std_data.append([
            P('합계', size=7, align=1),
            P(f"{_tot_g}g", size=7, align=2),
            P(f"{_tot_k}kcal", size=7, align=2),
            P(f"{_tot_cook}g", size=7, align=2),
            P(f"에너지 {_nut.get('energy_kcal', '-')}kcal", size=6, color=PURPLE),
        ])
        std_tbl = Table(std_data, colWidths=[22*mm, 24*mm, 24*mm, 24*mm, 54*mm])
        std_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  colors.HexColor('#607d8b')),
            ('BACKGROUND', (0,-1),(-1,-1), LGRAY),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(std_tbl)
        story.append(Spacer(1, 2*mm))

        # 공식기준 대비 잔반율
        _std_supply = _tot_g if _tot_g > 0 else 670
        _waste_ratio = (avg_pp / _std_supply * 100) if _std_supply > 0 and avg_pp > 0 else 0
        _wr_color = GREEN if _waste_ratio < 20 else (ORANGE if _waste_ratio < 30 else RED)
        story.append(P(
            f"공식기준 대비 잔반율: {avg_pp:.0f}g / {_std_supply}g = {_waste_ratio:.1f}% "
            f"| AI 분석과 공식기준을 결합하여 개선점을 도출합니다.",
            size=8, color=_wr_color))
        story.append(Spacer(1, 4*mm))

    # ══════════════════════════════════════════
    # AI 종합 코멘트 섹션 (스마트명세서에 없는 핵심 차별화)
    # ══════════════════════════════════════════
    if ai_comment:
        story.append(P("■ AI 종합 분석 코멘트", size=11, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        # AI 코멘트를 줄 단위로 파싱하여 테이블로
        comment_lines = [line.strip() for line in ai_comment.split('\n') if line.strip()]
        comment_text = '\n'.join(comment_lines[:20])  # 최대 20줄

        ai_box_data = [[P(comment_text, size=8, leading=12)]]
        ai_box = Table(ai_box_data, colWidths=[170*mm])
        ai_box.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f3e5f5')),
            ('BOX',        (0,0), (-1,-1), 1.0, PURPLE),
            ('PADDING',    (0,0), (-1,-1), 8),
            ('VALIGN',     (0,0), (-1,-1), 'TOP'),
        ]))
        story.append(ai_box)
        story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════
    # 비용 절감 효과 섹션
    # ══════════════════════════════════════════
    if cost_savings:
        story.append(P("■ 비용 절감 효과", size=11, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        unit_price = cost_savings.get('unit_price', 0)
        current_cost = cost_savings.get('current_cost', 0)
        target_cost = cost_savings.get('target_cost', 0)
        save_amount = cost_savings.get('save_amount', 0)
        save_pct = cost_savings.get('save_pct', 0)
        prev_cost = cost_savings.get('prev_cost', 0)
        mom_save = cost_savings.get('mom_save', 0)

        cost_data = [
            [P('항목', size=8, align=1, color=colors.white),
             P('금액/수치', size=8, align=1, color=colors.white),
             P('비고', size=8, align=1, color=colors.white)],
            [P('음식물 처리 단가', size=8, align=1),
             P(f"{unit_price:,.0f} 원/kg", size=8, align=2),
             P('customer_info 기준', size=7)],
            [P('이번 달 처리비용', size=8, align=1),
             P(f"{current_cost:,.0f} 원", size=8, align=2),
             P(f'총 잔반 {total_waste:.1f}kg 기준', size=7)],
        ]

        if prev_cost > 0:
            cost_data.append([
                P('전월 처리비용', size=8, align=1),
                P(f"{prev_cost:,.0f} 원", size=8, align=2),
                P('', size=7),
            ])
            mom_color = GREEN if mom_save > 0 else RED
            cost_data.append([
                P('전월 대비 절감', size=8, align=1, color=mom_color),
                P(f"{mom_save:,.0f} 원", size=9, align=2, color=mom_color),
                P(f"{'절감' if mom_save > 0 else '증가'}", size=7, color=mom_color),
            ])

        if target_cost > 0 and save_amount > 0:
            cost_data.append([
                P('10% 감소 시 절감액', size=8, align=1, color=GREEN),
                P(f"{save_amount:,.0f} 원/월", size=9, align=2, color=GREEN),
                P(f'연간 약 {save_amount * 12:,.0f}원 절감 가능', size=7, color=GREEN),
            ])

        cost_tbl = Table(cost_data, colWidths=[45*mm, 45*mm, 80*mm])
        cost_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  PURPLE),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 4),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        for i in range(1, len(cost_data)):
            bg = LGRAY if i % 2 == 0 else colors.white
            cost_tbl.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), bg)]))
        story.append(cost_tbl)
        story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════
    # 요일별 잔반 패턴 섹션
    # ══════════════════════════════════════════
    if weekday_pattern and weekday_pattern.get('data'):
        story.append(P("■ 요일별 잔반 패턴", size=11, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        wd_header = [P(h, size=8, align=1, color=colors.white)
                     for h in ['요일', '평균 잔반(kg)', '평균 1인당(g)', '수거 일수', '주요 메뉴 키워드']]
        wd_data = [wd_header]

        for wd in weekday_pattern['data']:
            wd_data.append([
                P(wd.get('weekday_name', ''), size=8, align=1),
                P(f"{wd.get('avg_kg', 0):.1f}", size=8, align=2),
                P(f"{wd.get('avg_pp', 0):.1f}", size=8, align=2),
                P(str(wd.get('count', 0)), size=8, align=2),
                P(wd.get('top_menus', '-'), size=7),
            ])

        wd_tbl = Table(wd_data, colWidths=[18*mm, 28*mm, 28*mm, 22*mm, 74*mm])
        wd_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  PURPLE),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        for i in range(1, len(wd_data)):
            bg = LGRAY if i % 2 == 0 else colors.white
            wd_tbl.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), bg)]))
        story.append(wd_tbl)

        if weekday_pattern.get('insight'):
            story.append(Spacer(1, 2*mm))
            story.append(P(weekday_pattern['insight'], size=8, color=PURPLE))
        story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════
    # 이상치 탐지 섹션
    # ══════════════════════════════════════════
    if anomalies:
        story.append(P("■ 이상치 탐지 (평소 대비 급증/급감)", size=11, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        an_header = [P(h, size=8, align=1, color=colors.white)
                     for h in ['날짜', '잔반량(kg)', 'Z-Score', '유형', '해당일 메뉴']]
        an_data = [an_header]

        for a in anomalies[:8]:  # 최대 8건
            z = a.get('z_score', 0)
            atype = '급증' if z > 0 else '급감'
            acolor = RED if z > 0 else GREEN
            an_data.append([
                P(str(a.get('date', '')), size=8, align=1),
                P(f"{a.get('waste_kg', 0):.1f}", size=8, align=2),
                P(f"{z:.2f}", size=8, align=2, color=acolor),
                P(atype, size=8, align=1, color=acolor),
                P(a.get('menus', '-'), size=7),
            ])

        an_tbl = Table(an_data, colWidths=[22*mm, 24*mm, 20*mm, 16*mm, 88*mm])
        an_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  RED),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        for i in range(1, len(an_data)):
            an_tbl.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), colors.HexColor('#fff8e1'))]))
        story.append(an_tbl)
        story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════
    # 메뉴 조합 분석 섹션
    # ══════════════════════════════════════════
    if combo_analysis:
        story.append(P("■ 메뉴 조합 효과 분석", size=11, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        cb_header = [P(h, size=8, align=1, color=colors.white)
                     for h in ['메뉴 조합', '평균 잔반(g/인)', '등장 횟수', '평가']]
        cb_data = [cb_header]

        for c in combo_analysis[:10]:
            avg_w = c.get('avg_waste', 0)
            rating = '우수' if avg_w < 150 else ('양호' if avg_w < 245 else ('주의' if avg_w < 300 else '경보'))
            r_color = GREEN if avg_w < 150 else (BLUE if avg_w < 245 else (ORANGE if avg_w < 300 else RED))
            cb_data.append([
                P(c.get('combo', ''), size=7),
                P(f"{avg_w:.1f}", size=8, align=2),
                P(str(c.get('count', 0)), size=8, align=2),
                P(rating, size=8, align=1, color=r_color),
            ])

        cb_tbl = Table(cb_data, colWidths=[90*mm, 30*mm, 22*mm, 28*mm])
        cb_tbl.setStyle(TableStyle([
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  PURPLE),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        for i in range(1, len(cb_data)):
            bg = LGRAY if i % 2 == 0 else colors.white
            cb_tbl.setStyle(TableStyle([('BACKGROUND', (0,i), (-1,i), bg)]))
        story.append(cb_tbl)
        story.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════
    # 일별 상세 테이블 (기존과 동일)
    # ══════════════════════════════════════════
    story.append(P("■ 일별 식단 × 잔반량", size=11, color=PURPLE))
    story.append(Spacer(1, 2*mm))

    header = ['날짜', '메뉴', '인원', '잔반(kg)', '1인당(g)', '등급', '특이사항']
    tdata = [[P(h, size=9, align=1, color=colors.white) for h in header]]

    for r in analysis_rows:
        try:
            menus = json.loads(r.get('menu_items', '[]'))
        except (json.JSONDecodeError, TypeError):
            menus = []
        menu_str = ", ".join(menus[:3])
        if len(menus) > 3:
            menu_str += f" 외 {len(menus)-3}"

        srv = int(r.get('servings', 0) or 0)
        wkg = float(r.get('waste_kg', 0) or 0)
        wpp = float(r.get('waste_per_person', 0) or 0)
        grade = r.get('grade', '-')
        grade_color = GREEN if grade == 'A' else (ORANGE if grade == 'B' else (RED if grade == 'D' else colors.black))
        remark = r.get('remark', '')

        tdata.append([
            P(r.get('meal_date', '')[-5:], size=9, align=1),
            P(menu_str, size=8),
            P(f"{srv:,}" if srv > 0 else '-', size=9, align=2),
            P(f"{wkg:.1f}", size=9, align=2),
            P(f"{wpp:.1f}", size=9, align=2),
            P(grade, size=10, align=1, color=grade_color),
            P(remark, size=7),
        ])

    detail_tbl = Table(tdata, colWidths=[16*mm, 48*mm, 14*mm, 14*mm, 14*mm, 10*mm, 49*mm])
    detail_style = [
        ('FONTNAME',   (0,0), (-1,-1), font),
        ('BACKGROUND', (0,0), (-1,0),  PURPLE),
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

    # ── 메뉴별 순위 ──
    if menu_ranking:
        story.append(P("■ 메뉴별 잔반 순위", size=11, color=PURPLE))
        story.append(Spacer(1, 2*mm))

        good = menu_ranking.get('good', [])[:5]
        bad = menu_ranking.get('bad', [])[:5]

        rank_header = [P('순위', size=7, align=1, color=colors.white),
                       P('잔반 적은 메뉴', size=7, align=1, color=colors.white),
                       P('평균(g)', size=7, align=1, color=colors.white),
                       P('', size=7),
                       P('잔반 많은 메뉴', size=7, align=1, color=colors.white),
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
            ('BACKGROUND', (0,0), (-1,0),  PURPLE),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID',  (0,0), (-1,-1), 0.2, DGRAY),
            ('PADDING',    (0,0), (-1,-1), 3),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(rank_tbl)

    story.append(Spacer(1, 5*mm))

    # ── 분석 근거 출처 ──
    story.append(P("■ 분석 근거 (공식기준 + AI 분석)", size=8, color=colors.grey))
    story.append(Spacer(1, 1*mm))
    _ai_refs = (school_standard or {}).get('references', WASTE_REFERENCES)
    for ref in _ai_refs:
        story.append(P(ref, size=5, color=colors.grey))
    story.append(P("+ ZERODA AI Analytics (Claude API 기반 잔반 패턴 분석, 비용절감 시뮬레이션, 이상치 탐지)", size=5, color=PURPLE))
    story.append(Spacer(1, 3*mm))
    story.append(P(
        "* 본 보고서는 공식기준(학교급식법) + AI 분석을 결합하여 ZERODA에서 자동 생성되었습니다.",
        size=7, color=PURPLE))

    # ══════════════════════════════════════════
    # 추가 페이지: AI 추천식단 (선택)
    # ══════════════════════════════════════════
    if ai_recommendation:
        story.append(PageBreak())
        story.append(P("AI 추천식단", size=18, align=1, color=PURPLE))
        story.append(Spacer(1, 2*mm))
        story.append(P("잔반 데이터 기반 다음달 최적 메뉴 (ZERODA AI)", size=9, align=1, color=colors.grey))
        story.append(HRFlowable(width="100%", thickness=1, color=PURPLE))
        story.append(Spacer(1, 4*mm))

        ai_header = ['날짜', '요일', '추천 메뉴', 'kcal', '선정 이유']
        ai_data = [[P(h, size=7, align=1, color=colors.white) for h in ai_header]]

        for m in ai_recommendation:
            menu_items = m.get('menu_items', [])
            menu_str = " / ".join(menu_items)
            ai_data.append([
                P(str(m.get('date', ''))[-5:], size=7, align=1),
                P(m.get('weekday', ''), size=7, align=1),
                P(menu_str, size=6),
                P(str(int(m.get('calories', 0))), size=7, align=2),
                P(m.get('reason', ''), size=5),
            ])

        ai_tbl = Table(ai_data, colWidths=[18*mm, 10*mm, 80*mm, 14*mm, 48*mm])
        ai_style = [
            ('FONTNAME',   (0,0), (-1,-1), font),
            ('BACKGROUND', (0,0), (-1,0),  PURPLE),
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
        story.append(P("* AI 추천식단은 과거 잔반 데이터와 영양균형을 기반으로 Claude AI가 생성하였습니다.",
                       size=8, color=colors.grey))
        story.append(P("* ZERODA AI Analytics Premium", size=8, color=PURPLE))

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
