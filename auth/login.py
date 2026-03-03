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

    st.markdown("""
    <div style="text-align:center;padding:40px 0 20px;">
        <div style="font-size:48px;font-weight:900;color:#1a73e8;">ZERODA</div>
        <h1 style="font-size:24px;font-weight:700;">제로다 폐기물데이터플랫폼</h1>
        <div style="color:#5f6368;">하영자원 | 경기도 화성시</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 로그인")
        user_id  = st.text_input("아이디", key="login_id", placeholder="아이디를 입력하세요")
        password = st.text_input("비밀번호", key="login_pw", type="password", placeholder="비밀번호를 입력하세요")

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
                # 임시 디버그
                from services.github_storage import is_github_available, _get_file
                with st.expander("🔍 디버그 (임시)"):
                    st.write(f"GitHub 연결: {is_github_available()}")
                    rows, _ = _get_file('users')
                    st.write(f"users.json 행 수: {len(rows) if rows else 0}")
                    if rows:
                        st.write(f"첫번째 user_id: {rows[0].get('user_id','없음')}")
                        st.write(f"pw_hash 앞 10자: {rows[0].get('pw_hash','없음')[:10]}")

    st.markdown("---")
    st.markdown("#### 접속 가능 역할")
    cols = st.columns(3)
    role_list = [
        ("admin",            "본사 관리자",      "전체 데이터 관리"),
        ("vendor_admin",     "외주업체 관리자",   "담당 학교 수거 관리"),
        ("driver",           "수거기사",          "수거일지 입력"),
        ("school_admin",     "학교 행정실",       "정산서 확인"),
        ("school_nutrition", "학교 영양사",       "수거일정 조회"),
        ("edu_office",       "교육청",            "학교 현황 조회"),
    ]
    for i, (role, title, desc) in enumerate(role_list):
        with cols[i % 3]:
            icon = ROLE_ICONS.get(role, "")
            st.markdown(f"""
            <div style="background:#f8f9fa;border-radius:10px;padding:15px;margin-bottom:10px;text-align:center;">
                <div style="font-weight:700;font-size:14px;color:#202124;">{icon} {title}</div>
                <div style="font-size:12px;color:#5f6368;margin-top:4px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
