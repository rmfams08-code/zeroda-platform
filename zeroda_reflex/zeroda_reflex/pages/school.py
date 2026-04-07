# zeroda_reflex/pages/school.py
# 학교 사용자 대시보드 — 5탭 (월별현황, 수거내역, 정산확인, ESG, 안전관리)
import reflex as rx
from zeroda_reflex.state.school_state import SchoolState, SCHOOL_TABS
from zeroda_reflex.state.auth_state import get_year_options, MONTH_OPTIONS

# ── 안전보건 점검 체크리스트 7항목 (모듈 상수) ──
SAFETY_CHECKLIST_ITEMS = [
    "과업지시서(또는 계약서)에 '안전관리 및 예방조치 후 작업' 실시 내용 포함",
    "공사(용역)업체에서 근로자에 대한 안전보건교육 실시",
    "안전보호구(안전모, 안전대, 안전화 등) 착용 주지",
    "위험사항(위험성평가 등)과 기계·기구·설비 안전점검 안내",
    "학교 현장 이동 시 행정실(담당자) 안내 주지",
    "유해·위험 작업 시 안전보건 점검표 제출 여부",
    "안전·보건에 관한 종사자 의견청취 실시",
]
# ── 공통 컴포넌트 import (Phase 0-A 모듈화) ──
from zeroda_reflex.components.shared import (
    kpi_card_compact as _kpi_card,    # 학교는 컴팩트형 KPI
    section_header as _section_header,
    card_box_light as _card_box,      # 학교는 라이트형 카드
)

# ══════════════════════════════════════════
#  공통 UI 헬퍼 — shared.py에서 import (Phase 0-A)
# ══════════════════════════════════════════


STATUS_MAP = {
    "draft": "임시저장",
    "submitted": "전송완료",
    "confirmed": "확인완료",
}


# ══════════════════════════════════════════
#  상단바 + 탭 네비게이션
# ══════════════════════════════════════════

def _topbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("school", size=20, color="#3b82f6"),
                rx.text("ZERODA", font_size="18px", font_weight="800", color="#1e293b"),
                rx.text("학교", font_size="14px", color="#64748b"),
                spacing="2", align="center",
            ),
            rx.spacer(),
            # 학교 선택 (여러 학교 배정 시)
            rx.cond(
                SchoolState.has_schools,
                rx.select(
                    SchoolState.school_list,
                    value=SchoolState.current_school,
                    on_change=SchoolState.set_current_school,
                    size="2", width="180px",
                ),
            ),
            rx.hstack(
                rx.icon("user", size=14, color="#64748b"),
                rx.text(SchoolState.user_name, font_size="13px", color="#64748b"),
                spacing="1", align="center",
            ),
            rx.button(
                rx.icon("log_out", size=14),
                "로그아웃",
                variant="outline", size="1",
                on_click=SchoolState.logout,
            ),
            spacing="3", align="center", width="100%",
        ),
        bg="white",
        padding="12px 24px",
        border_bottom="1px solid #e2e8f0",
        width="100%",
    )


def _tab_nav() -> rx.Component:
    def _tab_btn(label: str) -> rx.Component:
        return rx.button(
            label,
            on_click=SchoolState.set_active_tab(label),
            variant=rx.cond(SchoolState.active_tab == label, "solid", "ghost"),
            color_scheme=rx.cond(SchoolState.active_tab == label, "blue", "gray"),
            size="2",
        )
    return rx.hstack(
        *[_tab_btn(t) for t in SCHOOL_TABS],
        spacing="2",
        padding="8px 24px",
        bg="white",
        border_bottom="1px solid #e2e8f0",
        flex_wrap="wrap",
        width="100%",
    )


# ══════════════════════════════════════════
#  탭1: 월별현황
# ══════════════════════════════════════════

def _year_filter() -> rx.Component:
    return rx.hstack(
        rx.select(
            get_year_options(),
            value=SchoolState.selected_year,
            on_change=SchoolState.set_selected_year,
            size="2", width="90px",
        ),
        spacing="2",
    )


