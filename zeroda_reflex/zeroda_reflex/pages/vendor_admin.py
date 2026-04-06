# zeroda_reflex/pages/vendor_admin.py
# 업체관리자 대시보드 — 7개 탭 사이드바 레이아웃
import reflex as rx
from zeroda_reflex.state.vendor_state import VendorState
from zeroda_reflex.state.auth_state import get_year_options, MONTH_OPTIONS
# ── 공통 컴포넌트 import (Phase 0-A 모듈화) ──
from zeroda_reflex.components.shared import (
    kpi_card_icon_box as _kpi_card,           # 업체관리자는 아이콘박스형 KPI
    section_header_badge as _section_header,   # 배지 포함 헤더
    empty_state as _empty_state,
    logo_box as _logo_box,
    table_box as _table_box,
    table_header_row as _table_header,
    card_box as _card_box,                     # 차트용 카드 박스
)

# ── 연/월 선택 옵션 (Phase 0-B: 동적 생성으로 교체) ──
YEAR_OPTIONS = get_year_options()
# MONTH_OPTIONS → auth_state에서 import
WEEKDAYS_FILTER = ["전체", "월", "화", "수", "목", "금", "토"]
SCHED_SUBTABS = ["조회", "등록"]
SETTLE_SUBTABS = ["정산현황", "월말정산", "지출내역"]
SETTLE_TYPE_FILTERS = ["전체", "학교", "기타", "기타2(부가세포함)"]
SCHED_WEEKDAYS = ["월", "화", "수", "목", "금", "토"]
SCHED_ITEMS = ["음식물", "재활용", "일반"]
SCHED_ITEM_FILTERS = ["전체", "음식물", "재활용", "일반"]
CUST_SUBTABS = ["목록", "등록수정"]
CUST_TYPE_OPTIONS = ["학교", "기타", "기타2(부가세포함)"]
CUST_TYPE_FILTERS = ["전체", "학교", "기타", "기타2(부가세포함)"]
SAFETY_SUBTABS = ["안전교육", "차량안전점검", "사고신고", "일일안전점검"]
SETTINGS_SUBTABS = ["업장관리", "업체정보", "계정설정"]
SAFETY_CHECKLIST_LABELS = [
    "타이어·제동장치·오일류",
    "리프트 유압호스·연결부",
    "리프트 비상정지 스위치",
    "리프트 승강구간 이물질",
    "체인·와이어로프 상태",
    "적재함 도어 잠금장치",
    "후진경보음·경광등",
    "사이드브레이크·고임목",
]
EDU_TYPES = ["정기교육", "신규교육", "특별교육"]
EDU_RESULTS = ["이수", "미이수"]
ACC_TYPES = ["교통사고", "작업중사고", "차량고장", "기타"]
ACC_SEVERITIES = ["재산피해", "경상", "중상", "사망"]
DAILY_CATEGORIES = ["전체", "1인작업안전", "보호구위생", "차량장비점검", "중량물상하차"]

# ── 사이드바 메뉴 정의: (탭명, lucide 아이콘) ──
TABS = [
    ("수거현황",   "bar_chart_2"),
    ("수거데이터", "database"),
    ("거래처관리", "building_2"),
    ("일정관리",   "calendar"),
    ("정산관리",   "credit_card"),
    ("안전관리",   "shield_check"),
    ("설정",       "settings"),
]


# ══════════════════════════════════════════════
#  공통 헬퍼
# ══════════════════════════════════════════════

# ── 아래 함수들은 shared.py에서 import (Phase 0-A 모듈화) ──
# _logo_box, _section_header, _empty_state, _table_box, _table_header


# ══════════════════════════════════════════════
#  헤더
# ══════════════════════════════════════════════

def _header() -> rx.Component:
    """상단 헤더: 로고 + 업체명 + 사용자명 + 로그아웃"""
    return rx.box(
        rx.hstack(
            _logo_box(),
            rx.spacer(),
            rx.badge(
                VendorState.user_vendor,
                color_scheme="green",
                size="2",
                variant="soft",
                display=["none", "none", "inline-flex"],
            ),
            rx.text(
                VendorState.user_name,
                font_size="13px",
                color="#475569",
                font_weight="600",
                display=["none", "inline", "inline"],
            ),
            rx.button(
                rx.icon("log_out", size=15),
                rx.text("로그아웃", font_size="13px", display=["none", "none", "inline"]),
                on_click=VendorState.logout,
                variant="ghost",
                color="#94a3b8",
                size="2",
                cursor="pointer",
                _hover={"color": "#64748b"},
            ),
            spacing="3",
            align="center",
            width="100%",
        ),
        bg="white",
        border_bottom="1px solid #e2e8f0",
        padding_x=["16px", "20px", "24px"],
        padding_y="13px",
        position="sticky",
        top="0",
        z_index="100",
        box_shadow="0 1px 4px rgba(0,0,0,0.05)",
    )


# ══════════════════════════════════════════════
#  사이드바 (데스크톱)
# ══════════════════════════════════════════════

def _sidebar_item(label: str, icon: str) -> rx.Component:
    is_active = VendorState.active_tab == label
    return rx.button(
        rx.hstack(
            rx.icon(icon, size=17),
            rx.text(label, font_size="14px"),
            spacing="3",
            align="center",
            width="100%",
        ),
        on_click=VendorState.set_active_tab(label),
        width="100%",
        variant="ghost",
        justify="start",
        padding_x="14px",
        padding_y="10px",
        border_radius="10px",
        bg=rx.cond(is_active, "rgba(56,189,148,0.12)", "transparent"),
        color=rx.cond(is_active, "#38bd94", "#64748b"),
        font_weight=rx.cond(is_active, "700", "500"),
        cursor="pointer",
        _hover={"bg": "rgba(56,189,148,0.08)", "color": "#38bd94"},
    )


def _sidebar() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                "업체관리자",
                font_size="10px",
                font_weight="700",
                color="#94a3b8",
                letter_spacing="1.5px",
                padding_x="14px",
                padding_top="4px",
            ),
            rx.box(height="1px", bg="#e2e8f0", width="100%", margin_y="6px"),
            *[_sidebar_item(label, icon) for label, icon in TABS],
            spacing="1",
            width="100%",
            align="start",
        ),
        width="220px",
        min_width="220px",
        bg="white",
        border_right="1px solid #e2e8f0",
        padding="12px",
        min_height="calc(100vh - 62px)",
        display=["none", "none", "block"],
        flex_shrink="0",
    )


# ══════════════════════════════════════════════
#  모바일 하단 탭바
# ══════════════════════════════════════════════

def _mobile_nav_item(label: str, icon: str) -> rx.Component:
    is_active = VendorState.active_tab == label
    return rx.button(
        rx.vstack(
            rx.icon(icon, size=20),
            rx.text(label, font_size="9px"),
            spacing="1",
            align="center",
        ),
        on_click=VendorState.set_active_tab(label),
        variant="ghost",
        flex="1",
        padding_y="8px",
        padding_x="2px",
        color=rx.cond(is_active, "#38bd94", "#94a3b8"),
        font_weight=rx.cond(is_active, "700", "400"),
        _hover={"color": "#38bd94"},
        cursor="pointer",
        border_radius="0",
        min_width="0",
    )


def _mobile_nav() -> rx.Component:
    return rx.box(
        rx.hstack(
            *[_mobile_nav_item(label, icon) for label, icon in TABS],
            spacing="0",
            width="100%",
        ),
        display=["block", "block", "none"],
        position="fixed",
        bottom="0",
        left="0",
        right="0",
        bg="white",
        border_top="1px solid #e2e8f0",
        z_index="100",
        box_shadow="0 -2px 8px rgba(0,0,0,0.05)",
    )


# ══════════════════════════════════════════════
#  탭1: 수거현황
# ══════════════════════════════════════════════

# _kpi_card → shared.py에서 kpi_card_icon_box로 import (Phase 0-A)


def _school_summary_row(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["school_name"], font_size="13px", color="#1e293b",
                    font_weight="500", flex="2", min_width="0",
                    overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
            rx.hstack(
                rx.text(row["total_weight"], font_size="13px", font_weight="700", color="#0f172a"),
                rx.text("kg", font_size="11px", color="#94a3b8"),
                spacing="1", align="center", justify="end", flex="1",
            ),
            rx.hstack(
                rx.text(row["collect_count"], font_size="13px", font_weight="700", color="#0f172a"),
                rx.text("건", font_size="11px", color="#94a3b8"),
                spacing="1", align="center", justify="end", flex="1",
            ),
            width="100%", padding_x="16px", padding_y="11px", align="center",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


def _school_card(school: dict) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.icon("building_2", size=20, color="#38bd94"),
                width="36px", height="36px", bg="rgba(56,189,148,0.10)",
                border_radius="10px", display="flex",
                align_items="center", justify_content="center",
            ),
            rx.text(school["name"], font_size="12px", font_weight="600",
                    color="#1e293b", text_align="center", width="100%"),
            spacing="2", align="center", width="100%",
        ),
        bg="white", border_radius="12px", padding="14px 10px",
        border="1px solid #e2e8f0", box_shadow="0 1px 3px rgba(0,0,0,0.04)",
        text_align="center", flex="1 1 130px", min_width="130px", max_width="180px",
        _hover={"border_color": "#38bd94", "box_shadow": "0 2px 8px rgba(56,189,148,0.12)"},
        transition="all 0.15s ease",
    )


