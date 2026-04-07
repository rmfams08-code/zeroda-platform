# zeroda_reflex/pages/meal_manager.py
# 급식담당자 대시보드 — 6메뉴
import reflex as rx
from zeroda_reflex.state.meal_state import MealState, MEAL_TABS
from zeroda_reflex.state.auth_state import get_year_options, MONTH_OPTIONS
# ── 공통 컴포넌트 import (Phase 0-A 모듈화) ──
from zeroda_reflex.components.shared import (
    kpi_card_compact as _kpi,          # 급식은 컴팩트형 KPI (_kpi 별칭 유지)
    section_header as _header,         # 급식은 _header 별칭 사용
    card_box_light as _card,           # 급식은 _card 별칭 사용
    col_header as _col,                # rx.table 컬럼 헤더
    table_cell as _c,                  # rx.table 데이터 셀
)

# ══════════════════════════════════════════
#  공통 UI 헬퍼 — shared.py에서 import (Phase 0-A)
# ══════════════════════════════════════════


GRADE_COLORS = {"A": "green", "B": "blue", "C": "orange", "D": "red", "-": "gray"}

_WEEKDAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

# 수정1: 영양정보 키 목록 (NUTRITION_KEYS 하드코딩)
_NUTRITION_KEYS = [
    "에너지(kcal)", "탄수화물(g)", "단백질(g)", "지방(g)",
    "비타민A(μg RE)", "티아민(mg)", "리보플라빈(mg)", "비타민C(mg)", "칼슘(mg)",
]


def _grade_badge(grade) -> rx.Component:
    """수정12: 등급별 색상 badge"""
    return rx.match(
        grade,
        ("A", rx.badge(grade, color_scheme="green", size="1")),
        ("B", rx.badge(grade, color_scheme="blue", size="1")),
        ("C", rx.badge(grade, color_scheme="yellow", size="1")),
        ("D", rx.badge(grade, color_scheme="red", size="1")),
        rx.badge(grade, color_scheme="gray", size="1"),
    )


# ══════════════════════════════════════════
#  수정1: 달력형 식단 보기 (helper)
# ══════════════════════════════════════════

def _calendar_cell(cell: dict) -> rx.Component:
    """달력 한 칸 렌더링 (flat list용)"""
    return rx.box(
        rx.vstack(
            rx.text(
                cell["day"],
                font_size="12px",
                font_weight="600",
                color=rx.cond(cell["day"] == "", "transparent", "#1e293b"),
            ),
            rx.cond(
                cell["day"] != "",
                rx.vstack(
                    rx.cond(
                        cell["has_menu"] == "1",
                        rx.text("✅", font_size="10px"),
                        rx.text("❌", font_size="10px", color="#ef4444"),
                    ),
                    rx.cond(
                        cell["has_collect"] == "1",
                        rx.text("🟢", font_size="10px"),
                        rx.text("⚪", font_size="10px"),
                    ),
                    spacing="0",
                ),
                rx.text(""),
            ),
            spacing="0",
            align="center",
        ),
        width="calc(100% / 7)",
        min_height="58px",
        border="1px solid #e2e8f0",
        border_radius="6px",
        bg=rx.cond(cell["has_menu"] == "1", "#f0fdf4", "#ffffff"),
        padding="3px",
        box_sizing="border-box",
    )


def _calendar_view() -> rx.Component:
    return _card(
        rx.vstack(
            rx.hstack(
                _header("calendar", "달력형 식단 보기"),
                rx.button(
                    rx.icon("refresh_cw", size=13), "새로고침",
                    size="1", variant="ghost",
                    on_click=MealState.load_meal_calendar,
                ),
                width="100%", align="center",
            ),
            rx.text(
                "✅ 식단등록  ❌ 미등록  🟢 수거완료  ⚪ 수거없음",
                font_size="11px", color="#64748b",
            ),
            # 요일 헤더 (7칸 고정)
            rx.hstack(
                *[rx.text(h, font_size="11px", font_weight="700", color="#64748b",
                           flex="1", text_align="center")
                  for h in _WEEKDAY_LABELS],
                spacing="0", width="100%",
            ),
            # 달력 셀 — flex-wrap으로 7열 그리드 구성
            rx.cond(
                MealState.has_calendar,
                rx.box(
                    rx.foreach(MealState.calendar_cells, _calendar_cell),
                    display="flex",
                    flex_wrap="wrap",
                    width="100%",
                    gap="2px",
                ),
                rx.text("달력 데이터 없음", font_size="12px", color="#94a3b8"),
            ),
            spacing="2", width="100%",
        )
    )


# ══════════════════════════════════════════
#  상단바 + 네비게이션
# ══════════════════════════════════════════

def _topbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("utensils", size=20, color="#f59e0b"),
                rx.text("ZERODA", font_size="18px", font_weight="800", color="#1e293b"),
                rx.text("급식담당", font_size="14px", color="#64748b"),
                spacing="2", align="center"),
            rx.spacer(),
            rx.text(MealState.site_name, font_size="13px", font_weight="600", color="#3b82f6"),
            rx.hstack(
                rx.icon("user", size=14, color="#64748b"),
                rx.text(MealState.user_name, font_size="13px", color="#64748b"),
                spacing="1", align="center"),
            rx.button(rx.icon("log_out", size=14), "로그아웃",
                       variant="outline", size="1", on_click=MealState.logout),
            spacing="3", align="center", width="100%"),
        bg="white", padding="12px 24px",
        border_bottom="1px solid #e2e8f0", width="100%")


