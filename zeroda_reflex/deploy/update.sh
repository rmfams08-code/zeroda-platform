#!/bin/bash
# ZERODA Reflex 코드 업데이트 스크립트
# 사용법: bash update.sh
# GitHub에서 최신 코드를 가져와서 앱 재시작

set -e

echo "🔄 ZERODA Reflex 업데이트 시작..."

# 1. GitHub에서 최신 코드
echo "[1/3] git pull..."
cd /opt/zeroda-platform
git pull

# 2. Reflex 앱 재시작
echo "[2/3] 앱 재시작..."
systemctl restart zeroda-reflex

# 3. 상태 확인
echo "[3/3] 상태 확인..."
sleep 2
systemctl status zeroda-reflex --no-pager -l

echo ""
echo "✅ 업데이트 완료!"
echo "로그 확인: journalctl -u zeroda-reflex -n 20"