def _collection_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(YEAR_OPTIONS, value=VendorState.selected_year,
                      on_change=VendorState.set_selected_year, size="2", width="95px"),
            rx.text("년", font_size="13px", color="#64748b"),
            rx.select(MONTH_OPTIONS, value=VendorState.selected_month,
                      on_change=VendorState.set_selected_month, size="2", width="72px"),
            rx.text("월", font_size="13px", color="#64748b"),
            rx.button(
                rx.icon("refresh_cw", size=14),
                rx.text("새로고침", font_size="13px", display=["none", "inline", "inline"]),
                on_click=VendorState.load_dashboard_data,
                size="2", variant="soft", color_scheme="gray", cursor="pointer", gap="6px",
            ),
            rx.spacer(),
            # ── Excel 다운로드 버튼 (Phase 3) ──
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=VendorState.download_collection_excel,
            ),
            spacing="2", align="center",
        ),
        rx.flex(
            _kpi_card("총 수거량",   VendorState.total_weight,        "kg",  "weight",      "#38bd94", "rgba(56,189,148,0.12)"),
            _kpi_card("수거 건수",   VendorState.total_count,         "건",  "truck",       "#3b82f6", "rgba(59,130,246,0.10)"),
            _kpi_card("담당 학교",   VendorState.vendor_school_count, "개교","school",      "#f59e0b", "rgba(245,158,11,0.10)"),
            _kpi_card("학교당 평균", VendorState.avg_weight_per_school,"kg", "bar_chart_2", "#8b5cf6", "rgba(139,92,246,0.10)"),
            gap="12px", flex_wrap="wrap", width="100%",
        ),
        _table_box(
            _table_header(("학교명", "2"), ("수거량", "1"), ("건수", "1")),
            rx.cond(
                VendorState.has_summary,
                rx.box(rx.foreach(VendorState.school_summary, _school_summary_row),
                       max_height="320px", overflow_y="auto"),
                _empty_state("해당 월 수거 데이터가 없습니다."),
            ),
        ),
        # ── 학교별 수거량 차트 (Phase 9) ──
        rx.cond(
            VendorState.has_summary,
            _card_box(
                rx.vstack(
                    _section_header("bar_chart_2", "학교별 수거량 차트"),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="weight_num",
                            fill="#38bd94",
                            name="수거량(kg)",
                        ),
                        rx.recharts.x_axis(data_key="school_name", font_size=10, angle=-30),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.tooltip(),
                        data=VendorState.school_summary,
                        width="100%",
                        height=280,
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        _section_header("building_2", "담당 학교 목록", VendorState.vendor_school_count),
        rx.cond(
            VendorState.has_schools,
            rx.flex(rx.foreach(VendorState.vendor_schools, _school_card),
                    gap="12px", flex_wrap="wrap", width="100%"),
            rx.center(rx.text("담당 학교가 없습니다.", font_size="13px", color="#94a3b8"),
                      padding_y="24px", width="100%"),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭2: 수거데이터
# ══════════════════════════════════════════════

def _col_record_row(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["collect_date"], font_size="12px", color="#64748b",
                    flex="1", min_width="80px"),
            rx.text(row["school_name"], font_size="13px", color="#1e293b",
                    font_weight="500", flex="2", min_width="0",
                    overflow="hidden", text_overflow="ellipsis", white_space="nowrap"),
            rx.badge(row["item_type"], size="1", color_scheme="green",
                     variant="soft", flex_shrink="0"),
            rx.hstack(
                rx.text(row["weight"], font_size="13px", font_weight="700", color="#0f172a"),
                rx.text("kg", font_size="11px", color="#94a3b8"),
                spacing="1", align="center", flex_shrink="0",
            ),
            rx.text(row["driver"], font_size="12px", color="#94a3b8",
                    flex_shrink="0", display=["none", "inline", "inline"]),
            width="100%", padding_x="16px", padding_y="10px",
            align="center", gap="12px",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


COL_SUBTABS = ["수거내역", "수거입력", "처리확인"]
ITEM_TYPE_OPTIONS = ["음식물", "재활용", "일반"]
PROC_STATUS_OPTIONS = ["전체", "submitted", "confirmed", "rejected"]
PROC_STATUS_LABELS = {
    "전체": "전체",
    "submitted": "대기",
    "confirmed": "확인",
    "rejected": "반려",
}


def _col_subtab_btn(label: str) -> rx.Component:
    is_active = VendorState.col_active_subtab == label
    return rx.button(
        label,
        on_click=VendorState.set_col_subtab(label),
        size="2",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
    )


# ── 수거내역 조회 ──

def _col_history_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(YEAR_OPTIONS, value=VendorState.selected_year,
                      on_change=VendorState.set_selected_year, size="2", width="95px"),
            rx.text("년", font_size="13px", color="#64748b"),
            rx.select(MONTH_OPTIONS, value=VendorState.selected_month,
                      on_change=VendorState.set_selected_month, size="2", width="72px"),
            rx.text("월", font_size="13px", color="#64748b"),
            rx.select(
                VendorState.col_school_names,
                value=VendorState.col_school_filter,
                on_change=VendorState.set_col_school_filter,
                size="2", width="150px",
                placeholder="학교 선택",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=VendorState.load_dashboard_data,
                size="2", variant="soft", color_scheme="gray", cursor="pointer",
            ),
            spacing="2", align="center", flex_wrap="wrap",
        ),
        rx.hstack(
            rx.badge(VendorState.total_count, color_scheme="blue", size="2", variant="soft"),
            rx.text("건 조회됨", font_size="13px", color="#64748b"),
            spacing="2", align="center",
        ),
        _table_box(
            rx.box(
                rx.hstack(
                    rx.text("수거일", font_size="12px", font_weight="700", color="#64748b", flex="1"),
                    rx.text("학교명", font_size="12px", font_weight="700", color="#64748b", flex="2"),
                    rx.text("품목",   font_size="12px", font_weight="700", color="#64748b", flex_shrink="0", width="60px"),
                    rx.text("수거량", font_size="12px", font_weight="700", color="#64748b", flex_shrink="0"),
                    rx.text("기사",   font_size="12px", font_weight="700", color="#64748b",
                            flex_shrink="0", display=["none", "inline", "inline"]),
                    width="100%", padding_x="16px", padding_y="10px", gap="12px",
                ),
                bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                border_radius="12px 12px 0 0",
            ),
            rx.cond(
                VendorState.has_collections,
                rx.box(rx.foreach(VendorState.filtered_collections, _col_record_row),
                       max_height="420px", overflow_y="auto"),
                _empty_state("해당 조건의 수거 데이터가 없습니다."),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ── 수거입력 폼 ──

def _col_input_panel() -> rx.Component:
    return rx.box(
        rx.vstack(
            _section_header("circle_plus", "수거 데이터 입력"),
            rx.box(height="1px", bg="#e2e8f0", width="100%"),
            rx.vstack(
                # 거래처 + 수거일
                rx.hstack(
                    rx.vstack(
                        rx.text("거래처 *", font_size="12px", color="#64748b", font_weight="600"),
                        rx.select(
                            VendorState.col_school_names,
                            value=VendorState.form_school,
                            on_change=VendorState.set_form_school,
                            size="3",
                            placeholder="거래처 선택",
                            width="100%",
                        ),
                        spacing="1", align="start", flex="1",
                    ),
                    rx.vstack(
                        rx.text("수거일 *", font_size="12px", color="#64748b", font_weight="600"),
                        rx.input(
                            placeholder="YYYY-MM-DD",
                            value=VendorState.form_date,
                            on_change=VendorState.set_form_date,
                            size="3",
                            width="100%",
                        ),
                        spacing="1", align="start", flex="1",
                    ),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                # 품목 + 수거량
                rx.hstack(
                    rx.vstack(
                        rx.text("품목 *", font_size="12px", color="#64748b", font_weight="600"),
                        rx.select(
                            ITEM_TYPE_OPTIONS,
                            value=VendorState.form_item_type,
                            on_change=VendorState.set_form_item_type,
                            size="3",
                            width="100%",
                        ),
                        spacing="1", align="start", flex="1",
                    ),
                    rx.vstack(
                        rx.text("수거량 (kg) *", font_size="12px", color="#64748b", font_weight="600"),
                        rx.input(
                            placeholder="0.0",
                            value=VendorState.form_weight,
                            on_change=VendorState.set_form_weight,
                            size="3",
                            type="number",
                            width="100%",
                        ),
                        spacing="1", align="start", flex="1",
                    ),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                # 기사 + 메모
                rx.hstack(
                    rx.vstack(
                        rx.text("기사명", font_size="12px", color="#64748b", font_weight="600"),
                        rx.input(
                            placeholder="기사명 입력",
                            value=VendorState.form_driver,
                            on_change=VendorState.set_form_driver,
                            size="3",
                            width="100%",
                        ),
                        spacing="1", align="start", flex="1",
                    ),
                    rx.vstack(
                        rx.text("메모", font_size="12px", color="#64748b", font_weight="600"),
                        rx.input(
                            placeholder="메모 (선택)",
                            value=VendorState.form_memo,
                            on_change=VendorState.set_form_memo,
                            size="3",
                            width="100%",
                        ),
                        spacing="1", align="start", flex="1",
                    ),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                # 저장 버튼
                rx.button(
                    rx.icon("save", size=16),
                    rx.text("저장", font_size="14px"),
                    on_click=VendorState.save_collection_form,
                    size="3",
                    color_scheme="green",
                    width="100%",
                    cursor="pointer",
                    gap="8px",
                ),
                # 결과 메시지
                rx.cond(
                    VendorState.form_save_has_msg,
                    rx.box(
                        rx.hstack(
                            rx.icon(
                                rx.cond(VendorState.form_save_ok, "circle_check", "circle_alert"),
                                size=15,
                                color=rx.cond(VendorState.form_save_ok, "#38bd94", "#ef4444"),
                            ),
                            rx.text(
                                VendorState.form_save_msg,
                                font_size="13px",
                                color=rx.cond(VendorState.form_save_ok, "#38bd94", "#ef4444"),
                                font_weight="500",
                            ),
                            spacing="2", align="center",
                        ),
                        bg=rx.cond(VendorState.form_save_ok,
                                   "rgba(56,189,148,0.08)", "rgba(239,68,68,0.08)"),
                        border=rx.cond(VendorState.form_save_ok,
                                       "1px solid rgba(56,189,148,0.3)",
                                       "1px solid rgba(239,68,68,0.3)"),
                        border_radius="8px",
                        padding="10px 14px",
                        width="100%",
                    ),
                    rx.box(),
                ),
                spacing="4", width="100%",
            ),
            spacing="4", align="start", width="100%",
        ),
        bg="white", border_radius="12px", padding="20px",
        border="1px solid #e2e8f0",
        box_shadow="0 1px 4px rgba(0,0,0,0.04)",
        width="100%", max_width="600px",
    )


# ── 처리확인 (계근표) ──

def _proc_confirm_row(row: dict) -> rx.Component:
    status_color_map = {
        "submitted": "blue",
        "confirmed": "green",
        "rejected":  "red",
    }
    status_label_map = {
        "submitted": "대기",
        "confirmed": "확인",
        "rejected":  "반려",
    }
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text(row["confirm_date"], font_size="12px", color="#64748b"),
                    rx.text(row["confirm_time"], font_size="11px", color="#94a3b8"),
                    spacing="2", align="center",
                ),
                rx.hstack(
                    rx.icon("user", size=11, color="#94a3b8"),
                    rx.text(row["driver"], font_size="12px", color="#475569"),
                    spacing="1", align="center",
                ),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.text(row["total_weight"], font_size="14px",
                        font_weight="700", color="#0f172a"),
                rx.text("kg", font_size="11px", color="#94a3b8"),
                spacing="1", align="center",
            ),
            rx.badge(
                status_label_map.get(row["status"], row["status"]),
                color_scheme=status_color_map.get(row["status"], "gray"),
                size="1", variant="soft",
            ),
            rx.cond(
                row["status"] == "submitted",
                rx.hstack(
                    rx.button(
                        rx.icon("check", size=13),
                        rx.text("승인", font_size="12px"),
                        on_click=VendorState.confirm_processing(row["id"]),
                        size="1", color_scheme="green", variant="soft",
                        cursor="pointer", gap="4px",
                    ),
                    rx.button(
                        rx.icon("x", size=13),
                        rx.text("반려", font_size="12px"),
                        on_click=VendorState.reject_processing(row["id"]),
                        size="1", color_scheme="red", variant="soft",
                        cursor="pointer", gap="4px",
                    ),
                    spacing="2",
                ),
                rx.box(),
            ),
            width="100%", padding_x="16px", padding_y="12px",
            align="center", gap="12px",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


def _col_confirm_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(
                PROC_STATUS_OPTIONS,
                value=VendorState.proc_status_filter,
                on_change=VendorState.set_proc_status_filter,
                size="2", width="110px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                rx.text("새로고침", font_size="13px"),
                on_click=VendorState.load_processing_confirms,
                size="2", variant="soft", color_scheme="gray",
                cursor="pointer", gap="6px",
            ),
            spacing="2", align="center",
        ),
        _table_box(
            rx.box(
                rx.hstack(
                    rx.text("처리일시 / 기사", font_size="12px", font_weight="700",
                            color="#64748b", flex="1"),
                    rx.text("처리량",          font_size="12px", font_weight="700",
                            color="#64748b", flex_shrink="0"),
                    rx.text("상태",            font_size="12px", font_weight="700",
                            color="#64748b", flex_shrink="0"),
                    rx.text("처리",            font_size="12px", font_weight="700",
                            color="#64748b", flex_shrink="0"),
                    width="100%", padding_x="16px", padding_y="10px", gap="12px",
                ),
                bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                border_radius="12px 12px 0 0",
            ),
            rx.cond(
                VendorState.has_processing_confirms,
                rx.box(
                    rx.foreach(VendorState.filtered_processing_confirms, _proc_confirm_row),
                    max_height="420px", overflow_y="auto",
                ),
                _empty_state("처리확인 데이터가 없습니다."),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ── 수거데이터 탭 (서브탭 라우터) ──

def _collection_data_tab() -> rx.Component:
    return rx.vstack(
        # 서브탭 전환 버튼
        rx.hstack(
            *[_col_subtab_btn(label) for label in COL_SUBTABS],
            spacing="2",
        ),
        rx.box(height="1px", bg="#e2e8f0", width="100%"),
        # 서브탭 콘텐츠
        rx.cond(
            VendorState.col_active_subtab == "수거내역",
            _col_history_panel(),
            rx.cond(
                VendorState.col_active_subtab == "수거입력",
                _col_input_panel(),
                _col_confirm_panel(),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭3: 거래처관리
# ══════════════════════════════════════════════

def _cust_subtab_btn(label: str) -> rx.Component:
    is_active = VendorState.cust_active_subtab == label
    return rx.button(
        label,
        on_click=VendorState.set_cust_subtab(label),
        size="2",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
    )


def _cust_type_filter_btn(t: str) -> rx.Component:
    is_active = VendorState.filter_cust_type == t
    return rx.button(
        t,
        on_click=VendorState.set_filter_cust_type(t),
        size="1",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="6px",
    )


def _cust_list_row(cust: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(cust["name"], font_size="13px", font_weight="600", color="#1e293b"),
        ),
        rx.table.cell(
            rx.badge(cust["cust_type"], size="1", color_scheme="blue", variant="soft"),
        ),
        rx.table.cell(
            rx.text(cust["ceo"], font_size="13px", color="#475569"),
        ),
        rx.table.cell(
            rx.text(cust["phone"], font_size="13px", color="#475569"),
        ),
        rx.table.cell(
            rx.hstack(
                rx.text("음식", font_size="11px", color="#94a3b8"),
                rx.text(cust["price_food"], font_size="12px", font_weight="600", color="#1e293b"),
                rx.text("원", font_size="11px", color="#94a3b8"),
                spacing="1", align="center",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.button(
                    rx.icon("pencil", size=13),
                    on_click=VendorState.select_cust_for_edit(cust["name"]),
                    size="1", variant="soft", color_scheme="blue", cursor="pointer",
                ),
                rx.button(
                    rx.icon("trash_2", size=13),
                    on_click=VendorState.delete_cust(cust["name"]),
                    size="1", variant="soft", color_scheme="red", cursor="pointer",
                ),
                spacing="2",
            ),
        ),
        _hover={"bg": "#f8fafc"},
    )


def _cust_list_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.foreach(CUST_TYPE_FILTERS, _cust_type_filter_btn),
            rx.spacer(),
            rx.button(
                rx.icon("refresh_cw", size=14),
                rx.text("새로고침", font_size="13px"),
                on_click=VendorState.load_customers,
                size="2", variant="soft", color_scheme="gray", cursor="pointer", gap="6px",
            ),
            spacing="2", align="center", width="100%",
        ),
        rx.cond(
            VendorState.cust_delete_has_msg,
            rx.callout(
                VendorState.cust_delete_msg,
                icon="info",
                color_scheme=rx.cond(VendorState.cust_save_ok, "green", "red"),
                size="1",
            ),
            rx.box(),
        ),
        rx.cond(
            VendorState.has_filtered_customers,
            _table_box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _table_header("이름"),
                            _table_header("구분"),
                            _table_header("대표자"),
                            _table_header("전화"),
                            _table_header("음식 단가"),
                            _table_header(""),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(VendorState.filtered_customers, _cust_list_row),
                    ),
                    width="100%",
                ),
            ),
            _empty_state("조건에 맞는 거래처가 없습니다."),
        ),
        spacing="4", width="100%", align="start",
    )


def _cust_form_panel() -> rx.Component:
    field_label_style = {"font_size": "12px", "color": "#64748b", "font_weight": "600", "min_width": "90px"}
    return rx.vstack(
        rx.hstack(
            rx.badge(
                VendorState.cust_form_mode_label,
                size="2",
                color_scheme=rx.cond(VendorState.edit_mode, "orange", "green"),
                variant="soft",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("x", size=14),
                rx.text("초기화", font_size="13px"),
                on_click=VendorState.clear_cust_form,
                size="2", variant="soft", color_scheme="gray", cursor="pointer", gap="6px",
            ),
            align="center", width="100%",
        ),
        rx.box(height="1px", bg="#e2e8f0", width="100%"),

        # ── 거래처명 ──
        rx.hstack(
            rx.text("거래처명 *", **field_label_style),
            rx.input(
                placeholder="거래처명",
                value=VendorState.cust_name,
                on_change=VendorState.set_cust_name,
                size="2", width="100%", is_disabled=VendorState.edit_mode,
            ),
            align="center", width="100%", spacing="3",
        ),

        # ── 구분 ──
        rx.hstack(
            rx.text("구분 *", **field_label_style),
            rx.select(
                CUST_TYPE_OPTIONS,
                value=VendorState.cust_type,
                on_change=VendorState.set_cust_type,
                size="2", width="100%",
            ),
            align="center", width="100%", spacing="3",
        ),

        # ── 사업자번호 / 대표자 ──
        rx.hstack(
            rx.hstack(
                rx.text("사업자번호", **field_label_style),
                rx.input(
                    placeholder="000-00-00000",
                    value=VendorState.cust_biz_no,
                    on_change=VendorState.set_cust_biz_no,
                    size="2", width="100%",
                ),
                align="center", spacing="3", flex="1",
            ),
            rx.hstack(
                rx.text("대표자", **field_label_style),
                rx.input(
                    placeholder="대표자명",
                    value=VendorState.cust_ceo,
                    on_change=VendorState.set_cust_ceo,
                    size="2", width="100%",
                ),
                align="center", spacing="3", flex="1",
            ),
            spacing="4", width="100%",
        ),

        # ── 주소 ──
        rx.hstack(
            rx.text("주소", **field_label_style),
            rx.input(
                placeholder="주소",
                value=VendorState.cust_addr,
                on_change=VendorState.set_cust_addr,
                size="2", width="100%",
            ),
            align="center", width="100%", spacing="3",
        ),

        # ── 업태 / 종목 ──
        rx.hstack(
            rx.hstack(
                rx.text("업태", **field_label_style),
                rx.input(
                    placeholder="업태",
                    value=VendorState.cust_biz_type,
                    on_change=VendorState.set_cust_biz_type,
                    size="2", width="100%",
                ),
                align="center", spacing="3", flex="1",
            ),
            rx.hstack(
                rx.text("종목", **field_label_style),
                rx.input(
                    placeholder="종목",
                    value=VendorState.cust_biz_item,
                    on_change=VendorState.set_cust_biz_item,
                    size="2", width="100%",
                ),
                align="center", spacing="3", flex="1",
            ),
            spacing="4", width="100%",
        ),

        # ── 이메일 / 전화번호 ──
        rx.hstack(
            rx.hstack(
                rx.text("이메일", **field_label_style),
                rx.input(
                    placeholder="example@email.com",
                    value=VendorState.cust_email,
                    on_change=VendorState.set_cust_email,
                    size="2", width="100%",
                ),
                align="center", spacing="3", flex="1",
            ),
            rx.hstack(
                rx.text("전화번호", **field_label_style),
                rx.input(
                    placeholder="000-0000-0000",
                    value=VendorState.cust_phone,
                    on_change=VendorState.set_cust_phone,
                    size="2", width="100%",
                ),
                align="center", spacing="3", flex="1",
            ),
            spacing="4", width="100%",
        ),

        # ── 재활용자 ──
        rx.hstack(
            rx.text("재활용자", **field_label_style),
            rx.input(
                placeholder="재활용업체명",
                value=VendorState.cust_recycler,
                on_change=VendorState.set_cust_recycler,
                size="2", width="100%",
            ),
            align="center", width="100%", spacing="3",
        ),

        rx.box(height="1px", bg="#e2e8f0", width="100%"),

        # ── 단가 (음식물 / 재활용 / 일반) ──
        rx.hstack(
            rx.hstack(
                rx.text("음식물 단가", **field_label_style),
                rx.input(
                    placeholder="0",
                    value=VendorState.cust_price_food,
                    on_change=VendorState.set_cust_price_food,
                    size="2", width="100%", type="number",
                ),
                align="center", spacing="3", flex="1",
            ),
            rx.hstack(
                rx.text("재활용 단가", **field_label_style),
                rx.input(
                    placeholder="0",
                    value=VendorState.cust_price_recycle,
                    on_change=VendorState.set_cust_price_recycle,
                    size="2", width="100%", type="number",
                ),
                align="center", spacing="3", flex="1",
            ),
            rx.hstack(
                rx.text("일반 단가", **field_label_style),
                rx.input(
                    placeholder="0",
                    value=VendorState.cust_price_general,
                    on_change=VendorState.set_cust_price_general,
                    size="2", width="100%", type="number",
                ),
                align="center", spacing="3", flex="1",
            ),
            spacing="4", width="100%",
        ),

        # ── 월정액 (기타 타입만) ──
        rx.cond(
            VendorState.cust_is_other_type,
            rx.hstack(
                rx.text("월정액", **field_label_style),
                rx.input(
                    placeholder="0",
                    value=VendorState.cust_fixed_fee,
                    on_change=VendorState.set_cust_fixed_fee,
                    size="2", width="100%", type="number",
                ),
                align="center", width="100%", spacing="3",
            ),
            rx.box(),
        ),

        # ── NEIS 코드 (학교 타입만) ──
        rx.cond(
            VendorState.cust_is_school_type,
            rx.hstack(
                rx.hstack(
                    rx.text("NEIS 교육청", **field_label_style),
                    rx.input(
                        placeholder="교육청 코드",
                        value=VendorState.cust_neis_edu,
                        on_change=VendorState.set_cust_neis_edu,
                        size="2", width="100%",
                    ),
                    align="center", spacing="3", flex="1",
                ),
                rx.hstack(
                    rx.text("NEIS 학교", **field_label_style),
                    rx.input(
                        placeholder="학교 코드",
                        value=VendorState.cust_neis_school,
                        on_change=VendorState.set_cust_neis_school,
                        size="2", width="100%",
                    ),
                    align="center", spacing="3", flex="1",
                ),
                spacing="4", width="100%",
            ),
            rx.box(),
        ),

        rx.box(height="1px", bg="#e2e8f0", width="100%"),

        # ── 저장 메시지 ──
        rx.cond(
            VendorState.cust_save_has_msg,
            rx.callout(
                VendorState.cust_save_msg,
                icon="info",
                color_scheme=rx.cond(VendorState.cust_save_ok, "green", "red"),
                size="1",
            ),
            rx.box(),
        ),

        # ── 저장 버튼 ──
        rx.hstack(
            rx.button(
                rx.icon("save", size=15),
                rx.text("저장", font_size="14px"),
                on_click=VendorState.save_cust_form,
                size="3", color_scheme="green", cursor="pointer", gap="6px",
            ),
            spacing="3",
        ),

        spacing="3", width="100%", align="start",
        bg="white", border_radius="12px", padding="20px",
        border="1px solid #e2e8f0",
    )


def _customer_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + Excel 다운로드 (Phase 3) ──
        rx.hstack(
            _section_header("building_2", "거래처관리", VendorState.vendor_school_count),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=VendorState.download_customer_excel,
            ),
            width="100%", align="center",
        ),
        rx.hstack(
            rx.foreach(CUST_SUBTABS, _cust_subtab_btn),
            spacing="2",
        ),
        rx.cond(
            VendorState.cust_active_subtab == "목록",
            _cust_list_panel(),
            _cust_form_panel(),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭4: 일정관리
# ══════════════════════════════════════════════

def _weekday_filter_btn(day: str) -> rx.Component:
    is_active = VendorState.sched_day_filter == day
    return rx.button(
        day,
        on_click=VendorState.set_sched_day_filter(day),
        size="2",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
        min_width="44px",
    )


def _sched_subtab_btn(label: str) -> rx.Component:
    is_active = VendorState.sched_active_subtab == label
    return rx.button(
        label,
        on_click=VendorState.set_sched_subtab(label),
        size="2",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
    )


def _sched_item_filter_btn(item: str) -> rx.Component:
    is_active = VendorState.sched_item_filter == item
    return rx.button(
        item,
        on_click=VendorState.set_sched_item_filter(item),
        size="1",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="6px",
    )


def _sched_card(sched: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.icon("calendar", size=13, color="#38bd94"),
                    rx.text(sched["month_key"], font_size="13px",
                            font_weight="600", color="#1e293b"),
                    spacing="1", align="center",
                ),
                rx.cond(
                    sched["weekdays"] != "",
                    rx.hstack(
                        rx.icon("clock", size=11, color="#94a3b8"),
                        rx.text(sched["weekdays"], font_size="11px", color="#64748b"),
                        spacing="1", align="center",
                    ),
                    rx.box(height="0"),
                ),
                rx.cond(
                    sched["items"] != "",
                    rx.badge(sched["items"], size="1",
                             color_scheme="green", variant="soft"),
                    rx.box(height="0"),
                ),
                spacing="1", align="start",
            ),
            rx.spacer(),
            rx.vstack(
                rx.cond(
                    sched["driver"] != "",
                    rx.hstack(
                        rx.icon("user", size=11, color="#94a3b8"),
                        rx.text(sched["driver"], font_size="11px", color="#64748b"),
                        spacing="1", align="center",
                    ),
                    rx.box(height="0"),
                ),
                rx.cond(
                    sched["schools"] != "",
                    rx.text(
                        sched["schools"],
                        font_size="11px", color="#64748b",
                        max_width="200px", overflow="hidden",
                        text_overflow="ellipsis", white_space="nowrap",
                    ),
                    rx.box(height="0"),
                ),
                rx.cond(
                    sched["registered_by"] == "vendor",
                    rx.button(
                        rx.icon("trash_2", size=13),
                        on_click=VendorState.delete_schedule_handler(sched["id"]),
                        size="1", variant="soft", color_scheme="red", cursor="pointer",
                    ),
                    rx.text("본사 등록", font_size="10px", color="#94a3b8"),
                ),
                spacing="2", align="end",
            ),
            width="100%", padding_x="16px", padding_y="12px", align="center",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


def _sched_view_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            *[_weekday_filter_btn(d) for d in WEEKDAYS_FILTER],
            spacing="2", flex_wrap="wrap",
        ),
        rx.hstack(
            *[_sched_item_filter_btn(t) for t in SCHED_ITEM_FILTERS],
            spacing="2",
        ),
        rx.hstack(
            rx.button(
                rx.icon("refresh_cw", size=14),
                rx.text("새로고침", font_size="13px"),
                on_click=VendorState.load_schedules,
                size="2", variant="soft", color_scheme="gray", cursor="pointer", gap="6px",
            ),
            rx.spacer(),
            align="center", width="100%",
        ),
        _table_box(
            rx.box(
                rx.hstack(
                    rx.text("일정(월/일)", font_size="12px", font_weight="700",
                            color="#64748b", flex="1"),
                    rx.text("요일 / 품목", font_size="12px", font_weight="700",
                            color="#64748b"),
                    rx.text("기사 / 거래처", font_size="12px", font_weight="700",
                            color="#64748b", text_align="right", flex="1"),
                    width="100%", padding_x="16px", padding_y="10px",
                ),
                bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                border_radius="12px 12px 0 0",
            ),
            rx.cond(
                VendorState.has_schedules,
                rx.box(
                    rx.foreach(VendorState.filtered_schedules, _sched_card),
                    max_height="460px", overflow_y="auto",
                ),
                _empty_state("등록된 수거 일정이 없습니다."),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


def _sched_school_btn(school: dict) -> rx.Component:
    is_selected = VendorState.sched_form_schools.contains(school["name"])
    return rx.button(
        school["name"],
        on_click=VendorState.toggle_sched_school(school["name"]),
        size="1",
        variant=rx.cond(is_selected, "solid", "outline"),
        color_scheme=rx.cond(is_selected, "green", "gray"),
        cursor="pointer",
        border_radius="6px",
    )


def _sched_weekday_btn_form(day: str) -> rx.Component:
    is_selected = VendorState.sched_form_weekdays.contains(day)
    return rx.button(
        day,
        on_click=VendorState.toggle_sched_weekday(day),
        size="2",
        variant=rx.cond(is_selected, "solid", "outline"),
        color_scheme=rx.cond(is_selected, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
        min_width="44px",
    )


def _sched_item_btn_form(item: str) -> rx.Component:
    is_selected = VendorState.sched_form_items.contains(item)
    return rx.button(
        item,
        on_click=VendorState.toggle_sched_item(item),
        size="2",
        variant=rx.cond(is_selected, "solid", "outline"),
        color_scheme=rx.cond(is_selected, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
    )


def _sched_form_panel() -> rx.Component:
    label_style = {"font_size": "12px", "color": "#64748b", "font_weight": "600"}
    return rx.vstack(
        # ── 등록 모드 선택 ──
        rx.hstack(
            rx.button(
                rx.icon("calendar", size=14),
                rx.text("월반복", font_size="13px"),
                on_click=VendorState.set_schedule_mode("monthly"),
                size="2",
                variant=rx.cond(VendorState.sched_is_daily_mode, "outline", "solid"),
                color_scheme=rx.cond(VendorState.sched_is_daily_mode, "gray", "blue"),
                cursor="pointer", gap="6px",
            ),
            rx.button(
                rx.icon("calendar_days", size=14),
                rx.text("특정일", font_size="13px"),
                on_click=VendorState.set_schedule_mode("daily"),
                size="2",
                variant=rx.cond(VendorState.sched_is_daily_mode, "solid", "outline"),
                color_scheme=rx.cond(VendorState.sched_is_daily_mode, "blue", "gray"),
                cursor="pointer", gap="6px",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("x", size=14),
                rx.text("초기화", font_size="13px"),
                on_click=VendorState.clear_sched_form,
                size="2", variant="soft", color_scheme="gray", cursor="pointer", gap="6px",
            ),
            spacing="2", align="center", width="100%",
        ),

        rx.box(height="1px", bg="#e2e8f0", width="100%"),

        # ── 월/일 선택 ──
        rx.cond(
            VendorState.sched_is_daily_mode,
            rx.hstack(
                rx.text("수거 날짜 *", **label_style, min_width="80px"),
                rx.input(
                    type="date",
                    value=VendorState.sched_form_date,
                    on_change=VendorState.set_sched_form_date,
                    size="2",
                ),
                align="center", spacing="3",
            ),
            rx.hstack(
                rx.select(
                    YEAR_OPTIONS,
                    value=VendorState.sched_form_year,
                    on_change=VendorState.set_sched_form_year,
                    size="2", width="95px",
                ),
                rx.text("년", font_size="13px", color="#64748b"),
                rx.select(
                    MONTH_OPTIONS,
                    value=VendorState.sched_form_month,
                    on_change=VendorState.set_sched_form_month,
                    size="2", width="72px",
                ),
                rx.text("월", font_size="13px", color="#64748b"),
                spacing="2", align="center",
            ),
        ),

        # ── 수거 요일 (월반복만 표시) ──
        rx.cond(
            VendorState.sched_is_daily_mode,
            rx.box(),
            rx.vstack(
                rx.text("수거 요일 *", **label_style),
                rx.hstack(
                    *[_sched_weekday_btn_form(d) for d in SCHED_WEEKDAYS],
                    spacing="2", flex_wrap="wrap",
                ),
                spacing="2", align="start", width="100%",
            ),
        ),

        # ── 담당 거래처 ──
        rx.vstack(
            rx.text("담당 거래처 *", **label_style),
            rx.box(
                rx.flex(
                    rx.foreach(VendorState.vendor_schools, _sched_school_btn),
                    gap="6px", flex_wrap="wrap",
                ),
                max_height="150px", overflow_y="auto",
                border="1px solid #e2e8f0", border_radius="8px",
                padding="8px", width="100%",
            ),
            spacing="2", align="start", width="100%",
        ),

        # ── 수거 품목 ──
        rx.vstack(
            rx.text("수거 품목 *", **label_style),
            rx.hstack(
                *[_sched_item_btn_form(item) for item in SCHED_ITEMS],
                spacing="2",
            ),
            spacing="2", align="start",
        ),

        # ── 담당 기사 ──
        rx.hstack(
            rx.text("담당 기사", **label_style, min_width="80px"),
            rx.select(
                VendorState.sched_driver_options,
                value=VendorState.sched_form_driver,
                on_change=VendorState.set_sched_form_driver,
                size="2", width="100%",
            ),
            align="center", spacing="3", width="100%",
        ),

        rx.box(height="1px", bg="#e2e8f0", width="100%"),

        # ── 저장 메시지 ──
        rx.cond(
            VendorState.sched_save_has_msg,
            rx.callout(
                VendorState.sched_save_msg,
                icon="info",
                color_scheme=rx.cond(VendorState.sched_save_ok, "green", "red"),
                size="1",
            ),
            rx.box(),
        ),

        # ── 저장 버튼 ──
        rx.button(
            rx.icon("save", size=15),
            rx.text("일정 저장", font_size="14px"),
            on_click=VendorState.save_schedule_form,
            size="3", color_scheme="green", cursor="pointer", gap="6px",
        ),

        spacing="3", width="100%", align="start",
        bg="white", border_radius="12px", padding="20px",
        border="1px solid #e2e8f0",
    )


def _schedule_tab() -> rx.Component:
    return rx.vstack(
        _section_header("calendar", "일정관리"),
        rx.hstack(
            *[_sched_subtab_btn(label) for label in SCHED_SUBTABS],
            spacing="2",
        ),
        rx.cond(
            VendorState.sched_active_subtab == "조회",
            _sched_view_panel(),
            _sched_form_panel(),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭5: 정산관리
# ══════════════════════════════════════════════

def _settle_subtab_btn(label: str) -> rx.Component:
    is_active = VendorState.settle_active_subtab == label
    return rx.button(
        label,
        on_click=VendorState.set_settle_subtab(label),
        size="2",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="8px",
    )


def _settle_type_filter_btn(t: str) -> rx.Component:
    is_active = VendorState.settle_filter_type == t
    return rx.button(
        t,
        on_click=VendorState.set_settle_filter_type(t),
        size="1",
        variant=rx.cond(is_active, "solid", "outline"),
        color_scheme=rx.cond(is_active, "green", "gray"),
        cursor="pointer",
        border_radius="6px",
    )


def _settlement_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(row["name"], font_size="13px", font_weight="600", color="#1e293b"),
        ),
        rx.table.cell(
            rx.badge(row["cust_type"], size="1", color_scheme="blue", variant="soft"),
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(row["weight"], font_size="13px", color="#475569"),
                rx.text("kg", font_size="11px", color="#94a3b8"),
                spacing="1", align="center",
            ),
        ),
        rx.table.cell(
            rx.text(row["supply"], font_size="13px", color="#475569"),
        ),
        rx.table.cell(
            rx.text(row["vat"], font_size="13px", color="#94a3b8"),
        ),
        rx.table.cell(
            rx.text(row["total"], font_size="13px", font_weight="700", color="#0f172a"),
        ),
        _hover={"bg": "#f8fafc"},
    )


def _expense_row(row: dict) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(row["item"], font_size="13px", font_weight="600", color="#1e293b"),
        ),
        rx.table.cell(
            rx.hstack(
                rx.text(row["amount"], font_size="13px", color="#475569"),
                rx.text("원", font_size="11px", color="#94a3b8"),
                spacing="1", align="center",
            ),
        ),
        rx.table.cell(
            rx.text(row["pay_date"], font_size="12px", color="#64748b"),
        ),
        rx.table.cell(
            rx.text(row["memo"], font_size="12px", color="#94a3b8"),
        ),
        rx.table.cell(
            rx.button(
                rx.icon("trash_2", size=13),
                on_click=VendorState.delete_expense_handler(row["id"]),
                size="1", variant="soft", color_scheme="red", cursor="pointer",
            ),
        ),
        _hover={"bg": "#f8fafc"},
    )


def _settle_summary_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(YEAR_OPTIONS, value=VendorState.selected_year,
                      on_change=VendorState.set_selected_year, size="2", width="95px"),
            rx.text("년", font_size="13px", color="#64748b"),
            rx.select(MONTH_OPTIONS, value=VendorState.selected_month,
                      on_change=VendorState.set_selected_month, size="2", width="72px"),
            rx.text("월", font_size="13px", color="#64748b"),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=VendorState.load_settlement,
                size="2", variant="soft", color_scheme="gray", cursor="pointer",
            ),
            spacing="2", align="center",
        ),
        rx.flex(
            _kpi_card("총 수거량",   VendorState.total_weight,   "kg", "weight",      "#38bd94", "rgba(56,189,148,0.12)"),
            _kpi_card("공급가 합계", VendorState.total_revenue,  "원", "credit_card",  "#8b5cf6", "rgba(139,92,246,0.10)"),
            _kpi_card("거래처 수",   VendorState.school_count,   "곳", "building_2",   "#f59e0b", "rgba(245,158,11,0.10)"),
            gap="12px", flex_wrap="wrap", width="100%",
        ),
        _section_header("list", "거래처별 정산 요약"),
        rx.cond(
            VendorState.has_settlement_data,
            _table_box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _table_header("거래처"),
                            _table_header("구분"),
                            _table_header("수거량"),
                            _table_header("공급가"),
                            _table_header("부가세"),
                            _table_header("합계"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(VendorState.settlement_data, _settlement_row),
                    ),
                    width="100%",
                ),
            ),
            _empty_state("해당 월 정산 데이터가 없습니다."),
        ),
        spacing="4", width="100%", align="start",
    )


