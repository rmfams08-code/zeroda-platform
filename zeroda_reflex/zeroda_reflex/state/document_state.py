"""
================================================================
zeroda 문서자동화 State (Reflex)
================================================================
저장 위치 : zeroda_reflex/zeroda_reflex/state/document_state.py
사용 페이지: pages/documents.py (/documents 라우트)
의존     : utils/document_service.py, utils/database.py

⚠️ 사례5 절대 준수 사항
  1) Reflex Var 와 Python 문자열 '+' 결합 금지
     → 반드시 f-string 또는 .to(str) 사용
  2) 함수명/state 클래스명 변경 금지 (페이지에서 import)
  3) DB 컬럼명은 customer_info 영문 컬럼 그대로
  4) AuthState 실제 필드명 사용: user_vendor (vendor 아님), user_id (username 아님)

검증
  python -c "import ast; ast.parse(open('zeroda_reflex/zeroda_reflex/state/document_state.py',encoding='utf-8').read())"
================================================================
"""
from __future__ import annotations

import json

import reflex as rx

from ..utils import document_service as docsvc
from ..utils.database import db_get
from .auth_state import AuthState


class DocumentState(AuthState):
    # ── 공통 ──
    sub_tab: str = "계약서"        # "계약서" | "견적서" | "발급내역"
    customer_options: list[str] = []
    selected_customer: str = ""

    # ── 계약서 ──
    contract_template_id: int = 0   # 0 = 표준 빌트인
    contract_start: str = ""
    contract_end: str = ""
    contract_preview_html: str = ""
    contract_pdf_path: str = ""

    # ── 견적서 ──
    quote_mode: str = "auto"        # "auto" | "manual"
    quote_months: str = "1"
    quote_remark: str = ""
    quote_items_json: str = "[]"    # 수기모드 입력 (JSON 문자열)
    quote_preview_html: str = ""
    quote_pdf_path: str = ""

    # ── 발급내역 ──
    issued_rows: list[dict] = []

    # ── 임시 보관 (발급 전 미리보기 결과) ──
    last_contract_html: str = ""
    last_contract_doc_no: str = ""
    last_contract_payload: str = ""   # JSON 직렬화
    last_quote_html: str = ""
    last_quote_doc_no: str = ""
    last_quote_payload: str = ""      # JSON 직렬화
    last_quote_total: int = 0
    last_quote_valid_until: str = ""

    # =====================================================
    # 페이지 on_load 핸들러
    # =====================================================
    async def on_doc_load(self):
        """페이지 진입 시 거래처 목록 + 인증 확인."""
        if not self.is_authenticated:
            return rx.redirect("/")
        await self.load_customers()

    # =====================================================
    # 거래처 옵션 로드
    # =====================================================
    async def load_customers(self):
        rows = db_get("customer_info", {"vendor": self.user_vendor or ""})
        self.customer_options = [r["name"] for r in rows]

    # =====================================================
    # 계약서
    # =====================================================
    async def generate_contract(self):
        if not self.selected_customer:
            yield rx.toast.warning("거래처를 선택하세요")
            return
        try:
            result = docsvc.render_contract(
                vendor=self.user_vendor or "",
                customer_name=self.selected_customer,
                template_id=self.contract_template_id or None,
                contract_start=self.contract_start or None,
                contract_end=self.contract_end or None,
            )
            self.contract_preview_html = result["html"]
            self.last_contract_html = result["html"]
            self.last_contract_doc_no = result["doc_no"]
            self.last_contract_payload = json.dumps(result["payload"], ensure_ascii=False)
        except Exception as e:
            yield rx.toast.error(f"계약서 생성 실패: {e}")

    async def issue_contract(self):
        if not self.last_contract_html:
            yield rx.toast.warning("먼저 [미리보기 생성]을 눌러주세요")
            return
        try:
            payload = json.loads(self.last_contract_payload or "{}")
            pdf = docsvc.issue_document(
                vendor=self.user_vendor or "",
                doc_type="contract",
                customer_name=self.selected_customer,
                html=self.last_contract_html,
                doc_no=self.last_contract_doc_no,
                payload=payload,
                template_id=self.contract_template_id or None,
                created_by=self.user_id or "",
            )
            self.contract_pdf_path = pdf
            yield rx.toast.success(f"계약서 발급 완료: {self.last_contract_doc_no}")
        except Exception as e:
            yield rx.toast.error(f"계약서 발급 실패: {e}")

    # =====================================================
    # 견적서
    # =====================================================
    async def generate_quote(self):
        if not self.selected_customer:
            yield rx.toast.warning("거래처를 선택하세요")
            return
        items = None
        if self.quote_mode == "manual":
            try:
                items = json.loads(self.quote_items_json or "[]")
            except json.JSONDecodeError:
                yield rx.toast.warning("수기 품목 JSON 형식이 잘못되었습니다")
        try:
            result = docsvc.render_quote(
                vendor=self.user_vendor or "",
                customer_name=self.selected_customer,
                items=items,
                auto_months=int(self.quote_months or 1),
                remark=self.quote_remark or "",
            )
            self.quote_preview_html = result["html"]
            self.last_quote_html = result["html"]
            self.last_quote_doc_no = result["doc_no"]
            self.last_quote_payload = json.dumps(result["payload"], ensure_ascii=False)
            self.last_quote_total = int(result["total"])
            self.last_quote_valid_until = result["valid_until"]
        except Exception as e:
            yield rx.toast.error(f"견적서 생성 실패: {e}")

    async def issue_quote(self):
        if not self.last_quote_html:
            yield rx.toast.warning("먼저 [미리보기 생성]을 눌러주세요")
            return
        try:
            payload = json.loads(self.last_quote_payload or "{}")
            pdf = docsvc.issue_document(
                vendor=self.user_vendor or "",
                doc_type="quote",
                customer_name=self.selected_customer,
                html=self.last_quote_html,
                doc_no=self.last_quote_doc_no,
                payload=payload,
                valid_until=self.last_quote_valid_until,
                total_amount=self.last_quote_total,
                created_by=self.user_id or "",
            )
            self.quote_pdf_path = pdf
            yield rx.toast.success(f"견적서 발급 완료: {self.last_quote_doc_no}")
        except Exception as e:
            yield rx.toast.error(f"견적서 발급 실패: {e}")

    # =====================================================
    # 발급내역
    # =====================================================
    async def load_issued(self):
        rows = db_get("issued_documents", {"vendor": self.user_vendor or ""})
        rows.sort(key=lambda r: r.get("issued_date", ""), reverse=True)
        self.issued_rows = rows[:200]
