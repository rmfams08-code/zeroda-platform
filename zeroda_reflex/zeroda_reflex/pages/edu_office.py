# zeroda_reflex/pages/edu_office.py
# 교육청 사용자 대시보드 — 6탭
import reflex as rx
from zeroda_reflex.state.edu_state import EduState, EDU_TABS
from zeroda_reflex.state.auth_state import get_year_options, MONTH_OPTIONS
# ── 공통 컴포넌트 import (Phase 0-A 모듈화) ──
from zeroda_reflex.components.shared import (
    kpi_card_compact as _kpi_card,    # 교육청은 컴팩트형 KPI
    section_header as _section_header,
    card_box_light as _card_box,      # 교육청은 라이트형 카드
    col_header as _col_header,        # rx.table 컬럼 헤더
    table_cell as _cell,              # rx.table 데이터 셀
)

# ══════════════════════════════════════════
#  공통 UI 헬퍼 — shared.py에서 import (Phase 0-A)
# ══════════════════════════════════════════


# ══════════════════════════════════════════
#  상단바 + 탭 네비게이션
# ══════════════════════════════════════════

def _topbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("landmark", size=20, color="#3b82f6"),
                rx.text("ZERODA", font_size="18px", font_weight="800", color="#1e293b"),
                rx.text("교육청", font_size="14px", color="#64748b"),
                spacing="2", align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.icon("user", size=14, color="#64748b"),
                rx.text(EduState.user_name, font_size="13px", color="#64748b"),
                spacing="1", align="center",
            ),
            rx.button(
                rx.icon("log_out", size=14), "로그아웃",
                variant="outline", size="1",
                on_click=EduState.logout,
            ),
            spacing="3", align="center", width="100%",
        ),
        bg="white", padding="12px 24px",
        border_bottom="1px solid #e2e8f0", width="100%",
    )


def _tab_nav() -> rx.Component:
    def _btn(label: str) -> rx.Component:
        return rx.button(
            label,
            on_click=EduState.set_active_tab(label),
            variant=rx.cond(EduState.active_tab == label, "solid", "ghost"),
            color_scheme=rx.cond(EduState.active_tab == label, "blue", "gray"),
            size="2",
        )
    return rx.hstack(
        *[_btn(t) for t in EDU_TABS],
        spacing="2", padding="8px 24px",
        bg="white", border_bottom="1px solid #e2e8f0",
        flex_wrap="wrap", width="100%",
    )


def _year_month_filter() -> rx.Component:
    return rx.hstack(
        rx.select(
            get_year_options(),
            value=EduState.selected_year,
            on_change=EduState.set_selected_year,
            size="2", width="90px",
        ),
        rx.select(
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
            value=EduState.selected_month,
            on_change=EduState.set_selected_month,
            size="2", width="80px",
        ),
        spacing="2",
    )


# ══════════════════════════════════════════
#  탭1: 전체현황
# ══════════════════════════════════════════