def _settle_monthly_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(YEAR_OPTIONS, value=VendorState.selected_year,
                      on_change=VendorState.set_selected_year, size="2", width="95px"),
            rx.text("년", font_size="13px", color="#64748b"),
            rx.select(MONTH_OPTIONS, value=VendorState.selected_month,
                      on_change=VendorState.set_selected_month, size="2", width="72px"),
            rx.text("월", font_size="13px", color="#64748b"),
            spacing="2", align="center",
        ),
        rx.hstack(
            *[_settle_type_filter_btn(t) for t in SETTLE_TYPE_FILTERS],
            spacing="2", flex_wrap="wrap",
        ),
        _section_header("receipt", "수입 내역"),
        rx.cond(
            VendorState.has_filtered_settlement,
            _table_box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _table_header("거래처"),
                            _table_header("구분"),
                            _table_header("수거량"),
                            _table_header("공급가"),
                            _table_header("부가세"),
                            _table_header("합계"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(VendorState.filtered_settlement, _settlement_row),
                    ),
                    width="100%",
                ),
            ),
            _empty_state("해당 조건의 정산 데이터가 없습니다."),
        ),
        rx.box(height="1px", bg="#e2e8f0", width="100%"),
        rx.flex(
            _kpi_card("총 수입",   VendorState.total_revenue, "원", "trending_up",   "#38bd94", "rgba(56,189,148,0.12)"),
            _kpi_card("총 지출",   VendorState.total_expense, "원", "trending_down",  "#ef4444", "rgba(239,68,68,0.10)"),
            _kpi_card("순이익",    VendorState.net_profit,    "원", "circle_dollar_sign", "#3b82f6", "rgba(59,130,246,0.10)"),
            gap="12px", flex_wrap="wrap", width="100%",
        ),
        spacing="4", width="100%", align="start",
    )