def _nav() -> rx.Component:
    def _btn(label: str) -> rx.Component:
        return rx.button(
            label,
            on_click=MealState.set_active_tab(label),
            variant=rx.cond(MealState.active_tab == label, "solid", "ghost"),
            color_scheme=rx.cond(MealState.active_tab == label, "blue", "gray"),
            size="2")
    return rx.hstack(
        *[_btn(t) for t in MEAL_TABS],
        spacing="2", padding="8px 24px",
        bg="white", border_bottom="1px solid #e2e8f0",
        flex_wrap="wrap", width="100%")


def _ym_filter() -> rx.Component:
    return rx.hstack(
        rx.select(get_year_options(),
                   value=MealState.selected_year,
                   on_change=MealState.set_selected_year,
                   size="2", width="90px"),
        rx.select(["01", "02", "03", "04", "05", "06",
                    "07", "08", "09", "10", "11", "12"],
                   value=MealState.selected_month,
                   on_change=MealState.set_selected_month,
                   size="2", width="80px"),
        spacing="2")


# ══════════════════════════════════════════
#  탭1: 식단등록
# ══════════════════════════════════════════

def _menu_tab() -> rx.Component:
    return rx.vstack(
        _header("calendar", "식단 등록"),
        _ym_filter(),
        # 수정1: 달력형 식단 보기
        _calendar_view(),
        # 메시지
        rx.cond(
            MealState.has_msg,
            rx.callout(
                MealState.msg,
                icon=rx.cond(MealState.msg_ok, "circle_check", "circle_alert"),
                color_scheme=rx.cond(MealState.msg_ok, "green", "red"),
                size="1"),
        ),
        # 등록 폼
        _card(
            rx.vstack(
                rx.text("식단 입력", font_size="14px", font_weight="600"),
                rx.hstack(
                    rx.vstack(
                        rx.text("날짜 (YYYY-MM-DD)", font_size="12px", color="#64748b"),
                        rx.input(value=MealState.mf_date, on_change=MealState.set_mf_date,
                                  placeholder="2026-04-07", size="2"),
                        spacing="1", flex="1"),
                    rx.vstack(
                        rx.text("칼로리(kcal)", font_size="12px", color="#64748b"),
                        rx.input(value=MealState.mf_calories, on_change=MealState.set_mf_calories,
                                  placeholder="700", size="2"),
                        spacing="1", width="100px"),
                    rx.vstack(
                        rx.text("배식인원", font_size="12px", color="#64748b"),
                        rx.input(value=MealState.mf_servings, on_change=MealState.set_mf_servings,
                                  placeholder="300", size="2"),
                        spacing="1", width="100px"),
                    spacing="3", width="100%"),
                rx.vstack(
                    rx.text("메뉴 (쉼표 구분)", font_size="12px", color="#64748b"),
                    rx.input(value=MealState.mf_menu, on_change=MealState.set_mf_menu,
                              placeholder="잡곡밥, 된장찌개, 돈까스, 배추김치, 우유", size="2",
                              width="100%"),
                    spacing="1", width="100%"),
                # 수정1: 영양정보 입력 (선택)
                rx.accordion.root(
                    rx.accordion.item(
                        rx.accordion.header(
                            rx.accordion.trigger(
                                rx.text("영양정보 입력 (선택)", font_size="12px"),
                                rx.accordion.icon(),
                            ),
                        ),
                        rx.accordion.content(
                            rx.grid(
                                rx.vstack(rx.text(_NUTRITION_KEYS[0], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[0])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[1], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[1])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[2], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[2])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[3], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[3])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[4], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[4])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[5], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[5])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[6], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[6])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[7], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[7])), spacing="1"),
                                rx.vstack(rx.text(_NUTRITION_KEYS[8], font_size="11px", color="#64748b"),
                                          rx.input(placeholder="0", size="1", on_change=MealState.set_mf_nut(_NUTRITION_KEYS[8])), spacing="1"),
                                columns="3", spacing="2", width="100%",
                            ),
                        ),
                        value="nutrition",
                    ),
                    collapsible=True, type="single", variant="outline", width="100%",
                ),
                rx.button(rx.icon("save", size=14), "저장",
                           color_scheme="blue", size="2", on_click=MealState.save_menu),
                spacing="3", width="100%")),
        # ── CSV/Excel 일괄 업로드 (Phase 4) ──
        _card(
            rx.vstack(
                rx.text("식단 일괄 업로드", font_size="14px", font_weight="600"),
                rx.text(
                    "CSV 또는 Excel 파일로 식단을 한번에 등록합니다. "
                    "필수 컬럼: 날짜, 메뉴 | 선택 컬럼: 칼로리, 배식인원",
                    font_size="12px", color="#64748b",
                ),
                rx.upload(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("upload", size=20, color="#64748b"),
                            rx.text("파일을 여기에 끌어놓거나 클릭하세요",
                                    font_size="13px", color="#64748b"),
                            align="center", spacing="2",
                        ),
                        rx.text("(.csv, .xlsx 지원)", font_size="11px", color="#94a3b8"),
                        align="center", spacing="1", padding="20px",
                    ),
                    id="meal_upload",
                    accept={".csv": ["text/csv"],
                            ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]},
                    max_files=1,
                    border="2px dashed #cbd5e1",
                    border_radius="8px",
                    cursor="pointer",
                    _hover={"border_color": "#3b82f6", "bg": "#f0f9ff"},
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("upload", size=14), "업로드",
                        size="2", color_scheme="blue",
                        on_click=MealState.handle_meal_upload(
                            rx.upload_files(upload_id="meal_upload")
                        ),
                    ),
                    rx.cond(
                        MealState.upload_progress > 0,
                        rx.hstack(
                            rx.progress(value=MealState.upload_progress, width="120px"),
                            rx.text(MealState.upload_progress.to(str) + "%",
                                    font_size="12px", color="#64748b"),
                            spacing="2", align="center",
                        ),
                    ),
                    spacing="3", align="center",
                ),
                spacing="3", width="100%",
            ),
        ),
        # ── 수정2: NEIS 엑셀 업로드 ──
        _card(
            rx.vstack(
                rx.text("📂 NEIS 엑셀 업로드", font_size="14px", font_weight="600"),
                rx.text(
                    "NEIS에서 내려받은 급식식단 엑셀 파일을 업로드하면 자동 파싱됩니다. "
                    "헤더에 '급식일자', '요리명' 컬럼이 있어야 합니다.",
                    font_size="12px", color="#64748b",
                ),
                rx.upload(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("file_spreadsheet", size=20, color="#64748b"),
                            rx.text("NEIS 엑셀 파일을 여기에 끌어놓거나 클릭하세요",
                                    font_size="13px", color="#64748b"),
                            align="center", spacing="2",
                        ),
                        rx.text("(.xlsx 지원)", font_size="11px", color="#94a3b8"),
                        align="center", spacing="1", padding="20px",
                    ),
                    id="neis_upload",
                    accept={".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]},
                    max_files=1,
                    border="2px dashed #bfdbfe",
                    border_radius="8px",
                    cursor="pointer",
                    _hover={"border_color": "#3b82f6", "bg": "#eff6ff"},
                    width="100%",
                ),
                rx.button(
                    rx.icon("upload", size=14), "NEIS 업로드",
                    size="2", color_scheme="indigo",
                    on_click=MealState.handle_neis_upload(
                        rx.upload_files(upload_id="neis_upload")
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        # 등록된 식단 목록
        _card(
            rx.vstack(
                rx.hstack(
                    rx.text("등록된 식단", font_size="14px", font_weight="600"),
                    rx.badge(MealState.menu_count, color_scheme="blue", size="1"),
                    spacing="2", align="center"),
                rx.cond(
                    MealState.has_menus,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col("날짜"), _col("메뉴"), _col("칼로리"),
                                _col("배식인원"), _col("관리"))),
                        rx.table.body(
                            rx.foreach(
                                MealState.menu_rows,
                                lambda r: rx.table.row(
                                    _c(r["meal_date"]),
                                    _c(r["menu_items"], max_width="300px", overflow="hidden"),
                                    _c(r["calories"]),
                                    _c(r["servings"]),
                                    rx.table.cell(
                                        rx.button("삭제", size="1", variant="outline",
                                                   color_scheme="red",
                                                   on_click=MealState.delete_menu(r["meal_date"])))))),
                        width="100%"),
                    rx.text("등록된 식단이 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center")),
                spacing="3", width="100%")),
        spacing="4", width="100%")


