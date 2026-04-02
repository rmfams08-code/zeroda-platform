# zeroda_platform/auth/login.py
import streamlit as st
import hashlib
import json
from datetime import datetime
from config.settings import ROLES, ROLE_ICONS, COMMON_CSS
from database.db_manager import db_get


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    if plain.strip() == hashed.strip():
        return True
    if hash_password(plain.strip()) == hashed.strip():
        return True
    return False


def get_cookie_manager():
    try:
        import extra_streamlit_components as stx
        return stx.CookieManager(key="zeroda_cookie_mgr")
    except Exception:
        return None


def authenticate(user_id: str, password: str):
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
        return False, None
    user = rows[0]
    if int(user.get('is_active', 1)) == 0:
        return False, None
    if not verify_password(password, user.get('pw_hash', '')):
        return False, None
    return True, user


def get_current_user():
    return st.session_state.get('user', None)


def is_logged_in():
    # 세션 확인
    if 'user' in st.session_state and st.session_state.user is not None:
        return True
    # 쿠키에서 복원
    cookies = get_cookie_manager()
    if cookies:
        try:
            user_json = cookies.get("zeroda_user")
            if user_json:
                user = json.loads(user_json)
                st.session_state.user = user
                return True
        except Exception:
            pass
    return False


def save_login_cookie(user):
    cookies = get_cookie_manager()
    if cookies:
        try:
            cookies.set("zeroda_user", json.dumps(user), key="set_user_cookie")
        except Exception:
            pass


def logout():
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

    /* ── 다크 배경 ── */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    }

    /* ── 배경 장식 원 ── */
    .stApp::before {
        content: '';
        position: fixed; width: 500px; height: 500px; border-radius: 50%;
        background: radial-gradient(circle, rgba(56,189,148,0.07) 0%, transparent 70%);
        top: -120px; left: -100px; pointer-events: none;
    }
    .stApp::after {
        content: '';
        position: fixed; width: 400px; height: 400px; border-radius: 50%;
        background: radial-gradient(circle, rgba(59,130,246,0.05) 0%, transparent 70%);
        bottom: -80px; right: -60px; pointer-events: none;
    }

    /* ── 중앙 컬럼을 카드로 스타일링 ── */
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stVerticalBlock"] > div.stMarkdown > div > div > .zeroda-brand) {
        background: #ffffff;
        border-radius: 24px;
        padding: 48px 40px 40px !important;
        box-shadow: 0 25px 60px rgba(0,0,0,0.35);
        max-width: 440px;
        margin: 0 auto;
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
        font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 4px;
    }
    .login-subtitle {
        font-size: 14px; color: #94a3b8; margin-bottom: 24px;
    }

    /* ── 입력 필드 라벨 ── */
    .field-label {
        font-size: 13px; font-weight: 600; color: #334155;
        margin-bottom: 6px; margin-top: 4px;
    }

    /* ── Streamlit 입력 필드 ── */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        padding: 13px 16px !important;
        font-size: 15px !important;
        background: #f8fafc !important;
        color: #0f172a !important;
        transition: all 0.2s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #38bd94 !important;
        background: #fff !important;
        color: #0f172a !important;
        box-shadow: 0 0 0 4px rgba(56,189,148,0.1) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #94a3b8 !important;
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
        font-size: 11px; color: rgba(148,163,184,0.5);
    }
    </style>
    """, unsafe_allow_html=True)

    # ── 상단 여백 ──
    st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)

    # ── 중앙 카드 ──
    col1, col2, col3 = st.columns([1.3, 2, 1.3])
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
            success, user = authenticate(user_id, password)
            if success:
                st.session_state.user = user
                st.session_state.login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                save_login_cookie(user)
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

        st.markdown("""
        <div class="login-footer">
            &copy; 2026 ZERODA &middot; 하영자원 폐기물데이터플랫폼
        </div>
        """, unsafe_allow_html=True)
