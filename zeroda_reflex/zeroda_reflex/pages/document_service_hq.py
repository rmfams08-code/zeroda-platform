"""
zeroda 본사관리자 문서서비스 패널 — /hq_admin 내부 "문서서비스" 탭
================================================================
저장 위치 : zeroda_reflex/zeroda_reflex/pages/document_service_hq.py
의존     : state/admin_state.py (AdminState)
신규일   : 2026-04-10

기능
  1) 문서발급  : 양식 선택 → 거래처 선택 → 수동입력 → 미리보기 → PDF 발급
  2) 양식관리  : 본사관리자만 — hwpx 업로드 / 목록 / 비활성화 / 태그 확인
  3) 발급내역  : 최근 100건 로그 조회

⚠️ CLAUDE.md 사례5 준수
  - Reflex Var + 파이썬 문자열 '+' 금지
  - f-string 내 Reflex Var 직접 삽입 금지 → rx.text 다중 인자 또는 .to(str)
================================================================
"""
from __future__ import annotations

import reflex as rx

from ..state.admin_state import (
    AdminState, DOC_SERVICE_HQ_TABS, DOC_CATEGORIES,
    WASTE_TYPE_OPTIONS, TREATMENT_OPTIONS, FREQUENCY_OPTIONS,
)


# ══════════════════════════════════════════
#  공통 헤더
# ══════════════════════════════════════════

def _doc_sub_tab_bar() -> rx.Component:
    """문서서비스 상단 서브탭 3개 버튼."""
    return rx.hstack(
        rx.foreach(
            DOC_SERVICE_HQ_TABS,
            lambda t: rx.button(
                t,
                on_click=AdminState.set_doc_sub_tab(t),
                variant=rx.cond(AdminState.doc_sub_tab == t, "solid", "soft"),
                color_scheme=rx.cond(AdminState.doc_sub_tab == t, "blue", "gray"),
                size="2",
            ),
        ),
        spacing="2",
    )


# ══════════════════════════════════════════
#  1) 양식관리 패널 (본사관리자 전용)
# ══════════════════════════════════════════

