#!/bin/bash
# NEIS 월별 동기화 — 매월 1일/2일/3일 03:00 실행
set -e
cd /opt/zeroda-reflex/zeroda_reflex
set -a
source /opt/zeroda-reflex/.env
set +a
/opt/zeroda-reflex/venv/bin/python3 -c "
from zeroda_reflex.utils.neis_sync_service import sync_all_schools
stats = sync_all_schools()
print(f'[neis_sync] {stats}')
" >> /var/log/zeroda/neis_sync.log 2>&1