def _overview_tab() -> rx.Component:
    return rx.vstack(
        _section_header("layout_dashboard", "전체 현황"),
        _year_month_filter(),
        # KPI
        rx.hstack(
            _kpi_card("관할 학교", EduState.overview_data.get("school_count", "0"), "개교", "school", "#3b82f6"),
            _kpi_card("총 수거량", EduState.overview_data.get("total_weight", "0"), "kg", "weight", "#38bd94"),
            _kpi_card("수거 건수", EduState.overview_data.get("total_count", "0"), "건", "hash", "#f59e0b"),
            _kpi_card("등록 업체", EduState.overview_data.get("vendor_count", "0"), "개사", "building_2", "#8b5cf6"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        # 학교별 테이블
        _card_box(
            rx.vstack(
                _section_header("school", "학교별 수거 현황"),
                rx.cond(
                    EduState.has_overview_schools,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("학교명"),
                                _col_header("수거량(kg)"),
                                _col_header("건수"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.overview_school_list,
                                lambda r: rx.table.row(
                                    _cell(r["school_name"], font_weight="600"),
                                    _cell(r["weight"]),
                                    _cell(r["count"]),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("해당 기간 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭2: 학교별조회
# ══════════════════════════════════════════

def _by_school_tab() -> rx.Component:
    return rx.vstack(
        _section_header("search", "학교별 수거 조회"),
        rx.hstack(
            rx.select(
                EduState.school_name_options,
                value=EduState.sel_school,
                on_change=EduState.set_sel_school,
                placeholder="학교 선택",
                size="2", width="200px",
            ),
            _year_month_filter(),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=EduState.load_by_school,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        _card_box(
            rx.cond(
                EduState.has_school_rows,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _col_header("수거일"),
                            _col_header("품목"),
                            _col_header("중량(kg)"),
                            _col_header("업체"),
                            _col_header("기사"),
                            _col_header("상태"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            EduState.school_rows,
                            lambda r: rx.table.row(
                                _cell(r["collect_date"]),
                                _cell(r["item_type"]),
                                _cell(r["weight"], font_weight="600"),
                                _cell(r["vendor"]),
                                _cell(r["driver"]),
                                rx.table.cell(
                                    rx.badge(
                                        r["status"],
                                        color_scheme=rx.cond(
                                            r["status"] == "confirmed", "green",
                                            rx.cond(r["status"] == "submitted", "blue", "gray"),
                                        ),
                                        size="1",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("해당 기간 수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭3: 업체별현황
# ══════════════════════════════════════════

def _by_vendor_tab() -> rx.Component:
    return rx.vstack(
        _section_header("building_2", "업체별 수거 현황"),
        rx.hstack(
            rx.select(
                EduState.vendor_name_options,
                value=EduState.sel_vendor,
                on_change=EduState.set_sel_vendor,
                placeholder="업체 선택",
                size="2", width="180px",
            ),
            rx.select(
                get_year_options(),
                value=EduState.selected_year,
                on_change=EduState.set_selected_year,
                size="2", width="90px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=EduState.load_by_vendor,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # KPI
        rx.cond(
            EduState.has_vendor_data,
            rx.hstack(
                _kpi_card("총 수거량", EduState.vendor_data.get("total_weight", "0"), "kg", "weight", "#38bd94"),
                _kpi_card("관할 학교", EduState.vendor_data.get("school_count", "0"), "개교", "school", "#3b82f6"),
                spacing="3", width="100%", flex_wrap="wrap",
            ),
        ),
        _card_box(
            rx.vstack(
                _section_header("school", "학교별 수거량"),
                rx.cond(
                    EduState.has_vendor_schools,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("학교명"),
                                _col_header("수거량(kg)"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.vendor_school_list,
                                lambda r: rx.table.row(
                                    _cell(r["school_name"], font_weight="600"),
                                    _cell(r["weight"]),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("해당 업체의 수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭4: 탄소감축
# ══════════════════════════════════════════

def _carbon_tab() -> rx.Component:
    return rx.vstack(
        _section_header("leaf", "탄소배출 감축 현황"),
        rx.hstack(
            rx.select(
                get_year_options(),
                value=EduState.selected_year,
                on_change=EduState.set_selected_year,
                size="2", width="90px",
            ),
            rx.select(
                ["전체", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
                value=EduState.selected_month,
                on_change=EduState.set_selected_month,
                size="2", width="80px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=EduState.load_carbon,
                variant="outline", size="2",
            ),
            spacing="2",
        ),
        rx.cond(
            EduState.has_carbon,
            rx.vstack(
                rx.hstack(
                    _kpi_card("총 수거량", EduState.carbon_data.get("total_kg", "0"), "kg", "weight", "#38bd94"),
                    _kpi_card("음식물", EduState.carbon_data.get("food_kg", "0"), "kg", "apple", "#f59e0b"),
                    _kpi_card("재활용", EduState.carbon_data.get("recycle_kg", "0"), "kg", "recycle", "#3b82f6"),
                    _kpi_card("일반", EduState.carbon_data.get("general_kg", "0"), "kg", "trash_2", "#94a3b8"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                rx.hstack(
                    _kpi_card("탄소 감축량", EduState.carbon_data.get("carbon_reduced", "0"), "kg CO₂", "leaf", "#22c55e"),
                    _kpi_card("나무 환산", EduState.carbon_data.get("tree_equivalent", "0"), "그루", "tree_pine", "#16a34a"),
                    _kpi_card("CO₂ 톤", EduState.carbon_data.get("carbon_tons", "0"), "tCO₂", "globe", "#0ea5e9"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                spacing="3", width="100%",
            ),
        ),
        # 학교별 순위
        _card_box(
            rx.vstack(
                _section_header("trophy", "학교별 수거량 / 탄소감축 TOP 15"),
                rx.cond(
                    EduState.has_carbon_ranking,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("학교명"),
                                _col_header("수거량(kg)"),
                                _col_header("CO₂ 감축(kg)"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.carbon_ranking,
                                lambda r: rx.table.row(
                                    _cell(r["school_name"], font_weight="600"),
                                    _cell(r["weight"]),
                                    _cell(r["carbon"], color="#22c55e", font_weight="600"),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("데이터가 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭5: ESG 보고서
# ══════════════════════════════════════════

def _esg_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF 다운로드 (Phase 5) ──
        rx.hstack(
            _section_header("file_text", "ESG 종합 보고서"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=EduState.download_esg_pdf,
            ),
            width="100%", align="center",
        ),
        rx.hstack(
            rx.select(
                EduState.school_name_options,
                value=EduState.esg_school,
                on_change=EduState.set_esg_school,
                placeholder="학교 선택",
                size="2", width="200px",
            ),
            rx.select(
                get_year_options(),
                value=EduState.selected_year,
                on_change=EduState.set_selected_year,
                size="2", width="90px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=EduState.load_esg,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        rx.cond(
            EduState.has_esg,
            rx.vstack(
                rx.hstack(
                    _kpi_card("총 수거량", EduState.esg_data.get("total_kg", "0"), "kg", "weight", "#38bd94"),
                    _kpi_card("음식물", EduState.esg_data.get("food_kg", "0"), "kg", "apple", "#f59e0b"),
                    _kpi_card("재활용", EduState.esg_data.get("recycle_kg", "0"), "kg", "recycle", "#3b82f6"),
                    _kpi_card("일반", EduState.esg_data.get("general_kg", "0"), "kg", "trash_2", "#94a3b8"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                rx.hstack(
                    _kpi_card("탄소 감축", EduState.esg_data.get("carbon_reduced", "0"), "kg CO₂", "leaf", "#22c55e"),
                    _kpi_card("나무 환산", EduState.esg_data.get("tree_equivalent", "0"), "그루", "tree_pine", "#16a34a"),
                    _kpi_card("CO₂ 톤", EduState.esg_data.get("carbon_tons", "0"), "tCO₂", "globe", "#0ea5e9"),
                    _kpi_card("수거 건수", EduState.esg_data.get("count", "0"), "건", "hash", "#8b5cf6"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                _card_box(
                    rx.vstack(
                        _section_header("info", "산출 기준"),
                        rx.text("음식물: 0.47 kgCO₂/kg | 재활용: 0.21 kgCO₂/kg | 일반: 0.09 kgCO₂/kg",
                                 font_size="12px", color="#64748b"),
                        rx.text("나무 환산: 21.77 kgCO₂/그루 (소나무 기준)",
                                 font_size="12px", color="#64748b"),
                        spacing="1", width="100%",
                    ),
                ),
                spacing="4", width="100%",
            ),
            rx.text("학교를 선택하고 조회하세요.", font_size="13px", color="#94a3b8",
                     padding="20px", text_align="center"),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭6: 안전관리
# ══════════════════════════════════════════

def _safety_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF 다운로드 (Phase 5) ──
        rx.hstack(
            _section_header("shield_check", "안전관리 현황"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=EduState.download_safety_pdf,
            ),
            width="100%", align="center",
        ),
        _year_month_filter(),

        # 안전등급
        _card_box(
            rx.vstack(
                _section_header("award", "수거업체 안전등급"),
                rx.cond(
                    EduState.has_safety_scores,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("업체"),
                                _col_header("위반(40)"),
                                _col_header("점검(15)"),
                                _col_header("일상(15)"),
                                _col_header("교육(30)"),
                                _col_header("총점"),
                                _col_header("등급"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.safety_scores,
                                lambda r: rx.table.row(
                                    _cell(r["vendor"]),
                                    _cell(r["violation_score"]),
                                    _cell(r["checklist_score"]),
                                    _cell(r["daily_check_score"]),
                                    _cell(r["education_score"]),
                                    _cell(r["total_score"], font_weight="700"),
                                    rx.table.cell(rx.badge(r["grade"], size="1")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("안전등급 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 스쿨존 위반
        _card_box(
            rx.vstack(
                _section_header("triangle_alert", "스쿨존 위반 이력"),
                rx.cond(
                    EduState.has_safety_violations,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("위반일"),
                                _col_header("업체"),
                                _col_header("기사"),
                                _col_header("유형"),
                                _col_header("장소"),
                                _col_header("과태료"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.safety_violations,
                                lambda r: rx.table.row(
                                    _cell(r["violation_date"]),
                                    _cell(r["vendor"]),
                                    _cell(r["driver"]),
                                    _cell(r["violation_type"]),
                                    _cell(r["location"]),
                                    _cell(r["fine_amount"]),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("위반 기록이 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 안전교육
        _card_box(
            rx.vstack(
                _section_header("graduation_cap", "안전교육 이수 현황"),
                rx.cond(
                    EduState.has_safety_education,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("업체"),
                                _col_header("기사"),
                                _col_header("교육명"),
                                _col_header("교육일"),
                                _col_header("수료"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.safety_education,
                                lambda r: rx.table.row(
                                    _cell(r["vendor"]),
                                    _cell(r["driver"]),
                                    _cell(r["edu_name"]),
                                    _cell(r["edu_date"]),
                                    rx.table.cell(
                                        rx.badge(
                                            r["completed"],
                                            color_scheme=rx.cond(r["completed"] == "수료", "green", "red"),
                                            size="1",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("안전교육 기록이 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 사고 보고
        _card_box(
            rx.vstack(
                _section_header("siren", "사고 보고 현황"),
                rx.cond(
                    EduState.has_safety_accidents,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                _col_header("발생일"),
                                _col_header("업체"),
                                _col_header("기사"),
                                _col_header("유형"),
                                _col_header("장소"),
                                _col_header("피해"),
                                _col_header("상태"),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                EduState.safety_accidents,
                                lambda r: rx.table.row(
                                    _cell(r["accident_date"]),
                                    _cell(r["vendor"]),
                                    _cell(r["driver"]),
                                    _cell(r["accident_type"]),
                                    _cell(r["location"]),
                                    _cell(r["damage"]),
                                    rx.table.cell(
                                        rx.badge(
                                            r["status"],
                                            color_scheme=rx.cond(r["status"] == "완료", "green", "orange"),
                                            size="1",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("사고 보고 기록이 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭 콘텐츠 라우터
# ══════════════════════════════════════════

def _tab_content() -> rx.Component:
    return rx.box(
        rx.cond(EduState.active_tab == "전체현황", _overview_tab()),
        rx.cond(EduState.active_tab == "학교별조회", _by_school_tab()),
        rx.cond(EduState.active_tab == "업체별현황", _by_vendor_tab()),
        rx.cond(EduState.active_tab == "탄소감축", _carbon_tab()),
        rx.cond(EduState.active_tab == "ESG보고서", _esg_tab()),
        rx.cond(EduState.active_tab == "안전관리", _safety_tab()),
        width="100%",
    )


# ══════════════════════════════════════════
#  메인 페이지
# ══════════════════════════════════════════

def edu_office_page() -> rx.Component:
    """교육청 메인 페이지"""
    return rx.box(
        _topbar(),
        _tab_nav(),
        rx.box(
            _tab_content(),
            padding="24px",
            min_height="calc(100vh - 110px)",
            bg="#f1f5f9",
        ),
    )
