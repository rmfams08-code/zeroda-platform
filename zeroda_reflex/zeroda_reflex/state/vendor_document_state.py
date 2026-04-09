"""
================================================================
zeroda 외주업체 문서함 State
================================================================
저장 위치 : zeroda_reflex/zeroda_reflex/state/vendor_document_state.py
사용 페이지: pages/vendor_documents.py (/vendor_documents 라우트)
의존     : utils/document_service.py (render_contract_for_vendor,
           render_quote_for_vendor, issue_document)

⚠️ 사례5 준수
  - Reflex Var + 문자열 '+' 결합 금지
  - rx.window_alert 금지 → rx.toast 사용
  - State 이벤트 핸들러 언더스코어 접두어 금지
  - get_state(AuthState) 금지 → 상속으로 직접 접근
  - quote_months 는 str (EventHandlerArgTypeMismatchError 방지)
================================================================
"""
from __future__ import annotations

import json

import reflex as rx

from ..utils import document_service as docsvc
from ..utils.database import db_get
from .auth_state import AuthState


class VendorDocumentState(AuthState):
    # ── 공통 ──
    sub_tab: str = "계약서"          # "계약서" | "견적서" | "발급내역"
    vendor_customers: list[str] = []
    selected_customer: str = ""

    # ── 계약서 ──
    contract_start: str = ""
    contract_end: str = ""
    contract_preview_html: str = ""
    contract_pdf_path: str = ""

    # ── 견적서 ──
    quote_mode: str = "auto"         # "auto" | "manual"
    quote_months: str = "1"          # str — on_change는 str로 전달됨
    quote_remark: str = ""
    quote_items_json: str = "[]"
    quote_preview_html: str = ""
    quote_pdf_path: str = ""

    # ── 발급내역 ──
    issued_list: list[dict] = []

    # ── 임시 보관 (발급 전 미리보기 결과) ──
    last_contract_html: str = ""
    last_contract_doc_no: str = ""
    last_contract_payload: str = ""
    last_quote_html: str = ""
    last_quote_doc_no: str = ""
    last_quote_payload: str = ""
    last_quote_total: int = 0
    last_quote_valid_until: str = ""

    # ── 거래처 조회 UI 상태 (vendor 스코프) ──
    vcust_search_query: str = ""
    vcust_found: bool = False
    vcust_is_new: bool = False
    vcust_in_schedule: bool = True
    vcust_approve_msg: str = ""
    vcust_found_name: str = ""
    vcust_found_bizno: str = ""
    vcust_found_rep: str = ""
    vcust_found_addr: str = ""
    vcust_found_phone: str = ""
    new_vcust_name: str = ""
    new_vcust_bizno: str = ""
    new_vcust_rep: str = ""
    new_vcust_addr: str = ""
    new_vcust_phone: str = ""
    new_vcust_biz_type: str = ""
    new_vcust_biz_item: str = ""

    # =====================================================
    # 페이지 on_load 핸들러
    # =====================================================
    async def on_vendor_doc_load(self):
        """페이지 진입 시 권한 확인 + 거래처 목록 로드."""
        if not self.is_authenticated:
            return rx.redirect("/")
        if self.user_role not in ("vendor_admin", "vendor"):
            return rx.redirect("/")
        await self.load_vendor_customers()

    # =====================================================
    # 거래처 옵션 로드 (자기 vendor만)
    # =====================================================
    async def load_vendor_customers(self):
        rows = db_get("customer_info", {"vendor": self.user_vendor or ""})
        self.vendor_customers = [r["name"] for r in rows]

    # =====================================================
    # 거래처 조회 + 신규 승인 (vendor 스코프)
    # =====================================================
    async def search_vcustomer_for_contract(self):
        """상호명/사업자번호로 거래처 조회 (자기 vendor 스코프)."""
        if not self.vcust_search_query:
            yield rx.toast.warning("상호명 또는 사업자번호를 입력하세요")
            return
        result = docsvc.search_customer_by_query(
            vendor=self.user_vendor or "",
            query=self.vcust_search_query,
        )
        if result:
            self.vcust_found = True
            self.vcust_is_new = False
            self.vcust_found_name = result.get("name", "")
            self.vcust_found_bizno = result.get("biz_no", "")
            self.vcust_found_rep = result.get("rep", "")
            self.vcust_found_addr = result.get("addr", "")
            self.vcust_found_phone = result.get("phone", "")
            self.selected_customer = result.get("name", "")
            self.vcust_in_schedule = docsvc.is_customer_in_schedule(
                vendor=self.user_vendor or "",
                customer_name=result.get("name", ""),
            )
            self.vcust_approve_msg = ""
        else:
            self.vcust_found = False
            self.vcust_is_new = True
            self.vcust_found_name = ""
            self.new_vcust_name = self.vcust_search_query
            self.vcust_in_schedule = False
            self.vcust_approve_msg = ""

    async def approve_new_vcustomer(self):
        """신규 거래처 승인 → customer_info INSERT (vendor 스코프) → 드롭다운 새로고침."""
        if not self.new_vcust_name:
            yield rx.toast.warning("상호명을 입력하세요")
            return
        ok = docsvc.create_customer_in_db(
            vendor=self.user_vendor or "",
            name=self.new_vcust_name,
            biz_no=self.new_vcust_bizno,
            rep=self.new_vcust_rep,
            addr=self.new_vcust_addr,
            phone=self.new_vcust_phone,
            biz_type=self.new_vcust_biz_type,
            biz_item=self.new_vcust_biz_item,
        )
        if ok:
            self.vcust_approve_msg = self.new_vcust_name + " 거래처 등록 완료"
            self.selected_customer = self.new_vcust_name
            self.vcust_found = True
            self.vcust_is_new = False
            self.vcust_found_name = self.new_vcust_name
            self.vcust_found_bizno = self.new_vcust_bizno
            self.vcust_found_rep = self.new_vcust_rep
            self.vcust_found_addr = self.new_vcust_addr
            self.vcust_found_phone = self.new_vcust_phone
            self.vcust_in_schedule = False
            yield rx.toast.success(self.vcust_approve_msg)
            await self.load_vendor_customers()
        else:
            yield rx.toast.error("거래처 등록 실패 (이미 존재하거나 입력 오류)")

    # =====================================================
    # 계약서
    # =====================================================
    async def preview_contract(self):
        if not self.selected_customer:
            yield rx.toast.warning("거래처를 선택하세요")
            return
        try:
            result = docsvc.render_contract_for_vendor(
                vendor=self.user_vendor or "",
                customer_name=self.selected_customer,
                contract_start=self.contract_start or None,
                contract_end=self.contract_end or None,
            )
            self.contract_preview_html = result["html"]
            self.last_contract_html = result["html"]
            self.last_contract_doc_no = result["doc_no"]
            self.last_contract_payload = json.dumps(result["payload"], ensure_ascii=False)
        except Exception as e:
            yield rx.toast.error(f"계약서 생성 실패: {e}")

    async def issue_contract_pdf(self):
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
                created_by=self.user_id or "",
            )
            self.contract_pdf_path = pdf
            yield rx.toast.success(f"계약서 발급 완료: {self.last_contract_doc_no}")
        except Exception as e:
            yield rx.toast.error(f"계약서 발급 실패: {e}")

    # =====================================================
    # 견적서
    # =====================================================
    async def preview_quote(self):
        if not self.selected_customer:
            yield rx.toast.warning("거래처를 선택하세요")
            return
        items = None
        if self.quote_mode == "manual":
            try:
                items = json.loads(self.quote_items_json or "[]")
            except json.JSONDecodeError:
                yield rx.toast.warning("수기 품목 JSON 형식이 잘못되었습니다")
                return
        try:
            result = docsvc.render_quote_for_vendor(
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

    async def issue_quote_pdf(self):
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
    # 발급내역 (자기 vendor만)
    # =====================================================
    async def load_issued_list_for_vendor(self):
        rows = db_get("issued_documents", {"vendor": self.user_vendor or ""})
        rows.sort(key=lambda r: r.get("issued_date", ""), reverse=True)
        self.issued_list = rows[:200]
