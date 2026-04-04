# zeroda_platform/auth/login.py
import streamlit as st
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta
from config.settings import ROLES, ROLE_ICONS, COMMON_CSS
from database.db_manager import db_get, db_upsert

# ── 보안 설정 상수 ──
LOGIN_MAX_ATTEMPTS = 5          # 최대 로그인 실패 횟수
LOGIN_LOCKOUT_MINUTES = 15      # 잠금 시간(분)
SESSION_TIMEOUT_MINUTES = 30    # 세션 타임아웃(분) — 기본값
SESSION_TIMEOUT_DRIVER = 480    # 기사 역할 세션 타임아웃(분) = 8시간
COOKIE_SECRET = "zeroda-2026-hmac-secret-key"  # 쿠키 서명 키
AUTO_LOGIN_TOKEN_SECRET = "zeroda-2026-autologin-hmac"  # 자동로그인 토큰 서명 키

# ── 비밀번호 정책 상수 ──
PW_MIN_LENGTH = 8
PW_REQUIRE_UPPER = True
PW_REQUIRE_DIGIT = True
PW_REQUIRE_SPECIAL = True


def validate_password(pw: str) -> tuple:
    """비밀번호 정책 검증. (통과여부, 오류메시지)"""
    errors = []
    if len(pw) < PW_MIN_LENGTH:
        errors.append(f"최소 {PW_MIN_LENGTH}자 이상")
    if PW_REQUIRE_UPPER and not re.search(r'[A-Z]', pw):
        errors.append("대문자 1개 이상 포함")
    if PW_REQUIRE_DIGIT and not re.search(r'[0-9]', pw):
        errors.append("숫자 1개 이상 포함")
    if PW_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', pw):
        errors.append("특수문자 1개 이상 포함")
    if errors:
        return False, "비밀번호 조건: " + ", ".join(errors)
    return True, ""


