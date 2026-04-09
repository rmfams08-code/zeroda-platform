"""
================================================================
zeroda 문서함 페이지 — /documents
================================================================
저장 위치 : zeroda_reflex/zeroda_reflex/pages/documents.py
라우트    : /documents  (본사관리자 전용)
의존     : state/document_state.py, state/auth_state.py

⚠️ 사례5 절대 준수
  - Reflex Var + 문자열 '+' 결합 금지
  - f-string 내 Reflex Var 직접 삽입 금지 (rx.text 다중 인자 사용)
  - state 메서드 시그니처는 document_state.py 와 동일
================================================================
"""
import reflex as rx

from ..state.document_state import DocumentState


# ============================================================
# 내부 패널 컴포넌트
# ============================================================

def _contract_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(
                DocumentState.customer_options,
                placeholder="거래처 선택",
                value=DocumentState.selected_customer,
                on_change=DocumentState.set_selected_customer,
            ),
            rx.input(
                placeholder="시작일 YYYY-MM-DD",
                value=DocumentState.contract_start,
                on_change=DocumentState.set_contract_start,
            ),
            rx.input(
                placeholder="종료일 YYYY-MM-DD",
                value=DocumentState.contract_end,
                on_change=DocumentState.set_contract_end,
            ),
            rx.button(
                "미리보기 생성",
                on_click=DocumentState.generate_contract,
                color_scheme="blue",
            ),
            rx.button(
                "PDF 발급",
                on_click=DocumentState.issue_contract,
                color_scheme="green",
            ),
            spacing="2",
        ),
        rx.cond(
            DocumentState.contract_pdf_path != "",
            rx.text(
                "발급 PDF: ",
                DocumentState.contract_pdf_path,
                color="green",
            ),
        ),
        rx.box(
            rx.html(DocumentState.contract_preview_html),
            border="1px solid #ddd",
            padding="12px",
            max_height="600px",
            overflow="auto",
            width="100%",
        ),
        width="100%",
    )


def _quote_panel() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.select(
                DocumentState.customer_options,
                placeholder="거래처 선택",
                value=DocumentState.selected_customer,
                on_change=DocumentState.set_selected_customer,
            ),
            rx.select(
                ["auto", "manual"],
                value=DocumentState.quote_mode,
                on_change=DocumentState.set_quote_mode,
            ),
            rx.input(
                placeholder="개월수(자동모드, 숫자 입력)",
                value=DocumentState.quote_months.to(str),
                on_change=DocumentState.set_quote_months,
            ),
            rx.button(
                "미리보기 생성",
                on_click=DocumentState.generate_quote,
                color_scheme="blue",
            ),
            rx.button(
                "PDF 발급",
                on_click=DocumentState.issue_quote,
                color_scheme="green",
            ),
            spacing="2",
        ),
        rx.cond(
            DocumentState.quote_mode == "manual",
            rx.text_area(
                placeholder='[{"name":"음식물","spec":"kg","qty":300,"price":250},...]',
                value=DocumentState.quote_items_json,
                on_change=DocumentState.set_quote_items_json,
                height="120px",
            ),
        ),
        rx.input(
            placeholder="비고",
            value=DocumentState.quote_remark,
            on_change=DocumentState.set_quote_remark,
        ),
        rx.cond(
            DocumentState.quote_pdf_path != "",
            rx.text(
                "발급 PDF: ",
                DocumentState.quote_pdf_path,
                color="green",
            ),
        ),
        rx.box(
            rx.html(DocumentState.quote_preview_html),
            border="1px solid #ddd",
            padding="12px",
            max_height="600px",
            overflow="auto",
            width="100%",
        ),
        width="100%",
    )


def _issued_panel() -> rx.Component:
    return rx.vstack(
        rx.button("새로고침", on_click=DocumentState.load_issued),
        rx.foreach(
            DocumentState.issued_rows,
            lambda r: rx.hstack(
                rx.text(r["doc_no"], width="120px"),
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


def _doc_center_panel() -> rx.Component:
    return rx.vstack(
        rx.heading("문서함", size="6"),
        rx.hstack(
            rx.button("계약서", on_click=DocumentState.set_sub_tab("계약서")),
            rx.button("견적서", on_click=DocumentState.set_sub_tab("견적서")),
            rx.button(
                "발급내역",
                on_click=[
                    DocumentState.set_sub_tab("발급내역"),
                    DocumentState.load_issued,
                ],
            ),
            spacing="3",
        ),
        rx.divider(),
        rx.cond(DocumentState.sub_tab == "계약서", _contract_panel()),
        rx.cond(DocumentState.sub_tab == "견적서", _quote_panel()),
        rx.cond(DocumentState.sub_tab == "발급내역", _issued_panel()),
        on_mount=DocumentState.load_customers,
        spacing="3",
        width="100%",
    )


# ============================================================
# 페이지 진입점
# ============================================================

def documents_page() -> rx.Component:
    return rx.cond(
        DocumentState.is_authenticated & (DocumentState.user_role == "hq_admin"),
        _doc_center_panel(),
        rx.vstack(
            rx.text("본사관리자만 접근 가능합니다.", color="#ef4444"),
            rx.link("← 로그인으로", href="/", color="#3b82f6"),
            padding="40px",
        ),
    )
