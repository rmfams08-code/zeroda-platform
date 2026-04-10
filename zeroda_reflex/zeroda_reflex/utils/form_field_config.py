# zeroda_reflex/zeroda_reflex/utils/form_field_config.py
# 2026-04-10 Phase 1: 양식별 셀 매핑 + 시스템 입력필드 정의
#
# 역할
#   1) CELL_MAP  — hwpx 테이블 셀 좌표 → 데이터 키 매핑
#   2) BODY_MAP  — hwpx 본문 텍스트 치환 패턴 매핑
#   3) FORM_FIELDS — UI에 표시할 시스템 입력필드 정의
#   4) AUTO_FILL_KEYS — DB에서 자동채움하는 키 목록
#
# 좌표 규칙
#   (테이블idx, 행idx, 열idx) — 0-based, section0.xml 내 <hp:tbl> 순서
#
# ⚠️ 사례5 준수: 이 파일은 순수 Python dict/list — Reflex Var 사용 없음

from __future__ import annotations

# ── 선택지 옵션 ──
WASTE_TYPE_OPTIONS: list[str] = [
    "음식물류폐기물", "일반폐기물", "재활용폐기물",
    "음식물+일반", "음식물+재활용",
]
TREATMENT_OPTIONS: list[str] = [
    "퇴비화", "사료화", "소각", "매립", "바이오가스", "재활용", "기타",
]
UNIT_OPTIONS: list[str] = ["월", "kg", "톤", "ℓ"]
FREQUENCY_OPTIONS: list[str] = [
    "매일", "주6회", "주5회", "주3회", "주2회", "주1회", "격주", "월1회",
]


# ══════════════════════════════════════════
#  2자 계약서 — 폐기물 위수탁계약서(2자).hwpx
# ══════════════════════════════════════════
#
# 테이블 구조 (section0.xml):
#   테이블0: 제목 (1행) — 수정 불필요
#   테이블1: 전체 본문 (1행1열 — 텍스트 블록) — 본문 치환 대상
#   테이블2: 폐기물 테이블 헤더+데이터 (8행) — 중첩되어 있으나 독립 테이블3과 동일
#   테이블3: 폐기물 품목 테이블 (8행8열) — 실제 데이터 입력 대상
#   테이블4: 서명란 (4행) — 배출자(갑) + 수집운반자(을)

CELL_MAP_2JA: dict[tuple[int, int, int], str] = {
    # ── 테이블3: 폐기물 품목 (행2~행7 = 데이터행, 행0~1 = 헤더) ──
    # 행2 (첫 번째 품목행)
    (3, 2, 0): "waste_type_1",        # 폐기물 종류
    (3, 2, 1): "unit_1",              # 단위
    (3, 2, 2): "quantity_1",          # 물량(예상배출량)
    (3, 2, 3): "price_transport_1",   # 운반 단가
    (3, 2, 4): "price_treatment_1",   # 처리 단가
    (3, 2, 5): "amount_transport_1",  # 운반 금액
    (3, 2, 6): "amount_treatment_1",  # 처리 금액 (= 계약금액)
    (3, 2, 7): "method_1",           # 처리방법
    # 행3 (두 번째 품목행)
    (3, 3, 0): "waste_type_2",
    (3, 3, 1): "unit_2",
    (3, 3, 2): "quantity_2",
    (3, 3, 3): "price_transport_2",
    (3, 3, 4): "price_treatment_2",
    (3, 3, 5): "amount_transport_2",
    (3, 3, 6): "amount_treatment_2",
    (3, 3, 7): "method_2",
    # 행4~7 (추가 품목행) — 동일 패턴, 필요 시 확장
    # 행8: 총계
    (3, 7, 6): "total_amount",        # 총 계약금액

    # ── 테이블4: 서명란 ──
    # 행0: 배출자(갑) | 상호 | (값) | 소재지 | (값)
    (4, 0, 2): "emitter_name",        # 배출자 상호
    (4, 0, 4): "emitter_address",     # 배출자 소재지
    # 행1: 사업자등록번호 | (값) | 전화번호 | (값) | 대표자 | (인)
    (4, 1, 1): "emitter_bizno",       # 배출자 사업자번호
    (4, 1, 3): "emitter_phone",       # 배출자 전화번호
    (4, 1, 5): "emitter_rep",         # 배출자 대표자 + (인)
    # 행2: 수집운반자(을) | 상호 | (값) | 소재지 | (값)
    (4, 2, 2): "transporter_name",    # 수집운반자 상호
    (4, 2, 4): "transporter_address", # 수집운반자 소재지
    # 행3: 허가번호 | (값) | 전화번호 | (값) | 대표자 | (인)
    (4, 3, 1): "transporter_license", # 수집운반자 허가번호
    (4, 3, 3): "transporter_phone",   # 수집운반자 전화번호
    (4, 3, 5): "transporter_rep",     # 수집운반자 대표자 + (인)
}