def _settle_expense_panel() -> rx.Component:
    field_label_style = {"font_size": "12px", "color": "#64748b", "font_weight": "600", "min_width": "80px"}
    return rx.vstack(
        rx.hstack(
            rx.select(YEAR_OPTIONS, value=VendorState.selected_year,
                      on_change=VendorState.set_selected_year, size="2", width="95px"),
            rx.text("년", font_size="13px", color="#64748b"),
            rx.select(MONTH_OPTIONS, value=VendorState.selected_month,
                      on_change=VendorState.set_selected_month, size="2", width="72px"),
            rx.text("월", font_size="13px", color="#64748b"),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=VendorState.load_expenses,
                size="2", variant="soft", color_scheme="gray", cursor="pointer",
            ),
            spacing="2", align="center",
        ),

        # ── 지출 등록 폼 ──
        rx.vstack(
            rx.hstack(
                rx.hstack(
                    rx.text("항목명 *", **field_label_style),
                    rx.input(
                        placeholder="예: 차량할부, 유류비",
                        value=VendorState.exp_name,
                        on_change=VendorState.set_exp_name,
                        size="2", width="100%",
                    ),
                    align="center", spacing="3", flex="1",
                ),
                rx.hstack(
                    rx.text("금액", **field_label_style),
                    rx.input(
                        placeholder="0",
                        value=VendorState.exp_amount,
                        on_change=VendorState.set_exp_amount,
                        size="2", width="100%", type="number",
                    ),
                    rx.text("원", font_size="13px", color="#64748b"),
                    align="center", spacing="2", flex="1",
                ),
                spacing="4", width="100%",
            ),
            rx.hstack(
                rx.hstack(
                    rx.text("결제일", **field_label_style),
                    rx.input(
                        placeholder="예: 5일, 매월10일",
                        value=VendorState.exp_date,
                        on_change=VendorState.set_exp_date,
                        size="2", width="100%",
                    ),
                    align="center", spacing="3", flex="1",
                ),
                rx.hstack(
                    rx.text("메모", **field_label_style),
                    rx.input(
                        placeholder="비고",
                        value=VendorState.exp_memo,
                        on_change=VendorState.set_exp_memo,
                        size="2", width="100%",
                    ),
                    align="center", spacing="3", flex="1",
                ),
                spacing="4", width="100%",
            ),
            rx.cond(
                VendorState.exp_save_has_msg,
                rx.callout(
                    VendorState.exp_save_msg,
                    icon="info",
                    color_scheme=rx.cond(VendorState.exp_save_ok, "green", "red"),
                    size="1",
                ),
                rx.box(),
            ),
            rx.button(
                rx.icon("plus", size=15),
                rx.text("지출 등록", font_size="14px"),
                on_click=VendorState.save_expense_form,
                size="3", color_scheme="blue", cursor="pointer", gap="6px",
            ),
            spacing="3", width="100%",
            bg="white", border_radius="12px", padding="16px",
            border="1px solid #e2e8f0",
        ),

        # ── 지출 목록 ──
        _section_header("list", "지출 내역"),
        rx.cond(
            VendorState.has_expenses,
            _table_box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _table_header("항목"),
                            _table_header("금액"),
                            _table_header("결제일"),
                            _table_header("메모"),
                            _table_header(""),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(VendorState.expenses_list, _expense_row),
                    ),
                    width="100%",
                ),
            ),
            _empty_state("등록된 지출 내역이 없습니다."),
        ),
        spacing="4", width="100%", align="start",
    )