# ══════════════════════════════════════════
#  탭2: 스마트잔반분석
# ══════════════════════════════════════════

def _standard_accordion() -> rx.Component:
    """수정4: 학교급식법 공식기준 안내 accordion"""
    return rx.accordion.root(
        rx.accordion.item(
            rx.accordion.header(
                rx.accordion.trigger(
                    rx.hstack(
                        rx.icon("book_open", size=14, color="#3b82f6"),
                        rx.text("📋 학교급식법 공식기준 안내",
                                font_size="13px", font_weight="600", color="#1e293b"),
                        rx.accordion.icon(),
                        spacing="2", align="center",
                    ),
                    padding="10px 12px",
                ),
            ),
            rx.accordion.content(
                rx.vstack(
                    rx.hstack(
                        # 등급 기준 테이블
                        rx.vstack(
                            rx.text("잔반 등급 기준 (1인당)", font_size="12px",
                                    font_weight="700", color="#374151"),
                            rx.table.root(
                                rx.table.header(
                                    rx.table.row(
                                        _col("등급"), _col("범위"), _col("판정"))),
                                rx.table.body(
                                    rx.foreach(
                                        MealState.waste_grade_table,
                                        lambda r: rx.table.row(
                                            rx.table.cell(
                                                rx.badge(r["grade"], color_scheme=r["color"], size="1")),
                                            _c(r["range"]),
                                            _c(r["label"]),
                                        )
                                    )
                                ),
                                size="1",
                            ),
                            spacing="2",
                        ),
                        # 학교급별 표준 제공량
                        rx.cond(
                            MealState.has_standard,
                            rx.vstack(
                                rx.text("학교급별 표준 1끼 제공량(g)",
                                        font_size="12px", font_weight="700", color="#374151"),
                                rx.table.root(
                                    rx.table.header(
                                        rx.table.row(
                                            _col("항목"), _col("제공량(g)"))),
                                    rx.table.body(
                                        rx.table.row(_c("밥"), _c(MealState.school_standard.get("밥", ""))),
                                        rx.table.row(_c("국"), _c(MealState.school_standard.get("국", ""))),
                                        rx.table.row(_c("반찬"), _c(MealState.school_standard.get("반찬", ""))),
                                        rx.table.row(_c("김치"), _c(MealState.school_standard.get("김치", ""))),
                                        rx.table.row(_c("우유"), _c(MealState.school_standard.get("우유", ""))),
                                        rx.table.row(
                                            rx.table.cell(rx.text("합계", font_weight="700")),
                                            rx.table.cell(rx.text(
                                                MealState.school_standard.get("합계", ""),
                                                font_weight="700", color="#3b82f6"))),
                                    ),
                                    size="1",
                                ),
                                spacing="2",
                            ),
                        ),
                        spacing="6", align="start", flex_wrap="wrap",
                    ),
                    # 기준 대비 달성률 KPI
                    rx.cond(
                        MealState.has_analysis,
                        rx.hstack(
                            rx.vstack(
                                rx.text("기준 대비 잔반율", font_size="11px", color="#64748b"),
                                rx.text(
                                    MealState.standard_compliance + "%",
                                    font_size="20px", font_weight="800", color="#ef4444",
                                ),
                                rx.text("(기준 245g 대비)", font_size="10px", color="#94a3b8"),
                                spacing="0", align="center",
                            ),
                            padding="8px 16px",
                            bg="#fef2f2", border_radius="8px",
                        ),
                    ),
                    spacing="3", padding="8px 12px 12px", width="100%",
                ),
            ),
            value="standard",
        ),
        collapsible=True,
        type="single",
        variant="outline",
        width="100%",
    )