# 본문 텍스트 치환 — (검색패턴, 데이터키)
BODY_MAP_2JA: list[tuple[str, str]] = [
    # "2. 배  출  장  소 :" 뒤에 배출 장소
    ("배  출  장  소 :", "emitter_address"),
    # "5. 위...수탁 계약기간 :" 뒤에 계약기간
    # 이건 복잡한 패턴이므로 별도 처리
]


# ══════════════════════════════════════════
#  3자 계약서 — 폐기물 위수탁계약서(3자).hwpx
# ══════════════════════════════════════════
#
# 테이블 구조 (section0.xml):
#   테이블0: 서명란 (11행5열) — 배출자/운반자/재활용업자

CELL_MAP_3JA: dict[tuple[int, int, int], str] = {
    # ── 테이블0: 서명란 ──
    # 배출자 (행0~행2)
    (0, 0, 2): "emitter_name",           # 상호명(사업장명)
    (0, 0, 4): "emitter_bizno",          # 사업자 번호
    (0, 1, 1): "emitter_address",        # 사업장 소재지
    (0, 1, 3): "emitter_phone",          # 사업장연락처
    (0, 2, 1): "emitter_rep",            # 대표자 성명 + (인)
    (0, 2, 3): "emitter_fax",            # 팩스
    # 구분행 (행3 — 빈칸)
    # 운반자 (행4~행6)
    (0, 4, 2): "transporter_name",       # 상호명
    (0, 4, 4): "transporter_bizno",      # 사업자 번호
    (0, 5, 1): "transporter_address",    # 소재지
    (0, 5, 3): "transporter_phone",      # 연락처
    (0, 6, 1): "transporter_rep",        # 대표자 + (인)
    (0, 6, 3): "transporter_fax",        # 팩스
    # 구분행 (행7 — 빈칸)
    # 재활용업자 (행8~행10)
    (0, 8, 2): "processor_name",         # 상호명
    (0, 8, 4): "processor_bizno",        # 사업자 번호
    (0, 9, 1): "processor_address",      # 소재지
    (0, 9, 3): "processor_phone",        # 연락처
    (0, 10, 1): "processor_rep",         # 대표자 + (인)
    (0, 10, 3): "processor_fax",         # 팩스
}

# 본문 텍스트 치환
BODY_MAP_3JA: list[tuple[str, str]] = [
    # 배출자명, 수집운반업자명, 재활용업자명 치환
    ("폐기물 배출자", "emitter_name_in_body"),
    ("수집·운반업자", "transporter_name_in_body"),
    ("폐기물종합 재활용업자", "processor_name_in_body"),
]


# ══════════════════════════════════════════
#  처리확인서 — 폐기물 처리확인서.hwpx
# ══════════════════════════════════════════
#
# 테이블 구조 (section0.xml):
#   테이블0: 배출자/운반자/처리자 정보 (8행4열)
#   테이블1: 위탁량 테이블 (4행4열)