def hash_password_bcrypt(pw: str) -> str:
    """bcrypt 해싱 (신규 계정용)"""
    import bcrypt
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def hash_password(pw: str) -> str:
    """SHA256 해싱 (하위 호환용 — 신규는 bcrypt 사용)"""
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 우선 검증, SHA256 폴백 (기존 계정 호환)"""
    if not plain or not hashed:
        return False
    # 1) bcrypt 해시 ($2b$ 또는 $2a$ 접두사)
    if hashed.startswith('$2b$') or hashed.startswith('$2a$'):
        import bcrypt
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception:
            return False
    # 2) SHA256 폴백 (기존 계정)
    if hashlib.sha256(plain.strip().encode()).hexdigest() == hashed.strip():
        return True
    # 3) 평문 비교 (최초 계정 등)
    if plain.strip() == hashed.strip():
        return True
    return False


def _migrate_to_bcrypt(user_id: str, plain_pw: str):
    """기존 SHA256 계정을 bcrypt로 자동 마이그레이션"""
    try:
        new_hash = hash_password_bcrypt(plain_pw)
        db_upsert('users', {'user_id': user_id, 'pw_hash': new_hash})
    except Exception:
        pass  # 마이그레이션 실패해도 로그인은 진행


def get_cookie_manager():
    try:
        import extra_streamlit_components as stx
        return stx.CookieManager(key="zeroda_cookie_mgr")
    except Exception:
        return None


def _sign_cookie(data: str) -> str:
    """쿠키 데이터에 HMAC 서명 추가"""
    sig = hmac.new(COOKIE_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{data}|sig={sig}"


def _verify_cookie(signed: str) -> str:
    """서명 검증 후 원본 데이터 반환. 실패 시 None"""
    if '|sig=' not in signed:
        return None
    data, sig_part = signed.rsplit('|sig=', 1)
    expected = hmac.new(COOKIE_SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig_part, expected):
        return None
    return data


# ── 로그인 시도 제한 (세션 기반) ──
def _get_login_attempts(user_id: str) -> dict:
    """로그인 실패 기록 조회"""
    attempts = st.session_state.get('_login_attempts', {})
    return attempts.get(user_id, {'count': 0, 'locked_until': None})


def _record_login_failure(user_id: str):
    """로그인 실패 기록"""
    if '_login_attempts' not in st.session_state:
        st.session_state['_login_attempts'] = {}
    attempts = st.session_state['_login_attempts']
    info = attempts.get(user_id, {'count': 0, 'locked_until': None})
    info['count'] = info.get('count', 0) + 1
    if info['count'] >= LOGIN_MAX_ATTEMPTS:
        info['locked_until'] = (datetime.now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).isoformat()
    attempts[user_id] = info


def _reset_login_attempts(user_id: str):
    """로그인 성공 시 실패 기록 초기화"""
    attempts = st.session_state.get('_login_attempts', {})
    attempts.pop(user_id, None)


def _is_locked(user_id: str) -> tuple:
    """계정 잠금 상태 확인. (잠금여부, 남은시간문자열)"""
    info = _get_login_attempts(user_id)
    locked_until = info.get('locked_until')
    if not locked_until:
        return False, ""
    lock_time = datetime.fromisoformat(locked_until)
    if datetime.now() >= lock_time:
        _reset_login_attempts(user_id)
        return False, ""
    remaining = lock_time - datetime.now()
    mins = int(remaining.total_seconds() // 60) + 1
    return True, f"{mins}분"


def authenticate(user_id: str, password: str):
    # ── 계정 잠금 체크 ──
    locked, remain = _is_locked(user_id)
    if locked:
        return False, None, f"로그인 {LOGIN_MAX_ATTEMPTS}회 실패로 계정이 잠겼습니다. {remain} 후 재시도하세요."

    # 1) GitHub 직접 시도
    from services.github_storage import is_github_available, _get_file
    if is_github_available():
        rows, _ = _get_file('users')
        rows = [r for r in (rows or []) if r.get('user_id') == user_id]
    else:
        rows = db_get('users', {'user_id': user_id})

    # 2) GitHub에 없으면 SQLite 폴백
    if not rows:
        rows = db_get('users', {'user_id': user_id})

    if not rows:
        _record_login_failure(user_id)
        info = _get_login_attempts(user_id)
        remain_tries = max(0, LOGIN_MAX_ATTEMPTS - info.get('count', 0))
        return False, None, f"아이디 또는 비밀번호가 올바르지 않습니다. (남은 시도: {remain_tries}회)"

    user = rows[0]

    # 승인대기 상태 체크
    if user.get('approval_status') == 'pending':
        return False, None, "회원가입 승인 대기 중입니다. 본사 관리자의 승인 후 로그인할 수 있습니다."
    if user.get('approval_status') == 'rejected':
        return False, None, "회원가입이 거부되었습니다. 관리자에게 문의하세요."

    if int(user.get('is_active', 1)) == 0:
        return False, None, "비활성화된 계정입니다. 관리자에게 문의하세요."

    if not verify_password(password, user.get('pw_hash', '')):
        _record_login_failure(user_id)
        info = _get_login_attempts(user_id)
        remain_tries = max(0, LOGIN_MAX_ATTEMPTS - info.get('count', 0))
        return False, None, f"아이디 또는 비밀번호가 올바르지 않습니다. (남은 시도: {remain_tries}회)"

    # ── 로그인 성공 ──
    _reset_login_attempts(user_id)

    # 기존 SHA256 해시 → bcrypt 자동 마이그레이션
    pw_hash = user.get('pw_hash', '')
    if pw_hash and not pw_hash.startswith('$2b$') and not pw_hash.startswith('$2a$'):
        _migrate_to_bcrypt(user_id, password)

    return True, user, ""


def get_current_user():
    return st.session_state.get('user', None)


def _check_session_timeout() -> bool:
    """세션 타임아웃 체크. 만료 시 False"""
    login_time_str = st.session_state.get('login_time')
    if not login_time_str:
        return True  # login_time 없으면 통과 (하위 호환)
    try:
        login_time = datetime.strptime(login_time_str, '%Y-%m-%d %H:%M:%S')
        last_activity = st.session_state.get('_last_activity')
        if last_activity:
            check_time = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
        else:
            check_time = login_time
        # 기사 역할은 타임아웃 8시간, 나머지 30분
        user = st.session_state.get('user')
        timeout = SESSION_TIMEOUT_DRIVER if (user and user.get('role') == 'driver') else SESSION_TIMEOUT_MINUTES
        if datetime.now() - check_time > timedelta(minutes=timeout):
            return False
    except Exception:
        pass
    # 활동 시간 갱신
    st.session_state['_last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return True


def is_logged_in():
    # 세션 확인
    if 'user' in st.session_state and st.session_state.user is not None:
        # 타임아웃 체크
        if not _check_session_timeout():
            st.session_state.clear()
            st.warning("⏰ 세션이 만료되었습니다. 다시 로그인해 주세요.")
            return False
        return True
    # 쿠키에서 복원 (서명 검증)
    cookies = get_cookie_manager()
    if cookies:
        try:
            signed_cookie = cookies.get("zeroda_user")
            if signed_cookie:
                verified = _verify_cookie(signed_cookie)
                if verified:
                    user = json.loads(verified)
                    # 쿠키에서 복원 시에도 DB에서 유효성 재확인
                    db_rows = db_get('users', {'user_id': user.get('user_id', '')})
                    if db_rows and int(db_rows[0].get('is_active', 1)) == 1:
                        st.session_state.user = db_rows[0]
                        st.session_state['_last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        return True
                # 서명 실패 또는 비활성 계정 → 쿠키 삭제
                try:
                    cookies.delete("zeroda_user", key="del_invalid_cookie")
                except Exception:
                    pass
        except Exception:
            pass
    # ── localStorage 토큰 기반 자동 로그인 (PWA 기사앱) ──
    auto_token = st.session_state.get('_auto_login_token', '')
    if auto_token:
        uid = _verify_auto_login_token(auto_token)
        if uid:
            db_rows = db_get('users', {'user_id': uid})
            if db_rows and int(db_rows[0].get('is_active', 1)) == 1:
                user = db_rows[0]
                # 승인 상태 확인
                if user.get('approval_status', 'approved') == 'approved' or not user.get('approval_status'):
                    st.session_state.user = user
                    st.session_state.login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    st.session_state['_last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return True
        # 토큰 무효 → 세션에서 제거
        st.session_state.pop('_auto_login_token', None)
    return False


def save_login_cookie(user):
    """서명된 쿠키 저장 (민감정보 최소화)"""
    cookies = get_cookie_manager()
    if cookies:
        try:
            # 쿠키에는 user_id만 저장 (역할/이름은 DB에서 조회)
            safe_data = json.dumps({'user_id': user.get('user_id', '')})
            signed = _sign_cookie(safe_data)
            cookies.set("zeroda_user", signed, key="set_user_cookie")
        except Exception:
            pass


# ══════════════════════════════════════════════════════
# JS localStorage 기반 자동 로그인 (PWA 기사앱 전용)
# ══════════════════════════════════════════════════════

def _create_auto_login_token(user_id: str) -> str:
    """user_id + 만료일(30일)을 HMAC 서명하여 토큰 생성"""
    expires = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    payload = json.dumps({'uid': user_id, 'exp': expires})
    sig = hmac.new(AUTO_LOGIN_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:24]
    return f"{payload}|{sig}"


def _verify_auto_login_token(token: str):
    """토큰 검증. 성공 시 user_id 반환, 실패 시 None"""
    if not token or '|' not in token:
        return None
    try:
        payload, sig = token.rsplit('|', 1)
        expected = hmac.new(AUTO_LOGIN_TOKEN_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:24]
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(payload)
        # 만료 체크
        exp_date = datetime.strptime(data['exp'], '%Y-%m-%d')
        if datetime.now() > exp_date:
            return None
        return data.get('uid')
    except Exception:
        return None


def inject_auto_login_js(user=None):
    """
    로그인 페이지 또는 메인 페이지에 JS를 주입:
    - user가 주어지면: localStorage에 토큰 저장 (로그인 성공 직후)
    - user가 None이면: localStorage에서 토큰 읽어 hidden input에 전달
    """
    if user:
        # 로그인 성공 → 토큰 저장 (기사 역할만)
        if user.get('role') == 'driver':
            token = _create_auto_login_token(user.get('user_id', ''))
            st.markdown(f"""
            <script>
            try {{ localStorage.setItem('zeroda_auto_token', '{token}'); }} catch(e) {{}}
            </script>
            """, unsafe_allow_html=True)
    else:
        # 로그인 페이지 → 토큰 존재 시 자동 로그인 시도
        # hidden text_input에 토큰 값을 JS로 주입 → Streamlit에서 읽기
        st.markdown("""
        <script>
        (function() {
            try {
                var token = localStorage.getItem('zeroda_auto_token');
                if (token) {
                    // 숨겨진 input에 토큰 전달
                    var attempts = 0;
                    var interval = setInterval(function() {
                        var inputs = document.querySelectorAll('input[aria-label="__zeroda_auto_token__"]');
                        if (inputs.length > 0) {
                            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                                window.HTMLInputElement.prototype, 'value').set;
                            nativeInputValueSetter.call(inputs[0], token);
                            inputs[0].dispatchEvent(new Event('input', { bubbles: true }));
                            clearInterval(interval);
                        }
                        attempts++;
                        if (attempts > 30) clearInterval(interval);
                    }, 200);
                }
            } catch(e) {}
        })();
        </script>
        """, unsafe_allow_html=True)


def clear_auto_login_js():
    """로그아웃 시 localStorage 토큰 삭제"""
    st.markdown("""
    <script>
    try { localStorage.removeItem('zeroda_auto_token'); } catch(e) {}
    </script>
    """, unsafe_allow_html=True)


def logout():
    # localStorage 자동 로그인 토큰 삭제
    clear_auto_login_js()
    # 쿠키 삭제
    try:
        cookies = get_cookie_manager()
        if cookies:
            cookies.delete("zeroda_user", key="del_user_cookie")
    except Exception:
        pass
    # 세션 전체 초기화
    st.session_state.clear()
    st.rerun()


def render_login_page():
    # 회원가입 화면 분기
    if st.session_state.get('show_register'):
        _render_register_page()
        return

    # ── localStorage 자동 로그인 토큰 수신용 hidden input ──
    inject_auto_login_js()  # JS: localStorage → hidden input 전달
    # hidden input (화면에 안 보이게 CSS 처리)
    st.markdown("""<style>
    div:has(> div > div > input[aria-label="__zeroda_auto_token__"]) {
        position: absolute; left: -9999px; height: 0; overflow: hidden;
    }
    </style>""", unsafe_allow_html=True)
    _auto_tok = st.text_input("__zeroda_auto_token__", key="_auto_token_input",
                               label_visibility="collapsed")
    if _auto_tok:
        uid = _verify_auto_login_token(_auto_tok)
        if uid:
            db_rows = db_get('users', {'user_id': uid})
            if db_rows and int(db_rows[0].get('is_active', 1)) == 1:
                user = db_rows[0]
                if user.get('approval_status', 'approved') == 'approved' or not user.get('approval_status'):
                    st.session_state.user = user
                    st.session_state.login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    st.session_state['_last_activity'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    st.rerun()

    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    # ── 로그인 전용 CSS ──
    st.markdown("""
    <style>
    /* ── 시스템 UI 숨김 ── */
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    header[data-testid="stHeader"],
    #MainMenu,
    .css-1dp5vir, .css-10pw50,
    [data-testid="stPageLink"] { display: none !important; }

    /* ── 밝은 배경 ── */
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 50%, #f8fafc 100%) !important;
    }

    /* ── 배경 장식 원 ── */
    .stApp::before {
        content: '';
        position: fixed; width: 500px; height: 500px; border-radius: 50%;
        background: radial-gradient(circle, rgba(56,189,148,0.12) 0%, transparent 70%);
        top: -120px; left: -100px; pointer-events: none;
    }
    .stApp::after {
        content: '';
        position: fixed; width: 400px; height: 400px; border-radius: 50%;
        background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
        bottom: -80px; right: -60px; pointer-events: none;
    }

    /* ── 중앙 컬럼을 카드로 스타일링 ── */
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stVerticalBlock"] > div.stMarkdown > div > div > .zeroda-brand) {
        background: #ffffff;
        border-radius: 24px;
        padding: 48px 48px 40px !important;
        box-shadow: 0 20px 50px rgba(0,0,0,0.10), 0 4px 16px rgba(0,0,0,0.06);
        max-width: 600px;
        margin: 0 auto;
        border: 1px solid rgba(226,232,240,0.6);
    }

    /* ── 브랜드 로고 ── */
    .zeroda-brand {
        display: flex; align-items: center; gap: 14px; margin-bottom: 32px;
    }
    .zeroda-brand-icon {
        width: 50px; height: 50px;
        background: linear-gradient(135deg, #38bd94, #3b82f6);
        border-radius: 14px;
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; font-weight: 800; color: #fff;
        box-shadow: 0 6px 20px rgba(56,189,148,0.35);
        flex-shrink: 0;
    }
    .zeroda-brand-name {
        font-size: 26px; font-weight: 800; letter-spacing: -0.5px;
        background: linear-gradient(135deg, #0f172a, #334155);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        line-height: 1.2;
    }
    .zeroda-brand-desc {
        font-size: 11px; font-weight: 600; color: #94a3b8;
        letter-spacing: 2.5px; text-transform: uppercase;
    }

    /* ── 로그인 타이틀 ── */
    .login-title {
        font-size: 24px; font-weight: 700; color: #0f172a; margin-bottom: 4px;
    }
    .login-subtitle {
        font-size: 14px; color: #64748b; margin-bottom: 28px;
    }

    /* ── 입력 필드 라벨 ── */
    .field-label {
        font-size: 13px; font-weight: 600; color: #1e293b;
        margin-bottom: 6px; margin-top: 8px;
    }

    /* ── Streamlit 입력 필드 ── */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 16px 18px !important;
        font-size: 16px !important;
        background: #f8fafc !important;
        color: #0f172a !important;
        transition: all 0.2s !important;
        width: 100% !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #38bd94 !important;
        background: #fff !important;
        color: #0f172a !important;
        box-shadow: 0 0 0 4px rgba(56,189,148,0.12) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #94a3b8 !important;
    }
    .stTextInput > div {
        width: 100% !important;
    }

    /* ── 로그인 버튼 ── */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #38bd94, #2da37e) !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 14px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 16px rgba(56,189,148,0.3) !important;
        transition: all 0.3s !important;
        margin-top: 8px !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(56,189,148,0.4) !important;
    }

    /* ── 하단 카피라이트 ── */
    .login-footer {
        text-align: center; margin-top: 28px;
        font-size: 11px; color: #94a3b8;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── 상단 여백 ──
    st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)

    # ── 중앙 카드 ──
    col1, col2, col3 = st.columns([1, 2.4, 1])
    with col2:
        # 브랜드 로고 + 타이틀
        st.markdown("""
        <div class="zeroda-brand">
            <div class="zeroda-brand-icon">Z</div>
            <div>
                <div class="zeroda-brand-name">ZERODA</div>
                <div class="zeroda-brand-desc">Waste Data Platform</div>
            </div>
        </div>
        <div class="login-title">로그인</div>
        <div class="login-subtitle">계정 정보를 입력하여 접속하세요</div>
        <div class="field-label">아이디</div>
        """, unsafe_allow_html=True)

        user_id = st.text_input("아이디", key="login_id",
                                placeholder="아이디를 입력하세요",
                                label_visibility="collapsed")

        st.markdown('<div class="field-label">비밀번호</div>', unsafe_allow_html=True)

        password = st.text_input("비밀번호", key="login_pw", type="password",
                                 placeholder="비밀번호를 입력하세요",
                                 label_visibility="collapsed")

        if st.button("로그인", type="primary", use_container_width=True):
            if not user_id or not password:
                st.warning("아이디와 비밀번호를 모두 입력하세요.")
                return
            success, user, err_msg = authenticate(user_id, password)
            if success:
                st.session_state.user = user
                st.session_state.login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_login_cookie(user)
                # 기사 역할: localStorage에 자동 로그인 토큰 저장
                inject_auto_login_js(user)
                st.rerun()
            else:
                st.error(err_msg if err_msg else "아이디 또는 비밀번호가 올바르지 않습니다.")

        # ── 회원가입 버튼 ──
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        if st.button("📝 회원가입", use_container_width=True, key="btn_goto_register"):
            st.session_state['show_register'] = True
            st.rerun()

        st.markdown("""
        <div class="login-footer">
            &copy; 2026 ZERODA &middot; 하영자원 폐기물데이터플랫폼
        </div>
        """, unsafe_allow_html=True)