def _trend_subtabs() -> rx.Component:
    """수정3: 잔반 트렌드 서브탭 (요일별/월별/계절별)"""
    return _card(
        rx.vstack(
            _header("trending_up", "잔반 트렌드 분석"),
            rx.tabs.root(
                rx.tabs.list(
                    rx.tabs.trigger("요일별", value="weekday"),
                    rx.tabs.trigger("월별", value="monthly"),
                    rx.tabs.trigger("계절별", value="seasonal"),
                    size="1",
                ),
                # 요일별 탭
                rx.tabs.content(
                    rx.vstack(
                        rx.cond(
                            MealState.has_weekday,
                            rx.recharts.bar_chart(
                                rx.recharts.bar(
                                    data_key="avg_num", fill="#ef4444", name="평균 잔반(kg)"),
                                rx.recharts.bar(
                                    data_key="pp_num", fill="#f59e0b", name="1인당(g)"),
                                rx.recharts.x_axis(data_key="weekday", font_size=12),
                                rx.recharts.y_axis(font_size=11),
                                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                rx.recharts.legend(),
                                rx.recharts.tooltip(),
                                data=MealState.weekday_pattern,
                                width="100%", height=260,
                            ),
                            rx.text("요일별 데이터 없음", font_size="12px", color="#94a3b8"),
                        ),
                        spacing="2", width="100%",
                    ),
                    value="weekday",
                ),
                # 월별 탭
                rx.tabs.content(
                    rx.vstack(
                        rx.cond(
                            MealState.has_monthly_trend,
                            rx.recharts.line_chart(
                                rx.recharts.line(
                                    data_key="avg_num", stroke="#3b82f6",
                                    name="1인당 평균(g)", type_="monotone", dot=True),
                                rx.recharts.x_axis(data_key="month", font_size=11),
                                rx.recharts.y_axis(font_size=11),
                                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                rx.recharts.legend(),
                                rx.recharts.tooltip(),
                                data=MealState.monthly_trend,
                                width="100%", height=260,
                            ),
                            rx.text("월별 데이터 없음", font_size="12px", color="#94a3b8"),
                        ),
                        spacing="2", width="100%",
                    ),
                    value="monthly",
                ),
                # 계절별 탭
                rx.tabs.content(
                    rx.vstack(
                        rx.cond(
                            MealState.has_seasonal,
                            rx.recharts.bar_chart(
                                rx.recharts.bar(
                                    data_key="avg_num", fill="#8b5cf6", name="1인당 평균(g)"),
                                rx.recharts.x_axis(data_key="season", font_size=12),
                                rx.recharts.y_axis(font_size=11),
                                rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                                rx.recharts.legend(),
                                rx.recharts.tooltip(),
                                data=MealState.seasonal_compare,
                                width="100%", height=260,
                            ),
                            rx.text("계절별 데이터 없음", font_size="12px", color="#94a3b8"),
                        ),
                        spacing="2", width="100%",
                    ),
                    value="seasonal",
                ),
                default_value="weekday",
                width="100%",
            ),
            spacing="3", width="100%",
        )
    )


