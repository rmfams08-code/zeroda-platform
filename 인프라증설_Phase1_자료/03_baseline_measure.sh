#!/bin/bash
# ============================================================
# 03_baseline_measure.sh
# 목적: Phase 1 적용 후 현재 서버 성능 베이스라인 측정
# 실행 위치: 서버 (ssh root@223.130.131.188)
# 소요: 약 1~2분
# ============================================================
set -e

OUT=/tmp/zeroda_baseline_$(date +%Y%m%d_%H%M).txt

echo "════════════════════════════════════════" | tee "$OUT"
echo "ZERODA Phase 1 Baseline  $(date)"         | tee -a "$OUT"
echo "════════════════════════════════════════" | tee -a "$OUT"

# ── 1. systemd 상태 ──────────────────
echo ""                                          | tee -a "$OUT"
echo "[1] systemctl status zeroda-reflex"        | tee -a "$OUT"
systemctl is-active zeroda-reflex                | tee -a "$OUT"
systemctl show zeroda-reflex --property=MainPID,MemoryCurrent,TasksCurrent | tee -a "$OUT"

# ── 2. 포트 리스닝 ───────────────────
echo ""                                          | tee -a "$OUT"
echo "[2] 포트 3000/8000 리스닝"                  | tee -a "$OUT"
ss -tlnp 2>/dev/null | grep -E '3000|8000'       | tee -a "$OUT" || echo "  (없음)" | tee -a "$OUT"

# ── 3. Reflex 백엔드 프로세스 수 ─────
echo ""                                          | tee -a "$OUT"
echo "[3] Reflex 백엔드 프로세스"                 | tee -a "$OUT"
ps -ef | grep -E 'reflex run|uvicorn' | grep -v grep | tee -a "$OUT"
echo "  → Worker 개수: $(ps -ef | grep -E 'reflex run|uvicorn' | grep -v grep | wc -l)" | tee -a "$OUT"
echo "  (기대값: 1  → Phase 2에서 Redis 도입 후 4로 증설)" | tee -a "$OUT"

# ── 4. 메모리/CPU ────────────────────
echo ""                                          | tee -a "$OUT"
echo "[4] 시스템 리소스"                          | tee -a "$OUT"
free -h                                          | tee -a "$OUT"
echo ""                                          | tee -a "$OUT"
uptime                                           | tee -a "$OUT"

# ── 5. PG 접속 확인 ──────────────────
echo ""                                          | tee -a "$OUT"
echo "[5] PostgreSQL 접속 확인"                  | tee -a "$OUT"
if [ -f /opt/zeroda-platform/.env ]; then
    # .env에서 PG 변수 로드
    set -a; source /opt/zeroda-platform/.env; set +a
    export PGPASSWORD="$ZERODA_PG_PASSWORD"
    psql -h "$ZERODA_PG_HOST" -U "$ZERODA_PG_USER" -d "$ZERODA_PG_DB" -p "${ZERODA_PG_PORT:-5432}" \
         -c "SELECT version();" 2>&1 | head -3 | tee -a "$OUT"
else
    echo "  .env 파일 없음" | tee -a "$OUT"
fi

# ── 6. 인덱스 확인 (Phase 1 적용 후) ──
echo ""                                          | tee -a "$OUT"
echo "[6] real_collection / schedules / processing_confirm 인덱스" | tee -a "$OUT"
psql -h "$ZERODA_PG_HOST" -U "$ZERODA_PG_USER" -d "$ZERODA_PG_DB" -p "${ZERODA_PG_PORT:-5432}" -c "
SELECT tablename, indexname FROM pg_indexes
 WHERE tablename IN ('real_collection','schedules','processing_confirm')
 ORDER BY tablename, indexname;
" 2>&1 | tee -a "$OUT"

echo ""                                          | tee -a "$OUT"
echo "════════════════════════════════════════" | tee -a "$OUT"
echo "결과 파일: $OUT"                            | tee -a "$OUT"
echo "카톡으로 사장님께 전송: cat $OUT"            | tee -a "$OUT"
