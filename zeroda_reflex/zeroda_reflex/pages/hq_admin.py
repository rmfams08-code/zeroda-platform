# zeroda_reflex/pages/hq_admin.py
# 본사관리자 페이지 — 섹션A: 기본 구조 + 대시보드 + 계정관리
import reflex as rx
from zeroda_reflex.state.admin_state import AdminState, HQ_TABS
from zeroda_reflex.state.auth_state import get_year_options, MONTH_OPTIONS
# ── 공통 컴포넌트 import (Phase 0-A 모듈화) ──
from zeroda_reflex.components.shared import (
    kpi_card as _kpi_card,           # 본사관리자는 기본형 KPI
    section_header as _section_header,
    card_box as _card_box,
)

# ══════════════════════════════════════════
#  공통 헬퍼 — shared.py에서 import (Phase 0-A)
# ══════════════════════════════════════════


ROLE_LABELS = {
    "admin": "본사관리자",
    "vendor_admin": "업체관리자",
    "driver": "기사",
    "school": "학교",
    "edu_office": "교육청",
}

STATUS_COLORS = {
    "pending": ("승인대기", "orange"),
    "approved": ("승인완료", "green"),
    "rejected": ("반려", "red"),
}


# ══════════════════════════════════════════
#  사이드바
# ══════════════════════════════════════════

def _sidebar() -> rx.Component:
    """좌측 사이드바 네비게이션"""
    tab_icons = {
        "대시보드": "layout_dashboard",
        "수거데이터": "database",
        "외주업체관리": "building_2",
        "수거일정": "calendar",
        "정산관리": "receipt",
        "안전관리": "shield_check",
        "탄소감축": "leaf",
        "폐기물분석": "bar_chart_3",
        "계정관리": "users",
    }

    def _nav_item(tab_name: str) -> rx.Component:
        icon_name = tab_icons.get(tab_name, "circle")
        return rx.button(
            rx.hstack(
                rx.icon(icon_name, size=16),
                rx.text(tab_name, font_size="13px"),
                spacing="2",
                width="100%",
            ),
            on_click=AdminState.set_active_tab(tab_name),
            variant="ghost",
            width="100%",
            justify_content="flex-start",
            padding_x="12px",
            padding_y="8px",
            border_radius="8px",
            bg=rx.cond(
                AdminState.active_tab == tab_name,
                "rgba(59,130,246,0.1)",
                "transparent",
            ),
            color=rx.cond(
                AdminState.active_tab == tab_name,
                "#1a73e8",
                "#475569",
            ),
            font_weight=rx.cond(
                AdminState.active_tab == tab_name,
                "700",
                "500",
            ),
            _hover={"bg": "rgba(59,130,246,0.06)"},
        )

    return rx.box(
        rx.vstack(
            # 헤더
            rx.hstack(
                rx.box(
                    rx.text("Z", font_size="16px", font_weight="800", color="white"),
                    width="32px", height="32px",
                    bg="linear-gradient(135deg, #38bd94, #3b82f6)",
                    border_radius="8px",
                    display="flex", align_items="center", justify_content="center",
                ),
                rx.vstack(
                    rx.text("ZERODA", font_size="14px", font_weight="800", color="#0f172a"),
                    rx.text("본사 관리자", font_size="10px", color="#94a3b8"),
                    spacing="0",
                ),
                spacing="2", align="center",
                padding_bottom="16px",
                border_bottom="1px solid #e2e8f0",
                margin_bottom="8px",
            ),

            # 메뉴
            *[_nav_item(t) for t in HQ_TABS],

            # 로그아웃
            rx.box(height="16px"),
            rx.button(
                rx.hstack(
                    rx.icon("log_out", size=14),
                    rx.text("로그아웃", font_size="12px"),
                    spacing="2",
                ),
                on_click=AdminState.logout,
                variant="ghost",
                color="#94a3b8",
                width="100%",
                justify_content="flex-start",
                padding_x="12px",
                _hover={"color": "#ef4444"},
            ),

            spacing="1",
            width="100%",
        ),
        bg="white",
        border_right="1px solid #e2e8f0",
        padding="16px",
        width="220px",
        min_height="100vh",
        position="fixed",
        left="0",
        top="0",
        overflow_y="auto",
    )


# ══════════════════════════════════════════
#  대시보드 탭
# ══════════════════════════════════════════

