-- ============================================================
-- 02_pg_slow_query_enable.sql
-- 목적: pg_stat_statements 활성화 (슬로우쿼리 추적 베이스라인)
-- 이유: Phase 2(Redis) 도입 전/후 성능 비교 기준 데이터 확보
-- 대상: NCloud Cloud DB for PostgreSQL
-- 주의: NCloud Cloud DB는 일부 확장이 콘솔 설정에서 활성화되어야 함.
--       psql에서 에러가 나면 NCloud 콘솔 → DB파라미터 그룹에서
--       shared_preload_libraries 에 pg_stat_statements 추가 필요.
-- ============================================================

-- ── 1. 확장 활성화 시도 ────────────────────────────
-- 슈퍼유저 권한 필요. NCloud 관리 DB는 기본 제공되는 경우가 많음
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ── 2. 확인 쿼리 ──────────────────────────────────
-- 설치 여부 확인
SELECT * FROM pg_extension WHERE extname = 'pg_stat_statements';
-- 기대 출력: 1행 (extname=pg_stat_statements)

-- ── 3. 베이스라인 측정용 상위 느린 쿼리 TOP 10 ─────
-- 인덱스 추가 전 한 번, 추가 후 한 번 실행해서 비교
-- (pg_stat_statements_reset() 으로 초기화 후 24시간 누적)

-- SELECT
--     LEFT(query, 80) AS query_sample,
--     calls,
--     ROUND(total_exec_time::numeric, 1) AS total_ms,
--     ROUND(mean_exec_time::numeric, 1)  AS avg_ms,
--     rows
-- FROM pg_stat_statements
-- ORDER BY total_exec_time DESC
-- LIMIT 10;

-- ── 4. 리셋 (필요 시) ──────────────────────────────
-- SELECT pg_stat_statements_reset();