CELL_MAP_CONFIRM: dict[tuple[int, int, int], str] = {
    # ── 테이블0: 3자 정보 ──
    # 행0: 구분 | 배출자 | 운반자 | 처리자 (헤더)
    # 행1: 업체명
    (0, 1, 1): "emitter_name",
    (0, 1, 2): "transporter_name",
    (0, 1, 3): "processor_name",
    # 행2: 등록번호 (= 사업자번호)
    (0, 2, 1): "emitter_bizno",
    (0, 2, 2): "transporter_bizno",
    (0, 2, 3): "processor_bizno",
    # 행3: 법인번호 / 허가번호
    (0, 3, 1): "emitter_corpno",
    (0, 3, 2): "transporter_license",
    (0, 3, 3): "processor_license",
    # 행4: 허가업종
    (0, 4, 1): "emitter_biztype",
    (0, 4, 2): "transporter_biztype",
    (0, 4, 3): "processor_biztype",
    # 행5: 주소
    (0, 5, 1): "emitter_address",
    (0, 5, 2): "transporter_address",
    (0, 5, 3): "processor_address",
    # 행6: 전화번호
    (0, 6, 1): "emitter_phone",
    (0, 6, 2): "transporter_phone",
    (0, 6, 3): "processor_phone",
    # 행7: 계약건명
    (0, 7, 1): "contract_title",

    # ── 테이블1: 위탁량 ──
    # 행0: 종류 | 세부사항 | 수량(kg) | 비고 (헤더)
    # 행1 (첫 번째 데이터행)
    (1, 1, 0): "waste_type_1",
    (1, 1, 1): "waste_detail_1",
    (1, 1, 2): "waste_qty_1",
    (1, 1, 3): "waste_remark_1",
    # 행2 (두 번째 데이터행)
    (1, 2, 0): "waste_type_2",
    (1, 2, 1): "waste_detail_2",
    (1, 2, 2): "waste_qty_2",
    (1, 2, 3): "waste_remark_2",
    # 행3 (세 번째 데이터행)
    (1, 3, 0): "waste_type_3",
    (1, 3, 1): "waste_detail_3",
    (1, 3, 2): "waste_qty_3",
    (1, 3, 3): "waste_remark_3",
}


# ══════════════════════════════════════════
#  카테고리 → 매핑 dict 연결
# ══════════════════════════════════════════

CATEGORY_CELL_MAP: dict[str, dict] = {
    "2자계약서": CELL_MAP_2JA,
    "3자계약서": CELL_MAP_3JA,
    "처리확인서": CELL_MAP_CONFIRM,
}

CATEGORY_BODY_MAP: dict[str, list] = {
    "2자계약서": BODY_MAP_2JA,
    "3자계약서": BODY_MAP_3JA,
    "처리확인서": [],
}


# ══════════════════════════════════════════
#  시스템 입력필드 정의 (UI 렌더링용)
# ══════════════════════════════════════════
#
# type: "date" | "text" | "number" | "select" | "textarea"
# auto: True면 DB에서 자동채움 (읽기전용)
# options: select 타입일 때 선택지 리스트