def _dashboard_tab() -> rx.Component:
    return rx.vstack(
        # 제목 + 연/월 필터
        rx.hstack(
            _section_header("layout_dashboard", "본사 대시보드"),
            rx.spacer(),
            rx.hstack(
                rx.select(
                    get_year_options(),
                    value=AdminState.selected_year,
                    on_change=AdminState.set_selected_year,
                    size="2", width="90px",
                ),
                rx.select(
                    ["1","2","3","4","5","6","7","8","9","10","11","12"],
                    value=AdminState.selected_month,
                    on_change=AdminState.set_selected_month,
                    size="2", width="80px",
                ),
                rx.button(
                    rx.icon("refresh_cw", size=14),
                    on_click=AdminState.refresh_dashboard,
                    variant="outline", size="2",
                ),
                spacing="2",
            ),
            width="100%", align="center",
        ),

        # KPI 카드
        rx.hstack(
            _kpi_card("총 수거량", AdminState.dash_total_weight, "kg",
                       "weight", "#38bd94"),
            _kpi_card("수거 건수", AdminState.dash_total_count, "건",
                       "hash", "#3b82f6"),
            _kpi_card("참여 업체", AdminState.dash_vendor_count, "개",
                       "building_2", "#8b5cf6"),
            _kpi_card("참여 학교", AdminState.dash_school_count, "곳",
                       "school", "#f59e0b"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),

        # 업체별 수거 현황
        _card_box(
            rx.vstack(
                _section_header("building_2", "업체별 수거 현황"),
                rx.cond(
                    AdminState.has_vendor_summary,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("업체명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(
                                    rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.dash_vendor_summary,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["vendor"], font_size="13px")),
                                    rx.table.cell(rx.text(r["total_weight"], font_size="13px", font_weight="600")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("해당 월 데이터가 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 학교별 TOP5
        _card_box(
            rx.vstack(
                _section_header("school", "학교별 수거량 TOP 5"),
                rx.cond(
                    AdminState.has_top5,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(
                                    rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(
                                    rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.dash_top5_schools,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["school_name"], font_size="13px")),
                                    rx.table.cell(rx.text(r["total_weight"], font_size="13px", font_weight="600")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("해당 월 데이터가 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  계정관리 탭
# ══════════════════════════════════════════

def _role_badge(role: str) -> rx.Component:
    color_map = {
        "admin": "blue",
        "vendor_admin": "purple",
        "driver": "green",
        "school": "orange",
        "edu_office": "cyan",
    }
    label = ROLE_LABELS.get(role, role)
    return rx.badge(label, color_scheme=color_map.get(role, "gray"), size="1")


def _user_row(user: dict) -> rx.Component:
    uid = user["user_id"]
    status = user.get("approval_status", "approved")
    is_active = str(user.get("is_active", "1"))
    status_label, status_color = STATUS_COLORS.get(status, ("알수없음", "gray"))

    return rx.table.row(
        rx.table.cell(rx.text(uid, font_size="13px", font_weight="600")),
        rx.table.cell(rx.text(user.get("name", ""), font_size="13px")),
        rx.table.cell(_role_badge(user.get("role", ""))),
        rx.table.cell(rx.text(user.get("vendor", ""), font_size="13px")),
        rx.table.cell(rx.badge(status_label, color_scheme=status_color, size="1")),
        rx.table.cell(
            rx.badge(
                rx.cond(is_active == "1", "활성", "비활성"),
                color_scheme=rx.cond(is_active == "1", "green", "gray"),
                size="1",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    status == "pending",
                    rx.hstack(
                        rx.button("승인", size="1", color_scheme="green",
                                   on_click=AdminState.approve_user(uid)),
                        rx.button("반려", size="1", color_scheme="red", variant="outline",
                                   on_click=AdminState.reject_user(uid)),
                        spacing="1",
                    ),
                ),
                rx.button(
                    rx.cond(is_active == "1", "비활성화", "활성화"),
                    size="1", variant="outline",
                    on_click=AdminState.toggle_user_active(uid),
                ),
                rx.button("PW초기화", size="1", variant="ghost", color="#94a3b8",
                           on_click=AdminState.reset_password(uid)),
                spacing="1",
            ),
        ),
    )


def _account_tab() -> rx.Component:
    return rx.vstack(
        # 제목 + 필터
        rx.hstack(
            _section_header("users", "계정 관리"),
            rx.spacer(),
            rx.cond(
                AdminState.pending_count > 0,
                rx.badge(
                    f"승인대기 {AdminState.pending_count}건",
                    color_scheme="orange", size="2",
                ),
            ),
            width="100%", align="center",
        ),

        # 필터
        rx.hstack(
            rx.select(
                ["전체", "admin", "vendor_admin", "driver", "school", "edu_office"],
                value=AdminState.acct_filter_role,
                on_change=AdminState.set_acct_filter_role,
                placeholder="역할 필터",
                size="2", width="150px",
            ),
            rx.select(
                ["전체", "승인대기", "승인완료", "반려", "비활성"],
                value=AdminState.acct_filter_status,
                on_change=AdminState.set_acct_filter_status,
                placeholder="상태 필터",
                size="2", width="130px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14), "새로고침",
                on_click=AdminState.load_users,
                variant="outline", size="2",
            ),
            spacing="2",
        ),

        # 메시지
        rx.cond(
            AdminState.acct_has_msg,
            rx.callout(
                AdminState.acct_msg,
                icon=rx.cond(AdminState.acct_ok, "circle_check", "circle_alert"),
                color_scheme=rx.cond(AdminState.acct_ok, "green", "red"),
                size="1",
            ),
        ),

        # 사용자 테이블
        _card_box(
            rx.cond(
                AdminState.has_users,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("아이디", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("이름", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("역할", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("승인", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(AdminState.filtered_users, _user_row),
                    ),
                    width="100%",
                ),
                rx.text("조건에 맞는 사용자가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  수거데이터 탭 (섹션B)
# ══════════════════════════════════════════

DATA_SUB_TABS = ["전송대기", "전체수거", "시뮬레이션", "처리확인"]


def _data_sub_nav() -> rx.Component:
    """수거데이터 서브 탭 네비게이션"""
    def _btn(label: str) -> rx.Component:
        return rx.button(
            label,
            on_click=AdminState.set_data_sub_tab(label),
            variant=rx.cond(AdminState.data_sub_tab == label, "solid", "outline"),
            color_scheme=rx.cond(AdminState.data_sub_tab == label, "blue", "gray"),
            size="2",
        )
    return rx.hstack(
        *[_btn(t) for t in DATA_SUB_TABS],
        spacing="2",
        flex_wrap="wrap",
    )


def _pending_sub() -> rx.Component:
    """전송 대기 (미확인) 서브탭"""
    return rx.vstack(
        rx.cond(
            AdminState.has_pending,
            rx.vstack(
                rx.callout(
                    rx.text(
                        "기사 전송 데이터 ",
                        rx.text(AdminState.pending_row_count, font_weight="700"),
                        "건 확인 필요",
                    ),
                    icon="triangle_alert",
                    color_scheme="orange",
                    size="1",
                ),
                # 테이블
                _card_box(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("ID", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("중량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.pending_rows,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r.get("id", ""), font_size="12px")),
                                    rx.table.cell(rx.text(r.get("collect_date", ""), font_size="12px")),
                                    rx.table.cell(rx.text(r.get("school_name", ""), font_size="12px")),
                                    rx.table.cell(rx.text(r.get("vendor", ""), font_size="12px")),
                                    rx.table.cell(rx.text(r.get("item_type", ""), font_size="12px")),
                                    rx.table.cell(rx.text(r.get("weight", ""), font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r.get("driver", ""), font_size="12px")),
                                    rx.table.cell(
                                        rx.button(
                                            "반려", size="1", variant="outline", color_scheme="red",
                                            on_click=AdminState.reject_single_collection(r.get("id", "")),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                ),
                # 전체 확인 버튼
                rx.hstack(
                    rx.button(
                        rx.icon("circle_check", size=14),
                        "전체 확인 처리",
                        color_scheme="green",
                        size="2",
                        on_click=AdminState.confirm_all_pending_data,
                    ),
                    spacing="2",
                ),
                spacing="3", width="100%",
            ),
            rx.callout(
                "미확인 전송 데이터가 없습니다.",
                icon="circle_check",
                color_scheme="green",
                size="1",
            ),
        ),
        spacing="3", width="100%",
    )


def _month_options() -> list[str]:
    """최근 12개월 옵션 생성"""
    from datetime import datetime
    opts = ["전체"]
    now = datetime.now()
    for i in range(12):
        y = now.year
        m = now.month - i
        while m <= 0:
            m += 12
            y -= 1
        opts.append(f"{y}-{str(m).zfill(2)}")
    return opts


def _collection_sub() -> rx.Component:
    """전체 수거 내역 / 시뮬레이션 서브탭"""
    return rx.vstack(
        # 필터
        rx.hstack(
            rx.select(
                AdminState.data_vendor_options_all,
                value=AdminState.data_vendor_filter,
                on_change=AdminState.set_data_vendor_filter,
                placeholder="업체",
                size="2", width="160px",
            ),
            rx.select(
                _month_options(),
                value=AdminState.data_month_filter,
                on_change=AdminState.set_data_month_filter,
                placeholder="월별",
                size="2", width="140px",
            ),
            rx.select(
                AdminState.data_school_options_all,
                value=AdminState.data_school_filter,
                on_change=AdminState.set_data_school_filter,
                placeholder="학교/거래처",
                size="2", width="180px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_collection_data,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # 테이블
        _card_box(
            rx.cond(
                AdminState.has_collection_rows,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("수거일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("중량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.data_collection_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r.get("collect_date", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("school_name", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("vendor", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("item_type", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("weight", ""), font_size="12px", font_weight="600")),
                                rx.table.cell(rx.text(r.get("driver", ""), font_size="12px")),
                                rx.table.cell(
                                    rx.badge(
                                        r.get("status", ""),
                                        color_scheme=rx.cond(
                                            r.get("status", "") == "confirmed", "green",
                                            rx.cond(r.get("status", "") == "rejected", "red", "orange"),
                                        ),
                                        size="1",
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("조건에 맞는 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="3", width="100%",
    )


def _processing_sub() -> rx.Component:
    """처리확인 (계근표) 서브탭"""
    return rx.vstack(
        # 필터
        rx.hstack(
            rx.select(
                AdminState.proc_vendor_options_all,
                value=AdminState.proc_vendor_filter,
                on_change=AdminState.set_proc_vendor_filter,
                placeholder="업체",
                size="2", width="150px",
            ),
            rx.select(
                AdminState.proc_driver_options_all,
                value=AdminState.proc_driver_filter,
                on_change=AdminState.set_proc_driver_filter,
                placeholder="기사",
                size="2", width="130px",
            ),
            rx.select(
                ["전체", "submitted", "confirmed", "rejected"],
                value=AdminState.proc_status_filter,
                on_change=AdminState.set_proc_status_filter,
                placeholder="상태",
                size="2", width="130px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_processing,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # KPI
        rx.hstack(
            _kpi_card("전체", AdminState.proc_total_count, "건", "hash", "#3b82f6"),
            _kpi_card("대기", AdminState.proc_pending_count, "건", "clock", "#f59e0b"),
            _kpi_card("확인", AdminState.proc_confirmed_count, "건", "circle_check", "#22c55e"),
            _kpi_card("총 처리량", AdminState.proc_total_weight, "kg", "weight", "#8b5cf6"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        # 테이블
        _card_box(
            rx.cond(
                AdminState.has_proc_rows,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("처리일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("시각", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("처리량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("처리장", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.proc_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r.get("confirm_date", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("confirm_time", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("vendor", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("driver", ""), font_size="12px")),
                                rx.table.cell(rx.text(r.get("total_weight", ""), font_size="12px", font_weight="600")),
                                rx.table.cell(rx.text(r.get("location_name", ""), font_size="12px")),
                                rx.table.cell(
                                    rx.badge(
                                        rx.cond(r.get("status", "") == "submitted", "대기",
                                                rx.cond(r.get("status", "") == "confirmed", "확인", "반려")),
                                        color_scheme=rx.cond(
                                            r.get("status", "") == "confirmed", "green",
                                            rx.cond(r.get("status", "") == "rejected", "red", "orange"),
                                        ),
                                        size="1",
                                    ),
                                ),
                                rx.table.cell(
                                    rx.cond(
                                        r.get("status", "") == "submitted",
                                        rx.hstack(
                                            rx.button("확인", size="1", color_scheme="green",
                                                       on_click=AdminState.confirm_proc_item(r.get("id", ""))),
                                            rx.button("반려", size="1", variant="outline", color_scheme="red",
                                                       on_click=AdminState.reject_proc_item(r.get("id", ""))),
                                            spacing="1",
                                        ),
                                        rx.text("-", font_size="12px", color="#94a3b8"),
                                    ),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("처리확인 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="3", width="100%",
    )


def _data_tab() -> rx.Component:
    """수거데이터 관리 탭 (메인)"""
    return rx.vstack(
        rx.hstack(
            _section_header("database", "수거 데이터 관리"),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=AdminState.download_collection_excel,
            ),
            width="100%", align="center",
        ),
        _data_sub_nav(),
        # 메시지
        rx.cond(
            AdminState.data_has_msg,
            rx.callout(
                AdminState.data_msg,
                icon=rx.cond(AdminState.data_ok, "circle_check", "circle_alert"),
                color_scheme=rx.cond(AdminState.data_ok, "green", "red"),
                size="1",
            ),
        ),
        # 서브탭 콘텐츠
        rx.cond(AdminState.data_sub_tab == "전송대기", _pending_sub()),
        rx.cond(AdminState.data_sub_tab == "전체수거", _collection_sub()),
        rx.cond(AdminState.data_sub_tab == "시뮬레이션", _collection_sub()),
        rx.cond(AdminState.data_sub_tab == "처리확인", _processing_sub()),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  외주업체 관리 탭 (섹션C)
# ══════════════════════════════════════════

VENDOR_SUB_TABS = ["업체목록", "업체등록", "학교별칭", "안전평가"]

GRADE_LABELS = {
    "S": "S등급 (최우수)", "A": "A등급 (우수)", "B": "B등급 (보통)",
    "C": "C등급 (주의)", "D": "D등급 (불량)",
}
GRADE_COLORS = {"S": "blue", "A": "green", "B": "yellow", "C": "orange", "D": "red"}


def _vendor_sub_nav() -> rx.Component:
    def _btn(label: str) -> rx.Component:
        return rx.button(
            label,
            on_click=AdminState.set_vendor_sub_tab(label),
            variant=rx.cond(AdminState.vendor_sub_tab == label, "solid", "outline"),
            color_scheme=rx.cond(AdminState.vendor_sub_tab == label, "blue", "gray"),
            size="2",
        )
    return rx.hstack(*[_btn(t) for t in VENDOR_SUB_TABS], spacing="2", flex_wrap="wrap")


def _vendor_list_sub() -> rx.Component:
    """업체 목록"""
    return _card_box(
        rx.cond(
            AdminState.has_vendors,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(rx.text("업체ID", font_size="12px", font_weight="700", color="#64748b")),
                        rx.table.column_header_cell(rx.text("상호명", font_size="12px", font_weight="700", color="#64748b")),
                        rx.table.column_header_cell(rx.text("대표자", font_size="12px", font_weight="700", color="#64748b")),
                        rx.table.column_header_cell(rx.text("사업자번호", font_size="12px", font_weight="700", color="#64748b")),
                        rx.table.column_header_cell(rx.text("연락처", font_size="12px", font_weight="700", color="#64748b")),
                        rx.table.column_header_cell(rx.text("차량번호", font_size="12px", font_weight="700", color="#64748b")),
                        rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        AdminState.vendor_list,
                        lambda v: rx.table.row(
                            rx.table.cell(rx.text(v["vendor"], font_size="12px", font_weight="600")),
                            rx.table.cell(rx.text(v["biz_name"], font_size="12px")),
                            rx.table.cell(rx.text(v["rep"], font_size="12px")),
                            rx.table.cell(rx.text(v["biz_no"], font_size="12px")),
                            rx.table.cell(rx.text(v["contact"], font_size="12px")),
                            rx.table.cell(rx.text(v["vehicle_no"], font_size="12px")),
                            rx.table.cell(
                                rx.button("수정", size="1", variant="outline",
                                           on_click=AdminState.load_vendor_for_edit(v["vendor"])),
                            ),
                        ),
                    ),
                ),
                width="100%",
            ),
            rx.text("등록된 업체가 없습니다.", font_size="13px", color="#94a3b8",
                     padding="20px", text_align="center"),
        ),
    )


def _vendor_form_sub() -> rx.Component:
    """업체 등록/수정 폼"""
    return _card_box(
        rx.vstack(
            _section_header("building_2", "업체 정보 등록/수정"),
            rx.hstack(
                rx.vstack(
                    rx.text("업체 ID (영문)", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_vendor, on_change=AdminState.set_vf_vendor,
                             placeholder="예: hayoung", size="2"),
                    rx.text("상호명", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_biz_name, on_change=AdminState.set_vf_biz_name,
                             placeholder="예: 하영자원", size="2"),
                    rx.text("대표자", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_rep, on_change=AdminState.set_vf_rep, size="2"),
                    rx.text("사업자번호", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_biz_no, on_change=AdminState.set_vf_biz_no, size="2"),
                    spacing="1", flex="1",
                ),
                rx.vstack(
                    rx.text("주소", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_address, on_change=AdminState.set_vf_address, size="2"),
                    rx.text("연락처", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_contact, on_change=AdminState.set_vf_contact, size="2"),
                    rx.text("이메일", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_email, on_change=AdminState.set_vf_email, size="2"),
                    rx.text("차량번호 (쉼표 구분)", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.vf_vehicle_no, on_change=AdminState.set_vf_vehicle_no,
                             placeholder="예: 12가3456,78나9012", size="2"),
                    spacing="1", flex="1",
                ),
                spacing="4", width="100%",
            ),
            rx.button(
                rx.icon("save", size=14), "저장",
                color_scheme="blue", size="2",
                on_click=AdminState.save_vendor,
            ),
            spacing="3", width="100%",
        ),
    )


def _alias_sub() -> rx.Component:
    """학교 별칭 관리"""
    return _card_box(
        rx.vstack(
            _section_header("school", "학교 별칭 관리"),
            rx.text("수거 데이터의 학교명과 계정의 담당학교명이 다를 때 별칭을 등록하세요.",
                     font_size="12px", color="#94a3b8"),
            rx.cond(
                AdminState.has_school_master,
                rx.vstack(
                    rx.select(
                        AdminState.school_name_options,
                        value=AdminState.alias_school_sel,
                        on_change=AdminState.set_alias_school_sel,
                        placeholder="학교 선택",
                        size="2", width="280px",
                    ),
                    rx.text("별칭 (쉼표로 구분)", font_size="12px", color="#64748b"),
                    rx.input(
                        value=AdminState.alias_input,
                        on_change=AdminState.set_alias_input,
                        placeholder="예: 서초고,서초고교,서초고등",
                        size="2", width="100%",
                    ),
                    rx.button(
                        rx.icon("save", size=14), "별칭 저장",
                        color_scheme="blue", size="2",
                        on_click=AdminState.save_alias,
                    ),
                    spacing="2", width="100%",
                ),
                rx.text("등록된 학교가 없습니다.", font_size="13px", color="#94a3b8"),
            ),
            # 학교 마스터 테이블
            rx.cond(
                AdminState.has_school_master,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("별칭", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("담당업체", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.school_master_list,
                            lambda s: rx.table.row(
                                rx.table.cell(rx.text(s["school_name"], font_size="12px")),
                                rx.table.cell(rx.text(s.get("alias", ""), font_size="12px", color="#94a3b8")),
                                rx.table.cell(rx.text(s.get("vendor", ""), font_size="12px")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
            ),
            spacing="3", width="100%",
        ),
    )


def _safety_eval_sub() -> rx.Component:
    """안전관리 평가"""
    return rx.vstack(
        # 평가 실행
        _card_box(
            rx.vstack(
                _section_header("shield_check", "월별 평가 실행"),
                rx.text("평가 기준: 스쿨존위반(40) + 차량점검(15) + 일일안전점검(15) + 교육이수(30) = 100점",
                         font_size="12px", color="#94a3b8"),
                rx.hstack(
                    rx.select(
                        AdminState.vendor_name_options,
                        value=AdminState.eval_vendor_sel,
                        on_change=AdminState.set_eval_vendor_sel,
                        placeholder="업체 선택",
                        size="2", width="160px",
                    ),
                    rx.select(
                        get_year_options(),
                        value=AdminState.eval_year,
                        on_change=AdminState.set_eval_year,
                        size="2", width="90px",
                    ),
                    rx.select(
                        ["1","2","3","4","5","6","7","8","9","10","11","12"],
                        value=AdminState.eval_month,
                        on_change=AdminState.set_eval_month,
                        size="2", width="80px",
                    ),
                    rx.button(
                        rx.icon("refresh_cw", size=14), "평가 계산",
                        color_scheme="blue", size="2",
                        on_click=AdminState.calculate_eval,
                    ),
                    spacing="2", flex_wrap="wrap",
                ),
                # 평가 결과
                rx.cond(
                    AdminState.has_eval_result,
                    rx.hstack(
                        _kpi_card("스쿨존위반", AdminState.eval_result["violation_score"], "/40", "shield_alert", "#ef4444"),
                        _kpi_card("차량점검", AdminState.eval_result["checklist_score"], "/15", "truck", "#3b82f6"),
                        _kpi_card("일일점검", AdminState.eval_result["daily_check_score"], "/15", "clipboard_list", "#f59e0b"),
                        _kpi_card("교육이수", AdminState.eval_result["education_score"], "/30", "graduation_cap", "#8b5cf6"),
                        _kpi_card("총점", AdminState.eval_result["total_score"], "점", "award", "#22c55e"),
                        spacing="3", width="100%", flex_wrap="wrap",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 위반 기록 입력
        _card_box(
            rx.vstack(
                _section_header("alert_triangle", "스쿨존 위반 기록 등록"),
                rx.hstack(
                    rx.vstack(
                        rx.text("업체", font_size="12px", color="#64748b"),
                        rx.select(AdminState.vendor_name_options,
                                   value=AdminState.viol_vendor,
                                   on_change=AdminState.set_viol_vendor,
                                   placeholder="업체", size="2", width="140px"),
                        rx.text("기사명", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.viol_driver, on_change=AdminState.set_viol_driver,
                                 placeholder="기사명", size="2"),
                        rx.text("위반일 (YYYY-MM-DD)", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.viol_date, on_change=AdminState.set_viol_date,
                                 placeholder="2026-04-06", size="2"),
                        spacing="1", flex="1",
                    ),
                    rx.vstack(
                        rx.text("위반 유형", font_size="12px", color="#64748b"),
                        rx.select(["과속", "신호위반", "주정차위반", "보행자보호 위반", "기타"],
                                   value=AdminState.viol_type, on_change=AdminState.set_viol_type,
                                   size="2", width="160px"),
                        rx.text("위반 장소", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.viol_location, on_change=AdminState.set_viol_location, size="2"),
                        rx.text("과태료 (원)", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.viol_fine, on_change=AdminState.set_viol_fine, size="2"),
                        spacing="1", flex="1",
                    ),
                    spacing="4", width="100%",
                ),
                rx.input(value=AdminState.viol_memo, on_change=AdminState.set_viol_memo,
                         placeholder="비고", size="2", width="100%"),
                rx.button(
                    rx.icon("save", size=14), "위반 기록 저장",
                    color_scheme="red", size="2",
                    on_click=AdminState.save_violation,
                ),
                spacing="2", width="100%",
            ),
        ),

        # 평가 현황 테이블
        _card_box(
            rx.vstack(
                _section_header("bar_chart_3", "전체 평가 현황"),
                rx.cond(
                    AdminState.has_safety_scores,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("평가월", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("위반(40)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("점검(15)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("일일(15)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("교육(30)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("총점", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("등급", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.safety_scores_list,
                                lambda s: rx.table.row(
                                    rx.table.cell(rx.text(s["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(s["year_month"], font_size="12px")),
                                    rx.table.cell(rx.text(s["violation_score"], font_size="12px")),
                                    rx.table.cell(rx.text(s["checklist_score"], font_size="12px")),
                                    rx.table.cell(rx.text(s["daily_check_score"], font_size="12px")),
                                    rx.table.cell(rx.text(s["education_score"], font_size="12px")),
                                    rx.table.cell(rx.text(s["total_score"], font_size="12px", font_weight="700")),
                                    rx.table.cell(rx.badge(s["grade"], size="1")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("평가 기록이 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 위반 이력
        _card_box(
            rx.vstack(
                _section_header("triangle_alert", "스쿨존 위반 이력"),
                rx.select(
                    AdminState.vendor_name_options_all,
                    value=AdminState.viol_vendor_filter,
                    on_change=AdminState.set_viol_vendor_filter,
                    placeholder="업체 필터",
                    size="2", width="160px",
                ),
                rx.cond(
                    AdminState.has_violations,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("위반일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("유형", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("장소", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("과태료", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("비고", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.violations_list,
                                lambda v: rx.table.row(
                                    rx.table.cell(rx.text(v["violation_date"], font_size="12px")),
                                    rx.table.cell(rx.text(v["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(v["driver"], font_size="12px")),
                                    rx.table.cell(rx.text(v["violation_type"], font_size="12px")),
                                    rx.table.cell(rx.text(v["location"], font_size="12px")),
                                    rx.table.cell(rx.text(v["fine_amount"], font_size="12px")),
                                    rx.table.cell(rx.text(v["memo"], font_size="12px")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("위반 기록이 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),

        spacing="4", width="100%",
    )


def _vendor_mgmt_tab() -> rx.Component:
    """외주업체 관리 탭 (메인)"""
    return rx.vstack(
        _section_header("building_2", "외주업체 관리"),
        _vendor_sub_nav(),
        # 메시지
        rx.cond(
            AdminState.vendor_has_msg,
            rx.callout(
                AdminState.vendor_msg,
                icon=rx.cond(AdminState.vendor_ok, "circle_check", "circle_alert"),
                color_scheme=rx.cond(AdminState.vendor_ok, "green", "red"),
                size="1",
            ),
        ),
        # 서브탭 콘텐츠
        rx.cond(AdminState.vendor_sub_tab == "업체목록", _vendor_list_sub()),
        rx.cond(AdminState.vendor_sub_tab == "업체등록", _vendor_form_sub()),
        rx.cond(AdminState.vendor_sub_tab == "학교별칭", _alias_sub()),
        rx.cond(AdminState.vendor_sub_tab == "안전평가", _safety_eval_sub()),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  수거일정 탭 (섹션D) + NEIS 급식연동
# ══════════════════════════════════════════

SCHED_SUB_TABS = ["일정조회", "일정등록", "NEIS연동"]


def _sched_sub_nav() -> rx.Component:
    def _btn(label: str) -> rx.Component:
        return rx.button(
            label,
            on_click=AdminState.set_sched_sub_tab(label),
            variant=rx.cond(AdminState.sched_sub_tab == label, "solid", "outline"),
            color_scheme=rx.cond(AdminState.sched_sub_tab == label, "blue", "gray"),
            size="2",
        )
    return rx.hstack(*[_btn(t) for t in SCHED_SUB_TABS], spacing="2", flex_wrap="wrap")


def _sched_view_sub() -> rx.Component:
    """일정 조회"""
    return rx.vstack(
        rx.hstack(
            rx.select(
                AdminState.vendor_name_options_all,
                value=AdminState.sched_vendor_filter,
                on_change=AdminState.set_sched_vendor_filter,
                placeholder="업체",
                size="2", width="160px",
            ),
            rx.select(
                _month_options(),
                value=AdminState.sched_month_filter,
                on_change=AdminState.set_sched_month_filter,
                placeholder="월별",
                size="2", width="140px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_schedules,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        _card_box(
            rx.cond(
                AdminState.has_sched_rows,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("ID", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("월/날짜", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("요일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("거래처", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.sched_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["id"], font_size="11px", color="#94a3b8")),
                                rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                rx.table.cell(rx.text(r["month_key"], font_size="12px")),
                                rx.table.cell(rx.text(r["weekdays"], font_size="12px")),
                                rx.table.cell(rx.text(r["schools"], font_size="12px", max_width="200px", overflow="hidden")),
                                rx.table.cell(rx.text(r["items"], font_size="12px")),
                                rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                rx.table.cell(
                                    rx.button("삭제", size="1", variant="outline", color_scheme="red",
                                               on_click=AdminState.delete_sched(r["id"])),
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("등록된 일정이 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="3", width="100%",
    )


def _sched_form_sub() -> rx.Component:
    """일정 등록 폼"""
    return _card_box(
        rx.vstack(
            _section_header("calendar", "일정 등록"),
            rx.hstack(
                rx.vstack(
                    rx.text("업체", font_size="12px", color="#64748b"),
                    rx.select(AdminState.vendor_name_options,
                               value=AdminState.sf_vendor, on_change=AdminState.set_sf_vendor,
                               placeholder="업체", size="2", width="160px"),
                    rx.text("월 또는 날짜 (YYYY-MM 또는 YYYY-MM-DD)", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.sf_month_key, on_change=AdminState.set_sf_month_key,
                             placeholder="2026-04 또는 2026-04-07", size="2"),
                    rx.text("요일 (쉼표 구분)", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.sf_weekdays, on_change=AdminState.set_sf_weekdays,
                             placeholder="월,수,금", size="2"),
                    spacing="1", flex="1",
                ),
                rx.vstack(
                    rx.text("거래처 (쉼표 구분)", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.sf_schools, on_change=AdminState.set_sf_schools,
                             placeholder="서초초,서초중", size="2"),
                    rx.text("품목 (쉼표 구분)", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.sf_items, on_change=AdminState.set_sf_items,
                             placeholder="음식물,재활용", size="2"),
                    rx.text("담당 기사", font_size="12px", color="#64748b"),
                    rx.input(value=AdminState.sf_driver, on_change=AdminState.set_sf_driver,
                             placeholder="기사명", size="2"),
                    spacing="1", flex="1",
                ),
                spacing="4", width="100%",
            ),
            rx.button(
                rx.icon("save", size=14), "일정 저장",
                color_scheme="blue", size="2",
                on_click=AdminState.save_sched,
            ),
            spacing="3", width="100%",
        ),
    )


def _neis_sub() -> rx.Component:
    """NEIS 급식일정 연동"""
    return rx.vstack(
        _card_box(
            rx.vstack(
                _section_header("utensils", "NEIS 급식일정 → 수거일정 자동 생성"),
                rx.text(
                    "나이스(NEIS) Open API에서 학교 급식일을 조회하고, 급식일 기준 수거일정을 자동 생성합니다.",
                    font_size="12px", color="#94a3b8",
                ),
                # 필터
                rx.hstack(
                    rx.vstack(
                        rx.text("업체 선택", font_size="12px", color="#64748b"),
                        rx.select(
                            AdminState.vendor_name_options,
                            value=AdminState.neis_vendor,
                            on_change=AdminState.set_neis_vendor,
                            placeholder="업체",
                            size="2", width="160px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("조회 월", font_size="12px", color="#64748b"),
                        rx.select(
                            _month_options(),
                            value=AdminState.neis_month,
                            on_change=AdminState.set_neis_month,
                            placeholder="월",
                            size="2", width="140px",
                        ),
                        spacing="1",
                    ),
                    spacing="3",
                ),
                # NEIS 학교 선택
                rx.cond(
                    AdminState.has_neis_schools,
                    rx.vstack(
                        rx.text("학교 선택 (NEIS 코드 등록 학교)", font_size="12px", color="#64748b"),
                        rx.select(
                            AdminState.neis_school_name_options,
                            value=AdminState.neis_school_sel,
                            on_change=AdminState.set_neis_school_sel,
                            placeholder="학교 선택",
                            size="2", width="250px",
                        ),
                        rx.button(
                            rx.icon("search", size=14), "NEIS 급식일 조회",
                            color_scheme="blue", size="2",
                            on_click=AdminState.fetch_neis_meals,
                        ),
                        spacing="2",
                    ),
                    rx.callout(
                        "NEIS 학교코드가 등록된 거래처가 없습니다. 거래처 관리에서 NEIS 학교코드를 먼저 등록하세요.",
                        icon="circle_alert",
                        color_scheme="orange",
                        size="1",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        # 조회 결과 + 일정 생성
        rx.cond(
            AdminState.has_neis_meal_dates,
            _card_box(
                rx.vstack(
                    _section_header("calendar", "급식일 조회 결과"),
                    rx.callout(
                        rx.text(
                            AdminState.neis_school_sel, " — ",
                            AdminState.neis_month, " 급식일 ",
                            rx.text(AdminState.neis_meal_count, font_weight="700"),
                            "일",
                        ),
                        icon="circle_check",
                        color_scheme="green",
                        size="1",
                    ),
                    # 급식일 목록
                    rx.hstack(
                        rx.foreach(
                            AdminState.neis_meal_dates,
                            lambda d: rx.badge(d, color_scheme="blue", size="1"),
                        ),
                        flex_wrap="wrap", spacing="1",
                    ),
                    rx.separator(),
                    # 수거일정 생성 옵션
                    rx.text("수거일정 생성 옵션", font_size="14px", font_weight="600"),
                    rx.hstack(
                        rx.vstack(
                            rx.text("수거일 기준", font_size="12px", color="#64748b"),
                            rx.select(
                                ["0", "1"],
                                value=AdminState.neis_collect_offset,
                                on_change=AdminState.set_neis_collect_offset,
                                size="2", width="140px",
                            ),
                            rx.text(
                                rx.cond(AdminState.neis_collect_offset == "0", "급식 당일 수거", "급식 다음날 수거"),
                                font_size="11px", color="#94a3b8",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("수거 품목", font_size="12px", color="#64748b"),
                            rx.select(
                                ["음식물", "음식물,재활용"],
                                value=AdminState.neis_item_type,
                                on_change=AdminState.set_neis_item_type,
                                size="2", width="150px",
                            ),
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("담당 기사", font_size="12px", color="#64748b"),
                            rx.input(
                                value=AdminState.neis_driver,
                                on_change=AdminState.set_neis_driver,
                                placeholder="기사명",
                                size="2", width="140px",
                            ),
                            spacing="1",
                        ),
                        spacing="3", flex_wrap="wrap",
                    ),
                    rx.button(
                        rx.icon("calendar_plus", size=14),
                        rx.text("수거일정 생성 (", AdminState.neis_meal_count, "일)"),
                        color_scheme="green", size="2",
                        on_click=AdminState.create_neis_schedules,
                    ),
                    spacing="3", width="100%",
                ),
            ),
        ),
        spacing="4", width="100%",
    )


def _schedule_tab() -> rx.Component:
    """수거일정 관리 탭 (메인)"""
    return rx.vstack(
        _section_header("calendar", "수거일정 관리"),
        _sched_sub_nav(),
        # 메시지
        rx.cond(
            AdminState.sched_has_msg,
            rx.callout(
                AdminState.sched_msg,
                icon=rx.cond(AdminState.sched_ok, "circle_check", "circle_alert"),
                color_scheme=rx.cond(AdminState.sched_ok, "green", "red"),
                size="1",
            ),
        ),
        rx.cond(AdminState.sched_sub_tab == "일정조회", _sched_view_sub()),
        rx.cond(AdminState.sched_sub_tab == "일정등록", _sched_form_sub()),
        rx.cond(AdminState.sched_sub_tab == "NEIS연동", _neis_sub()),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  정산관리 탭 (섹션E)
# ══════════════════════════════════════════

def _settlement_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + PDF/Excel 다운로드 ──
        rx.hstack(
            _section_header("receipt", "정산 관리"),
            rx.spacer(),
            rx.button(
                rx.icon("file_text", size=14), "PDF",
                size="1", variant="outline", color_scheme="red",
                on_click=AdminState.download_statement_pdf,
            ),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=AdminState.download_settlement_excel,
            ),
            width="100%", align="center",
        ),
        # 필터
        rx.hstack(
            rx.select(
                get_year_options(),
                value=AdminState.settle_year,
                on_change=AdminState.set_settle_year,
                size="2", width="90px",
            ),
            rx.select(
                ["1","2","3","4","5","6","7","8","9","10","11","12"],
                value=AdminState.settle_month,
                on_change=AdminState.set_settle_month,
                size="2", width="80px",
            ),
            rx.select(
                AdminState.vendor_name_options_all,
                value=AdminState.settle_vendor,
                on_change=AdminState.set_settle_vendor,
                placeholder="업체",
                size="2", width="160px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_settlement,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # ── 이메일 발송 (Phase 6) ──
        rx.hstack(
            rx.icon("mail", size=14, color="#64748b"),
            rx.input(
                value=AdminState.email_to,
                on_change=AdminState.set_email_to,
                placeholder="수신 이메일",
                size="1", width="200px",
            ),
            rx.button(
                rx.cond(AdminState.email_sending, rx.spinner(size="1"), rx.icon("send", size=12)),
                "발송",
                size="1", color_scheme="blue", variant="soft",
                on_click=AdminState.send_statement_email,
                loading=AdminState.email_sending,
            ),
            rx.cond(
                AdminState.email_msg != "",
                rx.text(
                    AdminState.email_msg,
                    font_size="11px",
                    color=rx.cond(AdminState.email_ok, "#22c55e", "#ef4444"),
                ),
            ),
            spacing="2", align="center",
        ),
        # ── SMS 발송 (Phase 8) ──
        rx.hstack(
            rx.icon("message_square", size=14, color="#64748b"),
            rx.input(
                value=AdminState.sms_to,
                on_change=AdminState.set_sms_to,
                placeholder="수신 전화번호 (예: 010-1234-5678)",
                size="1", width="220px",
            ),
            rx.button(
                rx.cond(AdminState.sms_sending, rx.spinner(size="1"), rx.icon("smartphone", size=12)),
                "문자발송",
                size="1", color_scheme="green", variant="soft",
                on_click=AdminState.send_statement_sms,
                loading=AdminState.sms_sending,
            ),
            rx.cond(
                AdminState.sms_msg != "",
                rx.text(
                    AdminState.sms_msg,
                    font_size="11px",
                    color=rx.cond(AdminState.sms_ok, "#22c55e", "#ef4444"),
                ),
            ),
            spacing="2", align="center",
        ),
        # KPI
        rx.cond(
            AdminState.has_settle_summary,
            rx.hstack(
                _kpi_card("총 수거량", AdminState.settle_summary.get("total_weight", "0"), "kg", "weight", "#38bd94"),
                _kpi_card("공급가액", AdminState.settle_summary.get("total_amount", "0"), "원", "receipt", "#3b82f6"),
                _kpi_card("부가세", AdminState.settle_summary.get("vat", "0"), "원", "percent", "#f59e0b"),
                _kpi_card("합계", AdminState.settle_summary.get("grand_total", "0"), "원", "banknote", "#8b5cf6"),
                spacing="3", width="100%", flex_wrap="wrap",
            ),
        ),
        # 상세 테이블
        _card_box(
            rx.cond(
                AdminState.has_settle_rows,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("수거일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("중량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("단가(원)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("금액(원)", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.settle_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["collect_date"], font_size="12px")),
                                rx.table.cell(rx.text(r["school_name"], font_size="12px")),
                                rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                rx.table.cell(rx.text(r["item_type"], font_size="12px")),
                                rx.table.cell(rx.text(r["weight"], font_size="12px", font_weight="600")),
                                rx.table.cell(rx.text(r["unit_price"], font_size="12px")),
                                rx.table.cell(rx.text(r["amount"], font_size="12px", font_weight="600")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("해당 기간 정산 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  탄소감축 탭 (섹션E)
# ══════════════════════════════════════════

def _carbon_tab() -> rx.Component:
    return rx.vstack(
        # ── 헤더 + Excel 다운로드 ──
        rx.hstack(
            _section_header("leaf", "탄소배출 감축 현황"),
            rx.spacer(),
            rx.button(
                rx.icon("download", size=14), "Excel",
                size="1", variant="outline", color_scheme="green",
                on_click=AdminState.download_carbon_excel,
            ),
            width="100%", align="center",
        ),
        # 필터
        rx.hstack(
            rx.select(
                get_year_options(),
                value=AdminState.carbon_year,
                on_change=AdminState.set_carbon_year,
                size="2", width="90px",
            ),
            rx.select(
                ["전체","1","2","3","4","5","6","7","8","9","10","11","12"],
                value=AdminState.carbon_month,
                on_change=AdminState.set_carbon_month,
                size="2", width="80px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_carbon,
                variant="outline", size="2",
            ),
            spacing="2",
        ),
        # KPI
        rx.cond(
            AdminState.has_carbon_data,
            rx.vstack(
                rx.hstack(
                    _kpi_card("총 수거량", AdminState.carbon_data.get("total_kg", "0"), "kg", "weight", "#38bd94"),
                    _kpi_card("음식물", AdminState.carbon_data.get("food_kg", "0"), "kg", "apple", "#f59e0b"),
                    _kpi_card("재활용", AdminState.carbon_data.get("recycle_kg", "0"), "kg", "recycle", "#3b82f6"),
                    _kpi_card("일반", AdminState.carbon_data.get("general_kg", "0"), "kg", "trash_2", "#94a3b8"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                rx.hstack(
                    _kpi_card("탄소 감축량", AdminState.carbon_data.get("carbon_reduced", "0"), "kg CO₂", "leaf", "#22c55e"),
                    _kpi_card("나무 식재 환산", AdminState.carbon_data.get("tree_equivalent", "0"), "그루", "tree_pine", "#16a34a"),
                    _kpi_card("CO₂ 톤 환산", AdminState.carbon_data.get("carbon_tons", "0"), "tCO₂", "globe", "#0ea5e9"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                spacing="3", width="100%",
            ),
        ),
        # 학교별 순위
        _card_box(
            rx.vstack(
                _section_header("school", "학교별 수거량 / 탄소감축 TOP 10"),
                rx.cond(
                    AdminState.has_carbon_ranking,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("CO₂ 감축(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.carbon_school_ranking,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["school_name"], font_size="12px")),
                                    rx.table.cell(rx.text(r["total_weight"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["carbon"], font_size="12px", font_weight="600", color="#22c55e")),
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

        # ── 학교별 탄소감축 막대 차트 (Phase 9) ──
        _card_box(
            rx.vstack(
                _section_header("bar_chart_3", "학교별 탄소감축 차트 (TOP 10)"),
                rx.cond(
                    AdminState.has_carbon_ranking,
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="carbon_num",
                            fill="#22c55e",
                            name="CO₂ 감축(kg)",
                        ),
                        rx.recharts.bar(
                            data_key="weight_num",
                            fill="#3b82f6",
                            name="수거량(kg)",
                        ),
                        rx.recharts.x_axis(data_key="school_name", font_size=10, angle=-30),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.legend(),
                        rx.recharts.tooltip(),
                        data=AdminState.carbon_school_ranking,
                        width="100%",
                        height=320,
                    ),
                    rx.text("데이터가 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  안전관리 탭 (섹션F)
# ══════════════════════════════════════════

def _safety_tab() -> rx.Component:
    """안전관리 탭: 안전교육 이력 + 사고 보고"""
    return rx.vstack(
        _section_header("shield_check", "안전관리"),
        # 업체 필터
        rx.hstack(
            rx.select(
                AdminState.vendor_name_options_all,
                value=AdminState.safety_vendor_filter,
                on_change=AdminState.set_safety_vendor_filter,
                placeholder="업체 필터",
                size="2", width="160px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_safety,
                variant="outline", size="2",
            ),
            spacing="2",
        ),

        # 안전교육 이력
        _card_box(
            rx.vstack(
                _section_header("graduation_cap", "안전교육 이수 현황"),
                rx.cond(
                    AdminState.has_edu_rows,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("교육명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("교육일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수료여부", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("비고", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.safety_edu_rows,
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
                                    rx.table.cell(rx.text(r["memo"], font_size="12px")),
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
                    AdminState.has_accident_rows,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("발생일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("사고유형", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("장소", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("피해규모", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("조치내용", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.safety_accident_rows,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["accident_date"], font_size="12px")),
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                    rx.table.cell(rx.text(r["accident_type"], font_size="12px")),
                                    rx.table.cell(rx.text(r["location"], font_size="12px")),
                                    rx.table.cell(rx.text(r["damage"], font_size="12px")),
                                    rx.table.cell(rx.text(r["action_taken"], font_size="12px")),
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
#  폐기물 발생 분석 탭 (섹션F)
# ══════════════════════════════════════════

def _analytics_tab() -> rx.Component:
    """폐기물 발생 분석"""
    return rx.vstack(
        _section_header("bar_chart_3", "폐기물 발생 분석"),
        # 필터
        rx.hstack(
            rx.select(
                get_year_options(),
                value=AdminState.analytics_year,
                on_change=AdminState.set_analytics_year,
                size="2", width="90px",
            ),
            rx.select(
                ["전체", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"],
                value=AdminState.analytics_month,
                on_change=AdminState.set_analytics_month,
                size="2", width="80px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_analytics,
                variant="outline", size="2",
            ),
            spacing="2",
        ),
        # KPI
        rx.cond(
            AdminState.has_analytics,
            rx.hstack(
                _kpi_card("총 수거량", AdminState.analytics_data.get("total_weight", "0"), "kg", "weight", "#38bd94"),
                _kpi_card("수거 건수", AdminState.analytics_data.get("total_count", "0"), "건", "hash", "#3b82f6"),
                _kpi_card("건당 평균", AdminState.analytics_data.get("avg_weight", "0"), "kg", "calculator", "#f59e0b"),
                spacing="3", width="100%", flex_wrap="wrap",
            ),
        ),

        # 품목별 분석
        _card_box(
            rx.vstack(
                _section_header("pie_chart", "품목별 발생량"),
                rx.cond(
                    AdminState.has_by_item,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("비율(%)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_item,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["item_type"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["weight"], font_size="12px")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
                                    rx.table.cell(rx.text(r["ratio"], font_size="12px", color="#3b82f6")),
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

        # 학교별 분석
        _card_box(
            rx.vstack(
                _section_header("school", "학교별 발생량 TOP 10"),
                rx.cond(
                    AdminState.has_by_school,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("학교명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건당 평균(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_school,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["school_name"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["weight"], font_size="12px")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
                                    rx.table.cell(rx.text(r["avg"], font_size="12px", color="#38bd94")),
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

        # 업체별 분석
        _card_box(
            rx.vstack(
                _section_header("building_2", "업체별 수거 현황"),
                rx.cond(
                    AdminState.analytics_by_vendor.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("업체명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("거래처 수", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_vendor,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["weight"], font_size="12px")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
                                    rx.table.cell(rx.text(r["school_count"], font_size="12px")),
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

        # 월별 추이 테이블
        _card_box(
            rx.vstack(
                _section_header("trending_up", "월별 추이"),
                rx.cond(
                    AdminState.analytics_by_month.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("월", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건당 평균(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_month,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["month"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["weight"], font_size="12px")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
                                    rx.table.cell(rx.text(r["avg"], font_size="12px", color="#f59e0b")),
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

        # ── 품목별 막대 차트 (Phase 9) ──
        _card_box(
            rx.vstack(
                _section_header("bar_chart_3", "품목별 수거량 차트"),
                rx.cond(
                    AdminState.has_by_item,
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="weight_num",
                            fill="#3b82f6",
                            name="수거량(kg)",
                        ),
                        rx.recharts.x_axis(data_key="item_type", font_size=12),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.legend(),
                        rx.recharts.tooltip(),
                        data=AdminState.analytics_by_item,
                        width="100%",
                        height=280,
                    ),
                    rx.text("데이터가 없습니다.", font_size="13px", color="#94a3b8"),
                ),
                spacing="3", width="100%",
            ),
        ),

        # ── 월별 추이 꺾은선 차트 (Phase 9) ──
        _card_box(
            rx.vstack(
                _section_header("trending_up", "월별 수거 추이 차트"),
                rx.cond(
                    AdminState.analytics_by_month.length() > 0,
                    rx.recharts.composed_chart(
                        rx.recharts.bar(
                            data_key="weight_num",
                            fill="#3b82f6",
                            name="수거량(kg)",
                            bar_size=30,
                        ),
                        rx.recharts.line(
                            data_key="count_num",
                            stroke="#f59e0b",
                            name="건수",
                            type_="monotone",
                        ),
                        rx.recharts.x_axis(data_key="month", font_size=12),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.legend(),
                        rx.recharts.tooltip(),
                        data=AdminState.analytics_by_month,
                        width="100%",
                        height=300,
                    ),
                    rx.text("데이터가 없습니다.", font_size="13px", color="#94a3b8"),
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
        rx.cond(AdminState.active_tab == "대시보드", _dashboard_tab()),
        rx.cond(AdminState.active_tab == "계정관리", _account_tab()),
        rx.cond(AdminState.active_tab == "수거데이터", _data_tab()),
        rx.cond(AdminState.active_tab == "외주업체관리", _vendor_mgmt_tab()),
        rx.cond(AdminState.active_tab == "수거일정", _schedule_tab()),
        rx.cond(AdminState.active_tab == "정산관리", _settlement_tab()),
        rx.cond(AdminState.active_tab == "안전관리", _safety_tab()),
        rx.cond(AdminState.active_tab == "탄소감축", _carbon_tab()),
        rx.cond(AdminState.active_tab == "폐기물분석", _analytics_tab()),
        width="100%",
    )


# ══════════════════════════════════════════
#  메인 페이지
# ══════════════════════════════════════════

def hq_admin_page() -> rx.Component:
    """본사관리자 메인 페이지"""
    return rx.box(
        _sidebar(),
        rx.box(
            _tab_content(),
            margin_left="220px",
            padding="24px",
            min_height="100vh",
            bg="#f1f5f9",
        ),
    )