def _smart_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + Excel/PDF 다운로드 ──
        rx.hstack(
            _header("bar_chart_3", "스마트 잔반 분석"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=MealState.download_smart_pdf,
            ),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=MealState.download_meal_excel,
            ),
            width="100%", align="center",
        ),
        # 수정4: 학교급식법 공식기준 안내
        _standard_accordion(),
        _ym_filter(),
        # KPI
        rx.cond(
            MealState.has_analysis,
            rx.vstack(
                rx.hstack(
                    _kpi("평균 배식인원", MealState.analysis_summary.get("avg_servings", "0"), "명", "users", "#3b82f6"),
                    _kpi("총 잔반량", MealState.analysis_summary.get("total_waste", "0"), "kg", "trash_2", "#ef4444"),
                    _kpi("1인당 평균", MealState.analysis_summary.get("avg_waste_pp", "0"), "g", "user", "#f59e0b"),
                    _kpi("매칭일수", MealState.analysis_summary.get("matched_days", "0"), "일", "calendar_check", "#22c55e"),
                    spacing="3", width="100%", flex_wrap="wrap"),
                # 등급 분포
                rx.hstack(
                    _kpi("A등급(우수)", MealState.analysis_summary.get("grade_a", "0"), "일", "circle_check", "#22c55e"),
                    _kpi("B등급(양호)", MealState.analysis_summary.get("grade_b", "0"), "일", "circle", "#3b82f6"),
                    _kpi("C등급(주의)", MealState.analysis_summary.get("grade_c", "0"), "일", "triangle_alert", "#f59e0b"),
                    _kpi("D등급(경보)", MealState.analysis_summary.get("grade_d", "0"), "일", "circle_alert", "#ef4444"),
                    spacing="3", width="100%", flex_wrap="wrap"),
                spacing="3", width="100%"),
        ),
        # 일별 상세
        _card(
            rx.vstack(
                _header("clipboard_list", "일별 잔반 분석"),
                rx.cond(
                    MealState.has_analysis,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col("날짜"), _col("메뉴"), _col("배식"),
                                _col("잔반(kg)"), _col("1인당(g)"), _col("잔반율(%)"), _col("등급"))),
                        rx.table.body(
                            rx.foreach(
                                MealState.analysis_rows,
                                lambda r: rx.table.row(
                                    _c(r["meal_date"]),
                                    _c(r["menu_items"], max_width="200px", overflow="hidden"),
                                    _c(r["servings"]),
                                    _c(r["waste_kg"], font_weight="600"),
                                    _c(r["waste_per_person"], font_weight="600"),
                                    _c(r["waste_rate"]),
                                    rx.table.cell(_grade_badge(r["grade"]))))),
                        width="100%"),
                    rx.text("분석 데이터가 없습니다. 식단 등록 후 수거 데이터가 필요합니다.",
                             font_size="13px", color="#94a3b8", padding="20px", text_align="center")),
                # ── 일별 잔반 추이 차트 (Phase 9) ──
                rx.cond(
                    MealState.has_analysis,
                    rx.recharts.composed_chart(
                        rx.recharts.area(
                            data_key="waste_num",
                            fill="#fecaca",
                            stroke="#ef4444",
                            name="잔반(kg)",
                            type_="monotone",
                        ),
                        rx.recharts.line(
                            data_key="pp_num",
                            stroke="#f59e0b",
                            name="1인당(g)",
                            type_="monotone",
                            dot=False,
                        ),
                        rx.recharts.x_axis(data_key="meal_date", font_size=10, angle=-30),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.legend(),
                        rx.recharts.tooltip(),
                        data=MealState.analysis_rows,
                        width="100%",
                        height=280,
                    ),
                ),
                spacing="3", width="100%")),
        # 수정7: 이상치 탐지 callout
        rx.cond(
            MealState.has_anomaly,
            _card(
                rx.vstack(
                    _header("triangle_alert", "이상치 탐지 (Z-Score > 2)"),
                    rx.foreach(
                        MealState.anomaly_dates,
                        lambda a: rx.callout(
                            a["date"] + ": 잔반 " + a["type"] + " (" + a["waste_per_person"] + "g/인, Z=" + a["z_score"] + ")",
                            icon="triangle_alert",
                            color_scheme=rx.cond(a["type"] == "급증", "red", "blue"),
                            size="1",
                        ),
                    ),
                    spacing="1", width="100%",
                )
            ),
        ),
        # 수정3: 등급 분포 파이차트
        rx.cond(
            MealState.has_grade_distribution,
            _card(
                rx.vstack(
                    _header("pie_chart", "등급 분포"),
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=MealState.grade_distribution,
                            data_key="value",
                            name_key="name",
                            cx="50%", cy="50%",
                            outer_radius=80,
                            label=True,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.tooltip(),
                        width="100%", height=220,
                    ),
                    spacing="2", width="100%",
                )
            ),
        ),
        # 수정4: 일별 1인당 잔반 라인차트
        rx.cond(
            MealState.has_daily_chart,
            _card(
                rx.vstack(
                    _header("trending_up", "일별 1인당 잔반 추이"),
                    rx.recharts.line_chart(
                        rx.recharts.line(
                            data_key="waste_per_person",
                            stroke="#ef4444", name="1인당(g)",
                            type_="monotone", dot=True,
                        ),
                        rx.recharts.x_axis(data_key="date", font_size=10, angle=-30),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.tooltip(),
                        data=MealState.daily_waste_chart,
                        width="100%", height=260,
                    ),
                    spacing="2", width="100%",
                )
            ),
        ),
        # 요일별 패턴
        _card(
            rx.vstack(
                _header("calendar_days", "요일별 패턴"),
                rx.cond(
                    MealState.has_weekday,
                    rx.vstack(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    _col("요일"), _col("평균 잔반(kg)"), _col("1인당(g)"), _col("데이터수"))),
                            rx.table.body(
                                rx.foreach(
                                    MealState.weekday_pattern,
                                    lambda r: rx.table.row(
                                        _c(r["weekday"], font_weight="600"),
                                        _c(r["avg_kg"]),
                                        _c(r["avg_pp"]),
                                        _c(r["count"])))),
                            width="100%"),
                        # ── 요일별 잔반 차트 (Phase 9) ──
                        rx.recharts.bar_chart(
                            rx.recharts.bar(
                                data_key="avg_num",
                                fill="#ef4444",
                                name="평균 잔반(kg)",
                            ),
                            rx.recharts.bar(
                                data_key="pp_num",
                                fill="#f59e0b",
                                name="1인당(g)",
                            ),
                            rx.recharts.x_axis(data_key="weekday", font_size=12),
                            rx.recharts.y_axis(font_size=11),
                            rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                            rx.recharts.legend(),
                            rx.recharts.tooltip(),
                            data=MealState.weekday_pattern,
                            width="100%",
                            height=250,
                        ),
                        spacing="3", width="100%",
                    ),
                    rx.text("요일별 데이터가 없습니다.", font_size="13px", color="#94a3b8")),
                spacing="3", width="100%")),
        # 수정3: 잔반 트렌드 서브탭
        _trend_subtabs(),
        # 메뉴 랭킹
        rx.hstack(
            _card(
                rx.vstack(
                    _header("thumbs_up", "추천 유지 메뉴 TOP 10"),
                    rx.cond(
                        MealState.has_best,
                        rx.table.root(
                            rx.table.header(rx.table.row(_col("메뉴"), _col("1인당(g)"), _col("횟수"))),
                            rx.table.body(
                                rx.foreach(MealState.best_menus,
                                            lambda r: rx.table.row(
                                                _c(r["menu"], max_width="200px", overflow="hidden"),
                                                _c(r["avg_waste_pp"], color="#22c55e", font_weight="600"),
                                                _c(r["count"])))),
                            width="100%"),
                        rx.text("데이터 없음", font_size="12px", color="#94a3b8")),
                    spacing="2", width="100%"),
                flex="1"),
            _card(
                rx.vstack(
                    _header("thumbs_down", "개선 필요 메뉴 TOP 10"),
                    rx.cond(
                        MealState.has_worst,
                        rx.table.root(
                            rx.table.header(rx.table.row(_col("메뉴"), _col("1인당(g)"), _col("횟수"))),
                            rx.table.body(
                                rx.foreach(MealState.worst_menus,
                                            lambda r: rx.table.row(
                                                _c(r["menu"], max_width="200px", overflow="hidden"),
                                                _c(r["avg_waste_pp"], color="#ef4444", font_weight="600"),
                                                _c(r["count"])))),
                            width="100%"),
                        rx.text("데이터 없음", font_size="12px", color="#94a3b8")),
                    spacing="2", width="100%"),
                flex="1"),
            spacing="3", width="100%"),
        # 수정13: 전체 메뉴 통계 accordion
        rx.cond(
            MealState.has_all_menu_stats,
            rx.accordion.root(
                rx.accordion.item(
                    rx.accordion.header(
                        rx.accordion.trigger(
                            rx.hstack(
                                rx.icon("list", size=14, color="#3b82f6"),
                                rx.text("전체 메뉴별 통계 (출현 횟수 기준)",
                                        font_size="13px", font_weight="600"),
                                rx.accordion.icon(),
                                spacing="2", align="center",
                            ),
                            padding="10px 12px",
                        ),
                    ),
                    rx.accordion.content(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(_col("메뉴"), _col("횟수"), _col("1인당 평균(g)"))),
                            rx.table.body(
                                rx.foreach(
                                    MealState.all_menu_stats,
                                    lambda r: rx.table.row(
                                        _c(r["menu"], max_width="250px", overflow="hidden"),
                                        _c(r["count"]),
                                        _c(r["avg_waste_pp"]),
                                    ),
                                ),
                            ),
                            width="100%",
                        ),
                    ),
                    value="all_menu",
                ),
                collapsible=True, type="single", variant="outline", width="100%",
            ),
        ),
        # 수정14: 배식인원 효율 분석 바차트
        rx.cond(
            MealState.has_servings_analysis,
            _card(
                rx.vstack(
                    _header("users", "배식인원 구간별 1인당 잔반"),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="avg_waste_pp",
                            fill="#8b5cf6", name="1인당 평균(g)",
                        ),
                        rx.recharts.x_axis(data_key="range", font_size=11),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.tooltip(),
                        data=MealState.servings_analysis,
                        width="100%", height=240,
                    ),
                    spacing="2", width="100%",
                )
            ),
        ),
        # 수정6: 메뉴 조합 효과 분석
        rx.cond(
            MealState.has_combo_analysis,
            _card(
                rx.vstack(
                    _header("layers", "잔반 적은 메뉴 조합 TOP 10"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(_col("메뉴 조합"), _col("1인당 평균(g)"), _col("횟수"))),
                        rx.table.body(
                            rx.foreach(
                                MealState.menu_combo_analysis,
                                lambda r: rx.table.row(
                                    _c(r["combo"], max_width="300px", overflow="hidden"),
                                    _c(r["avg_waste_pp"], color="#22c55e", font_weight="600"),
                                    _c(r["count"]),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    spacing="2", width="100%",
                )
            ),
        ),
        spacing="4", width="100%")


# ══════════════════════════════════════════
#  탭3: AI잔반분석
# ══════════════════════════════════════════

def _ai_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF 다운로드 ──
        rx.hstack(
            _header("brain", "AI 잔반 분석"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "AI PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=MealState.download_ai_pdf,
            ),
            width="100%", align="center",
        ),
        _ym_filter(),
        # ── 비용 분석 KPI ──
        rx.cond(
            MealState.has_cost,
            _card(
                rx.vstack(
                    _header("banknote", "비용 절감 분석"),
                    rx.hstack(
                        _kpi("음식물 단가", MealState.cost_data.get("unit_price", "0"), "원/kg", "receipt", "#3b82f6"),
                        _kpi("월 처리비", MealState.cost_data.get("current_cost", "0"), "원", "banknote", "#ef4444"),
                        _kpi("10% 절감 시", MealState.cost_data.get("save_10pct", "0"), "원/월", "trending_down", "#22c55e"),
                        _kpi("연간 절감", MealState.cost_data.get("annual_save", "0"), "원/년", "piggy_bank", "#f59e0b"),
                        spacing="3", width="100%", flex_wrap="wrap"),
                    spacing="3", width="100%")),
        ),
        # ── 잔반 요약 KPI ──
        rx.cond(
            MealState.has_analysis,
            rx.hstack(
                _kpi("총 잔반량", MealState.analysis_summary.get("total_waste", "0"), "kg", "trash_2", "#ef4444"),
                _kpi("1인당 평균", MealState.analysis_summary.get("avg_waste_pp", "0"), "g", "user", "#f59e0b"),
                _kpi("매칭일수", MealState.analysis_summary.get("matched_days", "0"), "일", "calendar_check", "#22c55e"),
                spacing="3", width="100%", flex_wrap="wrap"),
        ),
        # ── 요일별 패턴 ──
        _card(
            rx.vstack(
                _header("calendar_days", "요일별 잔반 패턴"),
                rx.cond(
                    MealState.has_weekday,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col("요일"), _col("평균 잔반(kg)"), _col("1인당(g)"), _col("횟수"))),
                        rx.table.body(
                            rx.foreach(MealState.weekday_pattern,
                                        lambda r: rx.table.row(
                                            _c(r["weekday"], font_weight="600"),
                                            _c(r["avg_kg"]),
                                            _c(r["avg_pp"]),
                                            _c(r["count"])))),
                        width="100%"),
                    rx.text("데이터가 없습니다.", font_size="13px", color="#94a3b8")),
                spacing="3", width="100%")),
        # ══════════════════════════════
        #  AI 분석 실행 섹션 (Phase 5)
        # ══════════════════════════════
        _card(
            rx.vstack(
                _header("sparkles", "Claude AI 분석"),
                # API 키 입력 (환경변수 미설정 시)
                rx.cond(
                    ~MealState.has_api_key,
                    rx.vstack(
                        rx.text("Anthropic API 키를 입력하세요.", font_size="12px", color="#64748b"),
                        rx.input(
                            value=MealState.ai_api_key,
                            on_change=MealState.set_ai_api_key,
                            placeholder="sk-ant-api03-...",
                            type="password",
                            size="2", width="100%",
                        ),
                        spacing="2", width="100%",
                    ),
                ),
                # 실행 버튼
                rx.hstack(
                    rx.button(
                        rx.cond(MealState.ai_loading, rx.spinner(size="1"), rx.icon("brain", size=14)),
                        "종합 분석 실행",
                        size="2", color_scheme="violet",
                        on_click=MealState.run_ai_comprehensive,
                        loading=MealState.ai_loading,
                    ),
                    rx.button(
                        rx.cond(MealState.ai_loading, rx.spinner(size="1"), rx.icon("utensils", size=14)),
                        "추천 식단 생성",
                        size="2", color_scheme="blue",
                        on_click=MealState.run_ai_recommend,
                        loading=MealState.ai_loading,
                    ),
                    # 수정5: 잔반 원인 분석 버튼
                    rx.button(
                        rx.cond(MealState.ai_cause_loading, rx.spinner(size="1"), rx.icon("search", size=14)),
                        "잔반 원인 분석",
                        size="2", color_scheme="orange",
                        on_click=MealState.run_ai_cause_analysis,
                        loading=MealState.ai_cause_loading,
                    ),
                    # 수정10: 일별 특이사항 버튼
                    rx.button(
                        rx.cond(MealState.ai_daily_loading, rx.spinner(size="1"), rx.icon("calendar_days", size=14)),
                        "일별 특이사항",
                        size="2", color_scheme="teal",
                        on_click=MealState.generate_daily_remarks,
                        loading=MealState.ai_daily_loading,
                    ),
                    spacing="3", flex_wrap="wrap",
                ),
                # 에러 메시지
                rx.cond(
                    MealState.has_ai_error,
                    rx.callout(
                        MealState.ai_error,
                        icon="circle_alert",
                        color_scheme="red",
                        size="1",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        # ── AI 종합분석 결과 (마크다운) ──
        rx.cond(
            MealState.has_ai_result,
            _card(
                rx.vstack(
                    _header("file_text", "AI 종합분석 결과"),
                    rx.box(
                        rx.markdown(MealState.ai_comprehensive_result),
                        width="100%",
                        padding="12px",
                        bg="#f8fafc",
                        border_radius="8px",
                        border="1px solid #e2e8f0",
                        max_height="600px",
                        overflow_y="auto",
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        # ── AI 추천식단 결과 (테이블) ──
        rx.cond(
            MealState.has_ai_recommend,
            _card(
                rx.vstack(
                    _header("utensils", "AI 추천 식단"),
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col("일차"), _col("추천 메뉴"),
                                _col("예상 잔반(g)"), _col("선정 사유"))),
                        rx.table.body(
                            rx.foreach(
                                MealState.ai_recommend_result,
                                lambda r: rx.table.row(
                                    _c(r["day"], font_weight="600"),
                                    _c(r["menu"], max_width="300px"),
                                    _c(r["expected_waste"]),
                                    _c(r["reason"], max_width="250px"),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    # 수정8: AI 추천식단 일괄등록 버튼
                    rx.button(
                        rx.icon("calendar_plus", size=14), "AI 추천식단 일괄등록",
                        size="2", color_scheme="green",
                        on_click=MealState.save_ai_recommendations,
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        # 수정5: AI 잔반 원인 분석 결과
        rx.cond(
            MealState.has_ai_cause_result,
            _card(
                rx.vstack(
                    _header("search", "AI 잔반 원인 분석"),
                    rx.box(
                        rx.markdown(MealState.ai_cause_result),
                        width="100%",
                        padding="12px",
                        bg="#fff7ed",
                        border_radius="8px",
                        border="1px solid #fed7aa",
                        max_height="500px",
                        overflow_y="auto",
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        # 수정10: AI 일별 특이사항
        rx.cond(
            MealState.has_ai_daily_remarks,
            _card(
                rx.vstack(
                    _header("calendar_days", "AI 일별 특이사항"),
                    rx.foreach(
                        MealState.analysis_rows,
                        lambda r: rx.cond(
                            MealState.ai_daily_remarks.get(r["meal_date"], "") != "",
                            rx.hstack(
                                rx.text(r["meal_date"], font_size="12px", font_weight="600",
                                        color="#374151", min_width="100px"),
                                rx.text(MealState.ai_daily_remarks.get(r["meal_date"], ""),
                                        font_size="12px", color="#64748b"),
                                spacing="2", align="start", width="100%",
                            ),
                        ),
                    ),
                    spacing="2", width="100%",
                ),
            ),
        ),
        spacing="4", width="100%")


# ══════════════════════════════════════════
#  탭4: 수거현황
# ══════════════════════════════════════════

def _collection_tab() -> rx.Component:
    return rx.vstack(
        _header("truck", "수거 현황"),
        _ym_filter(),
        _card(
            rx.cond(
                MealState.has_collection,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _col("수거일"), _col("품목"), _col("중량(kg)"),
                            _col("기사"), _col("업체"), _col("상태"))),
                    rx.table.body(
                        rx.foreach(MealState.collection_rows,
                                    lambda r: rx.table.row(
                                        _c(r["collect_date"]),
                                        _c(r["item_type"]),
                                        _c(r["weight"], font_weight="600"),
                                        _c(r["driver"]),
                                        _c(r["vendor"]),
                                        rx.table.cell(
                                            rx.badge(r["status"],
                                                      color_scheme=rx.cond(
                                                          r["status"] == "confirmed", "green",
                                                          rx.cond(r["status"] == "submitted", "blue", "gray")),
                                                      size="1"))))),
                    width="100%"),
                rx.text("해당 기간 수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"))),
        spacing="4", width="100%")


# ══════════════════════════════════════════
#  탭5: 정산확인
# ══════════════════════════════════════════

def _settle_tab() -> rx.Component:
    return rx.vstack(
        _header("receipt", "정산 확인"),
        _ym_filter(),
        rx.cond(
            MealState.has_settle,
            rx.hstack(
                _kpi("총 수거량", MealState.settle_data.get("total_weight", "0"), "kg", "weight", "#38bd94"),
                _kpi("공급가액", MealState.settle_data.get("total_amount", "0"), "원", "receipt", "#3b82f6"),
                _kpi("부가세(10%)", MealState.settle_data.get("vat", "0"), "원", "percent", "#f59e0b"),
                _kpi("합계", MealState.settle_data.get("grand_total", "0"), "원", "banknote", "#8b5cf6"),
                spacing="3", width="100%", flex_wrap="wrap")),
        _card(
            rx.vstack(
                _header("pie_chart", "품목별 정산"),
                rx.cond(
                    MealState.has_settle_items,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(_col("품목"), _col("수거량(kg)"), _col("금액(원)"), _col("건수"))),
                        rx.table.body(
                            rx.foreach(MealState.settle_items,
                                        lambda r: rx.table.row(
                                            _c(r["item_type"], font_weight="600"),
                                            _c(r["weight"]),
                                            _c(r["amount"], font_weight="600"),
                                            _c(r["count"])))),
                        width="100%"),
                    rx.text("정산 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center")),
                spacing="3", width="100%")),
        spacing="4", width="100%")


# ══════════════════════════════════════════
#  탭6: ESG보고서
# ══════════════════════════════════════════

def _esg_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF 다운로드 (Phase 5) ──
        rx.hstack(
            _header("leaf", "ESG 폐기물 감축 보고서"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=MealState.download_esg_pdf,
            ),
            width="100%", align="center",
        ),
        rx.select(get_year_options(),
                   value=MealState.selected_year,
                   on_change=MealState.set_selected_year,
                   size="2", width="90px"),
        rx.cond(
            MealState.has_esg,
            rx.vstack(
                rx.hstack(
                    _kpi("총 수거량", MealState.esg_data.get("total_kg", "0"), "kg", "weight", "#38bd94"),
                    _kpi("음식물", MealState.esg_data.get("food_kg", "0"), "kg", "apple", "#f59e0b"),
                    _kpi("재활용", MealState.esg_data.get("recycle_kg", "0"), "kg", "recycle", "#3b82f6"),
                    _kpi("일반", MealState.esg_data.get("general_kg", "0"), "kg", "trash_2", "#94a3b8"),
                    spacing="3", width="100%", flex_wrap="wrap"),
                rx.hstack(
                    _kpi("탄소 감축", MealState.esg_data.get("carbon_reduced", "0"), "kg CO₂", "leaf", "#22c55e"),
                    _kpi("나무 환산", MealState.esg_data.get("tree_equivalent", "0"), "그루", "tree_pine", "#16a34a"),
                    _kpi("CO₂ 톤", MealState.esg_data.get("carbon_tons", "0"), "tCO₂", "globe", "#0ea5e9"),
                    spacing="3", width="100%", flex_wrap="wrap"),
                _card(
                    rx.vstack(
                        _header("info", "산출 기준"),
                        rx.text("음식물 0.47 | 재활용 0.21 | 일반 0.09 kgCO₂/kg",
                                 font_size="12px", color="#64748b"),
                        rx.text("나무 환산: 21.77 kgCO₂/그루 (소나무 기준)",
                                 font_size="12px", color="#64748b"),
                        spacing="1", width="100%")),
                spacing="4", width="100%"),
            rx.text("수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                     padding="20px", text_align="center")),
        spacing="4", width="100%")


# ══════════════════════════════════════════
#  탭 콘텐츠 라우터
# ══════════════════════════════════════════

def _tab_content() -> rx.Component:
    return rx.box(
        rx.cond(MealState.active_tab == "식단등록", _menu_tab()),
        rx.cond(MealState.active_tab == "스마트잔반분석", _smart_tab()),
        rx.cond(MealState.active_tab == "AI잔반분석", _ai_tab()),
        rx.cond(MealState.active_tab == "수거현황", _collection_tab()),
        rx.cond(MealState.active_tab == "정산확인", _settle_tab()),
        rx.cond(MealState.active_tab == "ESG보고서", _esg_tab()),
        width="100%")


# ══════════════════════════════════════════
#  메인 페이지
# ══════════════════════════════════════════

def meal_manager_page() -> rx.Component:
    """급식담당자 메인 페이지"""
    return rx.box(
        _topbar(),
        _nav(),
        rx.box(
            _tab_content(),
            padding="24px",
            min_height="calc(100vh - 110px)",
            bg="#f1f5f9"))
