"""
================================================================
zeroda 문서자동화 서비스
================================================================
저장 위치 : zeroda_reflex/zeroda_reflex/utils/document_service.py
호출 주체 : DocumentState (state/document_state.py) — 디스패치 신규 작성
의존     : utils/database.py, contract_templates / issued_documents 테이블

⚠️ 사례5 준수
  - Reflex Var 와 절대 직접 결합하지 않음 (이 파일은 순수 Python, Var 사용 안 함)
  - 함수명/시그니처 변경 금지 (state에서 import)
  - DB 컬럼명은 database.py 의 save_customer 와 동일하게 (rep, addr, biz_no ...)

검증 명령
  python -c "import ast; ast.parse(open('zeroda_reflex/zeroda_reflex/utils/document_service.py',encoding='utf-8').read())"
================================================================
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .database import get_db, db_get, get_vendor_info

# ─────────────────────────────────────────────
# wkhtmltopdf 래퍼 (pdf_export.py에 html_to_pdf 없으므로 여기서 정의)
# ─────────────────────────────────────────────
_log = logging.getLogger(__name__)


def html_to_pdf(html: str, out_path: str) -> bool:
    """wkhtmltopdf subprocess로 HTML → PDF 변환."""
    try:
        subprocess.run(
            ["wkhtmltopdf", "--encoding", "utf-8",
             "--quiet", "--disable-smart-shrinking",
             "-", out_path],
            input=html.encode("utf-8"),
            check=True,
            timeout=30,
        )
        return True
    except FileNotFoundError:
        _log.error("[document_service] wkhtmltopdf not found. apt-get install -y wkhtmltopdf")
        return False
    except subprocess.CalledProcessError as e:
        _log.error("[document_service] wkhtmltopdf error: %s", e)
        return False
    except Exception as e:
        _log.error("[document_service] html_to_pdf unexpected error: %s", e)
        return False


# ─────────────────────────────────────────────
# 경로 상수
# ─────────────────────────────────────────────
BASE_DIR        = Path("/opt/zeroda-platform")
TEMPLATE_DIR    = BASE_DIR / "assets" / "doc_templates"
ISSUED_PDF_DIR  = BASE_DIR / "assets" / "issued_documents"
SEAL_DIR        = BASE_DIR / "assets" / "seals"
ISSUED_PDF_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. 거래처 정보 조회 (계약서/견적서 공통)
# ============================================================
def fetch_customer(vendor: str, customer_name: str) -> dict[str, Any]:
    rows = db_get(
        "customer_info",
        {"vendor": vendor, "name": customer_name},
    )
    if not rows:
        raise ValueError(f"customer_info에 {vendor}/{customer_name} 없음")
    return dict(rows[0])


def fetch_vendor_company(vendor: str) -> dict[str, Any]:
    """수탁사(=하영자원 등) 정보. 1차: vendor_info 테이블, 폴백: 환경변수."""
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM vendor_info WHERE vendor=? LIMIT 1", (vendor,)
        )
        row = cur.fetchone()
        if row:
            d = dict(row)
            # vendor_info 컬럼명 → 표준 키 매핑
            # (biz_name→company_name, rep→ceo, contact→phone, address/biz_no 동일)
            return {
                "company_name": d.get("biz_name") or d.get("company_name") or vendor,
                "ceo":          d.get("rep") or d.get("ceo", ""),
                "biz_no":       d.get("biz_no", ""),
                "address":      d.get("address", ""),
                "phone":        d.get("contact") or d.get("phone", ""),
                "account":      d.get("account", "") or "",
            }
    except Exception:
        pass  # vendor_info 테이블이 없는 환경 폴백 (SQLite OperationalError / PG UndefinedTable 모두 처리)
    finally:
        conn.close()

    return {
        "company_name": vendor,
        "ceo":          os.getenv("VENDOR_CEO", ""),
        "biz_no":       os.getenv("VENDOR_BIZNO", ""),
        "address":      os.getenv("VENDOR_ADDR", ""),
        "phone":        os.getenv("VENDOR_PHONE", ""),
        "account":      os.getenv("VENDOR_ACCOUNT", ""),
    }


def seal_path(vendor: str) -> str:
    """직인 경로 조회 (멀티테넌트).

    우선순위:
      1차: vendor_info.stamp_path (DB 등록 경로 — 본사/업체관리자 직인 업로드 UI가 기록)
      2차: {SEAL_DIR}/{vendor}.png 파일시스템 폴백 (레거시 규약)
      3차: "" (빈 문자열 → 템플릿은 <img src=""> 로 렌더, 도장 빈칸)

    참고: 실제 업로드 경로는 /opt/zeroda-platform/storage/stamps/ 로
         database.set_vendor_stamp() 가 기록. SEAL_DIR 과 엇갈리므로
         DB 조회가 반드시 우선이어야 한다.
    """
    # 1차: DB 우선
    try:
        info = get_vendor_info(vendor) or {}
        db_path = info.get("stamp_path") or ""
        if db_path and os.path.exists(db_path):
            return db_path
    except Exception as e:
        _log.warning("[document_service] seal_path DB lookup 실패 (%s): %s", vendor, e)
    # 2차: 파일시스템 폴백
    p = SEAL_DIR / f"{vendor}.png"
    if p.exists():
        return str(p)
    # 3차: 없음
    return ""


# ============================================================
# 2. 계약서 생성 (표준 HTML 템플릿)
# ============================================================
def render_contract(
    vendor: str,
    customer_name: str,
    template_id: int | None = None,
    contract_start: str | None = None,
    contract_end: str | None = None,
) -> dict[str, Any]:
    """
    return: {"html": "...", "doc_no": "C-2026-0001", "payload": {...}}
    """
    cust  = fetch_customer(vendor, customer_name)
    biz   = fetch_vendor_company(vendor)
    today = date.today()

    start = contract_start or today.isoformat()
    end   = contract_end or (today.replace(year=today.year + 1)).isoformat()

    payload = {
        "거래처명":          cust.get("name", ""),
        "사업자번호":        cust.get("biz_no", ""),
        "대표자":            cust.get("rep", ""),
        "주소":              cust.get("addr", ""),
        "업태":              cust.get("biz_type", ""),
        "종목":              cust.get("biz_item", ""),
        "전화":              cust.get("phone", ""),
        "이메일":            cust.get("email", ""),
        "수탁사명":          biz.get("company_name", vendor),
        "수탁사_사업자번호": biz.get("biz_no", ""),
        "수탁사_대표":       biz.get("ceo", ""),
        "수탁사_주소":       biz.get("address", ""),
        "수탁사_계좌":       biz.get("account", ""),
        "단가_음식물":       _krw(cust.get("price_food", 0)),
        "단가_재활용":       _krw(cust.get("price_recycle", 0)),
        "단가_일반":         _krw(cust.get("price_general", 0)),
        "고정월비":          _krw(cust.get("fixed_monthly_fee", 0)),
        "계약시작일":        start,
        "계약종료일":        end,
        "발행일":            today.strftime("%Y년 %m월 %d일"),
        "직인_IMG":          seal_path(vendor),
    }

    # 템플릿 본문 로드
    if template_id:
        tmpl_row = db_get("contract_templates", {"id": template_id})
        if not tmpl_row:
            raise ValueError(f"contract_templates id={template_id} 없음")
        body = tmpl_row[0].get("body_html") or ""
    else:
        body = (TEMPLATE_DIR / "contract_standard.html").read_text(encoding="utf-8")

    html = _render(body, payload)
    doc_no = _next_doc_no(vendor, "contract")
    return {"html": html, "doc_no": doc_no, "payload": payload}


# ============================================================
# 3. 견적서 생성 (자동/수기 모드 공통)
# ============================================================
def render_quote(
    vendor: str,
    customer_name: str,
    items: list[dict] | None = None,   # 수기모드: [{name, spec, qty, price}, ...]
    auto_months: int = 1,              # 자동모드 사용 시 월 수
    remark: str = "",
    valid_days: int = 30,
) -> dict[str, Any]:
    cust  = fetch_customer(vendor, customer_name)
    biz   = fetch_vendor_company(vendor)
    today = date.today()

    # ── 1) items 결정 ──
    if items is None or len(items) == 0:
        items = _build_items_from_customer(cust, auto_months)

    # ── 2) 합계 계산 ──
    supply = sum(int(it.get("qty", 0)) * float(it.get("price", 0)) for it in items)
    vat    = round(supply * 0.10)
    total  = int(supply + vat)

    # ── 3) tbody HTML 생성 ──
    rows: list[str] = []
    for i, it in enumerate(items, start=1):
        amount = int(int(it.get("qty", 0)) * float(it.get("price", 0)))
        rows.append(
            "<tr>"
            f"<td style='text-align:center'>{i}</td>"
            f"<td>{_esc(it.get('name',''))}</td>"
            f"<td style='text-align:center'>{_esc(it.get('spec',''))}</td>"
            f"<td class='num'>{_krw(it.get('qty',0))}</td>"
            f"<td class='num'>{_krw(it.get('price',0))}</td>"
            f"<td class='num'>{_krw(amount)}</td>"
            "</tr>"
        )

    payload = {
        "견적번호":          _next_doc_no(vendor, "quote"),
        "발행일":            today.strftime("%Y-%m-%d"),
        "유효기간":          (today + timedelta(days=valid_days)).strftime("%Y-%m-%d"),
        "거래처명":          cust.get("name", ""),
        "대표자":            cust.get("rep", ""),
        "사업자번호":        cust.get("biz_no", ""),
        "주소":              cust.get("addr", ""),
        "전화":              cust.get("phone", ""),
        "수탁사명":          biz.get("company_name", vendor),
        "수탁사_대표":       biz.get("ceo", ""),
        "수탁사_사업자번호": biz.get("biz_no", ""),
        "수탁사_주소":       biz.get("address", ""),
        "수탁사_전화":       biz.get("phone", ""),
        "수탁사_계좌":       biz.get("account", ""),
        "ITEMS_TBODY":       "\n".join(rows),
        "공급가액":          _krw(int(supply)),
        "부가세":            _krw(int(vat)),
        "합계금액":          _krw(int(total)),
        "합계금액_한글":     _num_to_kor(int(total)),
        "비고":              _esc(remark).replace("\n", "<br>"),
        "직인_IMG":          seal_path(vendor),
    }

    body = (TEMPLATE_DIR / "quote_standard.html").read_text(encoding="utf-8")
    html = _render(body, payload)
    return {
        "html":       html,
        "doc_no":     payload["견적번호"],
        "total":      total,
        "payload":    payload,
        "valid_until": payload["유효기간"],
    }


def _build_items_from_customer(cust: dict, months: int) -> list[dict]:
    """customer_info 의 단가 3종을 그대로 견적 행으로 펼침"""
    rows: list[dict] = []
    if float(cust.get("price_food", 0) or 0) > 0:
        rows.append({"name": "음식물폐기물 수집·운반", "spec": "원/kg",
                     "qty": months, "price": float(cust["price_food"])})
    if float(cust.get("price_recycle", 0) or 0) > 0:
        rows.append({"name": "재활용품 수집·운반", "spec": "원/kg",
                     "qty": months, "price": float(cust["price_recycle"])})
    if float(cust.get("price_general", 0) or 0) > 0:
        rows.append({"name": "일반폐기물 수집·운반", "spec": "원/kg",
                     "qty": months, "price": float(cust["price_general"])})
    if float(cust.get("fixed_monthly_fee", 0) or 0) > 0:
        rows.append({"name": "고정 월정액", "spec": "월",
                     "qty": months, "price": float(cust["fixed_monthly_fee"])})
    return rows


# ============================================================
# 4. PDF 저장 + 이력 기록
# ============================================================
def issue_document(
    vendor: str,
    doc_type: str,           # 'contract' | 'quote'
    customer_name: str,
    html: str,
    doc_no: str,
    payload: dict,
    template_id: int | None = None,
    valid_until: str | None = None,
    total_amount: int = 0,
    created_by: str = "",
) -> str:
    """HTML → PDF 저장 → issued_documents INSERT → pdf_path 반환.

    BUG-C 가드: PDF 변환이 실패하면 DB INSERT 하지 않고 RuntimeError 발생.
    호출부(state)는 try/except 로 toast.error 표시.
    """
    fname = f"{doc_no}_{re.sub(r'[^0-9A-Za-z가-힣]', '_', customer_name)}.pdf"
    pdf_path = ISSUED_PDF_DIR / fname

    # ── PDF 변환 실패 시 즉시 중단 (데이터 정합성 보호) ──
    ok = html_to_pdf(html, str(pdf_path))
    if not ok:
        raise RuntimeError(
            "PDF 변환 실패 — wkhtmltopdf 미설치 또는 HTML 오류. "
            "서버 로그(_log) 확인 필요."
        )
    # 파일 실제 존재 + 0바이트 아님 재확인
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError(f"PDF 생성 후 파일 검증 실패: {pdf_path}")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO issued_documents "
            "(vendor, doc_type, customer_name, template_id, doc_no, "
            " issued_date, valid_until, total_amount, pdf_path, payload_json, created_by) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                vendor, doc_type, customer_name, template_id, doc_no,
                date.today().isoformat(), valid_until, total_amount,
                str(pdf_path), json.dumps(payload, ensure_ascii=False), created_by,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return str(pdf_path)


# ============================================================
# 5. 내부 유틸
# ============================================================
_VAR_RE = re.compile(r"\{\{\s*([^{}\s]+)\s*\}\}")


def _render(template: str, mapping: dict) -> str:
    return _VAR_RE.sub(lambda m: str(mapping.get(m.group(1), "")), template)


def _esc(s: Any) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _krw(n: Any) -> str:
    try:
        return f"{int(float(n)):,}"
    except (TypeError, ValueError):
        return "0"


def _next_doc_no(vendor: str, doc_type: str) -> str:
    """SQLite(?) 와 PostgreSQL(%s) 듀얼 백엔드 호환 채번."""
    prefix = "C" if doc_type == "contract" else "Q"
    year   = date.today().year
    rows   = db_get(
        "issued_documents",
        {"vendor": vendor, "doc_type": doc_type},
    )
    # issued_date가 해당 연도로 시작하는 건만 카운트
    count = sum(
        1 for r in rows
        if str(r.get("issued_date", "")).startswith(str(year))
    )
    seq = count + 1
    return f"{prefix}-{year}-{seq:04d}"


# ============================================================
# 6. 외주업체(vendor) 전용 문서 함수
# ============================================================

def fetch_vendor_company_info(vendor: str) -> dict[str, Any]:
    """
    외주업체 회사정보 조회.
    1차: vendor_company_info 테이블 (전용 신규 테이블, 관리자가 직접 입력)
    2차: vendor_info 테이블 (기존 데이터 — biz_name/rep/biz_no/address/contact)
    3차: 환경변수 폴백
    """
    conn = get_db()
    try:
        # 1차: vendor_company_info (신규 전용 테이블)
        cur = conn.execute(
            "SELECT * FROM vendor_company_info WHERE vendor_id=? LIMIT 1", (vendor,)
        )
        row = cur.fetchone()
        if row:
            d = dict(row)
            # 실제 데이터가 있는지 확인 (빈 레코드 방지)
            if any([d.get("company_name"), d.get("ceo_name"), d.get("bizno")]):
                return {
                    "company_name": d.get("company_name") or vendor,
                    "ceo":          d.get("ceo_name", ""),
                    "biz_no":       d.get("bizno", ""),
                    "address":      d.get("addr", ""),
                    "phone":        d.get("phone", ""),
                    "account":      d.get("account", "") or "",
                }

        # 2차: vendor_info 테이블 (기존 운영 데이터)
        cur2 = conn.execute(
            "SELECT * FROM vendor_info WHERE vendor=? LIMIT 1", (vendor,)
        )
        row2 = cur2.fetchone()
        if row2:
            d2 = dict(row2)
            # vendor_info 컬럼명 → 표준 키 매핑
            return {
                "company_name": d2.get("biz_name") or d2.get("company_name") or vendor,
                "ceo":          d2.get("rep") or d2.get("ceo", ""),
                "biz_no":       d2.get("biz_no", ""),
                "address":      d2.get("address", ""),
                "phone":        d2.get("contact") or d2.get("phone", ""),
                "account":      d2.get("account", "") or "",
            }
    except Exception:
        pass
    finally:
        conn.close()
    # 3차: 환경변수 폴백
    return {
        "company_name": vendor,
        "ceo":          os.getenv("VENDOR_CEO", ""),
        "biz_no":       os.getenv("VENDOR_BIZNO", ""),
        "address":      os.getenv("VENDOR_ADDR", ""),
        "phone":        os.getenv("VENDOR_PHONE", ""),
        "account":      os.getenv("VENDOR_ACCOUNT", ""),
    }


def _next_vendor_doc_no(vendor: str, doc_type: str) -> str:
    """외주업체 채번: C-<vendor>-<year>-<seq:04d>"""
    prefix = "C" if doc_type == "contract" else "Q"
    year   = date.today().year
    rows   = db_get(
        "issued_documents",
        {"vendor": vendor, "doc_type": doc_type},
    )
    count = sum(
        1 for r in rows
        if str(r.get("issued_date", "")).startswith(str(year))
    )
    seq = count + 1
    # vendor 이름에서 영숫자+한글만 추출하여 코드 생성 (공백/특수문자 제거)
    vendor_code = re.sub(r"[^\w가-힣]", "", vendor)[:8] or "VND"
    return f"{prefix}-{vendor_code}-{year}-{seq:04d}"


def render_contract_for_vendor(
    vendor: str,
    customer_name: str,
    template_id: int | None = None,
    contract_start: str | None = None,
    contract_end: str | None = None,
) -> dict[str, Any]:
    """
    외주업체용 계약서 렌더.
    - 수탁사 정보: vendor_company_info 우선 조회
    - 발급번호: C-<vendor>-<year>-<seq> 형식
    """
    cust  = fetch_customer(vendor, customer_name)
    biz   = fetch_vendor_company_info(vendor)
    today = date.today()

    start = contract_start or today.isoformat()
    end   = contract_end or (today.replace(year=today.year + 1)).isoformat()

    payload = {
        "거래처명":          cust.get("name", ""),
        "사업자번호":        cust.get("biz_no", ""),
        "대표자":            cust.get("rep", ""),
        "주소":              cust.get("addr", ""),
        "업태":              cust.get("biz_type", ""),
        "종목":              cust.get("biz_item", ""),
        "전화":              cust.get("phone", ""),
        "이메일":            cust.get("email", ""),
        "수탁사명":          biz.get("company_name", vendor),
        "수탁사_사업자번호": biz.get("biz_no", ""),
        "수탁사_대표":       biz.get("ceo", ""),
        "수탁사_주소":       biz.get("address", ""),
        "수탁사_계좌":       biz.get("account", ""),
        "단가_음식물":       _krw(cust.get("price_food", 0)),
        "단가_재활용":       _krw(cust.get("price_recycle", 0)),
        "단가_일반":         _krw(cust.get("price_general", 0)),
        "고정월비":          _krw(cust.get("fixed_monthly_fee", 0)),
        "계약시작일":        start,
        "계약종료일":        end,
        "발행일":            today.strftime("%Y년 %m월 %d일"),
        "직인_IMG":          seal_path(vendor),
    }

    if template_id:
        tmpl_row = db_get("contract_templates", {"id": template_id})
        if not tmpl_row:
            raise ValueError(f"contract_templates id={template_id} 없음")
        body = tmpl_row[0].get("body_html") or ""
    else:
        body = (TEMPLATE_DIR / "contract_standard.html").read_text(encoding="utf-8")

    html   = _render(body, payload)
    doc_no = _next_vendor_doc_no(vendor, "contract")
    return {"html": html, "doc_no": doc_no, "payload": payload}


def render_quote_for_vendor(
    vendor: str,
    customer_name: str,
    items: list[dict] | None = None,
    auto_months: int = 1,
    remark: str = "",
    valid_days: int = 30,
) -> dict[str, Any]:
    """
    외주업체용 견적서 렌더.
    - 수탁사 정보: vendor_company_info 우선 조회
    - 발급번호: Q-<vendor>-<year>-<seq> 형식
    """
    cust  = fetch_customer(vendor, customer_name)
    biz   = fetch_vendor_company_info(vendor)
    today = date.today()

    if items is None or len(items) == 0:
        items = _build_items_from_customer(cust, auto_months)

    supply = sum(int(it.get("qty", 0)) * float(it.get("price", 0)) for it in items)
    vat    = round(supply * 0.10)
    total  = int(supply + vat)

    rows: list[str] = []
    for i, it in enumerate(items, start=1):
        amount = int(int(it.get("qty", 0)) * float(it.get("price", 0)))
        rows.append(
            "<tr>"
            f"<td style='text-align:center'>{i}</td>"
            f"<td>{_esc(it.get('name',''))}</td>"
            f"<td style='text-align:center'>{_esc(it.get('spec',''))}</td>"
            f"<td class='num'>{_krw(it.get('qty',0))}</td>"
            f"<td class='num'>{_krw(it.get('price',0))}</td>"
            f"<td class='num'>{_krw(amount)}</td>"
            "</tr>"
        )

    doc_no = _next_vendor_doc_no(vendor, "quote")
    payload = {
        "견적번호":          doc_no,
        "발행일":            today.strftime("%Y-%m-%d"),
        "유효기간":          (today + timedelta(days=valid_days)).strftime("%Y-%m-%d"),
        "거래처명":          cust.get("name", ""),
        "대표자":            cust.get("rep", ""),
        "사업자번호":        cust.get("biz_no", ""),
        "주소":              cust.get("addr", ""),
        "전화":              cust.get("phone", ""),
        "수탁사명":          biz.get("company_name", vendor),
        "수탁사_대표":       biz.get("ceo", ""),
        "수탁사_사업자번호": biz.get("biz_no", ""),
        "수탁사_주소":       biz.get("address", ""),
        "수탁사_전화":       biz.get("phone", ""),
        "수탁사_계좌":       biz.get("account", ""),
        "ITEMS_TBODY":       "\n".join(rows),
        "공급가액":          _krw(int(supply)),
        "부가세":            _krw(int(vat)),
        "합계금액":          _krw(int(total)),
        "합계금액_한글":     _num_to_kor(int(total)),
        "비고":              _esc(remark).replace("\n", "<br>"),
        "직인_IMG":          seal_path(vendor),
    }

    body = (TEMPLATE_DIR / "quote_standard.html").read_text(encoding="utf-8")
    html = _render(body, payload)
    return {
        "html":        html,
        "doc_no":      doc_no,
        "total":       total,
        "payload":     payload,
        "valid_until": payload["유효기간"],
    }


# ============================================================
# (원래 섹션 5 계속)
# ============================================================

# ============================================================
# 7. 거래처 조회 / 신규 생성 / 수거일정 확인 (계약서 플로우 연동)
# ============================================================

def search_customer_by_query(vendor: str, query: str) -> dict[str, Any] | None:
    """
    상호명 또는 사업자번호로 거래처 조회.
    1차: 정확 일치 (name 또는 biz_no)
    2차: 부분 일치 (LIKE %query%)
    Returns first match as dict, or None if not found.
    """
    if not query:
        return None
    # 1차: 정확 일치
    for col in ("name", "biz_no"):
        rows = db_get("customer_info", {"vendor": vendor, col: query})
        if rows:
            return dict(rows[0])
    # 2차: 부분 일치 (파라미터화 LIKE — SQL injection 안전)
    conn = get_db()
    try:
        pattern = "%" + query + "%"
        cur = conn.execute(
            "SELECT * FROM customer_info "
            "WHERE vendor=? AND (name LIKE ? OR biz_no LIKE ?) LIMIT 5",
            (vendor, pattern, pattern),
        )
        row = cur.fetchone()
        if row:
            return dict(row)
    except Exception:
        pass
    finally:
        conn.close()
    return None


def create_customer_in_db(
    vendor: str,
    name: str,
    biz_no: str = "",
    rep: str = "",
    addr: str = "",
    phone: str = "",
    biz_type: str = "",
    biz_item: str = "",
    cust_type: str = "학교",
) -> bool:
    """
    신규 거래처를 customer_info 테이블에 INSERT.
    Returns True on success, False on failure.
    """
    if not name:
        return False
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO customer_info "
            "(vendor, name, biz_no, rep, addr, phone, biz_type, biz_item, cust_type) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (vendor, name, biz_no, rep, addr, phone, biz_type, biz_item, cust_type),
        )
        conn.commit()
        return True
    except Exception as e:
        _log.error("[document_service] create_customer_in_db error: %s", e)
        return False
    finally:
        conn.close()


def is_customer_in_schedule(vendor: str, customer_name: str) -> bool:
    """
    거래처가 수거일정(schedules.schools JSON 배열)에 등록되어 있는지 확인.
    """
    if not customer_name:
        return False
    rows = db_get("schedules", {"vendor": vendor})
    for r in rows:
        schools_json = r.get("schools") or "[]"
        try:
            schools = json.loads(schools_json)
            if customer_name in schools:
                return True
        except (json.JSONDecodeError, TypeError):
            pass
    return False


# ============================================================
# (원래 섹션 5 계속)
# ============================================================

_KOR_NUM   = "영일이삼사오육칠팔구"
_KOR_UNIT4 = ["", "만", "억", "조"]
_KOR_UNIT1 = ["", "십", "백", "천"]


def _num_to_kor(n: int) -> str:
    if n == 0:
        return "영"
    parts: list[str] = []
    group = 0
    while n > 0:
        chunk = n % 10000
        if chunk > 0:
            buf = ""
            for i, d in enumerate(reversed(str(chunk))):
                if d != "0":
                    buf = _KOR_NUM[int(d)] + _KOR_UNIT1[i] + buf
            parts.append(buf + _KOR_UNIT4[group])
        n //= 10000
        group += 1
    return "".join(reversed(parts))
