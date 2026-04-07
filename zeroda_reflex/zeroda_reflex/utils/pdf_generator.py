# zeroda_reflex/zeroda_reflex/utils/pdf_generator.py
"""
급식담당자 월말명세서 PDF 생성 — 독립형 ReportLab 구현
services/pdf_generator.py 의존성 완전 제거.

한글 폰트 탐색 순서:
  1. zeroda_reflex/zeroda_reflex/assets/fonts/NanumGothic.ttf (프로젝트 내부)
  2. C:/Windows/Fonts/malgun.ttf (Windows 맑은 고딕)
  3. /usr/share/fonts/truetype/nanum/NanumGothic.ttf (Linux)
폰트를 전혀 찾지 못하면 FileNotFoundError 발생 (조용한 실패 금지).

AI 코멘트 섹션:
  - Paragraph + ParagraphStyle(wordWrap='CJK') 사용 → 한글 자동 줄바꿈
  - 위치: 기관명/기간 테이블 다음, 분석 데이터 테이블 이전
"""
from __future__ import annotations

import json
import logging
import pathlib
from datetime import datetime
from io import BytesIO

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  잔반 분석 기준 상수 (학교급식법 시행규칙 [별표 3])
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WASTE_GRADE: dict[str, tuple[int, int]] = {
    "A": (0, 150),    # 우수: 150g 미만
    "B": (150, 245),  # 양호: 혼합평균(245g) 이하
    "C": (245, 300),  # 주의: 표준 초과
    "D": (300, 9999), # 경보: 300g 초과
}