def _template_mgmt_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("양식관리", size="5"),
        rx.text(
            "hwpx 양식을 업로드하세요. 업로드 후 양식에 포함된 {{태그}}가 자동으로 추출됩니다.",
            color="#6b7280",
            size="2",
        ),
        # 업로드 폼
        rx.card(
            rx.vstack(
                rx.text("신규 양식 업로드", weight="bold"),
                rx.hstack(
                    rx.input(
                        placeholder="양식 이름 (예: 2자 위수탁계약서)",
                        value=AdminState.doc_upload_name,
                        on_change=AdminState.set_doc_upload_name,
                        width="280px",
                    ),
                    rx.select(
                        DOC_CATEGORIES,
                        value=AdminState.doc_upload_category,
                        on_change=AdminState.set_doc_upload_category,
                    ),
                    spacing="2",
                ),
                rx.upload(
                    rx.vstack(
                        rx.button("hwpx 파일 선택", color_scheme="blue", size="2"),
                        rx.text(
                            "또는 hwpx 파일을 이 영역으로 드래그해서 놓으세요",
                            size="1",
                            color="#9ca3af",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    id="doc_template_upload",
                    # ⚠️ accept 미지정 — hwpx는 표준 MIME이 없어 브라우저가 거부함
                    #    확장자 검증은 admin_state.upload_document_template 에서 수행
                    multiple=False,
                    max_files=1,
                    border="1px dashed #9ca3af",
                    padding="20px",
                    width="100%",
                ),
                # 선택된 파일 미리보기 (사용자가 dropzone 안에 파일이 들어갔는지 확인)
                rx.foreach(
                    rx.selected_files("doc_template_upload"),
                    lambda f: rx.hstack(
                        rx.icon("file", size=14),
                        rx.text("선택됨: ", f, size="2", color="#059669"),
                        spacing="2",
                        align="center",
                    ),
                ),
                rx.button(
                    "업로드 완료",
                    on_click=AdminState.upload_document_template(
                        rx.upload_files(upload_id="doc_template_upload")
                    ),
                    color_scheme="green",
                    size="2",
                ),
                rx.cond(
                    AdminState.doc_upload_msg != "",
                    rx.text(
                        AdminState.doc_upload_msg,
                        color=rx.cond(AdminState.doc_upload_ok, "green", "red"),
                        weight="bold",
                    ),
                ),
                spacing="3",
            ),
            padding="16px",
            width="100%",
        ),
        # 등록된 양식 목록
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.text("등록된 양식", weight="bold"),
                    rx.spacer(),
                    rx.button(
                        "새로고침",
                        on_click=AdminState.load_doc_service,
                        variant="soft",
                        size="1",
                    ),
                    width="100%",
                ),
                rx.cond(
                    AdminState.doc_templates.length() == 0,
                    rx.text("등록된 양식이 없습니다.", color="#9ca3af"),
                    rx.foreach(
                        AdminState.doc_templates,
                        lambda t: rx.box(
                            rx.hstack(
                                rx.vstack(
                                    rx.hstack(
                                        rx.badge(t["category"], color_scheme="blue"),
                                        rx.text(t["template_name"], weight="bold"),
                                        spacing="2",
                                    ),
                                    rx.text(
                                        "태그: ", t["tag_list"],
                                        size="1",
                                        color="#6b7280",
                                    ),
                                    rx.text(
                                        "등록: ", t["created_by"], " / ", t["created_at"],
                                        size="1",
                                        color="#9ca3af",
                                    ),
                                    spacing="1",
                                    align="start",
                                ),
                                rx.spacer(),
                                rx.button(
                                    "비활성화",
                                    on_click=AdminState.deactivate_doc_template(t["id"]),
                                    color_scheme="red",
                                    variant="soft",
                                    size="1",
                                ),
                                width="100%",
                            ),
                            padding="10px",
                            border="1px solid #e5e7eb",
                            border_radius="6px",
                            width="100%",
                        ),
                    ),
                ),
                spacing="2",
            ),
            padding="16px",
            width="100%",
        ),
        spacing="4",
        width="100%",
    )


# ══════════════════════════════════════════
#  2) 문서발급 패널
# ══════════════════════════════════════════


