-- ============================================================
-- 04_rollback.sql
-- 목적: Phase 1 인덱스 롤백 (문제 발생 시에만 실행)
-- 실행 조건: 다음 중 하나라도 해당 시
--   (1) 인덱스 추가 후 쿼리가 오히려 느려진 경우 (극히 드뭄)
--   (2) DB 공간 부족 경고
--   (3) 사장님 판단으로 롤백 결정
-- 주의: 인덱스 삭제는 데이터 손실 없음. 안전함.
-- ============================================================

DROP INDEX IF EXISTS idx_real_collection_driver_date;
DROP INDEX IF EXISTS idx_real_collection_vendor_date;
DROP INDEX IF EXISTS idx_real_collection_school_date;
DROP INDEX IF EXISTS idx_real_collection_status;
DROP INDEX IF EXISTS idx_schedules_vendor_month;
DROP INDEX IF EXISTS idx_processing_confirm_vendor_date;
DROP INDEX IF EXISTS idx_processing_confirm_driver_date;

-- 확인
SELECT indexname FROM pg_indexes
 WHERE tablename IN ('real_collection','schedules','processing_confirm')
 ORDER BY indexname;
-- 기대 출력: 위 7개 인덱스가 목록에서 사라짐 (기본 PK 인덱스만 남음)