WASTE_REFERENCES: list[str] = [
    "[1] 학교급식법 시행규칙 [별표 3] (교육부, 2021.01.29 개정) — law.go.kr",
    "[2] 경기도교육청, 2023학년도 학교급식 정책추진 기본계획 (2023.02) — goe.go.kr",
    "[3] 경기도 학교급식 음식물쓰레기 발생 실태, 한국식품영양과학회 (2019, JAKO201908662572910)",
    "[4] 고등학생 학교급식 만족도와 메뉴 선호도, 한국식품영양학회지 KCI",
    "[5] 환경부/한국폐기물협회, 2023년 전국폐기물 발생 및 처리현황",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  한글 폰트 등록
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_FONT_CACHE: str | None = None  # 등록된 폰트명 캐시


def _register_korean_font() -> str:
    """
    한글 TTF 폰트를 ReportLab에 등록하고 폰트명을 반환.
    탐색 순서:
      1) zeroda_reflex/zeroda_reflex/assets/fonts/NanumGothic.ttf
      2) C:/Windows/Fonts/malgun.ttf  (Windows 맑은 고딕)
      3) /usr/share/fonts/truetype/nanum/NanumGothic.ttf  (Linux)
    모두 없으면 FileNotFoundError 발생.
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    _assets_dir = pathlib.Path(__file__).resolve().parent.parent / "assets" / "fonts"

    candidates: list[tuple[pathlib.Path, str]] = [
        (_assets_dir / "NanumGothic.ttf", "NanumGothic"),
        (pathlib.Path("C:/Windows/Fonts/malgun.ttf"), "MalgunGothic"),
        (pathlib.Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"), "NanumGothic"),
    ]

    for path, name in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("KoreanFont", str(path)))
                logger.info(f"한글 폰트 등록 완료: {path}")
                return "KoreanFont"
            except Exception as e:
                logger.warning(f"폰트 등록 실패 ({path}): {e}")
                continue

    raise FileNotFoundError(
        "한글 폰트 파일을 찾을 수 없어 PDF를 생성할 수 없습니다.\n"
        "아래 경로 중 하나에 폰트 파일을 배치하세요:\n"
        f"  1) {_assets_dir / 'NanumGothic.ttf'}  ← 권장 (프로젝트 내부)\n"
        "  2) C:/Windows/Fonts/malgun.ttf  (Windows 자동 인식)\n"
        "  3) /usr/share/fonts/truetype/nanum/NanumGothic.ttf  (Linux)\n\n"
        "NanumGothic.ttf 다운로드: https://hangeul.naver.com/font\n"
        "(나눔고딕 폰트 설치 후 폰트 파일을 위 경로에 복사하세요)"
    )


def _get_font() -> str:
    """폰트명 반환 (최초 1회만 등록, 이후 캐시 사용)"""
    global _FONT_CACHE
    if _FONT_CACHE is None:
        _FONT_CACHE = _register_korean_font()
    return _FONT_CACHE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  내부 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _make_para_factory(font: str):
    """
    주어진 폰트명으로 Paragraph 생성 팩토리 반환.
    wrap=True 시 wordWrap='CJK' 활성화 (한글 자동 줄바꿈).
    """
    from reportlab.lib import colors as _colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    def P(
        text: str,
        size: int = 10,
        align: int = 0,
        color=_colors.black,
        leading: float | None = None,
        wrap: bool = False,
    ) -> Paragraph:
        style = ParagraphStyle(
            "s",
            fontName=font,
            fontSize=size,
            alignment=align,
            textColor=color,
            leading=leading or size * 1.4,
            wordWrap="CJK" if wrap else "LTR",
        )
        # 줄바꿈 문자를 ReportLab 태그로 변환
        safe_text = str(text).replace("&", "&amp;").replace("\n", "<br/>")
        return Paragraph(safe_text, style)

    return P


def _parse_year_month(year_month: str) -> tuple[int, int]:
    try:
        return int(year_month[:4]), int(year_month[5:7])
    except (ValueError, IndexError):
        now = datetime.now()
        return now.year, now.month


def _grade_color(grade: str, GREEN, ORANGE, RED, default):
    """등급 → 색상 매핑"""
    return {"A": GREEN, "B": ORANGE, "D": RED}.get(grade, default)


def _summary_stats(analysis_rows: list[dict]) -> dict:
    """월간 요약 통계 계산"""
    total_waste = sum(float(r.get("waste_kg", 0) or 0) for r in analysis_rows)
    valid_days = [r for r in analysis_rows if float(r.get("waste_per_person", 0) or 0) > 0]
    avg_pp = (
        sum(float(r["waste_per_person"]) for r in valid_days) / len(valid_days)
        if valid_days else 0
    )
    matched_cnt = len([r for r in analysis_rows if float(r.get("waste_kg", 0) or 0) > 0])
    srv_list = [int(r.get("servings", 0) or 0) for r in analysis_rows
                if int(r.get("servings", 0) or 0) > 0]
    avg_srv = round(sum(srv_list) / len(srv_list)) if srv_list else 0
    grade_counts: dict[str, int] = {}
    for r in analysis_rows:
        g = str(r.get("grade", "-"))
        grade_counts[g] = grade_counts.get(g, 0) + 1
    main_grade = max(grade_counts, key=grade_counts.get) if grade_counts else "-"
    return {
        "total_waste": total_waste,
        "avg_pp": avg_pp,
        "matched_cnt": matched_cnt,
        "avg_srv": avg_srv,
        "main_grade": main_grade,
        "total_days": len(analysis_rows),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  공통 섹션 빌더
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_ai_comment_section(
    story: list, ai_comment: str, P, font: str,
    accent_color, bg_color, border_color,
):
    """
    AI 코멘트 박스 섹션 빌드.
    Paragraph + wordWrap='CJK' 로 한글 자동 줄바꿈.
    위치: 기관 정보 테이블 다음, 분석 데이터 테이블 이전.
    """
    from reportlab.lib import colors as _c
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    story.append(P("■ AI 잔반 감축 추천 식단", size=12, color=accent_color))
    story.append(Spacer(1, 2 * mm))

    # wordWrap='CJK' — 한글/CJK 문자 기준으로 단어를 분리하여 자동 줄바꿈
    ai_style = ParagraphStyle(
        "ai_cjk",
        fontName=font,
        fontSize=9,
        leading=14,
        wordWrap="CJK",
        textColor=_c.HexColor("#1a237e"),
    )
    safe_text = ai_comment.replace("&", "&amp;").replace("\n", "<br/>")
    ai_para = Paragraph(safe_text, ai_style)

    ai_box = Table([[ai_para]], colWidths=[170 * mm])
    ai_box.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX",        (0, 0), (-1, -1), 1.5, border_color),
        ("PADDING",    (0, 0), (-1, -1), 10),
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ai_box)
    story.append(Spacer(1, 6 * mm))


def _build_summary_section(story: list, stats: dict, P, BLUE, GREEN, ORANGE, RED, LGRAY, DGRAY, font: str):
    """월간 요약 KPI 테이블 빌드"""
    from reportlab.lib import colors as _c
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer, Table, TableStyle

    story.append(P("■ 월간 요약", size=11, color=BLUE))
    story.append(Spacer(1, 2 * mm))

    main_grade = stats["main_grade"]
    g_color = GREEN if main_grade == "A" else (ORANGE if main_grade == "B" else RED)

    sum_data = [
        [P("평균 배식인원", size=8, align=1, color=_c.white),
         P("총 잔반량",     size=8, align=1, color=_c.white),
         P("1인당 평균",    size=8, align=1, color=_c.white),
         P("매칭 일수",     size=8, align=1, color=_c.white),
         P("주요 등급",     size=8, align=1, color=_c.white)],
        [P(f"{stats['avg_srv']:,}명",                      size=11, align=1),
         P(f"{stats['total_waste']:.1f} kg",               size=11, align=1),
         P(f"{stats['avg_pp']:.1f} g",                     size=11, align=1),
         P(f"{stats['matched_cnt']}/{stats['total_days']}일", size=11, align=1),
         P(main_grade, size=14, align=1, color=g_color)],
    ]
    sum_tbl = Table(sum_data, colWidths=[36 * mm] * 5)
    sum_tbl.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (-1, 0),  BLUE),
        ("BACKGROUND", (0, 1), (-1, 1),  LGRAY),
        ("BOX",        (0, 0), (-1, -1), 0.8, _c.grey),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, DGRAY),
        ("PADDING",    (0, 0), (-1, -1), 5),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sum_tbl)
    story.append(Spacer(1, 3 * mm))


def _build_grade_legend(story: list, P, font: str, GREEN, ORANGE, RED, LGRAY, DGRAY):
    """등급 기준 범례 테이블 빌드"""
    from reportlab.lib import colors as _c
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer, Table, TableStyle

    story.append(P("■ 등급 기준 (학교급식법 시행규칙 [별표 3])", size=9, color=_c.grey))
    story.append(Spacer(1, 1 * mm))
    grade_info = [
        [P("등급",   size=6, align=1, color=_c.white),
         P("A (우수)", size=6, align=1, color=_c.white),
         P("B (양호)", size=6, align=1, color=_c.white),
         P("C (주의)", size=6, align=1, color=_c.white),
         P("D (경보)", size=6, align=1, color=_c.white)],
        [P("1인당", size=6, align=1),
         P("~150g",    size=6, align=1, color=GREEN),
         P("150~245g", size=6, align=1, color=ORANGE),
         P("245~300g", size=6, align=1, color=_c.HexColor("#ff8f00")),
         P("300g~",    size=6, align=1, color=RED)],
    ]
    grade_tbl = Table(grade_info, colWidths=[20 * mm, 35 * mm, 35 * mm, 35 * mm, 35 * mm])
    grade_tbl.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (-1, 0),  _c.HexColor("#607d8b")),
        ("BACKGROUND", (0, 1), (-1, 1),  LGRAY),
        ("BOX",        (0, 0), (-1, -1), 0.5, _c.grey),
        ("INNERGRID",  (0, 0), (-1, -1), 0.2, DGRAY),
        ("PADDING",    (0, 0), (-1, -1), 3),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(grade_tbl)
    story.append(Spacer(1, 4 * mm))


def _build_daily_detail(
    story: list, analysis_rows: list[dict], P, font: str,
    header_color, GREEN, ORANGE, RED, LGRAY, DGRAY,
):
    """일별 식단 × 잔반량 테이블 빌드 (메뉴 셀에 CJK 줄바꿈 적용)"""
    from reportlab.lib import colors as _c
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer, Table, TableStyle

    story.append(P("■ 일별 식단 × 잔반량", size=11, color=header_color))
    story.append(Spacer(1, 2 * mm))

    header = ["날짜", "메뉴", "인원", "잔반(kg)", "1인당(g)", "등급"]
    tdata = [[P(h, size=9, align=1, color=_c.white) for h in header]]

    for r in analysis_rows:
        try:
            menus: list = json.loads(r.get("menu_items", "[]"))
        except (json.JSONDecodeError, TypeError):
            menus = []
        menu_str = ", ".join(str(m) for m in menus[:3])
        if len(menus) > 3:
            menu_str += f" 외 {len(menus) - 3}"

        srv   = int(r.get("servings", 0) or 0)
        wkg   = float(r.get("waste_kg", 0) or 0)
        wpp   = float(r.get("waste_per_person", 0) or 0)
        grade = str(r.get("grade", "-"))
        gc    = _grade_color(grade, GREEN, ORANGE, RED, _c.black)

        tdata.append([
            P(str(r.get("meal_date", ""))[-5:], size=9, align=1),
            P(menu_str, size=8, wrap=True),            # CJK 자동 줄바꿈
            P(f"{srv:,}" if srv > 0 else "-", size=9, align=2),
            P(f"{wkg:.1f}",  size=9, align=2),
            P(f"{wpp:.1f}",  size=9, align=2),
            P(grade, size=10, align=1, color=gc),
        ])

    detail_tbl = Table(
        tdata,
        colWidths=[16 * mm, 64 * mm, 14 * mm, 18 * mm, 18 * mm, 10 * mm],
    )
    detail_style = [
        ("FONTNAME",  (0, 0), (-1, -1), font),
        ("BACKGROUND",(0, 0), (-1,  0), header_color),
        ("BOX",       (0, 0), (-1, -1), 0.8, _c.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, DGRAY),
        ("PADDING",   (0, 0), (-1, -1), 3),
        ("VALIGN",    (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(tdata)):
        bg = LGRAY if i % 2 == 0 else _c.white
        detail_style.append(("BACKGROUND", (0, i), (-1, i), bg))
    detail_tbl.setStyle(TableStyle(detail_style))
    story.append(detail_tbl)
    story.append(Spacer(1, 5 * mm))


def _build_menu_ranking(
    story: list, menu_ranking: dict, P, font: str,
    header_color, GREEN, RED, DGRAY,
):
    """메뉴별 잔반 순위 테이블 빌드"""
    from reportlab.lib import colors as _c
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer, Table, TableStyle

    story.append(P("■ 메뉴별 잔반 순위", size=11, color=header_color))
    story.append(Spacer(1, 2 * mm))

    # "good"/"bad" 키와 "best"/"worst" 키 모두 지원
    good = (menu_ranking.get("good") or menu_ranking.get("best", []))[:5]
    bad  = (menu_ranking.get("bad")  or menu_ranking.get("worst", []))[:5]

    rank_header = [
        P("순위", size=7, align=1, color=_c.white),
        P("잔반 적은 메뉴", size=7, align=1, color=_c.white),
        P("평균(g)", size=7, align=1, color=_c.white),
        P("", size=7),
        P("잔반 많은 메뉴", size=7, align=1, color=_c.white),
        P("평균(g)", size=7, align=1, color=_c.white),
    ]
    rank_data = [rank_header]
    for i in range(5):
        g = good[i] if i < len(good) else {}
        b = bad[i]  if i < len(bad)  else {}
        rank_data.append([
            P(str(i + 1), size=7, align=1),
            P(g.get("menu", "-"), size=7),
            P(f"{g.get('avg_waste', 0):.1f}" if g else "-", size=7, align=2, color=GREEN),
            P("", size=7),
            P(b.get("menu", "-"), size=7),
            P(f"{b.get('avg_waste', 0):.1f}" if b else "-", size=7, align=2, color=RED),
        ])

    rank_tbl = Table(rank_data, colWidths=[12 * mm, 50 * mm, 18 * mm, 5 * mm, 50 * mm, 18 * mm])
    rank_tbl.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (-1,  0), header_color),
        ("BOX",        (0, 0), (-1, -1), 0.5, _c.grey),
        ("INNERGRID",  (0, 0), (-1, -1), 0.2, DGRAY),
        ("PADDING",    (0, 0), (-1, -1), 3),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(rank_tbl)


def _build_footer(story: list, P):
    """분석 근거 + 푸터 빌드"""
    from reportlab.lib import colors as _c
    from reportlab.lib.units import mm
    from reportlab.platypus import Spacer

    story.append(Spacer(1, 5 * mm))
    story.append(P("■ 분석 근거", size=8, color=_c.grey))
    story.append(Spacer(1, 1 * mm))
    for ref in WASTE_REFERENCES:
        story.append(P(ref, size=5, color=_c.grey))
    story.append(Spacer(1, 3 * mm))
    story.append(P(
        "* 본 명세서는 ZERODA 폐기물데이터플랫폼에서 자동 생성되었습니다.",
        size=7, color=_c.grey,
    ))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  공개 함수 1: 스마트 월말명세서 PDF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_meal_statement_pdf(
    site_name: str,
    year_month: str,
    analysis_rows: list[dict],
    ai_comment: str = "",
    menu_ranking: dict | None = None,
    servings: int = 0,
    **kwargs,
) -> bytes:
    """
    스마트 월말명세서 PDF 생성 → bytes 반환.

    Parameters
    ----------
    site_name       급식소(학교) 이름
    year_month      "YYYY-MM" 형식
    analysis_rows   meal_analyze_waste() 결과
    ai_comment      AI 추천 텍스트 (있으면 기관정보 바로 아래, 분석표 이전에 배치)
    menu_ranking    {"best": [...], "worst": [...]} 또는 {"good": ..., "bad": ...}
    servings        기본 배식인원 (analysis_rows에 없을 때 사용)
    """
    from reportlab.lib import colors as _c
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, SimpleDocTemplate, Spacer, Table, TableStyle

    font = _get_font()
    P = _make_para_factory(font)
    year, month = _parse_year_month(year_month)

    BLUE   = _c.HexColor("#1a73e8")
    GREEN  = _c.HexColor("#34a853")
    ORANGE = _c.HexColor("#fbbc05")
    RED    = _c.HexColor("#ea4335")
    LGRAY  = _c.HexColor("#f5f5f5")
    DGRAY  = _c.HexColor("#e0e0e0")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    story: list = []

    # ── 제목 ──
    story.append(P("스마트 월말명세서", size=20, align=1, color=BLUE))
    story.append(Spacer(1, 3 * mm))
    today = datetime.now().strftime("%Y년 %m월 %d일")
    story.append(P(f"발행일: {today}　　분석기간: {year}년 {month}월", size=9, align=2))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE))
    story.append(Spacer(1, 4 * mm))

    # ── 기관 정보 ──
    info_data = [
        [P("기관명",   size=9, align=1, color=_c.white), P(site_name,          size=10)],
        [P("분석기간", size=9, align=1, color=_c.white), P(f"{year}년 {month}월", size=10)],
    ]
    info_tbl = Table(info_data, colWidths=[35 * mm, 145 * mm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (0,  -1), BLUE),
        ("BACKGROUND", (1, 0), (1,  -1), LGRAY),
        ("BOX",        (0, 0), (-1, -1), 0.8, _c.grey),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, DGRAY),
        ("PADDING",    (0, 0), (-1, -1), 5),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── AI 코멘트 (기관정보 다음 / 분석표 이전) ──
    if ai_comment:
        _build_ai_comment_section(
            story, ai_comment, P, font,
            accent_color=BLUE,
            bg_color=_c.HexColor("#e8eaf6"),
            border_color=BLUE,
        )

    # ── 월간 요약 ──
    stats = _summary_stats(analysis_rows)
    _build_summary_section(story, stats, P, BLUE, GREEN, ORANGE, RED, LGRAY, DGRAY, font)

    # ── 등급 기준 ──
    _build_grade_legend(story, P, font, GREEN, ORANGE, RED, LGRAY, DGRAY)

    # ── 일별 상세 ──
    _build_daily_detail(story, analysis_rows, P, font, BLUE, GREEN, ORANGE, RED, LGRAY, DGRAY)

    # ── 메뉴별 순위 ──
    if menu_ranking:
        _build_menu_ranking(story, menu_ranking, P, font, BLUE, GREEN, RED, DGRAY)

    _build_footer(story, P)

    doc.build(story)
    return buffer.getvalue()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  공개 함수 2: AI 월말명세서 PDF
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def generate_ai_meal_statement_pdf(
    site_name: str,
    year_month: str,
    analysis_rows: list[dict],
    ai_comment: str = "",
    servings: int = 0,
    price_food: int = 0,
    menu_ranking: dict | None = None,
    cost_savings: dict | None = None,
    weekday_pattern: list | None = None,
    **kwargs,
) -> bytes:
    """
    AI 월말명세서 PDF 생성 → bytes 반환.

    Parameters
    ----------
    site_name       급식소(학교) 이름
    year_month      "YYYY-MM" 형식
    analysis_rows   meal_analyze_waste() 결과
    ai_comment      AI 추천 텍스트 — Paragraph + wordWrap='CJK' 로 자동 줄바꿈
                    위치: 기관명/기간 테이블 다음, 월간 KPI 테이블 이전 (★ 최상단)
    servings        기본 배식인원
    price_food      음식물 처리 단가 (원/kg)
    menu_ranking    메뉴 순위 dict
    cost_savings    비용 절감 효과 dict
    weekday_pattern 요일별 잔반 패턴 list
    """
    from reportlab.lib import colors as _c
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, SimpleDocTemplate, Spacer, Table, TableStyle

    font = _get_font()
    P = _make_para_factory(font)
    year, month = _parse_year_month(year_month)

    PURPLE = _c.HexColor("#7c4dff")
    GREEN  = _c.HexColor("#34a853")
    ORANGE = _c.HexColor("#fbbc05")
    RED    = _c.HexColor("#ea4335")
    LGRAY  = _c.HexColor("#f5f5f5")
    DGRAY  = _c.HexColor("#e0e0e0")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    story: list = []

    # ── 제목 ──
    story.append(P("AI 월말명세서", size=22, align=1, color=PURPLE))
    story.append(Spacer(1, 2 * mm))
    story.append(P("ZERODA AI Analytics Report", size=9, align=1, color=_c.grey))
    story.append(Spacer(1, 2 * mm))
    today = datetime.now().strftime("%Y년 %m월 %d일")
    story.append(P(f"발행일: {today}　　분석기간: {year}년 {month}월", size=9, align=2))
    story.append(HRFlowable(width="100%", thickness=2, color=PURPLE))
    story.append(Spacer(1, 4 * mm))

    # ── 기관 정보 ──
    info_data = [
        [P("기관명",     size=9, align=1, color=_c.white), P(site_name, size=10)],
        [P("분석기간",   size=9, align=1, color=_c.white), P(f"{year}년 {month}월", size=10)],
        [P("보고서 유형", size=9, align=1, color=_c.white),
         P("AI 분석 보고서 (Claude API 기반)", size=10, color=PURPLE)],
    ]
    info_tbl = Table(info_data, colWidths=[35 * mm, 145 * mm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME",   (0, 0), (-1, -1), font),
        ("BACKGROUND", (0, 0), (0,  -1), PURPLE),
        ("BACKGROUND", (1, 0), (1,  -1), LGRAY),
        ("BOX",        (0, 0), (-1, -1), 0.8, _c.grey),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, DGRAY),
        ("PADDING",    (0, 0), (-1, -1), 5),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════
    # ★ AI 코멘트 — 최상단 배치 (기관정보 다음 / 월간KPI 이전)
    #   Paragraph + wordWrap='CJK' 로 한글 자동 줄바꿈
    # ══════════════════════════════════════════════════════════
    if ai_comment:
        _build_ai_comment_section(
            story, ai_comment, P, font,
            accent_color=PURPLE,
            bg_color=_c.HexColor("#f3e5f5"),
            border_color=PURPLE,
        )

    # ── 월간 KPI ──
    stats = _summary_stats(analysis_rows)
    _build_summary_section(story, stats, P, PURPLE, GREEN, ORANGE, RED, LGRAY, DGRAY, font)

    # ── 비용 절감 효과 ──
    if cost_savings:
        story.append(P("■ 비용 절감 효과", size=11, color=PURPLE))
        story.append(Spacer(1, 2 * mm))
        unit_p  = float(cost_savings.get("unit_price",   0) or 0)
        curr_c  = float(cost_savings.get("current_cost", 0) or 0)
        save_10 = float(cost_savings.get("save_10pct",   0) or 0)
        cost_data = [
            [P("항목", size=8, align=1, color=_c.white),
             P("금액/수치", size=8, align=1, color=_c.white),
             P("비고", size=8, align=1, color=_c.white)],
            [P("음식물 처리 단가", size=8),
             P(f"{unit_p:,.0f} 원/kg", size=8, align=2),
             P("customer_info 기준", size=7)],
            [P("이번 달 처리비용", size=8),
             P(f"{curr_c:,.0f} 원", size=8, align=2),
             P(f"총 잔반 {stats['total_waste']:.1f}kg", size=7)],
            [P("10% 절감 시 목표", size=8),
             P(f"{save_10:,.0f} 원/월", size=8, align=2, color=GREEN),
             P("절감 목표", size=7)],
        ]
        cost_tbl = Table(cost_data, colWidths=[55 * mm, 60 * mm, 55 * mm])
        cost_tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, 0), (-1, -1), font),
            ("BACKGROUND", (0, 0), (-1,  0), PURPLE),
            ("BACKGROUND", (0, 1), (-1, -1), LGRAY),
            ("BOX",        (0, 0), (-1, -1), 0.5, _c.grey),
            ("INNERGRID",  (0, 0), (-1, -1), 0.2, DGRAY),
            ("PADDING",    (0, 0), (-1, -1), 4),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(cost_tbl)
        story.append(Spacer(1, 5 * mm))

    # ── 요일별 잔반 패턴 ──
    if weekday_pattern:
        story.append(P("■ 요일별 잔반 패턴", size=11, color=PURPLE))
        story.append(Spacer(1, 2 * mm))
        wd_header = [
            P("요일",       size=8, align=1, color=_c.white),
            P("평균 잔반(kg)", size=8, align=1, color=_c.white),
            P("1인당(g)",   size=8, align=1, color=_c.white),
            P("횟수",       size=8, align=1, color=_c.white),
        ]
        wd_data = [wd_header]
        for wd in weekday_pattern:
            avg_kg = float(wd.get("avg_kg", 0) or 0)
            avg_pp = float(wd.get("avg_pp", 0) or 0)
            c = GREEN if avg_pp < 150 else (ORANGE if avg_pp < 245 else RED)
            wd_data.append([
                P(str(wd.get("weekday", "-")), size=8, align=1),
                P(f"{avg_kg:.1f}", size=8, align=2),
                P(f"{avg_pp:.1f}", size=8, align=2, color=c),
                P(str(wd.get("count", 0)), size=8, align=2),
            ])
        wd_tbl = Table(wd_data, colWidths=[30 * mm, 55 * mm, 55 * mm, 30 * mm])
        wd_tbl.setStyle(TableStyle([
            ("FONTNAME",   (0, 0), (-1, -1), font),
            ("BACKGROUND", (0, 0), (-1,  0), PURPLE),
            ("BACKGROUND", (0, 1), (-1, -1), LGRAY),
            ("BOX",        (0, 0), (-1, -1), 0.5, _c.grey),
            ("INNERGRID",  (0, 0), (-1, -1), 0.2, DGRAY),
            ("PADDING",    (0, 0), (-1, -1), 4),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(wd_tbl)
        story.append(Spacer(1, 5 * mm))

    # ── 일별 상세 ──
    _build_daily_detail(story, analysis_rows, P, font, PURPLE, GREEN, ORANGE, RED, LGRAY, DGRAY)

    # ── 메뉴별 순위 ──
    if menu_ranking:
        _build_menu_ranking(story, menu_ranking, P, font, PURPLE, GREEN, RED, DGRAY)

    _build_footer(story, P)

    doc.build(story)
    return buffer.getvalue()
