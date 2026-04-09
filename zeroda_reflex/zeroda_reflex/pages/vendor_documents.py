"""
================================================================
zeroda 외주업체 문서함 페이지 — /vendor_documents
================================================================
저장 위치 : zeroda_reflex/zeroda_reflex/pages/vendor_documents.py
라우트    : /vendor_documents  (vendor_admin 전용)
의존     : state/vendor_document_state.py, state/auth_state.py

⚠️ 사례5 절대 준수
  - Reflex Var + 문자열 '+' 결합 금지
  - f-string 내 Reflex Var 직접 삽입 금지 (rx.text 다중 인자 사용)
  - state 메서드 시그니처는 vendor_document_state.py 와 동일
================================================================
"""
import reflex as rx

from ..state.vendor_document_state import VendorDocumentState


# ============================================================
# 내부 패널 컴포넌트
# ============================================================

def _vendor_customer_search_block() -> rx.Component:
    """거래처 조회 + 자동 채움 + 신규 등록 + 수거일정 배지 (외주업체용)."""
    return rx.vstack(
        rx.hstack(
            rx.input(
                placeholder="상호명 또는 사업자번호 입력",
                value=VendorDocumentState.vcust_search_query,
                on_change=VendorDocumentState.set_vcust_search_query,
                width="260px",
            ),
            rx.button(
                "거래처 조회",
                on_click=VendorDocumentState.search_vcustomer_for_contract,
                color_scheme="blue",
                size="2",
            ),
            spacing="2",
            align="center",
        ),
        # ── 기존 거래처 조회 결과 ──
        rx.cond(
            VendorDocumentState.vcust_found,
            rx.vstack(
                rx.hstack(
                    rx.badge("✅ 기존 거래처", color_scheme="green"),
                    rx.cond(
                        ~VendorDocumentState.vcust_in_schedule,
                        rx.badge("⚠️ 수거일정 미등록", color_scheme="orange"),
                    ),
                    spacing="2",
                ),
                rx.hstack(
                    rx.text("상호: ", VendorDocumentState.vcust_found_name, weight="bold"),
                    rx.text("사업자번호: ", VendorDocumentState.vcust_found_bizno),
                    spacing="4",
                ),
                rx.hstack(
                    rx.text("대표자: ", VendorDocumentState.vcust_found_rep),
                    rx.text("연락처: ", VendorDocumentState.vcust_found_phone),
                    spacing="4",
                ),
                rx.text("주소: ", VendorDocumentState.vcust_found_addr),
                spacing="1",
                padding="8px",
                background="#f0fdf4",
                border_radius="6px",
                width="100%",
            ),
        ),
        # ── 신규 거래처 폼 ──
        rx.cond(
            VendorDocumentState.vcust_is_new,
            rx.vstack(
                rx.hstack(
                    rx.badge("🆕 신규 거래처", color_scheme="red"),
                    rx.badge("⚠️ 수거일정 미등록", color_scheme="orange"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.input(placeholder="상호명 *", value=VendorDocumentState.new_vcust_name,
                             on_change=VendorDocumentState.set_new_vcust_name, width="200px"),
                    rx.input(placeholder="사업자번호", value=VendorDocumentState.new_vcust_bizno,
                             on_change=VendorDocumentState.set_new_vcust_bizno, width="160px"),
                    spacing="2",
                ),
                rx.hstack(
                    rx.input(placeholder="대표자", value=VendorDocumentState.new_vcust_rep,
                             on_change=VendorDocumentState.set_new_vcust_rep, width="160px"),
                    rx.input(placeholder="연락처", value=VendorDocumentState.new_vcust_phone,
                             on_change=VendorDocumentState.set_new_vcust_phone, width="160px"),
                    spacing="2",
                ),
                rx.input(placeholder="주소", value=VendorDocumentState.new_vcust_addr,
                         on_change=VendorDocumentState.set_new_vcust_addr, width="100%"),
                rx.hstack(
                    rx.input(placeholder="업태", value=VendorDocumentState.new_vcust_biz_type,
                             on_change=VendorDocumentState.set_new_vcust_biz_type, width="160px"),
                    rx.input(placeholder="종목", value=VendorDocumentState.new_vcust_biz_item,
                             on_change=VendorDocumentState.set_new_vcust_biz_item, width="160px"),
                    spacing="2",
                ),
                rx.button(
                    "거래처 승인 및 등록",
                    on_click=VendorDocumentState.approve_new_vcustomer,
                    color_scheme="green",
                    size="2",
                ),
                spacing="2",
                padding="8px",
                background="#fff7ed",
                border_radius="6px",
                width="100%",
            ),
        ),
        rx.cond(
            VendorDocumentState.vcust_approve_msg != "",
            rx.text(VendorDocumentState.vcust_approve_msg, color="green", weight="bold"),
        ),
        border="1px solid #d1d5db",
        border_radius="8px",
        padding="12px",
        width="100%",
    )


def _vendor_contract_panel() -> rx.Component:
    return rx.vstack(
        _vendor_customer_search_block(),
        rx.hstack(
            rx.select(
                VendorDocumentState.vendor_customers,
                placeholder="거래처 선택",
                value=VendorDocumentState.selected_customer,
                on_change=VendorDocumentState.set_selected_customer,
            ),
            rx.input(
                placeholder="시작일 YYYY-MM-DD",
                value=VendorDocumentState.contract_start,
                on_change=VendorDocumentState.set_contract_start,
            ),
            rx.input(
                placeholder="종료일 YYYY-MM-DD",
                value=VendorDocumentState.contract_end,
                on_change=VendorDocumentState.set_contract_end,
            ),
            rx.button(
                "미리보기 생성",
                on_click=VendorDocumentState.preview_contract,
                color_scheme="blue",
            ),
            rx.button(
                "PDF 발급",
                on_click=VendorDocumentState.issue_contract_pdf,
                color_scheme="green",
            ),
            spacing="2",
            wrap="wrap",
        ),
        rx.cond(
            VendorDocumentState.contract_pdf_path != "",
            rx.text(
                "발급 PDF: ",
                VendorDocumentState.contract_pdf_path,
                color="green",
            ),
        ),
        rx.box(
            rx.html(VendorDocumentState.contract_preview_html),
            border="1px solid #ddd",
            padding="12px",
            max_height="600px",
            overflow="auto",
            width="100%",
        ),
        width="100%",
    )


def _vendor_quote_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(
                VendorDocumentState.vendor_customers,
                placeholder="거래처 선택",
                value=VendorDocumentState.selected_customer,
                on_change=VendorDocumentState.set_selected_customer,
            ),
            rx.select(
                ["auto", "manual"],
                value=VendorDocumentState.quote_mode,
                on_change=VendorDocumentState.set_quote_mode,
            ),
            rx.input(
                placeholder="개월수(자동모드, 숫자 입력)",
                value=VendorDocumentState.quote_months.to(str),
                on_change=VendorDocumentState.set_quote_months,
            ),
            rx.button(
                "미리보기 생성",
                on_click=VendorDocumentState.preview_quote,
                color_scheme="blue",
            ),
            rx.button(
                "PDF 발급",
                on_click=VendorDocumentState.issue_quote_pdf,
                color_scheme="green",
            ),
            spacing="2",
            wrap="wrap",
        ),
        rx.cond(
            VendorDocumentState.quote_mode == "manual",
            rx.text_area(
                placeholder='[{"name":"음식물","spec":"kg","qty":300,"price":250},...]',
                value=VendorDocumentState.quote_items_json,
                on_change=VendorDocumentState.set_quote_items_json,
                height="120px",
            ),
        ),
        rx.input(
            placeholder="비고",
            value=VendorDocumentState.quote_remark,
            on_change=VendorDocumentState.set_quote_remark,
        ),
        rx.cond(
            VendorDocumentState.quote_pdf_path != "",
            rx.text(
                "발급 PDF: ",
                VendorDocumentState.quote_pdf_path,
                color="green",
            ),
        ),
        rx.box(
            rx.html(VendorDocumentState.quote_preview_html),
            border="1px solid #ddd",
            padding="12px",
            max_height="600px",
            overflow="auto",
            width="100%",
        ),
        width="100%",
    )


