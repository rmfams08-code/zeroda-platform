#!/bin/bash
# ZERODA Reflex 서버 설치 스크립트 (Streamlit 교체)
# 사용법: bash setup.sh
set -e

echo "═══════════════════════════════════════"
echo "  ZERODA Reflex 설치 (zeroda.co.kr)"
echo "═══════════════════════════════════════"

# ── 1. 기본 패키지 ──
echo "[1/6] 시스템 패키지 확인..."
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl

if ! command -v node &> /dev/null || [ "$(node -v | cut -d. -f1 | tr -d v)" -lt 18 ]; then
    echo "  → Node.js 18 설치..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y -qq nodejs
fi
echo "  ✅ Python $(python3 --version | cut -d' ' -f2), Node $(node -v)"

# ── 2. Reflex 폴더 준비 ──
echo "[2/6] Reflex 폴더 준비..."
REFLEX_HOME="/opt/zeroda-reflex"
mkdir -p "$REFLEX_HOME"

if [ -d "/opt/zeroda-platform/zeroda_reflex" ]; then
    ln -sfn /opt/zeroda-platform/zeroda_reflex "$REFLEX_HOME/zeroda_reflex"
    echo "  ✅ 심볼릭 링크 생성"
else
    echo "  ⚠️  /opt/zeroda-platform/zeroda_reflex 없음 → git pull 먼저 실행하세요"
    exit 1
fi

# ── 3. 가상환경 + 의존성 ──
echo "[3/6] 가상환경 + 의존성 설치..."
if [ ! -d "$REFLEX_HOME/venv" ]; then
    python3 -m venv "$REFLEX_HOME/venv"
fi
source "$REFLEX_HOME/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$REFLEX_HOME/zeroda_reflex/requirements.txt"
echo "  ✅ 의존성 설치 완료"

# ── 4. 환경변수 ──
echo "[4/6] 환경변수 파일..."
if [ ! -f "$REFLEX_HOME/.env" ]; then
    cp "$REFLEX_HOME/zeroda_reflex/deploy/.env.example" "$REFLEX_HOME/.env"
    chmod 600 "$REFLEX_HOME/.env"
    echo "  ⚠️  .env 생성됨 → nano $REFLEX_HOME/.env 로 API 키 입력 필요"
else
    echo "  ✅ .env 이미 존재"
fi

# ── 5. systemd 등록 ──
echo "[5/6] systemd 서비스 등록..."
cp "$REFLEX_HOME/zeroda_reflex/deploy/zeroda-reflex.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable zeroda-reflex
echo "  ✅ zeroda-reflex.service 등록"

# ── 6. nginx 교체 ──
echo "[6/6] nginx 설정..."
if [ -f /etc/nginx/sites-available/zeroda ] && [ ! -f /etc/nginx/sites-available/zeroda.bak.streamlit ]; then
    cp /etc/nginx/sites-available/zeroda /etc/nginx/sites-available/zeroda.bak.streamlit
    echo "  ✅ 기존 Streamlit nginx 설정 백업 완료"
fi
cp "$REFLEX_HOME/zeroda_reflex/deploy/nginx-reflex.conf" /etc/nginx/sites-available/zeroda

if nginx -t 2>/dev/null; then
    echo "  ✅ nginx 설정 유효"
else
    echo "  ⚠️  nginx 설정 오류! 수동 확인 필요"
fi

# ── 완료 ──
echo ""
echo "═══════════════════════════════════════"
echo "  설치 완료! 다음 단계:"
echo "═══════════════════════════════════════"
echo ""
echo "  1. 환경변수 수정:  nano $REFLEX_HOME/.env"
echo "  2. Reflex 초기화:"
echo "     cd $REFLEX_HOME/zeroda_reflex"
echo "     source ../venv/bin/activate"
echo "     set -a; source ../.env; set +a"
echo "     reflex init && reflex export --frontend-only"
echo "  3. Streamlit 중지: systemctl stop zeroda && systemctl disable zeroda"
echo "  4. Reflex 시작:    systemctl start zeroda-reflex"
echo "  5. nginx 재시작:   systemctl restart nginx"
echo "  6. 접속 확인:      https://zeroda.co.kr"
echo ""
echo "  롤백 (문제 시):    systemctl stop zeroda-reflex"
echo "                     cp /etc/nginx/sites-available/zeroda.bak.streamlit /etc/nginx/sites-available/zeroda"
echo "                     systemctl start zeroda && systemctl restart nginx"
