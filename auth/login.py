# zeroda_platform/auth/login.py
# ==========================================
# 로그인 UI + 인증 처리
# ==========================================

import streamlit as st
import hashlib
from datetime import datetime
from config.settings import ROLES, ROLE_ICONS, COMMON_CSS
from database.db_manager import db_get


# ──────────────────────────────────────────
# 비밀번호 해시
# ──────────────────────────────────────────

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """평문 비밀번호와 해시 비교 (구형 평문 DB 호환 포함)"""
    if not plain or not hashed:
        return False
    # 신규: sha256 해시 비교
    if hash_password(plain) == hashed:
        return True
    # 구형 호환: 평문 저장된 경우
    if plain == hashed:
        return True
    return False


# ──────────────────────────────────────────
# 인증
# ──────────────────────────────────────────

def authenticate(user_id: str, password: str):
    """
    로그인 처리
    반환값: (True, user_dict) 또는 (False, None)
    """
    rows = db_get('users', {'user_id': user_id})
    if not rows:
        return False, None
    user = rows[0]

    # 비활성 계정 차단
    if int(user.get('is_active', 1)) == 0:
        return False, None

    if not verify_password(password, user.get('pw_hash', '')):
        return False, None

    return True, user


def get_current_user():
    """세션에서 현재 로그인 유저 반환"""
    return st.session_state.get('user', None)


def is_logged_in():
    return 'user' in st.session_state and st.session_state.user is not None


def logout():
    for key in ['user', 'page']:
        st.session_state.pop(key, None)
    st.rerun()


# ──────────────────────────────────────────
# 로그인 화면
# ──────────────────────────────────────────

def render_login_page():
    """로그인 페이지 렌더링"""
    st.markdown(COMMON_CSS, unsafe_allow_html=True)

    st.markdown("""
    <div class="landing-header">
        <div class="brand">♻️ ZERODA</div>
        <h1>제로다 폐기물데이터플랫폼</h1>
        <div class="subtitle">하영자원 | 경기도 화성시</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 로그인")
        user_id  = st.text_input("아이디",  key="login_id",  placeholder="아이디를 입력하세요")
        password = st.text_input("비밀번호", key="login_pw",  type="password", placeholder="비밀번호를 입력하세요")

        if st.button("로그인", type="primary", use_container_width=True):
            if not user_id or not password:
                st.warning("아이디와 비밀번호를 모두 입력하세요.")
                return

            success, user = authenticate(user_id, password)
            if success:
                st.session_state.user = user
                st.session_state.login_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    # 역할 안내 카드
    st.markdown("---")
    st.markdown("#### 접속 가능 역할")
    cols = st.columns(3)
    role_list = [
        ("admin",            "본사 관리자",       "전체 데이터 관리, 계정 관리"),
        ("vendor_admin",     "외주업체 관리자",    "담당 학교 수거 관리"),
        ("driver",           "수거기사",           "수거일지 입력"),
        ("school_admin",     "학교 행정실",        "정산서, 계약서 확인"),
        ("school_nutrition", "학교 영양사",        "수거일정, 수거량 조회"),
        ("edu_office",       "교육청/교육지원청",  "관할 학교 현황 조회"),
    ]
    for i, (role, title, desc) in enumerate(role_list):
        with cols[i % 3]:
            icon = ROLE_ICONS.get(role, "👤")
            st.markdown(f"""
            <div style="background:#f8f9fa;border-radius:10px;padding:15px;margin-bottom:10px;text-align:center;">
                <div style="font-size:32px;">{icon}</div>
                <div style="font-weight:700;font-size:14px;color:#202124;">{title}</div>
                <div style="font-size:12px;color:#5f6368;margin-top:4px;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)