def _vendor_issued_panel() -> rx.Component:
    return rx.vstack(
        rx.button(
            "새로고침",
            on_click=VendorDocumentState.load_issued_list_for_vendor,
        ),
        rx.foreach(
            VendorDocumentState.issued_list,
            lambda r: rx.hstack(
                rx.text(r["doc_no"], width="160px"),
                rx.text(r["doc_type"], width="80px"),
                rx.text(r["customer_name"], width="200px"),
                rx.text(r["issued_date"], width="120px"),
                rx.text(r["total_amount"].to(str), " 원", width="120px"),
                rx.link(
                    "PDF",
                    href=r["pdf_path"].to(str),
                    is_external=True,
                ),
                spacing="2",
            ),
        ),
        width="100%",
    )


def _vendor_doc_center_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("외주업체 문서함", size="6"),
        rx.hstack(
            rx.button(
                "계약서",
                on_click=VendorDocumentState.set_sub_tab("계약서"),
            ),
            rx.button(
                "견적서",
                on_click=VendorDocumentState.set_sub_tab("견적서"),
            ),
            rx.button(
                "발급내역",
                on_click=[
                    VendorDocumentState.set_sub_tab("발급내역"),
                    VendorDocumentState.load_issued_list_for_vendor,
                ],
            ),
            spacing="3",
        ),
        rx.divider(),
        rx.cond(
            VendorDocumentState.sub_tab == "계약서",
            _vendor_contract_panel(),
        ),
        rx.cond(
            VendorDocumentState.sub_tab == "견적서",
            _vendor_quote_panel(),
        ),
        rx.cond(
            VendorDocumentState.sub_tab == "발급내역",
            _vendor_issued_panel(),
        ),
        on_mount=VendorDocumentState.load_vendor_customers,
        spacing="3",
        width="100%",
        padding="24px",
    )


# ============================================================
# 페이지 진입점
# ============================================================

def vendor_documents_page() -> rx.Component:
    return rx.cond(
        VendorDocumentState.is_authenticated
        & (
            (VendorDocumentState.user_role == "vendor_admin")
            | (VendorDocumentState.user_role == "vendor")
        ),
        _vendor_doc_center_panel(),
        rx.vstack(
            rx.text("외주업체 관리자만 접근 가능합니다.", color="#ef4444"),
            rx.link("← 로그인으로", href="/", color="#3b82f6"),
            padding="40px",
        ),
    )
