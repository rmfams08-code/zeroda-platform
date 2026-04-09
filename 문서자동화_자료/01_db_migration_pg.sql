-- ============================================================
-- 문서자동화 P0 — 신규 테이블 2개 (PostgreSQL 변환본)
-- 원본: 01_db_migration.sql (SQLite)
-- 변환: SQLite → PostgreSQL
--
-- 실행 위치: PostgreSQL DB (zeroda)
-- 실행 명령:  psql [DSN] -f 01_db_migration_pg.sql
--
-- 변환 규칙 적용:
--   INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
--   TEXT DEFAULT (datetime('now','localtime')) → TEXT DEFAULT NOW()::TEXT
--   IF NOT EXISTS 유지
--   CHECK 제약 그대로 유지
--   SQLite 전용 함수 없음 (json_extract 등 미사용) — 변환 불필요
-- ============================================================

-- ① 계약서 템플릿 저장 (사장님 업로드한 .docx 또는 신규생성한 표준양식)
CREATE TABLE IF NOT EXISTS contract_templates (
    id              SERIAL PRIMARY KEY,
    vendor          TEXT NOT NULL,                  -- 멀티테넌트(직인 테이블과 동일 키)
    template_name   TEXT NOT NULL,                  -- '학교용 표준', '관공서용', '하영자원 자체양식'
    template_type   TEXT NOT NULL,                  -- 'standard' | 'uploaded'
    body_html       TEXT,                           -- standard일 때: 변수 치환용 HTML
    file_path       TEXT,                           -- uploaded일 때: 원본 docx 경로
    variables_json  TEXT,                           -- ["{{거래처명}}","{{단가_음식물}}",...]
    is_default      INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT NOW()::TEXT,
    UNIQUE(vendor, template_name)
);

-- ② 발급된 계약서/견적서 이력
CREATE TABLE IF NOT EXISTS issued_documents (
    id              SERIAL PRIMARY KEY,
    vendor          TEXT NOT NULL,
    doc_type        TEXT NOT NULL,                  -- 'contract' | 'quote'
    customer_name   TEXT NOT NULL,                  -- customer_info.name
    template_id     INTEGER,                        -- contract_templates.id (견적서는 NULL)
    doc_no          TEXT,                           -- 'C-2026-0001' / 'Q-2026-0001'
    issued_date     TEXT NOT NULL,
    valid_until     TEXT,                           -- 견적서 유효기간
    total_amount    REAL DEFAULT 0,
    pdf_path        TEXT,                           -- 생성된 PDF 절대경로
    payload_json    TEXT,                           -- 양식 입력값 전체 (재발급용)
    created_by      TEXT,                           -- users.username
    created_at      TEXT DEFAULT NOW()::TEXT
);

CREATE INDEX IF NOT EXISTS idx_issued_vendor_date
    ON issued_documents(vendor, doc_type, issued_date DESC);

-- ============================================================
-- 검증 쿼리 (실행 후 한 번 돌려보기)
-- ============================================================
-- psql [DSN] -c "\d contract_templates"
-- psql [DSN] -c "\d issued_documents"