def _render_register_page():
    """자가 회원가입 페이지 (관리자 승인 필요)"""
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    # ── 로그인과 동일한 배경 스타일 ──
    st.markdown("""
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    header[data-testid="stHeader"],
    #MainMenu { display: none !important; }
    .stApp {
        background: linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 50%, #f8fafc 100%) !important;
    }
    /* 회원가입 카드 배경 흰색 */
    div[data-testid="stVerticalBlock"] {
        background: transparent;
    }
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 14px 16px !important;
        font-size: 15px !important;
        background: #f8fafc !important;
        color: #0f172a !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #38bd94 !important;
        background: #fff !important;
        box-shadow: 0 0 0 4px rgba(56,189,148,0.12) !important;
    }
    label, .stMarkdown p, .stMarkdown div, h1, h2, h3, h4 {
        color: #0f172a !important;
    }
    .stSelectbox label, .stMultiSelect label {
        color: #0f172a !important;
    }
    /* 가입신청 버튼 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #38bd94, #2da37e) !important;
        border: none !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2.8, 1])
    with col2:
        st.markdown("""
        <div class="zeroda-brand">
            <div class="zeroda-brand-icon">Z</div>
            <div>
                <div class="zeroda-brand-name">ZERODA</div>
                <div class="zeroda-brand-desc">회원가입</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📝 신규 회원가입")
        st.caption("가입 후 본사 관리자 승인이 완료되면 로그인할 수 있습니다.")

        # ── 기본 정보 ──
        c1, c2 = st.columns(2)
        with c1:
            reg_id = st.text_input("아이디 *", key="reg_id",
                                   placeholder="영문/숫자 조합")
            reg_name = st.text_input("이름 *", key="reg_name")
        with c2:
            reg_pw = st.text_input("비밀번호 *", key="reg_pw", type="password",
                                   placeholder=f"최소 {PW_MIN_LENGTH}자 (대문자+숫자+특수문자)")
            reg_pw2 = st.text_input("비밀번호 확인 *", key="reg_pw2", type="password")

        # ── 역할 선택 (admin 제외) ──
        register_roles = {k: v for k, v in ROLES.items() if k != 'admin'}
        reg_role = st.selectbox(
            "역할 *", list(register_roles.keys()),
            format_func=lambda x: f"{ROLE_ICONS.get(x, '')} {register_roles.get(x, x)}",
            key="reg_role"
        )

        # ── 역할별 소속 정보 ──
        reg_vendor = ''
        reg_schools = ''
        reg_edu_office = ''

        if reg_role in ('vendor_admin', 'driver'):
            st.markdown("**📦 소속 업체**")
            from database.db_manager import get_vendor_options
            vendor_opts = get_vendor_options()
            if vendor_opts:
                opt_keys = list(vendor_opts.keys())
                sel_label = st.selectbox("소속 업체 *", opt_keys, key="reg_vendor_sel")
                reg_vendor = vendor_opts[sel_label]
            else:
                reg_vendor = st.text_input("소속 업체 ID *", key="reg_vendor_txt",
                                           placeholder="업체 ID 입력")

        elif reg_role in ('school_admin', 'school_nutrition', 'meal_manager'):
            label = "담당 급식소(학교)" if reg_role == 'meal_manager' else "담당 학교"
            st.markdown(f"**🏫 {label}**")
            from database.db_manager import get_all_schools
            all_schools = get_all_schools()
            if all_schools:
                sel = st.multiselect(f"{label} *", all_schools, key="reg_school_sel")
                reg_schools = ','.join(sel)
            else:
                reg_schools = st.text_input(f"{label} (쉼표 구분)", key="reg_school_txt")

        elif reg_role == 'edu_office':
            st.markdown("**🏛️ 교육청명**")
            reg_edu_office = st.text_input("교육청명 *", key="reg_edu")

        # ── 가입 버튼 ──
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("✅ 가입 신청", type="primary", use_container_width=True,
                         key="btn_register_submit"):
                # 검증
                if not reg_id or not reg_name or not reg_pw:
                    st.error("아이디, 이름, 비밀번호는 필수입니다.")
                elif reg_pw != reg_pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    # 비밀번호 정책 검증
                    pw_ok, pw_msg = validate_password(reg_pw)
                    if not pw_ok:
                        st.error(pw_msg)
                    else:
                        # 중복 체크
                        existing = db_get('users', {'user_id': reg_id})
                        if existing:
                            st.error("이미 존재하는 아이디입니다.")
                        else:
                            # 계정 생성 (approval_status='pending')
                            ok = db_upsert('users', {
                                'user_id': reg_id,
                                'pw_hash': hash_password_bcrypt(reg_pw),
                                'role': reg_role,
                                'name': reg_name,
                                'vendor': reg_vendor,
                                'schools': reg_schools,
                                'edu_office': reg_edu_office,
                                'is_active': 1,
                                'approval_status': 'pending',
                                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            })
                            if ok:
                                st.success("🎉 회원가입 신청 완료! 본사 관리자 승인 후 로그인할 수 있습니다.")
                                st.balloons()
                            else:
                                st.error("가입 처리 중 오류가 발생했습니다. 다시 시도해주세요.")

        with btn_col2:
            if st.button("← 로그인으로 돌아가기", use_container_width=True,
                         key="btn_back_to_login"):
                st.session_state.pop('show_register', None)
                st.rerun()
