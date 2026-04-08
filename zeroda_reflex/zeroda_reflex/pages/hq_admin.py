# zeroda_reflex/pages/hq_admin.py
# 본사관리자 페이지 — 섹션A: 기본 구조 + 대시보드 + 계정관리
import reflex as rx
from zeroda_reflex.state.admin_state import (
    AdminState, HQ_TABS, CUST_FORM_TYPE_OPTIONS, CUST_TYPE_OPTIONS,
    ANALYTICS_SUB_TABS, PHOTO_TYPE_OPTIONS,
)
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
    "meal_manager": "급식담당자",
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
        "거래처관리": "contact",
        "수거일정": "calendar",
        "정산관리": "receipt",
        "안전관리": "shield_check",
        "탄소감축": "leaf",
        "폐기물분석": "bar_chart_3",
        "현장사진": "camera",
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
        # P3: 환경 기여 KPI
        rx.hstack(
            _kpi_card("탄소감축", AdminState.dash_carbon_reduced, "kg CO₂",
                       "leaf", "#22c55e"),
            _kpi_card("나무식재 환산", AdminState.dash_tree_equivalent, "그루",
                       "tree_pine", "#16a34a"),
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

    return rx.table.row(
        rx.table.cell(rx.text(uid, font_size="13px", font_weight="600")),
        rx.table.cell(rx.text(user["name"], font_size="13px")),
        rx.table.cell(_role_badge(user["role"])),
        rx.table.cell(rx.text(user["vendor"], font_size="13px")),
        rx.table.cell(
            rx.badge(
                rx.cond(user["approval_status"] == "approved", "승인완료",
                    rx.cond(user["approval_status"] == "pending", "승인대기", "반려")),
                color_scheme=rx.cond(user["approval_status"] == "approved", "green",
                    rx.cond(user["approval_status"] == "pending", "orange", "red")),
                size="1",
            ),
        ),
        rx.table.cell(
            rx.badge(
                rx.cond(user["is_active"] == 1, "활성", "비활성"),
                color_scheme=rx.cond(user["is_active"] == 1, "green", "gray"),
                size="1",
            ),
        ),
        rx.table.cell(
            rx.hstack(
                rx.cond(
                    user["approval_status"] == "pending",
                    rx.hstack(
                        rx.cond(
                            user["_school_in_db"] == False,
                            rx.badge("거래처 미등록", color_scheme="red", size="1"),
                            rx.fragment(),
                        ),
                        rx.button("승인", size="1", color_scheme="green",
                                   disabled=user["_school_in_db"] == False,
                                   on_click=AdminState.approve_user(uid)),
                        rx.button("반려", size="1", color_scheme="red", variant="outline",
                                   on_click=AdminState.reject_user(uid)),
                        spacing="1",
                    ),
                    rx.fragment(),
                ),
                rx.button(
                    rx.cond(user["is_active"] == 1, "비활성화", "활성화"),
                    size="1", variant="outline",
                    on_click=AdminState.toggle_user_active(uid),
                ),
                rx.button("PW초기화", size="1", variant="ghost", color="#94a3b8",
                           on_click=AdminState.reset_password(uid)),
                rx.button("✏️ 수정", size="1", variant="outline", color_scheme="blue",
                           on_click=AdminState.open_edit_dialog(uid)),
                rx.button("🗑️ 삭제", size="1", variant="outline", color_scheme="red",
                           on_click=AdminState.open_delete_dialog(uid)),
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
                ["전체", "admin", "vendor_admin", "driver", "school", "meal_manager", "edu_office"],
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
            rx.button(
                "➕ 계정 생성", size="2", color_scheme="green",
                on_click=AdminState.open_create_dialog,
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

        # ── 계정 생성 다이얼로그 ──
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("계정 생성"),
                rx.vstack(
                    rx.vstack(
                        rx.text("아이디 *", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_new_id,
                                 on_change=AdminState.set_acct_new_id,
                                 placeholder="아이디 (영문/숫자)", width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("이름 *", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_new_name,
                                 on_change=AdminState.set_acct_new_name,
                                 placeholder="실명", width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("비밀번호 *", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_new_pw,
                                 on_change=AdminState.set_acct_new_pw,
                                 type="password",
                                 placeholder="최소 8자, 대·소문자+숫자+특수문자",
                                 width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("역할 *", size="2", weight="bold"),
                        rx.select(
                            ["admin", "vendor_admin", "driver", "school",
                             "meal_manager", "edu_office"],
                            value=AdminState.acct_new_role,
                            on_change=AdminState.set_acct_new_role,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                    rx.cond(
                        (AdminState.acct_new_role == "driver") |
                        (AdminState.acct_new_role == "vendor_admin"),
                        rx.vstack(
                            rx.text("업체명", size="2", weight="bold"),
                            rx.input(value=AdminState.acct_new_vendor,
                                     on_change=AdminState.set_acct_new_vendor,
                                     placeholder="소속 업체명", width="100%"),
                            spacing="1", width="100%",
                        ),
                    ),
                    rx.cond(
                        (AdminState.acct_new_role == "school") |
                        (AdminState.acct_new_role == "meal_manager"),
                        rx.vstack(
                            rx.text("학교명", size="2", weight="bold"),
                            rx.input(value=AdminState.acct_new_schools,
                                     on_change=AdminState.set_acct_new_schools,
                                     placeholder="소속 학교명", width="100%"),
                            spacing="1", width="100%",
                        ),
                    ),
                    rx.cond(
                        AdminState.acct_new_role == "edu_office",
                        rx.vstack(
                            rx.text("교육청", size="2", weight="bold"),
                            rx.input(value=AdminState.acct_new_edu,
                                     on_change=AdminState.set_acct_new_edu,
                                     placeholder="소속 교육청명", width="100%"),
                            spacing="1", width="100%",
                        ),
                    ),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button("취소", variant="outline",
                                      on_click=AdminState.close_create_dialog),
                        ),
                        rx.button("생성", color_scheme="green",
                                  on_click=AdminState.submit_create_user),
                        spacing="2", justify="end", width="100%",
                    ),
                    spacing="3", width="100%",
                ),
                max_width="420px",
            ),
            open=AdminState.acct_create_open,
        ),

        # ── 계정 수정 다이얼로그 ──
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("계정 수정"),
                rx.vstack(
                    rx.text("대상: ", AdminState.acct_edit_target,
                            size="2", color="gray"),
                    rx.vstack(
                        rx.text("이름", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_edit_name,
                                 on_change=AdminState.set_acct_edit_name,
                                 placeholder="이름", width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("역할", size="2", weight="bold"),
                        rx.select(
                            ["admin", "vendor_admin", "driver", "school",
                             "meal_manager", "edu_office"],
                            value=AdminState.acct_edit_role,
                            on_change=AdminState.set_acct_edit_role,
                            width="100%",
                        ),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("업체명", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_edit_vendor,
                                 on_change=AdminState.set_acct_edit_vendor,
                                 placeholder="업체명", width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("학교명", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_edit_schools,
                                 on_change=AdminState.set_acct_edit_schools,
                                 placeholder="학교명", width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("교육청", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_edit_edu,
                                 on_change=AdminState.set_acct_edit_edu,
                                 placeholder="교육청명", width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.vstack(
                        rx.text("새 비밀번호 (변경 시만 입력)", size="2", weight="bold"),
                        rx.input(value=AdminState.acct_edit_new_pw,
                                 on_change=AdminState.set_acct_edit_new_pw,
                                 type="password",
                                 placeholder="최소 8자, 대·소문자+숫자+특수문자",
                                 width="100%"),
                        spacing="1", width="100%",
                    ),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button("취소", variant="outline",
                                      on_click=AdminState.close_edit_dialog),
                        ),
                        rx.button("저장", color_scheme="blue",
                                  on_click=AdminState.submit_edit_user),
                        spacing="2", justify="end", width="100%",
                    ),
                    spacing="3", width="100%",
                ),
                max_width="420px",
            ),
            open=AdminState.acct_edit_open,
        ),

        # ── 계정 삭제 확인 다이얼로그 ──
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("계정 삭제"),
                rx.vstack(
                    rx.callout(
                        "삭제된 계정은 복구할 수 없습니다.",
                        color="red",
                        width="100%",
                    ),
                    rx.text("삭제 대상: ", AdminState.acct_delete_target,
                            size="2", weight="bold"),
                    rx.hstack(
                        rx.dialog.close(
                            rx.button("취소", variant="outline",
                                      on_click=AdminState.close_delete_dialog),
                        ),
                        rx.button("완전 삭제", color_scheme="red",
                                  on_click=AdminState.confirm_delete_user),
                        spacing="2", justify="end", width="100%",
                    ),
                    spacing="3", width="100%",
                ),
                max_width="380px",
            ),
            open=AdminState.acct_delete_open,
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  수거데이터 탭 (섹션B)
# ══════════════════════════════════════════

DATA_SUB_TABS = ["전송대기", "전체수거", "데이터업로드", "시뮬레이션", "처리확인"]


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
                            rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
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
                                rx.table.cell(
                                    rx.hstack(
                                        rx.button(
                                            rx.icon("pencil", size=12), size="1",
                                            variant="outline", color_scheme="blue",
                                            on_click=AdminState.open_edit_row(
                                                r.get("id", ""),
                                                r.get("weight", "0"),
                                                r.get("unit_price", "0"),
                                                r.get("item_type", ""),
                                                r.get("memo", ""),
                                            ),
                                        ),
                                        rx.button(
                                            rx.icon("trash_2", size=12), size="1",
                                            variant="outline", color_scheme="red",
                                            on_click=AdminState.delete_collection_row(r.get("id", "")),
                                        ),
                                        spacing="1",
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


def _data_upload_sub() -> rx.Component:
    """수거데이터 CSV/Excel 일괄 업로드 (P1 복원)"""
    return rx.vstack(
        _card_box(
            rx.vstack(
                _section_header("upload", "수거데이터 일괄 업로드"),
                rx.text(
                    "CSV 또는 Excel 파일로 수거 데이터를 한번에 등록합니다. "
                    "필수 컬럼: 업체, 학교명, 수거일, 중량 | 선택 컬럼: 품목, 단가, 기사, 메모",
                    font_size="12px", color="#64748b",
                ),
                rx.text(
                    "동일 업체·학교·날짜·품목·기사 조합은 자동으로 중복 처리(스킵)됩니다.",
                    font_size="11px", color="#94a3b8",
                ),
                # vendor 강제 지정 (옵션)
                rx.hstack(
                    rx.text("기본 업체 (선택)", font_size="12px", color="#64748b"),
                    rx.select(
                        AdminState.vendor_name_options,
                        value=AdminState.data_upload_vendor,
                        on_change=AdminState.set_data_upload_vendor,
                        placeholder="vendor 컬럼 미입력 시 사용",
                        size="2", width="200px",
                    ),
                    spacing="2", align="center",
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
                    id="hq_data_upload",
                    accept={
                        ".csv": ["text/csv"],
                        ".xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
                    },
                    max_files=1,
                    border="2px dashed #cbd5e1",
                    border_radius="8px",
                    cursor="pointer",
                    _hover={"border_color": "#3b82f6", "bg": "#f0f9ff"},
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("upload", size=14), "업로드 실행",
                        size="2", color_scheme="blue",
                        on_click=AdminState.handle_data_upload(
                            rx.upload_files(upload_id="hq_data_upload")
                        ),
                    ),
                    rx.cond(
                        AdminState.data_upload_progress > 0,
                        rx.hstack(
                            rx.progress(value=AdminState.data_upload_progress, width="120px"),
                            rx.text(AdminState.data_upload_progress.to(str) + "%",
                                    font_size="12px", color="#64748b"),
                            spacing="2", align="center",
                        ),
                    ),
                    spacing="3", align="center",
                ),
                # 결과 카운트
                rx.cond(
                    AdminState.data_upload_progress >= 100,
                    rx.hstack(
                        rx.badge(
                            rx.text("성공 ", AdminState.data_upload_success, "건"),
                            color_scheme="green", size="2",
                        ),
                        rx.badge(
                            rx.text("실패·중복 ", AdminState.data_upload_fail, "건"),
                            color_scheme="orange", size="2",
                        ),
                        spacing="2",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="3", width="100%",
    )


def _edit_row_dialog() -> rx.Component:
    """수거 행 편집 다이얼로그 (P1 복원)"""
    return rx.cond(
        AdminState.edit_row_open,
        rx.box(
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("pencil", size=16, color="#1e40af"),
                        rx.text("수거 행 수정 — ID ", AdminState.edit_row_id,
                                font_size="14px", font_weight="700"),
                        rx.spacer(),
                        rx.button(
                            rx.icon("x", size=14), size="1", variant="ghost",
                            on_click=AdminState.close_edit_row,
                        ),
                        width="100%", align="center",
                    ),
                    rx.divider(),
                    rx.vstack(
                        rx.text("중량 (kg)", font_size="11px", color="#64748b"),
                        rx.input(
                            value=AdminState.edit_row_weight,
                            on_change=AdminState.set_edit_row_weight,
                            type="number", size="2",
                        ),
                        rx.text("단가 (원)", font_size="11px", color="#64748b"),
                        rx.input(
                            value=AdminState.edit_row_unit_price,
                            on_change=AdminState.set_edit_row_unit_price,
                            type="number", size="2",
                        ),
                        rx.text("품목", font_size="11px", color="#64748b"),
                        rx.input(
                            value=AdminState.edit_row_item_type,
                            on_change=AdminState.set_edit_row_item_type,
                            placeholder="음식물 / 재활용 / 일반",
                            size="2",
                        ),
                        rx.text("메모", font_size="11px", color="#64748b"),
                        rx.input(
                            value=AdminState.edit_row_memo,
                            on_change=AdminState.set_edit_row_memo,
                            placeholder="메모 (선택)",
                            size="2",
                        ),
                        spacing="1", width="100%",
                    ),
                    rx.hstack(
                        rx.spacer(),
                        rx.button(
                            "취소", size="2", variant="outline",
                            on_click=AdminState.close_edit_row,
                        ),
                        rx.button(
                            rx.icon("save", size=14), "저장",
                            size="2", color_scheme="blue",
                            on_click=AdminState.save_edit_row,
                        ),
                        spacing="2", width="100%",
                    ),
                    spacing="3",
                ),
                background="white",
                border_radius="12px",
                padding="20px",
                width="380px",
                box_shadow="0 10px 30px rgba(0,0,0,0.2)",
            ),
            position="fixed",
            top="0", left="0", right="0", bottom="0",
            background="rgba(0,0,0,0.4)",
            display="flex",
            align_items="center",
            justify_content="center",
            z_index="1000",
        ),
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
        # ── 오늘 수거량 vs 처리량 비교 (P1 복원 — 섹션 5) ──
        rx.cond(
            AdminState.proc_show_today_compare,
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.icon("calendar_check", size=14, color="#0ea5e9"),
                        rx.text(
                            "오늘 수거량 vs 처리량 (선택 업체 기준)",
                            font_size="12px", font_weight="700", color="#0369a1",
                        ),
                        spacing="2", align="center",
                    ),
                    rx.hstack(
                        _kpi_card("오늘 수거량", AdminState.proc_today_coll_weight, "kg", "truck", "#38bd94"),
                        _kpi_card("오늘 처리량", AdminState.proc_today_proc_weight, "kg", "factory", "#3b82f6"),
                        _kpi_card("차이", AdminState.proc_today_diff, "kg", "scale", "#f59e0b"),
                        spacing="3", width="100%", flex_wrap="wrap",
                    ),
                    spacing="2", width="100%",
                ),
                background="#f0f9ff",
                border="1px solid #bae6fd",
                border_radius="8px",
                padding="12px",
                width="100%",
            ),
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
        rx.cond(AdminState.data_sub_tab == "데이터업로드", _data_upload_sub()),
        rx.cond(AdminState.data_sub_tab == "시뮬레이션", _collection_sub()),
        rx.cond(AdminState.data_sub_tab == "처리확인", _processing_sub()),
        # 편집 다이얼로그 (전체수거에서 사용)
        _edit_row_dialog(),
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
            # ── P2: 학교 배정 ──
            rx.vstack(
                rx.hstack(
                    rx.icon("school", size=14, color="#3b82f6"),
                    rx.text("배정 학교 (쉼표로 구분)", font_size="12px", font_weight="700", color="#475569"),
                    spacing="2", align="center",
                ),
                rx.text(
                    "예: 서초고, 방배중, 역삼초 — 등록 시 school_master에 자동 매핑됩니다.",
                    font_size="11px", color="#94a3b8",
                ),
                rx.text_area(
                    value=AdminState.vf_schools_text,
                    on_change=AdminState.set_vf_schools_text,
                    placeholder="서초고, 방배중, 역삼초",
                    rows="3",
                    width="100%",
                ),
                spacing="1", width="100%",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("save", size=14), "저장",
                    color_scheme="blue", size="2",
                    on_click=AdminState.save_vendor,
                ),
                rx.cond(
                    AdminState.vendor_msg != "",
                    rx.text(
                        AdminState.vendor_msg,
                        font_size="12px",
                        color=rx.cond(AdminState.vendor_ok, "#22c55e", "#ef4444"),
                    ),
                ),
                spacing="3", align="center",
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
                _section_header("triangle_alert", "스쿨존 위반 기록 등록"),
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

SCHED_SUB_TABS = ["오늘현황", "일정조회", "일정등록", "급식승인", "NEIS연동"]


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


def _sched_sync_card() -> rx.Component:
    """학사일정 NEIS 동기화 카드 (본사관리자)"""
    return _card_box(
        rx.vstack(
            _section_header("calendar_sync", "학사일정 NEIS 동기화"),
            rx.text(
                "NEIS API에서 전체 학교 학사일정(방학·개학·공휴일 등)을 가져와 DB에 저장합니다.",
                font_size="12px", color="#94a3b8",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("refresh_cw", size=14),
                    "학사일정 지금 갱신",
                    color_scheme="indigo",
                    size="2",
                    loading=AdminState.sched_sync_running,
                    on_click=AdminState.sync_all_school_schedules,
                ),
                rx.cond(
                    AdminState.sched_sync_msg != "",
                    rx.text(AdminState.sched_sync_msg, font_size="12px", color="#64748b"),
                    rx.fragment(),
                ),
                spacing="3", align="center",
            ),
            spacing="3", width="100%",
        ),
    )


def _neis_sub() -> rx.Component:
    """NEIS 급식일정 연동"""
    return rx.vstack(
        _sched_sync_card(),
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


def _today_status_sub() -> rx.Component:
    """오늘 수거 현황 (P1 복원)"""
    return rx.vstack(
        rx.hstack(
            rx.select(
                AdminState.vendor_name_options_all,
                value=AdminState.today_vendor_filter,
                on_change=AdminState.set_today_vendor_filter,
                placeholder="업체",
                size="2", width="160px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14), "새로고침",
                on_click=AdminState.load_today_status,
                variant="outline", size="2",
            ),
            spacing="2",
        ),
        # KPI 카드
        rx.hstack(
            _card_box(
                rx.vstack(
                    rx.text("오늘 수거 건수", font_size="11px", color="#64748b"),
                    rx.text(AdminState.today_total_count, " 건",
                            font_size="22px", font_weight="700", color="#1e40af"),
                    spacing="1",
                ),
                width="180px",
            ),
            _card_box(
                rx.vstack(
                    rx.text("오늘 총 수거량", font_size="11px", color="#64748b"),
                    rx.text(AdminState.today_total_weight, " kg",
                            font_size="22px", font_weight="700", color="#059669"),
                    spacing="1",
                ),
                width="180px",
            ),
            spacing="3",
        ),
        # 상세 테이블
        _card_box(
            rx.cond(
                AdminState.today_total_count > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("일시", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("학교/거래처", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("중량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.today_collection_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["collect_date"], font_size="12px")),
                                rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                rx.table.cell(rx.text(r["school_name"], font_size="12px")),
                                rx.table.cell(rx.text(r["item_type"], font_size="12px")),
                                rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                rx.table.cell(rx.text(r["weight"], font_size="12px")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("오늘 수거 데이터가 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="3", width="100%",
    )


def _meal_approval_sub() -> rx.Component:
    """급식일정 승인 워크플로우 (P1 복원)"""
    return rx.vstack(
        # 필터
        rx.hstack(
            rx.select(
                AdminState.vendor_name_options_all,
                value=AdminState.meal_approval_vendor,
                on_change=AdminState.set_meal_approval_vendor,
                placeholder="업체",
                size="2", width="160px",
            ),
            rx.input(
                value=AdminState.meal_approval_month,
                on_change=AdminState.set_meal_approval_month,
                placeholder="2026-04",
                size="2", width="120px",
            ),
            rx.select(
                ["draft", "approved", "cancelled"],
                value=AdminState.meal_approval_status,
                on_change=AdminState.set_meal_approval_status,
                size="2", width="130px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_meal_approval,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # 카운트 KPI
        rx.hstack(
            _card_box(
                rx.vstack(
                    rx.text("승인대기", font_size="11px", color="#64748b"),
                    rx.text(AdminState.meal_pending_count, " 건",
                            font_size="20px", font_weight="700", color="#d97706"),
                    spacing="1",
                ),
                width="140px",
            ),
            _card_box(
                rx.vstack(
                    rx.text("승인완료", font_size="11px", color="#64748b"),
                    rx.text(AdminState.meal_approved_count, " 건",
                            font_size="20px", font_weight="700", color="#059669"),
                    spacing="1",
                ),
                width="140px",
            ),
            _card_box(
                rx.vstack(
                    rx.text("반려", font_size="11px", color="#64748b"),
                    rx.text(AdminState.meal_cancelled_count, " 건",
                            font_size="20px", font_weight="700", color="#dc2626"),
                    spacing="1",
                ),
                width="140px",
            ),
            spacing="3",
        ),
        # 일괄 승인 컨트롤
        _card_box(
            rx.vstack(
                rx.text("일괄 승인 옵션 (선택 항목 → schedules 자동 반영)",
                        font_size="13px", font_weight="600"),
                rx.hstack(
                    rx.vstack(
                        rx.text("담당 기사", font_size="11px", color="#64748b"),
                        rx.input(
                            value=AdminState.meal_approval_driver,
                            on_change=AdminState.set_meal_approval_driver,
                            placeholder="기사명",
                            size="2", width="140px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("수거일 offset (급식일+N)", font_size="11px", color="#64748b"),
                        rx.select(
                            ["0", "1", "2"],
                            value=AdminState.meal_approval_offset,
                            on_change=AdminState.set_meal_approval_offset,
                            size="2", width="100px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("반려 사유 (선택)", font_size="11px", color="#64748b"),
                        rx.input(
                            value=AdminState.meal_cancel_note,
                            on_change=AdminState.set_meal_cancel_note,
                            placeholder="반려 사유",
                            size="2", width="200px",
                        ),
                        spacing="1",
                    ),
                    spacing="3", flex_wrap="wrap",
                ),
                rx.hstack(
                    rx.button(
                        rx.icon("check_check", size=14), "전체 선택",
                        size="2", variant="outline",
                        on_click=AdminState.select_all_meals,
                    ),
                    rx.button(
                        rx.icon("x", size=14), "선택 해제",
                        size="2", variant="outline",
                        on_click=AdminState.clear_meal_selection,
                    ),
                    rx.button(
                        rx.icon("circle_check", size=14), "선택 일괄 승인",
                        size="2", color_scheme="green",
                        on_click=AdminState.approve_selected_meals,
                    ),
                    rx.button(
                        rx.icon("circle_x", size=14), "선택 일괄 반려",
                        size="2", color_scheme="red",
                        on_click=AdminState.cancel_selected_meals,
                    ),
                    spacing="2", flex_wrap="wrap",
                ),
                spacing="3",
            ),
        ),
        # 목록 테이블
        _card_box(
            rx.cond(
                AdminState.meal_draft_rows.length() > 0,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("선택", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("ID", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("학교", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("급식일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("수거일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("등록자", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.meal_draft_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(
                                    rx.checkbox(
                                        checked=AdminState.meal_selected_ids.contains(r["id"]),
                                        on_change=AdminState.toggle_meal_id(r["id"]),
                                    ),
                                ),
                                rx.table.cell(rx.text(r["id"], font_size="11px", color="#94a3b8")),
                                rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                rx.table.cell(rx.text(r["school_name"], font_size="12px")),
                                rx.table.cell(rx.text(r["meal_date"], font_size="12px")),
                                rx.table.cell(rx.text(r["collect_date"], font_size="12px")),
                                rx.table.cell(rx.text(r["item_type"], font_size="12px")),
                                rx.table.cell(rx.badge(r["status"], color_scheme="blue", size="1")),
                                rx.table.cell(rx.text(r["uploaded_by"], font_size="11px", color="#94a3b8")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("해당 상태의 급식일정이 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
        ),
        spacing="3", width="100%",
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
        rx.cond(AdminState.sched_sub_tab == "오늘현황", _today_status_sub()),
        rx.cond(AdminState.sched_sub_tab == "일정조회", _sched_view_sub()),
        rx.cond(AdminState.sched_sub_tab == "일정등록", _sched_form_sub()),
        rx.cond(AdminState.sched_sub_tab == "급식승인", _meal_approval_sub()),
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
            rx.select(
                [
                    "전체", "학교", "기업", "관공서", "일반업장",
                    "기타", "기타1(면세사업장)", "기타2(부가세포함)",
                ],
                value=AdminState.settle_cust_type,
                on_change=AdminState.set_settle_cust_type,
                placeholder="거래처유형",
                size="2", width="160px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_settlement,
                variant="outline", size="2",
            ),
            spacing="2", flex_wrap="wrap",
        ),
        # P3: 수신자(거래처) 정보 카드
        _card_box(
            rx.vstack(
                rx.hstack(
                    rx.icon("user", size=14, color="#64748b"),
                    rx.text("수신자(거래처) 정보", font_size="12px", font_weight="700", color="#475569"),
                    rx.spacer(),
                    rx.text("(거래처 선택 시 자동 로드)", font_size="10px", color="#94a3b8"),
                    width="100%",
                ),
                rx.grid(
                    rx.vstack(
                        rx.text("대표자", font_size="10px", color="#94a3b8"),
                        rx.text(AdminState.settle_rcv_rep, font_size="12px", font_weight="600"),
                        spacing="0", align_items="start",
                    ),
                    rx.vstack(
                        rx.text("사업자번호", font_size="10px", color="#94a3b8"),
                        rx.text(AdminState.settle_rcv_biz_no, font_size="12px", font_weight="600"),
                        spacing="0", align_items="start",
                    ),
                    rx.vstack(
                        rx.text("연락처", font_size="10px", color="#94a3b8"),
                        rx.text(AdminState.settle_rcv_phone, font_size="12px", font_weight="600"),
                        spacing="0", align_items="start",
                    ),
                    rx.vstack(
                        rx.text("주소", font_size="10px", color="#94a3b8"),
                        rx.text(AdminState.settle_rcv_address, font_size="12px"),
                        spacing="0", align_items="start",
                    ),
                    rx.vstack(
                        rx.text("업태", font_size="10px", color="#94a3b8"),
                        rx.text(AdminState.settle_rcv_biz_type, font_size="12px"),
                        spacing="0", align_items="start",
                    ),
                    rx.vstack(
                        rx.text("업종", font_size="10px", color="#94a3b8"),
                        rx.text(AdminState.settle_rcv_biz_item, font_size="12px"),
                        spacing="0", align_items="start",
                    ),
                    columns="3", spacing="3", width="100%",
                ),
                spacing="3", width="100%",
            ),
        ),
        # ── 이메일 발송 (Phase 6) + P3 템플릿 편집 ──
        _card_box(
            rx.vstack(
                rx.hstack(
                    rx.icon("mail", size=14, color="#64748b"),
                    rx.text("이메일 발송", font_size="12px", font_weight="700", color="#475569"),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh_cw", size=12), "템플릿 재생성",
                        size="1", variant="outline",
                        on_click=AdminState.rebuild_email_template,
                    ),
                    width="100%",
                ),
                rx.input(
                    value=AdminState.settle_email_subject,
                    on_change=AdminState.set_settle_email_subject,
                    placeholder="이메일 제목",
                    size="2", width="100%",
                ),
                rx.text_area(
                    value=AdminState.settle_email_body,
                    on_change=AdminState.set_settle_email_body,
                    placeholder="이메일 본문",
                    rows="10",
                    width="100%",
                ),
                rx.hstack(
                    rx.input(
                        value=AdminState.email_to,
                        on_change=AdminState.set_email_to,
                        placeholder="수신 이메일",
                        size="1", width="240px",
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
                spacing="3", width="100%",
            ),
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
                "요약문자",
                size="1", color_scheme="green", variant="soft",
                on_click=AdminState.send_statement_sms,
                loading=AdminState.sms_sending,
            ),
            rx.button(
                rx.icon("file_text", size=12),
                "상세문자",
                size="1", color_scheme="green", variant="outline",
                on_click=AdminState.send_detail_sms,
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
        # ── 미수금 관리 (P1 복원) ──
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("circle_alert", size=14, color="#f59e0b"),
                    rx.text("미수금 관리", font_size="12px", font_weight="700", color="#475569"),
                    spacing="2", align="center",
                ),
                rx.hstack(
                    rx.input(
                        value=AdminState.overdue_amount,
                        on_change=AdminState.set_overdue_amount,
                        placeholder="미납금액 (원)",
                        type="number",
                        size="1", width="160px",
                    ),
                    rx.input(
                        value=AdminState.overdue_months,
                        on_change=AdminState.set_overdue_months,
                        placeholder="미납개월 (예: 2026-01, 2026-02)",
                        size="1", width="260px",
                    ),
                    spacing="2", flex_wrap="wrap",
                ),
                rx.text_area(
                    value=AdminState.overdue_memo,
                    on_change=AdminState.set_overdue_memo,
                    placeholder="미납 비고 (선택)",
                    size="1",
                    width="100%",
                    rows="2",
                ),
                rx.cond(
                    AdminState.has_overdue,
                    rx.text(
                        AdminState.overdue_warning_text,
                        font_size="11px",
                        color="#f59e0b",
                        font_weight="600",
                    ),
                ),
                spacing="2", width="100%",
            ),
            background="#fffbeb",
            border="1px solid #fde68a",
            border_radius="8px",
            padding="12px",
            width="100%",
        ),
        # KPI
        rx.cond(
            AdminState.has_settle_summary,
            rx.hstack(
                _kpi_card("총 수거량", AdminState.settle_summary.get("total_weight", "0"), "kg", "weight", "#38bd94"),
                _kpi_card(AdminState.settle_tax_label, AdminState.settle_summary.get("total_amount", "0"), "원", "receipt", "#3b82f6"),
                _kpi_card("부가세 (10%)", AdminState.settle_summary.get("vat", "0"), "원", "percent", "#f59e0b"),
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
                            rx.table.column_header_cell(rx.text("거래처유형", font_size="12px", font_weight="700", color="#64748b")),
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
                                rx.table.cell(rx.text(r["cust_type"], font_size="12px", color="#64748b")),
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
            rx.button(
                rx.icon("file_text", size=14), "CSV",
                size="1", variant="outline", color_scheme="blue",
                on_click=AdminState.download_carbon_csv,
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
        # P3: 품목별 탄소 기여도
        _card_box(
            rx.vstack(
                _section_header("apple", "품목별 탄소감축 기여도"),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("품목", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("CO₂ 감축(kg)", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.carbon_by_item,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["item_type"], font_size="12px", font_weight="600")),
                                rx.table.cell(rx.text(r["weight"], font_size="12px")),
                                rx.table.cell(rx.text(r["carbon_kg"], font_size="12px", color="#22c55e", font_weight="600")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                spacing="3", width="100%",
            ),
        ),
        # P3: 월별 추이 (연간 조회 시)
        rx.cond(
            AdminState.carbon_monthly_trend.length() > 0,
            _card_box(
                rx.vstack(
                    _section_header("trending_up", "월별 탄소감축 추이"),
                    rx.recharts.line_chart(
                        rx.recharts.line(
                            data_key="carbon_num",
                            stroke="#22c55e",
                            type_="monotone",
                            name="CO₂ 감축(kg)",
                        ),
                        rx.recharts.x_axis(data_key="month", font_size=11),
                        rx.recharts.y_axis(font_size=11),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.tooltip(),
                        rx.recharts.legend(),
                        data=AdminState.carbon_monthly_trend,
                        width="100%",
                        height=280,
                    ),
                    spacing="3", width="100%",
                ),
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

def _safety_sub_nav() -> rx.Component:
    """안전관리 서브탭 네비게이션 (P1 복원 — 5개 탭)"""
    return rx.hstack(
        *[
            rx.button(
                tab,
                size="1",
                variant=rx.cond(AdminState.safety_sub_tab == tab, "solid", "soft"),
                color_scheme=rx.cond(AdminState.safety_sub_tab == tab, "blue", "gray"),
                on_click=AdminState.set_safety_sub_tab(tab),
            )
            for tab in ["안전교육", "점검결과", "사고보고", "일일점검", "기사모니터링"]
        ],
        spacing="1", flex_wrap="wrap",
    )


def _safety_checklist_sub() -> rx.Component:
    """안전점검 결과 서브탭 — P2: 불합격 경고 배지 추가"""
    return _card_box(
        rx.vstack(
            _section_header("clipboard_check", "차량 안전점검 결과"),
            rx.cond(
                AdminState.safety_checklist_fail_count > 0,
                rx.box(
                    rx.hstack(
                        rx.icon("triangle_alert", size=14, color="#ef4444"),
                        rx.text(
                            f"불합격 항목이 있는 점검",
                            font_size="12px", font_weight="700", color="#991b1b",
                        ),
                        rx.text(
                            AdminState.safety_checklist_fail_count,
                            font_size="13px", font_weight="800", color="#ef4444",
                        ),
                        rx.text("건", font_size="12px", color="#991b1b"),
                        spacing="2", align="center",
                    ),
                    background="#fef2f2",
                    border="1px solid #fecaca",
                    border_radius="6px",
                    padding="8px 12px",
                ),
            ),
            rx.cond(
                AdminState.has_safety_checklist,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("점검일", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("차량번호", font_size="12px", font_weight="700", color="#64748b")),
                            rx.table.column_header_cell(rx.text("양호", font_size="12px", font_weight="700", color="#22c55e")),
                            rx.table.column_header_cell(rx.text("불합격", font_size="12px", font_weight="700", color="#ef4444")),
                            rx.table.column_header_cell(rx.text("점검자", font_size="12px", font_weight="700", color="#64748b")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            AdminState.safety_checklist_rows,
                            lambda r: rx.table.row(
                                rx.table.cell(rx.text(r["check_date"], font_size="12px")),
                                rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                rx.table.cell(rx.text(r["vehicle_no"], font_size="12px")),
                                rx.table.cell(rx.text(r["total_ok"], font_size="12px", color="#22c55e", font_weight="600")),
                                rx.table.cell(rx.text(r["total_fail"], font_size="12px", color="#ef4444", font_weight="600")),
                                rx.table.cell(rx.text(r["inspector"], font_size="12px")),
                            ),
                        ),
                    ),
                    width="100%",
                ),
                rx.text("점검 기록이 없습니다.", font_size="13px", color="#94a3b8",
                         padding="20px", text_align="center"),
            ),
            spacing="3", width="100%",
        ),
    )


def _daily_check_sub() -> rx.Component:
    """일일안전점검 이력 서브탭 (산안법 3년 보관 의무)"""
    return rx.vstack(
        rx.hstack(
            rx.input(
                value=AdminState.daily_check_month,
                on_change=AdminState.set_daily_check_month,
                placeholder="YYYY-MM",
                size="1", width="120px",
            ),
            rx.button(
                rx.icon("refresh_cw", size=14),
                on_click=AdminState.load_safety,
                variant="outline", size="2",
            ),
            spacing="2",
        ),
        rx.hstack(
            _kpi_card("총 점검 건수", AdminState.daily_check_rows.length(), "건", "hash", "#3b82f6"),
            _kpi_card("양호 합계", AdminState.daily_check_ok_count, "건", "circle_check", "#22c55e"),
            _kpi_card("불량 합계", AdminState.daily_check_fail_count, "건", "circle_x", "#ef4444"),
            _kpi_card("양호율", AdminState.daily_check_ok_rate, "", "percent", "#f59e0b"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        _card_box(
            rx.vstack(
                _section_header("clipboard_list", "일일안전점검 이력"),
                rx.cond(
                    AdminState.has_daily_check_rows,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("점검일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("차량", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("카테고리", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("양호", font_size="12px", font_weight="700", color="#22c55e")),
                                rx.table.column_header_cell(rx.text("불량", font_size="12px", font_weight="700", color="#ef4444")),
                                rx.table.column_header_cell(rx.text("불량메모", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.daily_check_rows,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["check_date"], font_size="12px")),
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                    rx.table.cell(rx.text(r["vehicle_no"], font_size="12px")),
                                    rx.table.cell(rx.text(r["category"], font_size="12px")),
                                    rx.table.cell(rx.text(r["total_ok"], font_size="12px", color="#22c55e")),
                                    rx.table.cell(rx.text(r["total_fail"], font_size="12px", color="#ef4444")),
                                    rx.table.cell(rx.text(r["fail_memo"], font_size="11px", color="#94a3b8")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("일일점검 기록이 없습니다.", font_size="13px", color="#94a3b8",
                             padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="3", width="100%",
    )


def _driver_monitor_sub() -> rx.Component:
    """기사 활동 모니터링 서브탭"""
    return rx.vstack(
        rx.hstack(
            _kpi_card("🟢 정상", AdminState.monitor_normal_count, "명", "circle_check", "#22c55e"),
            _kpi_card("🟡 주의", AdminState.monitor_caution_count, "명", "triangle_alert", "#facc15"),
            _kpi_card("🟠 경고", AdminState.monitor_warning_count, "명", "octagon_alert", "#f59e0b"),
            _kpi_card("🔴 긴급", AdminState.monitor_emergency_count, "명", "siren", "#ef4444"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        _card_box(
            rx.vstack(
                _section_header("activity", "기사 활동 모니터링 (오늘)"),
                rx.cond(
                    AdminState.has_driver_monitor,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("기사명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("업체", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("마지막 학교", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("입력 시각", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("경과", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.driver_monitor_rows,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["status"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["driver"], font_size="12px")),
                                    rx.table.cell(rx.text(r["vendor"], font_size="12px")),
                                    rx.table.cell(rx.text(r["last_school"], font_size="12px")),
                                    rx.table.cell(rx.text(r["last_time"], font_size="12px", color="#64748b")),
                                    rx.table.cell(rx.text(r["elapsed"], font_size="12px", color="#64748b")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text("등록된 기사가 없거나 오늘 활동이 없습니다.", font_size="13px",
                             color="#94a3b8", padding="20px", text_align="center"),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="3", width="100%",
    )


def _accident_status_box() -> rx.Component:
    """사고 상태 변경 입력 박스"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("settings", size=14, color="#64748b"),
                rx.text("사고 상태 변경", font_size="12px", font_weight="700", color="#475569"),
                spacing="2", align="center",
            ),
            rx.hstack(
                rx.input(
                    value=AdminState.accident_status_id,
                    on_change=AdminState.set_accident_status_id,
                    placeholder="사고 ID",
                    type="number",
                    size="1", width="120px",
                ),
                rx.select(
                    ["처리중", "완료"],
                    value=AdminState.accident_new_status,
                    on_change=AdminState.set_accident_new_status,
                    size="1", width="120px",
                ),
                rx.button(
                    "상태 변경",
                    size="1", color_scheme="blue", variant="soft",
                    on_click=AdminState.update_accident,
                ),
                rx.cond(
                    AdminState.safety_has_msg,
                    rx.text(
                        AdminState.safety_msg,
                        font_size="11px",
                        color=rx.cond(AdminState.safety_ok, "#22c55e", "#ef4444"),
                    ),
                ),
                spacing="2", align="center", flex_wrap="wrap",
            ),
            spacing="2", width="100%",
        ),
        background="#f8fafc",
        border="1px solid #e2e8f0",
        border_radius="8px",
        padding="10px",
        width="100%",
    )


def _safety_tab() -> rx.Component:
    """안전관리 탭: 5개 서브탭 (P1 복원)"""
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
        _safety_sub_nav(),

        # ── 서브탭별 내용 ──
        rx.cond(
            AdminState.safety_sub_tab == "안전교육",
            _safety_education_sub(),
        ),
        rx.cond(
            AdminState.safety_sub_tab == "점검결과",
            _safety_checklist_sub(),
        ),
        rx.cond(
            AdminState.safety_sub_tab == "사고보고",
            rx.vstack(
                _accident_status_box(),
                _accident_reports_sub(),
                spacing="3", width="100%",
            ),
        ),
        rx.cond(
            AdminState.safety_sub_tab == "일일점검",
            _daily_check_sub(),
        ),
        rx.cond(
            AdminState.safety_sub_tab == "기사모니터링",
            _driver_monitor_sub(),
        ),

        spacing="4", width="100%",
    )


def _safety_education_sub() -> rx.Component:
    """안전교육 이력 서브탭"""
    return _card_box(
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
    )


def _accident_reports_sub() -> rx.Component:
    """사고 보고 현황 서브탭"""
    return _card_box(
        rx.vstack(
            _section_header("siren", "사고 보고 현황"),
            rx.cond(
                AdminState.has_accident_rows,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("ID", font_size="12px", font_weight="700", color="#64748b")),
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
                                rx.table.cell(rx.text(r["id"], font_size="12px", color="#94a3b8")),
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
    )


# ══════════════════════════════════════════
#  P2: 거래처관리 탭 (섹션 신규)
# ══════════════════════════════════════════

def _customer_mgmt_tab() -> rx.Component:
    """거래처관리 탭 — 업체 선택 → 거래처 목록 + 등록/수정 폼"""
    return rx.vstack(
        _section_header("contact", "거래처 관리"),

        # 필터
        _card_box(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("업체 선택", font_size="12px", color="#64748b"),
                        rx.select(
                            AdminState.vendor_name_options,
                            value=AdminState.cust_vendor_filter,
                            on_change=AdminState.set_cust_vendor_filter,
                            placeholder="업체를 선택하세요",
                            size="2", width="200px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("거래처 유형", font_size="12px", color="#64748b"),
                        rx.select(
                            CUST_TYPE_OPTIONS,
                            value=AdminState.cust_type_filter,
                            on_change=AdminState.set_cust_type_filter,
                            size="2", width="180px",
                        ),
                        spacing="1",
                    ),
                    rx.button(
                        rx.icon("refresh_cw", size=14), "새로고침",
                        on_click=AdminState.load_customers,
                        variant="outline", size="2",
                    ),
                    spacing="3", align="end", flex_wrap="wrap",
                ),
                rx.cond(
                    AdminState.has_cust_msg,
                    rx.text(
                        AdminState.cust_msg,
                        font_size="12px",
                        color=rx.cond(AdminState.cust_ok, "#22c55e", "#ef4444"),
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 거래처 목록 테이블
        _card_box(
            rx.vstack(
                _section_header("list", "거래처 목록"),
                rx.cond(
                    AdminState.has_cust_rows,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("거래처명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("유형", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("음식물(원)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("재활용(원)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("일반(원)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("연락처", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("관리", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.cust_rows,
                                lambda c: rx.table.row(
                                    rx.table.cell(rx.text(c["name"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(c["cust_type"], font_size="12px")),
                                    rx.table.cell(rx.text(c["price_food"], font_size="12px", color="#3b82f6")),
                                    rx.table.cell(rx.text(c["price_recycle"], font_size="12px", color="#22c55e")),
                                    rx.table.cell(rx.text(c["price_general"], font_size="12px", color="#f59e0b")),
                                    rx.table.cell(rx.text(c["phone"], font_size="12px")),
                                    rx.table.cell(
                                        rx.hstack(
                                            rx.button(
                                                "편집", size="1", variant="outline",
                                                on_click=AdminState.load_customer_for_edit(c["name"]),
                                            ),
                                            rx.button(
                                                "삭제", size="1", variant="outline", color_scheme="red",
                                                on_click=AdminState.delete_customer_row(c["name"]),
                                            ),
                                            spacing="1",
                                        ),
                                    ),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text(
                        "업체를 선택하면 거래처 목록이 표시됩니다.",
                        font_size="13px", color="#94a3b8",
                        padding="20px", text_align="center",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),

        # 거래처 등록/수정 폼
        _card_box(
            rx.vstack(
                _section_header("user_plus", "거래처 등록 / 수정"),
                rx.hstack(
                    rx.vstack(
                        rx.text("거래처명 *", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_name, on_change=AdminState.set_cf_name,
                                 placeholder="예: 서초고등학교", size="2"),
                        rx.text("유형", font_size="12px", color="#64748b"),
                        rx.select(
                            CUST_FORM_TYPE_OPTIONS,
                            value=AdminState.cf_cust_type,
                            on_change=AdminState.set_cf_cust_type,
                            size="2",
                        ),
                        rx.text("대표자", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_ceo, on_change=AdminState.set_cf_ceo, size="2"),
                        rx.text("사업자번호", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_biz_no, on_change=AdminState.set_cf_biz_no,
                                 placeholder="123-45-67890", size="2"),
                        spacing="1", flex="1",
                    ),
                    rx.vstack(
                        rx.text("음식물 단가 (원/kg)", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_price_food, on_change=AdminState.set_cf_price_food,
                                 type="number", size="2"),
                        rx.text("재활용 단가 (원/kg)", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_price_recycle, on_change=AdminState.set_cf_price_recycle,
                                 type="number", size="2"),
                        rx.text("일반 단가 (원/kg)", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_price_general, on_change=AdminState.set_cf_price_general,
                                 type="number", size="2"),
                        rx.text("월정액 (기타/기타2용)", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_fixed_fee, on_change=AdminState.set_cf_fixed_fee,
                                 type="number", size="2"),
                        spacing="1", flex="1",
                    ),
                    spacing="4", width="100%",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("주소", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_address, on_change=AdminState.set_cf_address, size="2"),
                        spacing="1", flex="2",
                    ),
                    rx.vstack(
                        rx.text("연락처", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_phone, on_change=AdminState.set_cf_phone, size="2"),
                        spacing="1", flex="1",
                    ),
                    rx.vstack(
                        rx.text("이메일", font_size="12px", color="#64748b"),
                        rx.input(value=AdminState.cf_email, on_change=AdminState.set_cf_email, size="2"),
                        spacing="1", flex="1",
                    ),
                    spacing="3", width="100%",
                ),
                rx.button(
                    rx.icon("save", size=14), "거래처 저장",
                    color_scheme="blue", size="2",
                    on_click=AdminState.save_customer,
                ),
                spacing="3", width="100%",
            ),
        ),

        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  폐기물 발생 분석 탭 (섹션F)
# ══════════════════════════════════════════

def _analytics_sub_nav() -> rx.Component:
    """폐기물분석 서브탭 네비게이션 (P2)"""
    return rx.hstack(
        *[
            rx.button(
                tab,
                size="1",
                variant=rx.cond(AdminState.analytics_sub_tab == tab, "solid", "soft"),
                color_scheme=rx.cond(AdminState.analytics_sub_tab == tab, "blue", "gray"),
                on_click=AdminState.set_analytics_sub_tab(tab),
            )
            for tab in ANALYTICS_SUB_TABS
        ],
        spacing="1", flex_wrap="wrap",
    )


def _anomaly_sub() -> rx.Component:
    """P2: 이상치 탐지 서브탭"""
    return rx.vstack(
        _card_box(
            rx.vstack(
                _section_header("triangle_alert", "Z-Score 기반 이상치 탐지"),
                rx.text(
                    "선택한 연/월의 일별 수거량을 기준으로 평균에서 임계값 σ 이상 벗어난 날을 탐지합니다.",
                    font_size="11px", color="#94a3b8",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("Z-Score 임계값 (기본 2.0)", font_size="12px", color="#64748b"),
                        rx.input(
                            value=AdminState.anomaly_threshold,
                            on_change=AdminState.set_anomaly_threshold,
                            type="number",
                            size="2", width="120px",
                        ),
                        spacing="1",
                    ),
                    rx.button(
                        rx.icon("search", size=14), "이상치 탐지 실행",
                        color_scheme="orange", size="2",
                        on_click=AdminState.detect_anomalies,
                    ),
                    spacing="3", align="end",
                ),
                rx.cond(
                    AdminState.anomaly_msg != "",
                    rx.text(AdminState.anomaly_msg, font_size="12px", color="#475569"),
                ),
                spacing="3", width="100%",
            ),
        ),
        rx.hstack(
            _kpi_card("일평균 수거량", AdminState.anomaly_mean, "kg", "scale", "#3b82f6"),
            _kpi_card("표준편차 σ", AdminState.anomaly_std, "kg", "activity", "#f59e0b"),
            _kpi_card("이상치 건수", AdminState.anomaly_count, "건", "triangle_alert", "#ef4444"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        _card_box(
            rx.vstack(
                _section_header("list", "이상치 일자"),
                rx.cond(
                    AdminState.has_anomaly_rows,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("날짜", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("총 수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("Z-Score", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("상태", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.anomaly_rows,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["collect_date"], font_size="12px")),
                                    rx.table.cell(rx.text(r["total_kg"], font_size="12px")),
                                    rx.table.cell(rx.text(r["z_score"], font_size="12px", color="#ef4444", font_weight="600")),
                                    rx.table.cell(rx.text(r["status"], font_size="12px", color="#ef4444")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text(
                        "이상치 탐지를 실행하면 결과가 표시됩니다.",
                        font_size="13px", color="#94a3b8",
                        padding="20px", text_align="center",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%",
    )


def _weather_sub() -> rx.Component:
    """P2: 기상 상관분석 서브탭"""
    return rx.vstack(
        _card_box(
            rx.vstack(
                _section_header("cloud", "기상 상관분석 (피어슨 상관계수)"),
                rx.text(
                    "기상청 ASOS API로 일별 기상데이터를 조회하고 수거량과의 상관관계를 분석합니다.",
                    font_size="11px", color="#94a3b8",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("시작일", font_size="12px", color="#64748b"),
                        rx.input(
                            value=AdminState.weather_start_date,
                            on_change=AdminState.set_weather_start_date,
                            type="date",
                            size="2", width="160px",
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("종료일", font_size="12px", color="#64748b"),
                        rx.input(
                            value=AdminState.weather_end_date,
                            on_change=AdminState.set_weather_end_date,
                            type="date",
                            size="2", width="160px",
                        ),
                        spacing="1",
                    ),
                    rx.button(
                        rx.icon("search", size=14), "기상 분석 실행",
                        color_scheme="cyan", size="2",
                        on_click=AdminState.run_weather_analysis,
                    ),
                    spacing="3", align="end", flex_wrap="wrap",
                ),
                rx.cond(
                    AdminState.has_weather_msg,
                    rx.text(
                        AdminState.weather_msg,
                        font_size="12px",
                        color=rx.cond(AdminState.weather_ok, "#22c55e", "#ef4444"),
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        # 상관계수 KPI
        rx.hstack(
            _kpi_card("기온(r)", AdminState.weather_corr_temp, "", "thermometer", "#f59e0b"),
            _kpi_card("강수(r)", AdminState.weather_corr_rain, "", "cloud_rain", "#3b82f6"),
            _kpi_card("습도(r)", AdminState.weather_corr_humidity, "", "droplets", "#06b6d4"),
            _kpi_card("풍속(r)", AdminState.weather_corr_wind, "", "wind", "#8b5cf6"),
            spacing="3", width="100%", flex_wrap="wrap",
        ),
        # 우천 vs 맑은날
        _card_box(
            rx.vstack(
                _section_header("cloud_rain", "우천일 vs 맑은날 비교"),
                rx.hstack(
                    _kpi_card("우천일 평균", AdminState.weather_rainy_avg, "kg", "cloud_rain", "#3b82f6"),
                    _kpi_card("맑은날 평균", AdminState.weather_clear_avg, "kg", "sun", "#facc15"),
                    _kpi_card("차이(%)", AdminState.weather_diff_pct, "%", "trending_up", "#ef4444"),
                    spacing="3", width="100%", flex_wrap="wrap",
                ),
                spacing="3", width="100%",
            ),
        ),
        # 온도 구간별
        _card_box(
            rx.vstack(
                _section_header("thermometer", "온도 구간별 평균 수거량"),
                rx.cond(
                    AdminState.has_weather_temp_bins,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("온도 구간", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("평균 수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("데이터 수(일)", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.weather_temp_bins,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["temp_range"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["avg_kg"], font_size="12px", color="#3b82f6")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px", color="#94a3b8")),
                                ),
                            ),
                        ),
                        width="100%",
                    ),
                    rx.text(
                        "기상 분석을 실행하면 결과가 표시됩니다.",
                        font_size="13px", color="#94a3b8",
                        padding="20px", text_align="center",
                    ),
                ),
                spacing="3", width="100%",
            ),
        ),
        spacing="4", width="100%",
    )


def _analytics_overview_sub() -> rx.Component:
    """P2: 종합분석 서브탭 — 기존 폐기물분석 본문"""
    return rx.vstack(
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
                _kpi_card("전월 대비", AdminState.analytics_mom_change, "변화율", "trending_up", "#8b5cf6"),
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

        # P3: 요일별 평균 분석
        _card_box(
            rx.vstack(
                _section_header("calendar", "요일별 평균 수거량"),
                rx.cond(
                    AdminState.analytics_by_weekday.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("요일", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("평균(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("총량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_weekday,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["weekday"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["avg_kg"], font_size="12px", color="#3b82f6")),
                                    rx.table.cell(rx.text(r["total_kg"], font_size="12px")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
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

        # P3: 계절별 분포
        _card_box(
            rx.vstack(
                _section_header("sun", "계절별 발생량"),
                rx.cond(
                    AdminState.analytics_by_season.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("계절", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("총량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("일평균(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_season,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["season"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["total_kg"], font_size="12px")),
                                    rx.table.cell(rx.text(r["avg_daily_kg"], font_size="12px", color="#f59e0b")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
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

        # P3: 기사 실적
        _card_box(
            rx.vstack(
                _section_header("user", "기사별 수거 실적"),
                rx.cond(
                    AdminState.analytics_by_driver.length() > 0,
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell(rx.text("기사명", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("총 수거량(kg)", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("건수", font_size="12px", font_weight="700", color="#64748b")),
                                rx.table.column_header_cell(rx.text("학교 수", font_size="12px", font_weight="700", color="#64748b")),
                            ),
                        ),
                        rx.table.body(
                            rx.foreach(
                                AdminState.analytics_by_driver,
                                lambda r: rx.table.row(
                                    rx.table.cell(rx.text(r["driver"], font_size="12px", font_weight="600")),
                                    rx.table.cell(rx.text(r["total_kg"], font_size="12px", color="#22c55e")),
                                    rx.table.cell(rx.text(r["count"], font_size="12px")),
                                    rx.table.cell(rx.text(r["schools"], font_size="12px")),
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
#  P2: 폐기물분석 탭 — 서브탭 라우터
# ══════════════════════════════════════════

def _analytics_tab() -> rx.Component:
    """폐기물 발생 분석 — 3개 서브탭 (종합/이상치/기상)"""
    return rx.vstack(
        _section_header("bar_chart_3", "폐기물 발생 분석"),
        _analytics_sub_nav(),
        rx.cond(
            AdminState.analytics_sub_tab == "종합분석",
            _analytics_overview_sub(),
        ),
        rx.cond(
            AdminState.analytics_sub_tab == "이상치탐지",
            _anomaly_sub(),
        ),
        rx.cond(
            AdminState.analytics_sub_tab == "기상분석",
            _weather_sub(),
        ),
        spacing="4", width="100%",
    )


# ══════════════════════════════════════════
#  P3: 현장사진 탭
# ══════════════════════════════════════════

def _photo_card(p: dict) -> rx.Component:
    return rx.box(
        rx.image(
            src=p["photo_url"],
            width="100%",
            height="180px",
            object_fit="cover",
            border_radius="6px",
            fallback="📷",
        ),
        rx.vstack(
            rx.hstack(
                rx.badge(p["photo_type_kr"], color_scheme="blue", size="1"),
                rx.text(p["collect_date"], font_size="11px", color="gray"),
                spacing="2",
            ),
            rx.text(
                p["school_name"],
                font_size="13px", font_weight="600",
            ),
            rx.text(
                p["vendor"], font_size="11px", color="gray",
            ),
            rx.text(
                p["driver"], font_size="11px", color="gray",
            ),
            rx.cond(
                p["memo"] != "",
                rx.text(p["memo"], font_size="11px", color="#475569"),
            ),
            spacing="1", align_items="start", width="100%",
        ),
        bg="white",
        padding="10px",
        border="1px solid #e2e8f0",
        border_radius="8px",
        width="100%",
    )


def _photo_tab() -> rx.Component:
    """현장사진 갤러리 (필터 + 그리드)"""
    return rx.vstack(
        _section_header("camera", "현장사진"),
        _card_box(
            rx.vstack(
                rx.hstack(
                    rx.input(
                        placeholder="업체명 (선택)",
                        value=AdminState.photo_vendor_filter,
                        on_change=AdminState.set_photo_vendor_filter,
                        width="160px",
                    ),
                    rx.select(
                        PHOTO_TYPE_OPTIONS,
                        value=AdminState.photo_type_filter,
                        on_change=AdminState.set_photo_type_filter,
                        width="120px",
                    ),
                    rx.input(
                        type="date",
                        value=AdminState.photo_date_from,
                        on_change=AdminState.set_photo_date_from,
                        width="150px",
                    ),
                    rx.text("~", margin_x="4px"),
                    rx.input(
                        type="date",
                        value=AdminState.photo_date_to,
                        on_change=AdminState.set_photo_date_to,
                        width="150px",
                    ),
                    rx.button(
                        rx.icon("search", size=14),
                        "조회",
                        on_click=AdminState.load_photos,
                        size="2",
                    ),
                    spacing="2", wrap="wrap",
                ),
                rx.cond(
                    AdminState.photo_msg != "",
                    rx.text(AdminState.photo_msg, font_size="12px", color="gray"),
                ),
                spacing="3", width="100%",
            )
        ),
        rx.cond(
            AdminState.photo_rows.length() > 0,
            rx.grid(
                rx.foreach(AdminState.photo_rows, _photo_card),
                columns="3",
                spacing="4",
                width="100%",
            ),
            rx.box(
                rx.text(
                    "조회된 사진이 없습니다. 필터를 설정하고 [조회] 버튼을 눌러주세요.",
                    color="gray", font_size="13px",
                ),
                padding="40px",
                text_align="center",
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
        rx.cond(AdminState.active_tab == "거래처관리", _customer_mgmt_tab()),
        rx.cond(AdminState.active_tab == "수거일정", _schedule_tab()),
        rx.cond(AdminState.active_tab == "정산관리", _settlement_tab()),
        rx.cond(AdminState.active_tab == "안전관리", _safety_tab()),
        rx.cond(AdminState.active_tab == "탄소감축", _carbon_tab()),
        rx.cond(AdminState.active_tab == "폐기물분석", _analytics_tab()),
        rx.cond(AdminState.active_tab == "현장사진", _photo_tab()),
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