def _settlement_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF/Excel 다운로드 ──
        rx.hstack(
            _section_header("credit_card", "정산관리"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=VendorState.download_statement_pdf,
            ),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=VendorState.download_settlement_excel,
            ),
            width="100%", align="center",
        ),
        rx.hstack(
            *[_settle_subtab_btn(label) for label in SETTLE_SUBTABS],
            spacing="2",
        ),
        # ── 이메일 발송 (Phase 6) ──
        rx.box(
            rx.hstack(
                rx.icon("mail", size=14, color="#64748b"),
                rx.input(
                    value=VendorState.email_to,
                    on_change=VendorState.set_email_to,
                    placeholder="수신 이메일",
                    size="1", width="200px",
                ),
                rx.button(
                    rx.cond(VendorState.email_sending, rx.spinner(size="1"), rx.icon("send", size=12)),
                    "발송",
                    size="1", color_scheme="blue", variant="soft",
                    on_click=VendorState.send_statement_email,
                    loading=VendorState.email_sending,
                ),
                rx.cond(
                    VendorState.email_msg != "",
                    rx.text(
                        VendorState.email_msg,
                        font_size="11px",
                        color=rx.cond(VendorState.email_ok, "#22c55e", "#ef4444"),
                    ),
                ),
                spacing="2", align="center",
            ),
            padding="8px 0",
        ),
        # ── SMS 발송 (Phase 8) ──
        rx.box(
            rx.hstack(
                rx.icon("message_square", size=14, color="#64748b"),
                rx.input(
                    value=VendorState.sms_to,
                    on_change=VendorState.set_sms_to,
                    placeholder="수신 전화번호 (예: 010-1234-5678)",
                    size="1", width="220px",
                ),
                rx.button(
                    rx.cond(VendorState.sms_sending, rx.spinner(size="1"), rx.icon("smartphone", size=12)),
                    "문자발송",
                    size="1", color_scheme="green", variant="soft",
                    on_click=VendorState.send_statement_sms,
                    loading=VendorState.sms_sending,
                ),
                rx.cond(
                    VendorState.sms_msg != "",
                    rx.text(
                        VendorState.sms_msg,
                        font_size="11px",
                        color=rx.cond(VendorState.sms_ok, "#22c55e", "#ef4444"),
                    ),
                ),
                spacing="2", align="center",
            ),
            padding="4px 0",
        ),
        rx.cond(
            VendorState.settle_active_subtab == "정산현황",
            _settle_summary_panel(),
            rx.cond(
                VendorState.settle_active_subtab == "월말정산",
                _settle_monthly_panel(),
                _settle_expense_panel(),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭6: 안전관리
# ══════════════════════════════════════════════

def _edu_row(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["edu_date"], font_size="12px", color="#64748b",
                    flex_shrink="0", width="90px"),
            rx.text(row["driver"], font_size="13px", color="#1e293b",
                    font_weight="500", flex="1"),
            rx.badge(row["edu_type"], size="1", color_scheme="blue",
                     variant="soft", flex_shrink="0"),
            rx.badge(row["result"], size="1",
                     color_scheme=rx.cond(row["result"] == "이수", "green", "red"),
                     variant="soft", flex_shrink="0"),
            rx.text(row["edu_hours"], font_size="12px", color="#64748b",
                    flex_shrink="0", display=["none", "inline", "inline"]),
            width="100%", padding_x="16px", padding_y="10px",
            align="center", gap="10px",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


def _check_row(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["check_date"], font_size="12px", color="#64748b",
                    flex_shrink="0", width="90px"),
            rx.text(row["driver"], font_size="13px", color="#1e293b",
                    font_weight="500", flex="1"),
            rx.text(row["vehicle_no"], font_size="12px", color="#64748b",
                    flex_shrink="0", display=["none", "inline", "inline"]),
            rx.hstack(
                rx.text("양호", font_size="11px", color="#38bd94"),
                rx.text(row["total_ok"], font_size="12px", font_weight="700",
                        color="#38bd94"),
                spacing="1", align="center", flex_shrink="0",
            ),
            rx.hstack(
                rx.text("불량", font_size="11px", color="#ef4444"),
                rx.text(row["total_fail"], font_size="12px", font_weight="700",
                        color="#ef4444"),
                spacing="1", align="center", flex_shrink="0",
            ),
            width="100%", padding_x="16px", padding_y="10px",
            align="center", gap="10px",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


def _daily_row(row: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(row["check_date"], font_size="12px", color="#64748b",
                    flex_shrink="0", width="90px"),
            rx.text(row["driver"], font_size="13px", color="#1e293b",
                    font_weight="500", flex="1"),
            rx.text(row["category"], font_size="12px", color="#64748b",
                    flex_shrink="0", display=["none", "inline", "inline"]),
            rx.hstack(
                rx.text(row["total_ok"], font_size="12px", font_weight="700",
                        color="#38bd94"),
                rx.text("/", font_size="11px", color="#94a3b8"),
                rx.text(row["total_fail"], font_size="12px", font_weight="700",
                        color=rx.cond(row["total_fail"] == "0", "#94a3b8", "#ef4444")),
                spacing="1", align="center", flex_shrink="0",
            ),
            width="100%", padding_x="16px", padding_y="10px",
            align="center", gap="10px",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


def _safety_subtab_btn(label: str) -> rx.Component:
    is_active = VendorState.safety_active_subtab == label
    return rx.button(
        label,
        on_click=VendorState.set_safety_subtab(label),
        variant=rx.cond(is_active, "solid", "ghost"),
        color_scheme="green",
        size="2",
        cursor="pointer",
        border_radius="8px",
    )


def _chk_item_row(label: str, value_var, setter_ok, setter_bad) -> rx.Component:
    is_ok = value_var == "양호"
    return rx.hstack(
        rx.text(label, font_size="13px", color="#334155", flex="1", min_width="0"),
        rx.hstack(
            rx.button(
                "양호",
                on_click=setter_ok,
                variant=rx.cond(is_ok, "solid", "outline"),
                color_scheme="green",
                size="1",
                cursor="pointer",
            ),
            rx.button(
                "불량",
                on_click=setter_bad,
                variant=rx.cond(is_ok, "outline", "solid"),
                color_scheme=rx.cond(is_ok, "gray", "red"),
                size="1",
                cursor="pointer",
            ),
            spacing="1", flex_shrink="0",
        ),
        width="100%", padding_x="4px", padding_y="8px",
        border_bottom="1px solid #f1f5f9",
        align="center", gap="8px",
    )


def _acc_row(row: dict) -> rx.Component:
    sev_color = rx.cond(
        row["severity"] == "사망", "red",
        rx.cond(row["severity"] == "중상", "orange",
                rx.cond(row["severity"] == "경상", "yellow", "gray")),
    )
    return rx.box(
        rx.hstack(
            rx.text(row["occur_date"], font_size="12px", color="#64748b",
                    flex_shrink="0", width="90px"),
            rx.text(row["driver"], font_size="13px", color="#1e293b",
                    font_weight="500", flex="1"),
            rx.badge(row["accident_type"], size="1", color_scheme="blue",
                     variant="soft", flex_shrink="0"),
            rx.badge(row["severity"], size="1", color_scheme=sev_color,
                     variant="soft", flex_shrink="0"),
            rx.badge(row["status"], size="1", color_scheme="gray",
                     variant="outline", flex_shrink="0",
                     display=["none", "inline-flex", "inline-flex"]),
            width="100%", padding_x="16px", padding_y="10px",
            align="center", gap="10px",
        ),
        border_bottom="1px solid #f1f5f9",
        _hover={"bg": "#f8fafc"},
    )


# ── 안전교육 서브패널 ──
def _safety_edu_panel() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                _section_header("graduation_cap", "안전교육 등록"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.grid(
                    rx.vstack(
                        rx.text("기사명 *", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="기사명 입력", value=VendorState.edu_driver,
                                 on_change=VendorState.set_edu_driver, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("교육일 *", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="YYYY-MM-DD", value=VendorState.edu_date,
                                 on_change=VendorState.set_edu_date, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("교육 유형", font_size="13px", font_weight="600", color="#374151"),
                        rx.select(EDU_TYPES, value=VendorState.edu_type,
                                  on_change=VendorState.set_edu_type, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("교육 시간(h)", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="2", value=VendorState.edu_hours,
                                 on_change=VendorState.set_edu_hours,
                                 type="number", size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("강사/기관", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="강사 또는 기관명", value=VendorState.edu_instructor,
                                 on_change=VendorState.set_edu_instructor, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("이수 여부", font_size="13px", font_weight="600", color="#374151"),
                        rx.select(EDU_RESULTS, value=VendorState.edu_result,
                                  on_change=VendorState.set_edu_result, size="2", width="100%"),
                        gap="4px",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                rx.vstack(
                    rx.text("메모", font_size="13px", font_weight="600", color="#374151"),
                    rx.input(placeholder="메모 (선택)", value=VendorState.edu_memo,
                             on_change=VendorState.set_edu_memo, size="2", width="100%"),
                    gap="4px", width="100%",
                ),
                rx.cond(
                    VendorState.edu_save_has_msg,
                    rx.callout(VendorState.edu_save_msg,
                               color=rx.cond(VendorState.edu_save_ok, "green", "red"), size="1"),
                    rx.box(),
                ),
                rx.button(
                    rx.icon("save", size=14),
                    rx.text("교육 이력 저장", font_size="13px"),
                    on_click=VendorState.save_edu_form,
                    color_scheme="green", size="2", cursor="pointer", gap="6px",
                ),
                spacing="3", width="100%",
            ),
            bg="white", border="1px solid #e2e8f0", border_radius="12px",
            padding="20px", width="100%",
        ),
        _section_header("list", "교육 이력", VendorState.safety_edu_rows.length()),
        _table_box(
            rx.box(
                rx.hstack(
                    rx.text("교육일",   font_size="12px", font_weight="700", color="#64748b", width="90px", flex_shrink="0"),
                    rx.text("기사",     font_size="12px", font_weight="700", color="#64748b", flex="1"),
                    rx.text("유형",     font_size="12px", font_weight="700", color="#64748b", flex_shrink="0"),
                    rx.text("이수여부", font_size="12px", font_weight="700", color="#64748b", flex_shrink="0"),
                    rx.text("시간",     font_size="12px", font_weight="700", color="#64748b", flex_shrink="0",
                            display=["none", "inline", "inline"]),
                    width="100%", padding_x="16px", padding_y="10px", gap="10px",
                ),
                bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                border_radius="12px 12px 0 0",
            ),
            rx.cond(
                VendorState.has_edu,
                rx.box(rx.foreach(VendorState.safety_edu_rows, _edu_row),
                       max_height="260px", overflow_y="auto"),
                _empty_state("등록된 안전교육 이력이 없습니다."),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ── 차량안전점검 서브패널 ──
def _safety_chk_panel() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                _section_header("car", "차량 안전점검 등록"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.grid(
                    rx.vstack(
                        rx.text("기사명 *", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="기사명", value=VendorState.chk_driver,
                                 on_change=VendorState.set_chk_driver, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("점검일 *", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="YYYY-MM-DD", value=VendorState.chk_date,
                                 on_change=VendorState.set_chk_date, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("차량번호", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="차량번호", value=VendorState.chk_vehicle_no,
                                 on_change=VendorState.set_chk_vehicle_no, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("점검자", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="점검자명", value=VendorState.chk_inspector,
                                 on_change=VendorState.set_chk_inspector, size="2", width="100%"),
                        gap="4px",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                rx.text("점검 항목 (8개)", font_size="13px", font_weight="600",
                        color="#374151", margin_top="8px"),
                rx.box(
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[0], VendorState.chk_item_0,
                                  VendorState.set_chk_item_0("양호"),
                                  VendorState.set_chk_item_0("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[1], VendorState.chk_item_1,
                                  VendorState.set_chk_item_1("양호"),
                                  VendorState.set_chk_item_1("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[2], VendorState.chk_item_2,
                                  VendorState.set_chk_item_2("양호"),
                                  VendorState.set_chk_item_2("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[3], VendorState.chk_item_3,
                                  VendorState.set_chk_item_3("양호"),
                                  VendorState.set_chk_item_3("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[4], VendorState.chk_item_4,
                                  VendorState.set_chk_item_4("양호"),
                                  VendorState.set_chk_item_4("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[5], VendorState.chk_item_5,
                                  VendorState.set_chk_item_5("양호"),
                                  VendorState.set_chk_item_5("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[6], VendorState.chk_item_6,
                                  VendorState.set_chk_item_6("양호"),
                                  VendorState.set_chk_item_6("불량")),
                    _chk_item_row(SAFETY_CHECKLIST_LABELS[7], VendorState.chk_item_7,
                                  VendorState.set_chk_item_7("양호"),
                                  VendorState.set_chk_item_7("불량")),
                    bg="white", border="1px solid #e2e8f0", border_radius="8px",
                    padding_x="8px", width="100%",
                ),
                rx.vstack(
                    rx.text("특이사항", font_size="13px", font_weight="600", color="#374151"),
                    rx.input(placeholder="특이사항 (선택)", value=VendorState.chk_memo,
                             on_change=VendorState.set_chk_memo, size="2", width="100%"),
                    gap="4px", width="100%",
                ),
                rx.cond(
                    VendorState.chk_save_has_msg,
                    rx.callout(VendorState.chk_save_msg,
                               color=rx.cond(VendorState.chk_save_ok, "green", "orange"), size="1"),
                    rx.box(),
                ),
                rx.button(
                    rx.icon("clipboard_list", size=14),
                    rx.text("점검 결과 저장", font_size="13px"),
                    on_click=VendorState.save_checklist_form,
                    color_scheme="green", size="2", cursor="pointer", gap="6px",
                ),
                spacing="3", width="100%",
            ),
            bg="white", border="1px solid #e2e8f0", border_radius="12px",
            padding="20px", width="100%",
        ),
        rx.hstack(
            _section_header("car", "점검 이력", VendorState.safety_check_rows.length()),
            rx.cond(
                VendorState.safety_check_fail_count > 0,
                rx.badge(
                    "불량 " + VendorState.safety_check_fail_count.to(str) + "개",
                    color_scheme="red", size="1", variant="soft",
                ),
                rx.box(),
            ),
            spacing="3", align="center",
        ),
        _table_box(
            rx.box(
                rx.hstack(
                    rx.text("점검일",   font_size="12px", font_weight="700", color="#64748b", width="90px", flex_shrink="0"),
                    rx.text("기사",     font_size="12px", font_weight="700", color="#64748b", flex="1"),
                    rx.text("차량번호", font_size="12px", font_weight="700", color="#64748b", flex_shrink="0",
                            display=["none", "inline", "inline"]),
                    rx.text("양호",     font_size="12px", font_weight="700", color="#38bd94", flex_shrink="0"),
                    rx.text("불량",     font_size="12px", font_weight="700", color="#ef4444", flex_shrink="0"),
                    width="100%", padding_x="16px", padding_y="10px", gap="10px",
                ),
                bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                border_radius="12px 12px 0 0",
            ),
            rx.cond(
                VendorState.has_safety_checks,
                rx.box(rx.foreach(VendorState.safety_check_rows, _check_row),
                       max_height="260px", overflow_y="auto"),
                _empty_state("차량 안전점검 이력이 없습니다."),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ── 사고신고 서브패널 ──
def _safety_acc_panel() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                _section_header("triangle_alert", "사고 신고"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.grid(
                    rx.vstack(
                        rx.text("기사명 *", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="기사명", value=VendorState.acc_driver,
                                 on_change=VendorState.set_acc_driver, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("발생일 *", font_size="13px", font_weight="600", color="#374151"),
                        rx.input(placeholder="YYYY-MM-DD", value=VendorState.acc_date,
                                 on_change=VendorState.set_acc_date, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("사고 유형", font_size="13px", font_weight="600", color="#374151"),
                        rx.select(ACC_TYPES, value=VendorState.acc_type,
                                  on_change=VendorState.set_acc_type, size="2", width="100%"),
                        gap="4px",
                    ),
                    rx.vstack(
                        rx.text("심각도", font_size="13px", font_weight="600", color="#374151"),
                        rx.select(ACC_SEVERITIES, value=VendorState.acc_severity,
                                  on_change=VendorState.set_acc_severity, size="2", width="100%"),
                        gap="4px",
                    ),
                    columns="2", spacing="3", width="100%",
                ),
                rx.vstack(
                    rx.text("발생 장소", font_size="13px", font_weight="600", color="#374151"),
                    rx.input(placeholder="발생 장소", value=VendorState.acc_location,
                             on_change=VendorState.set_acc_location, size="2", width="100%"),
                    gap="4px", width="100%",
                ),
                rx.vstack(
                    rx.text("사고 경위 *", font_size="13px", font_weight="600", color="#374151"),
                    rx.text_area(placeholder="사고 경위를 상세히 입력하세요", value=VendorState.acc_desc,
                                 on_change=VendorState.set_acc_desc, size="2", width="100%",
                                 min_height="80px"),
                    gap="4px", width="100%",
                ),
                rx.vstack(
                    rx.text("조치 사항", font_size="13px", font_weight="600", color="#374151"),
                    rx.text_area(placeholder="취한 조치 사항 (선택)", value=VendorState.acc_action,
                                 on_change=VendorState.set_acc_action, size="2", width="100%",
                                 min_height="60px"),
                    gap="4px", width="100%",
                ),
                rx.cond(
                    VendorState.acc_save_has_msg,
                    rx.callout(VendorState.acc_save_msg,
                               color=rx.cond(
                                   VendorState.acc_save_msg == "사고 신고가 완료되었습니다.",
                                   "green", "red",
                               ), size="1"),
                    rx.box(),
                ),
                rx.button(
                    rx.icon("triangle_alert", size=14),
                    rx.text("사고 신고", font_size="13px"),
                    on_click=VendorState.save_accident_form,
                    color_scheme="red", size="2", cursor="pointer", gap="6px",
                ),
                spacing="3", width="100%",
            ),
            bg="white", border="1px solid #e2e8f0", border_radius="12px",
            padding="20px", width="100%",
        ),
        _section_header("list", "사고 이력", VendorState.accident_list.length()),
        _table_box(
            rx.box(
                rx.hstack(
                    rx.text("발생일",   font_size="12px", font_weight="700", color="#64748b", width="90px", flex_shrink="0"),
                    rx.text("기사",     font_size="12px", font_weight="700", color="#64748b", flex="1"),
                    rx.text("유형",     font_size="12px", font_weight="700", color="#64748b", flex_shrink="0"),
                    rx.text("심각도",   font_size="12px", font_weight="700", color="#64748b", flex_shrink="0"),
                    rx.text("상태",     font_size="12px", font_weight="700", color="#64748b", flex_shrink="0",
                            display=["none", "inline", "inline"]),
                    width="100%", padding_x="16px", padding_y="10px", gap="10px",
                ),
                bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                border_radius="12px 12px 0 0",
            ),
            rx.cond(
                VendorState.has_accidents,
                rx.box(rx.foreach(VendorState.accident_list, _acc_row),
                       max_height="280px", overflow_y="auto"),
                _empty_state("신고된 사고가 없습니다."),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ── 일일안전점검 서브패널 ──
def _safety_daily_panel() -> rx.Component:
    return rx.vstack(
        _section_header("clipboard_list", "일일안전보건 점검 조회"),
        rx.text("기사가 매일 출발 전 입력한 점검 결과를 조회합니다.",
                font_size="12px", color="#94a3b8"),
        rx.hstack(
            rx.input(
                placeholder="YYYY-MM",
                value=VendorState.safety_daily_ym,
                on_change=VendorState.set_safety_daily_ym,
                size="2", width="120px",
            ),
            rx.select(
                DAILY_CATEGORIES,
                value=VendorState.daily_check_category,
                on_change=VendorState.set_daily_check_category,
                size="2", width="160px",
                placeholder="카테고리",
            ),
            rx.button(
                rx.icon("search", size=14),
                rx.text("조회", font_size="13px"),
                on_click=VendorState.load_daily_check_summary,
                size="2", color_scheme="green", variant="soft",
                cursor="pointer", gap="6px",
            ),
            spacing="2", align="center",
        ),
        rx.cond(
            VendorState.has_daily_check_items,
            rx.vstack(
                rx.flex(
                    _kpi_card("점검 건수", VendorState.daily_check_count,
                              "건", "clipboard_list", "#38bd94", "#f0fdf4"),
                    _kpi_card("양호 항목", VendorState.daily_check_total_ok,
                              "개", "circle_check", "#3b82f6", "#eff6ff"),
                    _kpi_card("불량 항목", VendorState.daily_check_total_fail,
                              "개", "circle_x", "#ef4444", "#fef2f2"),
                    _kpi_card("양호율", VendorState.daily_check_rate_str,
                              "%", "trending_up", "#f59e0b", "#fffbeb"),
                    gap="12px", flex_wrap="wrap", width="100%",
                ),
                _table_box(
                    rx.box(
                        rx.hstack(
                            rx.text("점검일",    font_size="12px", font_weight="700", color="#64748b", width="90px", flex_shrink="0"),
                            rx.text("기사",      font_size="12px", font_weight="700", color="#64748b", flex="1"),
                            rx.text("카테고리",  font_size="12px", font_weight="700", color="#64748b", flex_shrink="0",
                                    display=["none", "inline", "inline"]),
                            rx.text("양호/불량", font_size="12px", font_weight="700", color="#64748b", flex_shrink="0"),
                            width="100%", padding_x="16px", padding_y="10px", gap="10px",
                        ),
                        bg="#f8fafc", border_bottom="1px solid #e2e8f0",
                        border_radius="12px 12px 0 0",
                    ),
                    rx.box(rx.foreach(VendorState.daily_check_items, _daily_row),
                           max_height="320px", overflow_y="auto"),
                ),
                spacing="4", width="100%",
            ),
            _empty_state("해당 월 일일점검 이력이 없습니다."),
        ),
        spacing="4", width="100%", align="start",
    )


def _safety_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + Excel 다운로드 (Phase 3) ──
        rx.hstack(
            _section_header("shield_check", "안전관리"),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=VendorState.download_safety_excel,
            ),
            width="100%", align="center",
        ),
        rx.hstack(
            *[_safety_subtab_btn(label) for label in SAFETY_SUBTABS],
            spacing="2", flex_wrap="wrap",
        ),
        rx.cond(
            VendorState.safety_active_subtab == "안전교육",
            _safety_edu_panel(),
            rx.cond(
                VendorState.safety_active_subtab == "차량안전점검",
                _safety_chk_panel(),
                rx.cond(
                    VendorState.safety_active_subtab == "사고신고",
                    _safety_acc_panel(),
                    _safety_daily_panel(),
                ),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭7: 설정
# ══════════════════════════════════════════════

def _settings_subtab_btn(label: str) -> rx.Component:
    is_active = VendorState.settings_active_subtab == label
    return rx.button(
        label,
        on_click=VendorState.set_settings_subtab(label),
        variant=rx.cond(is_active, "solid", "ghost"),
        color_scheme="green",
        size="2",
        cursor="pointer",
        border_radius="8px",
    )


def _biz_customer_row(name: str) -> rx.Component:
    return rx.hstack(
        rx.icon("building_2", size=14, color="#64748b", flex_shrink="0"),
        rx.text(name, font_size="13px", color="#1e293b", flex="1"),
        rx.button(
            "삭제",
            on_click=VendorState.delete_biz_customer_handler(name),
            size="1", variant="ghost", color_scheme="red", cursor="pointer",
        ),
        width="100%", padding_x="16px", padding_y="10px",
        border_bottom="1px solid #f1f5f9", align="center", gap="10px",
    )


# ── 업장관리 서브패널 ──
def _settings_biz_panel() -> rx.Component:
    return rx.vstack(
        # 업장 목록
        _section_header("building_2", "업장 목록", VendorState.biz_customers_list.length()),
        rx.cond(
            VendorState.has_biz_customers,
            rx.box(
                rx.foreach(VendorState.biz_customers_list, _biz_customer_row),
                bg="white", border="1px solid #e2e8f0", border_radius="12px",
                overflow="hidden", width="100%",
                box_shadow="0 1px 4px rgba(0,0,0,0.04)",
            ),
            _empty_state("등록된 업장이 없습니다."),
        ),
        # 단건 등록
        rx.box(
            rx.vstack(
                _section_header("circle_plus", "업장 단건 등록"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.hstack(
                    rx.input(
                        placeholder="업장명 입력 (예: 화성시청 구내식당)",
                        value=VendorState.new_biz_name,
                        on_change=VendorState.set_new_biz_name,
                        size="2", flex="1",
                    ),
                    rx.button(
                        rx.icon("plus", size=14),
                        rx.text("등록", font_size="13px"),
                        on_click=VendorState.save_biz_customer_form,
                        color_scheme="green", size="2", cursor="pointer", gap="4px",
                    ),
                    spacing="2", width="100%",
                ),
                rx.cond(
                    VendorState.biz_save_has_msg,
                    rx.callout(VendorState.biz_save_msg,
                               color=rx.cond(VendorState.biz_save_ok, "green", "red"), size="1"),
                    rx.box(),
                ),
                spacing="3", width="100%",
            ),
            bg="white", border="1px solid #e2e8f0", border_radius="12px",
            padding="20px", width="100%",
        ),
        # 일괄 등록
        rx.box(
            rx.vstack(
                _section_header("list", "업장 일괄 등록"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.text("업장명을 줄바꿈으로 구분하여 입력하세요.",
                        font_size="12px", color="#94a3b8"),
                rx.text_area(
                    placeholder="화성시청 구내식당\n동탄2청사 식당\n...",
                    value=VendorState.bulk_biz_names,
                    on_change=VendorState.set_bulk_biz_names,
                    size="2", width="100%", min_height="100px",
                ),
                rx.button(
                    rx.icon("upload", size=14),
                    rx.text("일괄 등록", font_size="13px"),
                    on_click=VendorState.bulk_save_biz_customers,
                    color_scheme="green", size="2", cursor="pointer", gap="6px",
                ),
                spacing="3", width="100%",
            ),
            bg="white", border="1px solid #e2e8f0", border_radius="12px",
            padding="20px", width="100%",
        ),
        spacing="4", width="100%", align="start",
    )


# ── 업체정보 서브패널 ──
def _settings_info_panel() -> rx.Component:
    def _info_field(label: str, value_var, setter, placeholder: str = "") -> rx.Component:
        return rx.vstack(
            rx.text(label, font_size="13px", font_weight="600", color="#374151"),
            rx.input(placeholder=placeholder or label, value=value_var,
                     on_change=setter, size="2", width="100%"),
            gap="4px", width="100%",
        )

    return rx.vstack(
        rx.box(
            rx.vstack(
                _section_header("building", "업체 정보 수정"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.grid(
                    _info_field("회사명", VendorState.vinfo_biz_name,
                                VendorState.set_vinfo_biz_name, "상호명"),
                    _info_field("대표자", VendorState.vinfo_rep,
                                VendorState.set_vinfo_rep, "대표자명"),
                    _info_field("사업자번호", VendorState.vinfo_biz_no,
                                VendorState.set_vinfo_biz_no, "000-00-00000"),
                    _info_field("연락처", VendorState.vinfo_contact,
                                VendorState.set_vinfo_contact, "010-0000-0000"),
                    columns="2", spacing="3", width="100%",
                ),
                _info_field("주소", VendorState.vinfo_address,
                            VendorState.set_vinfo_address, "사업장 주소"),
                _info_field("이메일", VendorState.vinfo_email,
                            VendorState.set_vinfo_email, "example@email.com"),
                _info_field("계좌정보", VendorState.vinfo_account,
                            VendorState.set_vinfo_account, "은행명 계좌번호 예금주"),
                rx.cond(
                    VendorState.info_save_has_msg,
                    rx.callout(VendorState.info_save_msg,
                               color=rx.cond(VendorState.info_save_ok, "green", "red"), size="1"),
                    rx.box(),
                ),
                rx.button(
                    rx.icon("save", size=14),
                    rx.text("업체 정보 저장", font_size="13px"),
                    on_click=VendorState.save_vendor_info_form,
                    color_scheme="green", size="2", cursor="pointer", gap="6px",
                ),
                spacing="3", width="100%",
            ),
            bg="white", border="1px solid #e2e8f0", border_radius="12px",
            padding="20px", width="100%",
        ),
        spacing="4", width="100%", align="start",
    )


# ── 계정설정 서브패널 (기존 계정정보 + 비밀번호 변경 그대로) ──
def _settings_account_panel() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.vstack(
                _section_header("user", "계정 정보"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.vstack(
                    rx.hstack(
                        rx.text("이름",   font_size="13px", color="#64748b",
                                font_weight="600", width="80px", flex_shrink="0"),
                        rx.text(VendorState.user_name, font_size="13px", color="#1e293b"),
                        spacing="4", align="center",
                    ),
                    rx.hstack(
                        rx.text("아이디", font_size="13px", color="#64748b",
                                font_weight="600", width="80px", flex_shrink="0"),
                        rx.text(VendorState.user_id, font_size="13px", color="#1e293b"),
                        spacing="4", align="center",
                    ),
                    rx.hstack(
                        rx.text("업체명", font_size="13px", color="#64748b",
                                font_weight="600", width="80px", flex_shrink="0"),
                        rx.badge(VendorState.user_vendor, color_scheme="green",
                                 size="2", variant="soft"),
                        spacing="4", align="center",
                    ),
                    rx.hstack(
                        rx.text("권한",   font_size="13px", color="#64748b",
                                font_weight="600", width="80px", flex_shrink="0"),
                        rx.badge(VendorState.user_role, color_scheme="blue",
                                 size="2", variant="soft"),
                        spacing="4", align="center",
                    ),
                    spacing="3", align="start", width="100%",
                ),
                spacing="3", align="start", width="100%",
            ),
            bg="white", border_radius="12px", padding="20px",
            border="1px solid #e2e8f0",
            box_shadow="0 1px 4px rgba(0,0,0,0.04)",
            width="100%", max_width="480px",
        ),
        rx.box(
            rx.vstack(
                _section_header("lock", "비밀번호 변경"),
                rx.box(height="1px", bg="#e2e8f0", width="100%"),
                rx.vstack(
                    rx.input(
                        placeholder="현재 비밀번호",
                        type="password",
                        value=VendorState.settings_old_pw,
                        on_change=VendorState.set_settings_old_pw,
                        size="3", width="100%",
                    ),
                    rx.input(
                        placeholder="새 비밀번호 (6자 이상)",
                        type="password",
                        value=VendorState.settings_new_pw,
                        on_change=VendorState.set_settings_new_pw,
                        size="3", width="100%",
                    ),
                    rx.input(
                        placeholder="새 비밀번호 확인",
                        type="password",
                        value=VendorState.settings_confirm_pw,
                        on_change=VendorState.set_settings_confirm_pw,
                        size="3", width="100%",
                    ),
                    rx.button(
                        rx.icon("key_round", size=15),
                        rx.text("비밀번호 변경", font_size="14px"),
                        on_click=VendorState.do_change_password,
                        size="3", color_scheme="green", width="100%",
                        cursor="pointer", gap="6px",
                    ),
                    spacing="3", width="100%",
                ),
                rx.cond(
                    VendorState.settings_has_msg,
                    rx.box(
                        rx.hstack(
                            rx.icon(
                                rx.cond(VendorState.settings_ok, "circle_check", "circle_alert"),
                                size=15,
                                color=rx.cond(VendorState.settings_ok, "#38bd94", "#ef4444"),
                            ),
                            rx.text(
                                VendorState.settings_msg, font_size="13px", font_weight="500",
                                color=rx.cond(VendorState.settings_ok, "#38bd94", "#ef4444"),
                            ),
                            spacing="2", align="center",
                        ),
                        bg=rx.cond(VendorState.settings_ok,
                                   "rgba(56,189,148,0.08)", "rgba(239,68,68,0.08)"),
                        border=rx.cond(VendorState.settings_ok,
                                       "1px solid rgba(56,189,148,0.3)",
                                       "1px solid rgba(239,68,68,0.3)"),
                        border_radius="8px", padding="10px 14px", width="100%",
                    ),
                    rx.box(),
                ),
                spacing="3", align="start", width="100%",
            ),
            bg="white", border_radius="12px", padding="20px",
            border="1px solid #e2e8f0",
            box_shadow="0 1px 4px rgba(0,0,0,0.04)",
            width="100%", max_width="480px",
        ),
        spacing="4", width="100%", align="start",
    )


def _settings_tab() -> rx.Component:
    return rx.vstack(
        _section_header("settings", "설정"),
        rx.hstack(
            *[_settings_subtab_btn(label) for label in SETTINGS_SUBTABS],
            spacing="2",
        ),
        rx.cond(
            VendorState.settings_active_subtab == "업장관리",
            _settings_biz_panel(),
            rx.cond(
                VendorState.settings_active_subtab == "업체정보",
                _settings_info_panel(),
                _settings_account_panel(),
            ),
        ),
        spacing="4", width="100%", align="start",
    )


# ══════════════════════════════════════════════
#  탭 콘텐츠 라우터
# ══════════════════════════════════════════════

def _placeholder_tab(tab_name: str) -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.box(
                rx.icon("wrench", size=40, color="#cbd5e1"),
                width="80px", height="80px", bg="#f1f5f9",
                border_radius="20px", display="flex",
                align_items="center", justify_content="center",
            ),
            rx.text(tab_name, font_size="18px", font_weight="700", color="#334155"),
            rx.text("이 화면은 현재 개발 중입니다.", font_size="13px", color="#94a3b8"),
            rx.badge("준비 중", color_scheme="gray", size="2", variant="soft"),
            spacing="3", align="center",
        ),
        min_height="300px", width="100%", padding_y="60px",
    )


def _tab_content() -> rx.Component:
    """활성 탭에 따른 콘텐츠 렌더링 (rx.cond 중첩)"""
    return rx.cond(
        VendorState.active_tab == "수거현황",
        _collection_tab(),
        rx.cond(
            VendorState.active_tab == "수거데이터",
            _collection_data_tab(),
            rx.cond(
                VendorState.active_tab == "거래처관리",
                _customer_tab(),
                rx.cond(
                    VendorState.active_tab == "일정관리",
                    _schedule_tab(),
                    rx.cond(
                        VendorState.active_tab == "정산관리",
                        _settlement_tab(),
                        rx.cond(
                            VendorState.active_tab == "안전관리",
                            _safety_tab(),
                            _settings_tab(),
                        ),
                    ),
                ),
            ),
        ),
    )


# ══════════════════════════════════════════════
#  메인 레이아웃
# ══════════════════════════════════════════════

def _main_content() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(VendorState.active_tab, font_size="20px",
                        font_weight="800", color="#0f172a"),
                rx.spacer(),
                rx.badge(
                    VendorState.selected_year + "년 " + VendorState.selected_month + "월",
                    color_scheme="blue", size="2", variant="soft",
                ),
                align="center", width="100%",
            ),
            rx.box(height="1px", bg="#e2e8f0", width="100%"),
            _tab_content(),
            spacing="4", width="100%",
        ),
        flex="1", min_width="0",
        padding=["16px 16px 80px", "20px 20px 80px", "24px"],
        overflow_y="auto",
    )


def vendor_admin_page() -> rx.Component:
    """업체관리자 대시보드 — 메인 페이지"""
    return rx.box(
        _header(),
        rx.box(
            _sidebar(),
            _main_content(),
            display="flex",
            flex_direction="row",
            width="100%",
            align_items="flex-start",
            flex="1",
        ),
        _mobile_nav(),
        display="flex",
        flex_direction="column",
        min_height="100vh",
        bg="#f8fafc",
    )