def _issue_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("문서발급", size="5"),
        rx.text(
            "양식을 선택하고 거래처를 지정하면 DB에서 자동으로 값을 채워 PDF로 발급합니다.",
            color="#6b7280",
            size="2",
        ),
        rx.card(
            rx.vstack(
                # 1단계: 양식 선택
                rx.text("1. 양식 선택", weight="bold"),
                rx.cond(
                    AdminState.doc_templates.length() == 0,
                    rx.text(
                        "등록된 양식이 없습니다. 먼저 [양식관리] 탭에서 양식을 업로드하세요.",
                        color="#ef4444",
                    ),
                    rx.hstack(
                        rx.foreach(
                            AdminState.doc_templates,
                            lambda t: rx.button(
                                t["template_name"],
                                on_click=AdminState.set_doc_selected_template(t["id"]),
                                variant=rx.cond(
                                    AdminState.doc_selected_template_id == t["id"],
                                    "solid",
                                    "soft",
                                ),
                                color_scheme="blue",
                                size="2",
                            ),
                        ),
                        spacing="2",
                        wrap="wrap",
                    ),
                ),
                rx.divider(),
                # 2단계: 거래처 선택
                rx.text("2. 거래처 선택", weight="bold"),
                # ── 기존거래처 / 신규거래처 토글 (2026-04-10 추가) ──
                rx.hstack(
                    rx.button(
                        rx.icon("search", size=14),
                        " 기존거래처 검색",
                        variant=rx.cond(
                            AdminState.doc_new_customer_mode,
                            "soft",
                            "solid",
                        ),
                        color_scheme=rx.cond(
                            AdminState.doc_new_customer_mode,
                            "gray",
                            "blue",
                        ),
                        on_click=rx.cond(
                            AdminState.doc_new_customer_mode,
                            AdminState.toggle_new_customer_mode,
                            AdminState.noop,
                        ),
                        size="2",
                    ),
                    rx.button(
                        rx.icon("plus", size=14),
                        " 신규거래처 직접입력",
                        variant=rx.cond(
                            AdminState.doc_new_customer_mode,
                            "solid",
                            "soft",
                        ),
                        color_scheme=rx.cond(
                            AdminState.doc_new_customer_mode,
                            "green",
                            "gray",
                        ),
                        on_click=rx.cond(
                            AdminState.doc_new_customer_mode,
                            AdminState.noop,
                            AdminState.toggle_new_customer_mode,
                        ),
                        size="2",
                    ),
                    spacing="2",
                ),
                # ── 기존거래처 검색 모드 ──
                rx.cond(
                    ~AdminState.doc_new_customer_mode,
                    rx.vstack(
                        rx.hstack(
                            rx.input(
                                placeholder="거래처 검색 (상호명/사업자번호)",
                                on_change=AdminState.set_doc_customer_query,
                                width="280px",
                            ),
                            rx.button(
                                "거래처 조회",
                                on_click=AdminState.search_doc_customers,
                                color_scheme="blue",
                                size="2",
                            ),
                            spacing="2",
                        ),
                        rx.cond(
                            AdminState.doc_customer_candidates.length() > 0,
                            rx.vstack(
                                rx.foreach(
                                    AdminState.doc_customer_candidates,
                                    lambda c: rx.button(
                                        rx.text(
                                            c["customer_name"],
                                            " / ",
                                            c["business_no"],
                                        ),
                                        on_click=AdminState.set_doc_selected_customer(c["id"]),
                                        variant=rx.cond(
                                            AdminState.doc_selected_customer_id == c["id"],
                                            "solid",
                                            "soft",
                                        ),
                                        color_scheme=rx.cond(
                                            AdminState.doc_selected_customer_id == c["id"],
                                            "blue",
                                            "gray",
                                        ),
                                        size="2",
                                        width="100%",
                                    ),
                                ),
                                spacing="1",
                                width="100%",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                # ── 신규거래처 직접입력 모드 (2026-04-10 추가) ──
                rx.cond(
                    AdminState.doc_new_customer_mode,
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.icon("building_2", size=16, color="#059669"),
                                rx.text(
                                    "신규거래처 정보 직접입력",
                                    size="2", weight="bold", color="#059669",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("상호명 *", size="1", color="#6b7280"),
                                    rx.input(
                                        placeholder="거래처 상호명",
                                        value=AdminState.doc_new_cust_name,
                                        on_change=AdminState.set_doc_new_cust_name,
                                        width="200px",
                                    ),
                                    spacing="1",
                                ),
                                rx.vstack(
                                    rx.text("사업자번호", size="1", color="#6b7280"),
                                    rx.input(
                                        placeholder="000-00-00000",
                                        value=AdminState.doc_new_cust_bizno,
                                        on_change=AdminState.set_doc_new_cust_bizno,
                                        width="160px",
                                    ),
                                    spacing="1",
                                ),
                                rx.vstack(
                                    rx.text("대표자", size="1", color="#6b7280"),
                                    rx.input(
                                        placeholder="대표자명",
                                        value=AdminState.doc_new_cust_rep,
                                        on_change=AdminState.set_doc_new_cust_rep,
                                        width="120px",
                                    ),
                                    spacing="1",
                                ),
                                spacing="4",
                                wrap="wrap",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("주소", size="1", color="#6b7280"),
                                    rx.input(
                                        placeholder="사업장 주소",
                                        value=AdminState.doc_new_cust_address,
                                        on_change=AdminState.set_doc_new_cust_address,
                                        width="300px",
                                    ),
                                    spacing="1",
                                ),
                                rx.vstack(
                                    rx.text("연락처", size="1", color="#6b7280"),
                                    rx.input(
                                        placeholder="000-0000-0000",
                                        value=AdminState.doc_new_cust_phone,
                                        on_change=AdminState.set_doc_new_cust_phone,
                                        width="160px",
                                    ),
                                    spacing="1",
                                ),
                                spacing="4",
                                wrap="wrap",
                            ),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("업종/업태", size="1", color="#6b7280"),
                                    rx.input(
                                        placeholder="예: 폐기물처리업",
                                        value=AdminState.doc_new_cust_type,
                                        on_change=AdminState.set_doc_new_cust_type,
                                        width="200px",
                                    ),
                                    spacing="1",
                                ),
                                spacing="4",
                                wrap="wrap",
                            ),
                            rx.text(
                                "* 상호명은 필수 입력입니다. 나머지는 선택사항입니다.",
                                size="1", color="#9ca3af",
                            ),
                            spacing="3",
                        ),
                        padding="12px",
                        border="1px solid #d1fae5",
                        border_radius="8px",
                        background="#f0fdf4",
                        width="100%",
                    ),
                ),
                # ── 선택된 거래처 + 외주업체 정보 카드 (기존모드일 때만 표시) ──
                rx.cond(
                    (~AdminState.doc_new_customer_mode) & (AdminState.doc_selected_customer_id > 0),
                    rx.vstack(
                        # 거래처(배출사업장) 정보
                        rx.box(
                            rx.vstack(
                                rx.hstack(
                                    rx.icon("building_2", size=16, color="#059669"),
                                    rx.text(
                                        "선택된 거래처 (배출사업장)",
                                        size="2", weight="bold", color="#059669",
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("상호명", size="1", color="#6b7280"),
                                        rx.text(
                                            AdminState.doc_selected_customer_info["customer_name"],
                                            size="2", weight="bold",
                                        ),
                                        spacing="0",
                                    ),
                                    rx.vstack(
                                        rx.text("사업자번호", size="1", color="#6b7280"),
                                        rx.text(
                                            AdminState.doc_selected_customer_info["business_no"],
                                            size="2",
                                        ),
                                        spacing="0",
                                    ),
                                    rx.vstack(
                                        rx.text("대표자", size="1", color="#6b7280"),
                                        rx.text(
                                            AdminState.doc_selected_customer_info["representative"],
                                            size="2",
                                        ),
                                        spacing="0",
                                    ),
                                    spacing="6",
                                    wrap="wrap",
                                ),
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("주소", size="1", color="#6b7280"),
                                        rx.text(
                                            AdminState.doc_selected_customer_info["address"],
                                            size="2",
                                        ),
                                        spacing="0",
                                    ),
                                    rx.vstack(
                                        rx.text("연락처", size="1", color="#6b7280"),
                                        rx.text(
                                            AdminState.doc_selected_customer_info["phone"],
                                            size="2",
                                        ),
                                        spacing="0",
                                    ),
                                    spacing="6",
                                    wrap="wrap",
                                ),
                                rx.hstack(
                                    rx.badge(
                                        "음식물 ",
                                        AdminState.doc_selected_customer_info["price_food"],
                                        "원/kg",
                                        color_scheme="green",
                                    ),
                                    rx.badge(
                                        "재활용 ",
                                        AdminState.doc_selected_customer_info["price_recycle"],
                                        "원/kg",
                                        color_scheme="blue",
                                    ),
                                    rx.badge(
                                        "일반 ",
                                        AdminState.doc_selected_customer_info["price_general"],
                                        "원/kg",
                                        color_scheme="orange",
                                    ),
                                    spacing="2",
                                    wrap="wrap",
                                ),
                                spacing="2",
                            ),
                            padding="12px",
                            border="1px solid #d1fae5",
                            border_radius="8px",
                            background="#f0fdf4",
                            width="100%",
                        ),
                        # 외주업체(수집운반업체) 정보
                        rx.cond(
                            AdminState.doc_vendor_info.length() > 0,
                            rx.box(
                                rx.vstack(
                                    rx.hstack(
                                        rx.icon("truck", size=16, color="#2563eb"),
                                        rx.text(
                                            "수집운반업체 정보",
                                            size="2", weight="bold", color="#2563eb",
                                        ),
                                        spacing="2",
                                        align="center",
                                    ),
                                    rx.hstack(
                                        rx.vstack(
                                            rx.text("업체명", size="1", color="#6b7280"),
                                            rx.text(
                                                AdminState.doc_vendor_info["biz_name"],
                                                size="2", weight="bold",
                                            ),
                                            spacing="0",
                                        ),
                                        rx.vstack(
                                            rx.text("사업자번호", size="1", color="#6b7280"),
                                            rx.text(
                                                AdminState.doc_vendor_info["biz_no"],
                                                size="2",
                                            ),
                                            spacing="0",
                                        ),
                                        rx.vstack(
                                            rx.text("대표자", size="1", color="#6b7280"),
                                            rx.text(
                                                AdminState.doc_vendor_info["rep"],
                                                size="2",
                                            ),
                                            spacing="0",
                                        ),
                                        spacing="6",
                                        wrap="wrap",
                                    ),
                                    rx.hstack(
                                        rx.vstack(
                                            rx.text("주소", size="1", color="#6b7280"),
                                            rx.text(
                                                AdminState.doc_vendor_info["address"],
                                                size="2",
                                            ),
                                            spacing="0",
                                        ),
                                        rx.vstack(
                                            rx.text("연락처", size="1", color="#6b7280"),
                                            rx.text(
                                                AdminState.doc_vendor_info["contact"],
                                                size="2",
                                            ),
                                            spacing="0",
                                        ),
                                        rx.vstack(
                                            rx.text("입금계좌", size="1", color="#6b7280"),
                                            rx.text(
                                                AdminState.doc_vendor_info["account"],
                                                size="2",
                                            ),
                                            spacing="0",
                                        ),
                                        spacing="6",
                                        wrap="wrap",
                                    ),
                                    spacing="2",
                                ),
                                padding="12px",
                                border="1px solid #bfdbfe",
                                border_radius="8px",
                                background="#eff6ff",
                                width="100%",
                            ),
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                rx.divider(),
                # 3단계: 양식별 동적 입력 필드
                rx.text("3. 수동 입력 항목", weight="bold"),
                rx.cond(
                    AdminState.doc_selected_template_id == 0,
                    rx.text(
                        "위에서 양식을 먼저 선택하면 해당 양식에 필요한 입력 항목이 표시됩니다.",
                        size="1", color="#9ca3af",
                    ),
                    rx.text(
                        "선택된 양식: ",
                        AdminState.doc_selected_category,
                        size="1", color="#6b7280",
                    ),
                ),
                # ── 처리확인서 필드 ──
                rx.cond(
                    AdminState.doc_selected_category == "처리확인서",
                    rx.vstack(
                        rx.text("확인기간", size="2", weight="bold", color="#374151"),
                        rx.hstack(
                            rx.input(
                                placeholder="확인기간 시작 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_start,
                                on_change=AdminState.set_doc_extra_start,
                                width="200px",
                            ),
                            rx.text("~", color="#9ca3af"),
                            rx.input(
                                placeholder="확인기간 종료 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_end,
                                on_change=AdminState.set_doc_extra_end,
                                width="200px",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.text("폐기물 종류", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    WASTE_TYPE_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_waste_type,
                                    on_change=AdminState.set_doc_extra_waste_type,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("처리방법", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    TREATMENT_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_treatment,
                                    on_change=AdminState.set_doc_extra_treatment,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("처리량 (톤)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 5.0",
                                    value=AdminState.doc_extra_quantity,
                                    on_change=AdminState.set_doc_extra_quantity,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                            wrap="wrap",
                        ),
                        rx.vstack(
                            rx.text("비고", size="2", weight="bold", color="#374151"),
                            rx.text_area(
                                placeholder="비고 사항을 입력하세요",
                                value=AdminState.doc_extra_memo,
                                on_change=AdminState.set_doc_extra_memo,
                                height="80px",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                        padding="12px",
                        border="1px solid #e5e7eb",
                        border_radius="8px",
                        background="#f9fafb",
                    ),
                ),
                # ── 2자계약서 필드 ──
                rx.cond(
                    AdminState.doc_selected_category == "2자계약서",
                    rx.vstack(
                        rx.text("계약기간", size="2", weight="bold", color="#374151"),
                        rx.hstack(
                            rx.input(
                                placeholder="계약기간 시작 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_start,
                                on_change=AdminState.set_doc_extra_start,
                                width="200px",
                            ),
                            rx.text("~", color="#9ca3af"),
                            rx.input(
                                placeholder="계약기간 종료 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_end,
                                on_change=AdminState.set_doc_extra_end,
                                width="200px",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.text("폐기물 종류", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    WASTE_TYPE_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_waste_type,
                                    on_change=AdminState.set_doc_extra_waste_type,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("예상 처리량 (월/톤)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 10.0",
                                    value=AdminState.doc_extra_quantity,
                                    on_change=AdminState.set_doc_extra_quantity,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("처리단가 (원/kg)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 120",
                                    value=AdminState.doc_extra_unit_price,
                                    on_change=AdminState.set_doc_extra_unit_price,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("수거주기", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    FREQUENCY_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_frequency,
                                    on_change=AdminState.set_doc_extra_frequency,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                            wrap="wrap",
                        ),
                        rx.vstack(
                            rx.text("특약사항", size="2", weight="bold", color="#374151"),
                            rx.text_area(
                                placeholder="특약사항을 입력하세요",
                                value=AdminState.doc_extra_memo,
                                on_change=AdminState.set_doc_extra_memo,
                                height="80px",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                        padding="12px",
                        border="1px solid #e5e7eb",
                        border_radius="8px",
                        background="#f9fafb",
                    ),
                ),
                # ── 3자계약서 필드 (2자 + 중간처리업체 정보) ──
                rx.cond(
                    AdminState.doc_selected_category == "3자계약서",
                    rx.vstack(
                        rx.text("계약기간", size="2", weight="bold", color="#374151"),
                        rx.hstack(
                            rx.input(
                                placeholder="계약기간 시작 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_start,
                                on_change=AdminState.set_doc_extra_start,
                                width="200px",
                            ),
                            rx.text("~", color="#9ca3af"),
                            rx.input(
                                placeholder="계약기간 종료 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_end,
                                on_change=AdminState.set_doc_extra_end,
                                width="200px",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.text("폐기물 종류", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    WASTE_TYPE_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_waste_type,
                                    on_change=AdminState.set_doc_extra_waste_type,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("예상 처리량 (월/톤)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 10.0",
                                    value=AdminState.doc_extra_quantity,
                                    on_change=AdminState.set_doc_extra_quantity,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("처리단가 (원/kg)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 120",
                                    value=AdminState.doc_extra_unit_price,
                                    on_change=AdminState.set_doc_extra_unit_price,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("수거주기", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    FREQUENCY_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_frequency,
                                    on_change=AdminState.set_doc_extra_frequency,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                            wrap="wrap",
                        ),
                        # 중간처리업체 (3자 전용)
                        rx.box(
                            rx.vstack(
                                rx.text(
                                    "중간처리업체 정보 (병)",
                                    size="2", weight="bold", color="#1e40af",
                                ),
                                rx.hstack(
                                    rx.vstack(
                                        rx.text("업체명", size="2", color="#374151"),
                                        rx.input(
                                            placeholder="중간처리업체명",
                                            value=AdminState.doc_extra_mid_company,
                                            on_change=AdminState.set_doc_extra_mid_company,
                                            width="200px",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("사업자번호", size="2", color="#374151"),
                                        rx.input(
                                            placeholder="000-00-00000",
                                            value=AdminState.doc_extra_mid_bizno,
                                            on_change=AdminState.set_doc_extra_mid_bizno,
                                            width="180px",
                                        ),
                                        spacing="1",
                                    ),
                                    rx.vstack(
                                        rx.text("처리방법", size="2", color="#374151"),
                                        rx.select(
                                            TREATMENT_OPTIONS,
                                            placeholder="선택하세요",
                                            value=AdminState.doc_extra_mid_method,
                                            on_change=AdminState.set_doc_extra_mid_method,
                                            width="180px",
                                        ),
                                        spacing="1",
                                    ),
                                    spacing="4",
                                    wrap="wrap",
                                ),
                                spacing="2",
                            ),
                            padding="12px",
                            border="1px dashed #93c5fd",
                            border_radius="6px",
                            background="#eff6ff",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.text("특약사항", size="2", weight="bold", color="#374151"),
                            rx.text_area(
                                placeholder="특약사항을 입력하세요",
                                value=AdminState.doc_extra_memo,
                                on_change=AdminState.set_doc_extra_memo,
                                height="80px",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                        padding="12px",
                        border="1px solid #e5e7eb",
                        border_radius="8px",
                        background="#f9fafb",
                    ),
                ),
                # ── 견적서 필드 ──
                rx.cond(
                    AdminState.doc_selected_category == "견적서",
                    rx.vstack(
                        rx.hstack(
                            rx.vstack(
                                rx.text("견적일자", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="YYYY-MM-DD",
                                    value=AdminState.doc_extra_quote_date,
                                    on_change=AdminState.set_doc_extra_quote_date,
                                    width="180px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("유효기간", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 30일",
                                    value=AdminState.doc_extra_valid_period,
                                    on_change=AdminState.set_doc_extra_valid_period,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                        ),
                        rx.hstack(
                            rx.vstack(
                                rx.text("폐기물 종류", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    WASTE_TYPE_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_waste_type,
                                    on_change=AdminState.set_doc_extra_waste_type,
                                    width="200px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("예상 수거량 (월/톤)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 10.0",
                                    value=AdminState.doc_extra_quantity,
                                    on_change=AdminState.set_doc_extra_quantity,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("단가 (원/kg)", size="2", weight="bold", color="#374151"),
                                rx.input(
                                    placeholder="예: 120",
                                    value=AdminState.doc_extra_unit_price,
                                    on_change=AdminState.set_doc_extra_unit_price,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            rx.vstack(
                                rx.text("수거주기", size="2", weight="bold", color="#374151"),
                                rx.select(
                                    FREQUENCY_OPTIONS,
                                    placeholder="선택하세요",
                                    value=AdminState.doc_extra_frequency,
                                    on_change=AdminState.set_doc_extra_frequency,
                                    width="150px",
                                ),
                                spacing="1",
                            ),
                            spacing="4",
                            wrap="wrap",
                        ),
                        rx.vstack(
                            rx.text("비고", size="2", weight="bold", color="#374151"),
                            rx.text_area(
                                placeholder="비고 사항을 입력하세요",
                                value=AdminState.doc_extra_memo,
                                on_change=AdminState.set_doc_extra_memo,
                                height="80px",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                        padding="12px",
                        border="1px solid #e5e7eb",
                        border_radius="8px",
                        background="#f9fafb",
                    ),
                ),
                # ── 기타 필드 ──
                rx.cond(
                    AdminState.doc_selected_category == "기타",
                    rx.vstack(
                        rx.text("계약기간", size="2", weight="bold", color="#374151"),
                        rx.hstack(
                            rx.input(
                                placeholder="계약기간 시작 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_start,
                                on_change=AdminState.set_doc_extra_start,
                                width="200px",
                            ),
                            rx.text("~", color="#9ca3af"),
                            rx.input(
                                placeholder="계약기간 종료 (YYYY-MM-DD)",
                                value=AdminState.doc_extra_end,
                                on_change=AdminState.set_doc_extra_end,
                                width="200px",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.vstack(
                            rx.text("특약사항 / 비고", size="2", weight="bold", color="#374151"),
                            rx.text_area(
                                placeholder="특약사항 / 비고를 입력하세요",
                                value=AdminState.doc_extra_memo,
                                on_change=AdminState.set_doc_extra_memo,
                                height="80px",
                                width="100%",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                        padding="12px",
                        border="1px solid #e5e7eb",
                        border_radius="8px",
                        background="#f9fafb",
                    ),
                ),
                rx.divider(),
                # 4단계: 미리보기/발급
                rx.hstack(
                    rx.button(
                        "미리보기 생성",
                        on_click=AdminState.preview_document,
                        color_scheme="blue",
                        size="2",
                    ),
                    rx.button(
                        "PDF 발급",
                        on_click=AdminState.issue_document,
                        color_scheme="green",
                        size="2",
                    ),
                    spacing="2",
                ),
                rx.cond(
                    AdminState.doc_issue_msg != "",
                    rx.text(
                        AdminState.doc_issue_msg,
                        color=rx.cond(AdminState.doc_issue_ok, "green", "red"),
                        weight="bold",
                    ),
                ),
                rx.cond(
                    AdminState.doc_last_issued_pdf != "",
                    rx.link(
                        "발급된 PDF 다운로드",
                        href=AdminState.doc_last_issued_pdf,
                        color="#3b82f6",
                        is_external=True,
                    ),
                ),
                spacing="3",
            ),
            padding="16px",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


# ══════════════════════════════════════════
#  3) 발급내역 패널
# ══════════════════════════════════════════

def _issue_log_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("발급내역", size="5"),
        rx.hstack(
            rx.button(
                "새로고침",
                on_click=AdminState.load_doc_service,
                variant="soft",
                size="2",
            ),
            spacing="2",
        ),
        rx.card(
            rx.cond(
                AdminState.doc_issue_log.length() == 0,
                rx.text("발급된 문서가 없습니다.", color="#9ca3af"),
                rx.vstack(
                    # 헤더
                    rx.hstack(
                        rx.text("발급번호", weight="bold", width="180px"),
                        rx.text("양식", weight="bold", width="140px"),
                        rx.text("거래처", weight="bold", width="200px"),
                        rx.text("발급자", weight="bold", width="120px"),
                        rx.text("발급일시", weight="bold", width="160px"),
                        rx.text("파일", weight="bold", width="80px"),
                        spacing="2",
                        padding="6px",
                        background="#f3f4f6",
                        border_radius="4px",
                        width="100%",
                    ),
                    rx.foreach(
                        AdminState.doc_issue_log,
                        lambda r: rx.hstack(
                            rx.text(r["issue_number"], size="1", width="180px"),
                            rx.text(r["template_name"], size="1", width="140px"),
                            rx.text(r["customer_name"], size="1", width="200px"),
                            rx.text(r["issued_by"], size="1", width="120px"),
                            rx.text(r["issued_at"], size="1", width="160px"),
                            rx.link(
                                "PDF",
                                href=r["file_path"],
                                is_external=True,
                                width="80px",
                            ),
                            spacing="2",
                            padding="6px",
                            border_bottom="1px solid #e5e7eb",
                            width="100%",
                        ),
                    ),
                    spacing="0",
                    width="100%",
                ),
            ),
            padding="16px",
            width="100%",
        ),
        spacing="3",
        width="100%",
    )


# ══════════════════════════════════════════
#  메인 패널 (hq_admin.py에서 호출)
# ══════════════════════════════════════════

def doc_service_hq_panel() -> rx.Component:
    """본사관리자 '문서서비스' 탭 본체."""
    return rx.vstack(
        rx.heading("문서서비스", size="6"),
        _doc_sub_tab_bar(),
        rx.divider(),
        rx.cond(
            AdminState.doc_sub_tab == "문서발급",
            _issue_panel(),
        ),
        rx.cond(
            AdminState.doc_sub_tab == "양식관리",
            _template_mgmt_panel(),
        ),
        rx.cond(
            AdminState.doc_sub_tab == "발급내역",
            _issue_log_panel(),
        ),
        spacing="3",
        width="100%",
        padding="16px",
    )