FORM_FIELDS: dict[str, dict] = {
    "2자계약서": {
        "sections": [
            {
                "title": "계약 기본정보",
                "fields": [
                    {"key": "contract_start", "label": "계약기간 시작", "type": "date", "required": True},
                    {"key": "contract_end", "label": "계약기간 종료", "type": "date", "required": True},
                    {"key": "contract_date", "label": "계약일자", "type": "date", "required": True},
                ],
            },
            {
                "title": "배출자(갑) 정보",
                "auto": True,
                "source": "customer_info",
                "fields": [
                    {"key": "emitter_name", "label": "상호", "auto": True},
                    {"key": "emitter_bizno", "label": "사업자번호", "auto": True},
                    {"key": "emitter_rep", "label": "대표자", "auto": True},
                    {"key": "emitter_address", "label": "소재지", "auto": True},
                    {"key": "emitter_phone", "label": "전화번호", "auto": True},
                ],
            },
            {
                "title": "수집운반자(을) 정보",
                "auto": True,
                "source": "vendor_info",
                "fields": [
                    {"key": "transporter_name", "label": "상호", "auto": True},
                    {"key": "transporter_bizno", "label": "사업자/허가번호", "auto": True},
                    {"key": "transporter_rep", "label": "대표자", "auto": True},
                    {"key": "transporter_address", "label": "소재지", "auto": True},
                    {"key": "transporter_phone", "label": "전화번호", "auto": True},
                    {"key": "transporter_license", "label": "허가번호", "auto": True},
                ],
            },
            {
                "title": "폐기물 및 처리금액",
                "fields": [
                    {"key": "waste_type_1", "label": "폐기물 종류", "type": "select",
                     "options": WASTE_TYPE_OPTIONS},
                    {"key": "unit_1", "label": "단위", "type": "select", "options": UNIT_OPTIONS},
                    {"key": "quantity_1", "label": "물량(예상배출량)", "type": "text"},
                    {"key": "price_transport_1", "label": "운반 단가(원)", "type": "number"},
                    {"key": "price_treatment_1", "label": "처리 단가(원)", "type": "number"},
                    {"key": "amount_treatment_1", "label": "계약금액(원)", "type": "number"},
                    {"key": "method_1", "label": "처리방법", "type": "select",
                     "options": TREATMENT_OPTIONS},
                ],
            },
            {
                "title": "결제조건",
                "fields": [
                    {"key": "payment_bank", "label": "은행명", "type": "text", "auto": True},
                    {"key": "payment_account", "label": "계좌번호", "type": "text", "auto": True},
                    {"key": "payment_holder", "label": "예금주", "type": "text", "auto": True},
                ],
            },
        ],
    },

    "3자계약서": {
        "sections": [
            {
                "title": "계약 기본정보",
                "fields": [
                    {"key": "contract_start", "label": "계약기간 시작", "type": "date", "required": True},
                    {"key": "contract_end", "label": "계약기간 종료", "type": "date", "required": True},
                    {"key": "contract_date", "label": "계약일자", "type": "date", "required": True},
                    {"key": "price_per_unit", "label": "단가(원/kg 또는 ℓ)", "type": "number",
                     "required": True},
                    {"key": "payment_day", "label": "결제일(익월 ~일)", "type": "text"},
                ],
            },
            {
                "title": "배출자 정보",
                "auto": True,
                "source": "customer_info",
                "fields": [
                    {"key": "emitter_name", "label": "상호명(사업장명)", "auto": True},
                    {"key": "emitter_bizno", "label": "사업자번호", "auto": True},
                    {"key": "emitter_address", "label": "사업장 소재지", "auto": True},
                    {"key": "emitter_phone", "label": "사업장연락처", "auto": True},
                    {"key": "emitter_rep", "label": "대표자 성명", "auto": True},
                    {"key": "emitter_fax", "label": "팩스", "type": "text"},
                ],
            },
            {
                "title": "운반자 정보",
                "auto": True,
                "source": "vendor_info",
                "fields": [
                    {"key": "transporter_name", "label": "상호명", "auto": True},
                    {"key": "transporter_bizno", "label": "사업자번호", "auto": True},
                    {"key": "transporter_address", "label": "소재지", "auto": True},
                    {"key": "transporter_phone", "label": "연락처", "auto": True},
                    {"key": "transporter_rep", "label": "대표자", "auto": True},
                    {"key": "transporter_fax", "label": "팩스", "type": "text"},
                ],
            },
            {
                "title": "재활용업자 정보",
                "auto": True,
                "source": "mid_processor",
                "fields": [
                    {"key": "processor_name", "label": "상호명", "auto": True},
                    {"key": "processor_bizno", "label": "사업자번호", "auto": True},
                    {"key": "processor_address", "label": "소재지", "auto": True},
                    {"key": "processor_phone", "label": "연락처", "auto": True},
                    {"key": "processor_rep", "label": "대표자", "auto": True},
                    {"key": "processor_fax", "label": "팩스", "type": "text"},
                ],
            },
        ],
    },

    "처리확인서": {
        "sections": [
            {
                "title": "확인기간",
                "fields": [
                    {"key": "confirm_start", "label": "확인기간 시작", "type": "date", "required": True},
                    {"key": "confirm_end", "label": "확인기간 종료", "type": "date", "required": True},
                ],
            },
            {
                "title": "배출자 정보",
                "auto": True,
                "source": "customer_info",
                "fields": [
                    {"key": "emitter_name", "label": "업체명", "auto": True},
                    {"key": "emitter_bizno", "label": "등록번호", "auto": True},
                    {"key": "emitter_corpno", "label": "법인번호", "type": "text"},
                    {"key": "emitter_biztype", "label": "허가업종", "type": "text"},
                    {"key": "emitter_address", "label": "주소", "auto": True},
                    {"key": "emitter_phone", "label": "전화번호", "auto": True},
                ],
            },
            {
                "title": "운반자 정보",
                "auto": True,
                "source": "vendor_info",
                "fields": [
                    {"key": "transporter_name", "label": "업체명", "auto": True},
                    {"key": "transporter_bizno", "label": "등록번호", "auto": True},
                    {"key": "transporter_license", "label": "허가번호", "auto": True},
                    {"key": "transporter_biztype", "label": "허가업종", "auto": True},
                    {"key": "transporter_address", "label": "주소", "auto": True},
                    {"key": "transporter_phone", "label": "전화번호", "auto": True},
                ],
            },
            {
                "title": "처리자 정보",
                "auto": True,
                "source": "mid_processor",
                "fields": [
                    {"key": "processor_name", "label": "업체명", "auto": True},
                    {"key": "processor_bizno", "label": "등록번호", "auto": True},
                    {"key": "processor_license", "label": "허가번호", "auto": True},
                    {"key": "processor_biztype", "label": "허가업종", "auto": True},
                    {"key": "processor_address", "label": "주소", "auto": True},
                    {"key": "processor_phone", "label": "전화번호", "auto": True},
                ],
            },
            {
                "title": "계약건명",
                "fields": [
                    {"key": "contract_title", "label": "계약건명", "type": "text",
                     "default": "음식물류폐기물"},
                ],
            },
            {
                "title": "위탁량",
                "fields": [
                    {"key": "waste_type_1", "label": "종류", "type": "select",
                     "options": WASTE_TYPE_OPTIONS, "default": "음식물류폐기물"},
                    {"key": "waste_detail_1", "label": "세부사항(처리방법)", "type": "select",
                     "options": TREATMENT_OPTIONS, "default": "재활용"},
                    {"key": "waste_qty_1", "label": "수량(kg)", "type": "number", "required": True},
                    {"key": "waste_remark_1", "label": "비고", "type": "text", "default": "퇴비화"},
                ],
            },
        ],
    },
}


