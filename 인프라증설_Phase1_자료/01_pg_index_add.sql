-- ============================================================
-- 01_pg_index_add.sql
-- 목적: real_collection / schedules / processing_confirm 주요 인덱스 추가
-- 대상 DB: NCloud Cloud DB for PostgreSQL (운영)
-- 실행 위치: 서버에서 psql 접속 후 실행
-- 소요 시간: 10~60초 (데이터량에 따라)
-- 무위험: 인덱스 추가는 데이터 손실 없음. 스키마 변경 0건.
-- ============================================================

-- ── 0. 기존 인덱스 확인 (선행 검증) ──────────────────
-- 이미 동일 인덱스가 있으면 IF NOT EXISTS가 무시함
-- 확인용: \di real_collection* 등

-- ── 1. real_collection 복합 인덱스 (기사모드 핵심) ──
-- 사용처: driver_state의 "내 오늘 수거내역" 조회, 월말 정산 집계
-- 예상 효과: 월말 집계 쿼리 500ms → 50ms (10배 가속)
CREATE INDEX IF NOT EXISTS idx_real_collection_driver_date
    ON real_collection (driver, collect_date);

CREATE INDEX IF NOT EXISTS idx_real_collection_vendor_date
    ON real_collection (vendor, collect_date);

CREATE INDEX IF NOT EXISTS idx_real_collection_school_date
    ON real_collection (school_name, collect_date);

CREATE INDEX IF NOT EXISTS idx_real_collection_status
    ON real_collection (status)
    WHERE status IN ('submitted', 'confirmed');

-- ── 2. schedules 인덱스 (월별 스케줄 조회) ──────────
-- 사용처: vendor_admin의 월별 일정 표시
CREATE INDEX IF NOT EXISTS idx_schedules_vendor_month
    ON schedules (vendor, month);

-- ── 3. processing_confirm 인덱스 (계근표 조회) ──────
-- 사용처: 계근표 일자별 조회, 기사별 집계
CREATE INDEX IF NOT EXISTS idx_processing_confirm_vendor_date
    ON processing_confirm (vendor, confirm_date);

CREATE INDEX IF NOT EXISTS idx_processing_confirm_driver_date
    ON processing_confirm (driver, confirm_date);

-- ── 4. VACUUM ANALYZE (통계 갱신) ──────────────────
-- 인덱스 추가 후 쿼리 플래너가 통계를 다시 읽도록
VACUUM ANALYZE real_collection;
VACUUM ANALYZE schedules;
VACUUM ANALYZE processing_confirm;

-- ── 5. 검증 쿼리 (실행 후 복붙해서 확인) ────────────
-- SELECT indexname, tablename FROM pg_indexes
--   WHERE tablename IN ('real_collection','schedules','processing_confirm')
--   ORDER BY tablename, indexname;
--
-- 기대 출력: 위에서 생성한 7개 인덱스가 목록에 나타나야 함
