#!/bin/bash
# 회원가입 복구 검증 스크립트
# 사용: bash 04_verify.sh
set -e

REPO=/opt/zeroda-platform
cd "$REPO"

echo "=== 1) Python 문법 검증 (3개 파일) ==="
for f in \
  zeroda_reflex/zeroda_reflex/state/auth_state.py \
  zeroda_reflex/zeroda_reflex/pages/register.py \
  zeroda_reflex/zeroda_reflex/pages/hq_admin.py; do
  python3 -c "import ast; ast.parse(open('$f').read())" \
    && echo "  ✅ $f" \
    || { echo "  ❌ $f 문법오류"; exit 1; }
done

echo ""
echo "=== 2) auth_state.py — _do_register 본문 존재 확인 ==="
LINES=$(wc -l < zeroda_reflex/zeroda_reflex/state/auth_state.py)
if [ "$LINES" -lt 150 ]; then
  echo "  ❌ auth_state.py 줄수 너무 적음 ($LINES) — 본문 누락 의심"; exit 1
fi
echo "  ✅ auth_state.py $LINES 줄"
grep -q "def _do_register" zeroda_reflex/zeroda_reflex/state/auth_state.py \
  && grep -q "create_user(" zeroda_reflex/zeroda_reflex/state/auth_state.py \
  && echo "  ✅ _do_register 본문 + create_user 호출 확인" \
  || { echo "  ❌ _do_register 본문 누락"; exit 1; }

echo ""
echo "=== 3) register.py — 가입 버튼 + on_mount 확인 ==="
grep -q "AuthState.submit_register" zeroda_reflex/zeroda_reflex/pages/register.py \
  && echo "  ✅ 가입 버튼 핸들러 연결" \
  || { echo "  ❌ submit_register 핸들러 누락"; exit 1; }
grep -q "load_signup_vendor_options" zeroda_reflex/zeroda_reflex/pages/register.py \
  && echo "  ✅ on_mount 핸들러 연결" \
  || { echo "  ❌ on_mount 누락"; exit 1; }

echo ""
echo "=== 4) hq_admin.py — meal_manager 패치 확인 ==="
COUNT=$(grep -c "meal_manager" zeroda_reflex/zeroda_reflex/pages/hq_admin.py)
if [ "$COUNT" -lt 2 ]; then
  echo "  ❌ meal_manager 패치 누락 (count=$COUNT, 기대값 >=2)"; exit 1
fi
echo "  ✅ meal_manager 패치 적용됨 (count=$COUNT)"

echo ""
echo "=== 5) Reflex 앱 import 시뮬레이션 ==="
cd zeroda_reflex
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from zeroda_reflex.state.auth_state import AuthState
    from zeroda_reflex.pages.register import register_page
    from zeroda_reflex.pages.hq_admin import ROLE_LABELS
    assert 'meal_manager' in ROLE_LABELS, 'ROLE_LABELS meal_manager missing'
    assert hasattr(AuthState, 'submit_register'), 'submit_register missing'
    assert hasattr(AuthState, '_do_register'), '_do_register missing'
    print('  ✅ import 성공 + 모든 항목 존재')
except Exception as e:
    print(f'  ❌ import 실패: {e}')
    sys.exit(1)
" || exit 1

echo ""
echo "✅✅✅ 회원가입 복구 검증 모두 통과"