# ══════════════════════════════════════════
#  자동채움 키 → DB 컬럼 매핑
# ══════════════════════════════════════════

# customer_info 테이블 → 배출자 필드
CUSTOMER_TO_EMITTER: dict[str, str] = {
    "emitter_name": "name",
    "emitter_bizno": "biz_no",
    "emitter_rep": "rep",
    "emitter_address": "addr",
    "emitter_phone": "phone",
}

# vendor_info 테이블 → 수집운반자 필드
VENDOR_TO_TRANSPORTER: dict[str, str] = {
    "transporter_name": "biz_name",
    "transporter_bizno": "biz_no",
    "transporter_rep": "rep",
    "transporter_address": "address",
    "transporter_phone": "contact",
    "transporter_license": "license_no",
    "transporter_biztype": "음식물류폐기물",  # 고정값
}

# mid_processor 테이블 → 재활용업자/처리자 필드
PROCESSOR_TO_FIELDS: dict[str, str] = {
    "processor_name": "name",
    "processor_bizno": "biz_no",
    "processor_rep": "rep",
    "processor_address": "address",
    "processor_phone": "phone",
    "processor_license": "license_no",
    "processor_biztype": "biz_type",
}

# 결제조건 (vendor_info.account 파싱)
PAYMENT_FIELDS: dict[str, str] = {
    "payment_bank": "bank",
    "payment_account": "account_no",
    "payment_holder": "account_holder",
}