def _esg_year_month_filter() -> rx.Component:
    return rx.hstack(
        rx.select(
            get_year_options(),
            value=SchoolState.selected_year,
            on_change=SchoolState.set_selected_year,
            size="2", width="90px",
        ),
        rx.select(
            ["전체", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
            value=SchoolState.selected_month,
            on_change=SchoolState.set_selected_month,
            size="2", width="90px",
        ),
        spacing="2",
    )


def _year_month_filter() -> rx.Component:
    return rx.hstack(
        rx.select(
            get_year_options(),
            value=SchoolState.selected_year,
            on_change=SchoolState.set_selected_year,
            size="2", width="90px",
        ),
        rx.select(
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
            value=SchoolState.selected_month,
            on_change=SchoolState.set_selected_month,
            size="2", width="80px",
        ),
        spacing="2",
    )


def _monthly_tab() -> rx.Component:
    return rx.vstack(
        _section_header("bar_chart_3", "월별 수거 현황"),
        rx.hstack(
            rx.text(SchoolState.current_school, font_size="14px", font_weight="600", color="#3b82f6"),
            rx.text(" — ", font_size="14px", color="#94a3b8"),
            rx.text(SchoolState.selected_year, font_size="14px"), rx.text("년", font_size="14px", color="#94a3b8"),
            spacing="1", align="center",
        ),
        _year_filter(),
        # KPI
        rx.hstack(
            _kpi_card("연간 총 수거량", SchoolState.monthly_total_weight, "kg", "weight", "#38bd94"),
            _kpi_card("연간 수거 건수", SchoolState.monthly_total_count, "건", "hash", "#3b82f6"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        # 월별 테이블
        _card_box(
            rx.cond(
                SchoolState.has_monthly,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("월", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            SchoolState.monthly_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["month"], "월", font_size="12px")),
                                rx.table.cell(rx.text(r["weight"], font_size="12px", font_weight="600",
                                                       color=rx.cond(r["weight"] != "0.0", "#1e293b", "#cbd5e1"))),
                                rx.table.cell(rx.text(r["count"], font_size="12px")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭2: 수거내역
# ══════════════════════════════════════════

def _detail_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + Excel 다운로드 (Phase 3) ──
        rx.hstack(
            _section_header("clipboard_list", "수거 내역"),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=SchoolState.download_collection_excel,
            ),
            width="100%", align="center",
        ),
        _year_month_filter(),
        _card_box(
            rx.cond(
                SchoolState.has_detail,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("수거일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("중량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("비고", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            SchoolState.detail_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["collect_date"], font_size="12px")),
                                rx.table.cell(rx.text(r["item_type"], font_size="12px")),
                                rx.table.cell(rx.text(r["weight"], font_size="12px", font_weight="600")),
                                rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                rx.table.cell(rx.text(r["vendor"], font_size="12px")),
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
                                rx.table.cell(rx.text(r["memo"], font_size="11px", color="#94a3b8")),
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
#  탭3: 정산확인
# ══════════════════════════════════════════

def _settlement_tab() -> rx.Component:
    return rx.vstack(
        _section_header("receipt", "정산 확인"),
        _year_month_filter(),
        # KPI
        rx.cond(
            SchoolState.has_settle,
            rx.hstack(
                _kpi_card("총 수거량", SchoolState.settle_data.get("total_weight", "0"), "kg", "weight", "#38bd94"),
                _kpi_card("공급가액", SchoolState.settle_data.get("total_amount", "0"), "원", "receipt", "#3b82f6"),
                _kpi_card("부가세(10%)", SchoolState.settle_data.get("vat", "0"), "원", "percent", "#f59e0b"),
                _kpi_card("합계", SchoolState.settle_data.get("grand_total", "0"), "원", "banknote", "#8b5cf6"),
                spacing="3", width="100%", flex_wrap="wrap",
            ),
        ),
        # 품목별 상세
        _card_box(
            rx.vstack(
                _section_header("pie_chart", "품목별 정산 내역"),
                rx.cond(
                    SchoolState.has_settle_items,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("금액(원)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                SchoolState.settle_items,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["item_type"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["weight"], font_size="12px")),
                                    rx.table.cell(rx.text(r["amount"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("해당 기간 정산 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭4: ESG 보고서
# ══════════════════════════════════════════

def _esg_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF 다운로드 (Phase 5) ──
        rx.hstack(
            _section_header("leaf", "ESG 폐기물 감축 보고서"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=SchoolState.download_esg_pdf,
            ),
            width="100%", align="center",
        ),
        _esg_year_month_filter(),
        rx.cond(
            SchoolState.has_esg,
            rx.vstack(
                # 수거량 KPI
                rx.hstack(
                    _kpi_card("총 수거량", SchoolState.esg_data.get("total_kg", "0"), "kg", "weight", "#38bd94"),
                    _kpi_card("음식물", SchoolState.esg_data.get("food_kg", "0"), "kg", "apple", "#f59e0b"),
                    _kpi_card("재활용", SchoolState.esg_data.get("recycle_kg", "0"), "kg", "recycle", "#3b82f6"),
                    _kpi_card("일반", SchoolState.esg_data.get("general_kg", "0"), "kg", "trash_2", "#94a3b8"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                # 탄소 KPI
                rx.hstack(
                    _kpi_card("탄소 감축량", SchoolState.esg_data.get("carbon_reduced", "0"), "kg CO₂", "leaf", "#22c55e"),
                    _kpi_card("나무 환산", SchoolState.esg_data.get("tree_equivalent", "0"), "그루", "tree_pine", "#16a34a"),
                    _kpi_card("CO₂ 톤", SchoolState.esg_data.get("carbon_tons", "0"), "tCO₂", "globe", "#0ea5e9"),
                    _kpi_card("수거 건수", SchoolState.esg_data.get("count", "0"), "건", "hash", "#8b5cf6"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                # 설명
                _card_box(
                    rx.vstack(
                        _section_header("info", "산출 기준"),
                        rx.text("음식물 폐기물: 0.47 kgCO₂/kg", font_size="12px", color="#64748b"),
                        rx.text("재활용 폐기물: 0.21 kgCO₂/kg", font_size="12px", color="#64748b"),
                        rx.text("일반 폐기물: 0.09 kgCO₂/kg", font_size="12px", color="#64748b"),
                        rx.text("나무 환산: 21.77 kgCO₂/그루 (소나무 기준)", font_size="12px", color="#64748b"),
                        spacing="1", width="100%",
                    ),
                ),
                spacing="4", width="100%",
            ),
            rx.text("해당 기간 수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                     padding="20px", text_align="center"),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭5: 안전관리 보고서
# ══════════════════════════════════════════

GRADE_COLORS = {
    "S": "green", "A": "blue", "B": "yellow", "C": "orange", "D": "red",
}


def _safety_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF 다운로드 ──
        rx.hstack(
            _section_header("shield_check", "안전관리 보고서"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=SchoolState.download_safety_pdf,
            ),
            width="100%", align="center",
        ),
        _year_month_filter(),

        # ── 수정2: 차량점검·사고 KPI ──
        rx.hstack(
            _kpi_card("안전교육 이수", SchoolState.safety_checklist_count, "건", "graduation_cap", "#3b82f6"),
            _kpi_card("차량점검 건수", SchoolState.safety_checklist_count, "건", "wrench", "#f59e0b"),
            _kpi_card("사고 보고 건수", SchoolState.safety_accident_count, "건", "triangle_alert", "#ef4444"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),

        # 안전등급
        _card_box(
            rx.vstack(
                _section_header("award", "수거업체 안전등급"),
                rx.cond(
                    SchoolState.has_safety_scores,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("위반(40)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("점검(15)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("일상(15)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("교육(30)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("총점", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("등급", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                SchoolState.safety_scores,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(r["violation_score"], font_size="12px")),
                                    rx.table.cell(rx.text(r["checklist_score"], font_size="12px")),
                                    rx.table.cell(rx.text(r["daily_check_score"], font_size="12px")),
                                    rx.table.cell(rx.text(r["education_score"], font_size="12px")),
                                    rx.table.cell(rx.text(r["total_score"], font_size="12px", font_weight="700")),
                                    rx.table.cell(rx.badge(r["grade"], size="1")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("담당 수거업체의 안전등급이 없습니다.", font_size="13px", color="#94a3b8",
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
                    SchoolState.has_safety_violations,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("위반일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("유형", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("장소", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("과태료", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                SchoolState.safety_violations,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["violation_date"], font_size="12px")),
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                    rx.table.cell(rx.text(r["violation_type"], font_size="12px")),
                                    rx.table.cell(rx.text(r["location"], font_size="12px")),
                                    rx.table.cell(rx.text(r["fine_amount"], font_size="12px")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("해당 기간 스쿨존 위반 기록이 없습니다.", font_size="13px", color="#94a3b8",
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
                    SchoolState.has_safety_education,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("교육명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("교육일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수료", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                SchoolState.safety_education,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                    rx.table.cell(rx.text(r["edu_name"], font_size="12px")),
                                    rx.table.cell(rx.text(r["edu_date"], font_size="12px")),
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

        # ── 수정3: 일일안전보건 점검 이행 현황 ──
        _card_box(
            rx.vstack(
                _section_header("clipboard_check", "일일안전보건 점검 이행 현황"),
                rx.cond(
                    SchoolState.has_daily_checks,
                    rx.vstack(
                        rx.hstack(
                            _kpi_card("점검 건수", SchoolState.daily_check_count, "건", "clipboard_check", "#3b82f6"),
                            _kpi_card("점검일 수", SchoolState.daily_check_days, "일", "calendar", "#8b5cf6"),
                            _kpi_card("양호율", SchoolState.daily_check_ok_rate, "%", "check_circle", "#22c55e"),
                            _kpi_card("불량 항목", SchoolState.daily_check_fail_count, "건", "x_circle", "#ef4444"),
                            spacing="3", width="100%", flex_wrap="wrap",
                        ),
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell(rx.text("점검일", font_size="12px", font_weight="700", color="#64748b")),
                                    rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                    rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                    rx.table.column_header_cell(rx.text("카테고리", font_size="12px", font_weight="700", color="#64748b")),
                                    rx.table.column_header_cell(rx.text("양호", font_size="12px", font_weight="700", color="#64748b")),
                                    rx.table.column_header_cell(rx.text("불량", font_size="12px", font_weight="700", color="#64748b")),
                                    rx.table.column_header_cell(rx.text("메모", font_size="12px", font_weight="700", color="#64748b")),
                                ),
                            ),
                            rx.table.body(
                                rx.foreach(
                                    SchoolState.daily_checks,
                                    lambda r: rx.table.row(
                                        rx.table.cell(rx.text(r["check_date"], font_size="12px")),
                                        rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                        rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                        rx.table.cell(rx.text(r["category"], font_size="12px")),
                                        rx.table.cell(rx.text(r["total_ok"], font_size="12px", color="#22c55e")),
                                        rx.table.cell(
                                            rx.text(
                                                r["total_fail"],
                                                font_size="12px",
                                                color=rx.cond(r["total_fail"] != "0", "#ef4444", "#64748b"),
                                                font_weight=rx.cond(r["total_fail"] != "0", "700", "400"),
                                            ),
                                        ),
                                        rx.table.cell(rx.text(r["memo"], font_size="11px", color="#94a3b8")),
                                    ),
                                ),
                            ),
                            width="100%",
                        ),
                        spacing="3", width="100%",
                    ),
                    rx.text("해당 기간 일일안전점검 이력이 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # ── 수정4: 안전보건 점검 체크리스트 7항목 ──
        _card_box(
            rx.vstack(
                _section_header("check_square", "안전보건 점검 체크리스트"),
                rx.text(
                    "도급·용역 업체 안전관리 점검 항목을 확인하고 예/아니오를 선택하세요.",
                    font_size="12px", color="#64748b",
                ),
                *[
                    rx.hstack(
                        rx.text(f"{i+1}.", font_size="12px", color="#64748b", min_width="20px"),
                        rx.text(SAFETY_CHECKLIST_ITEMS[i], font_size="12px", flex="1"),
                        rx.select(
                            ["예", "아니오"],
                            value=SchoolState.checklist_results[i],
                            on_change=lambda v, idx=i: SchoolState.set_checklist_item([str(idx), v]),
                            size="1",
                            width="80px",
                        ),
                        spacing="2", align="center", width="100%",
                        padding_y="4px",
                        border_bottom="1px solid #f1f5f9",
                    )
                    for i in range(7)
                ],
                spacing="2", width="100%",
            ),
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탭 콘텐츠 라우터
# ══════════════════════════════════════════

def _tab_content() -> rx.Component:
    return rx.box(
        rx.cond(SchoolState.active_tab == "월별현황", _monthly_tab()),
        rx.cond(SchoolState.active_tab == "수거내역", _detail_tab()),
        rx.cond(SchoolState.active_tab == "정산확인", _settlement_tab()),
        rx.cond(SchoolState.active_tab == "ESG보고서", _esg_tab()),
        rx.cond(SchoolState.active_tab == "안전관리보고서", _safety_tab()),
        width="100%",
    )


# ══════════════════════════════════════════
#  메인 페이지
# ══════════════════════════════════════════

def school_page() -> rx.Component:
    """학교 메인 페이지"""
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
