# zeroda_reflex/state/auth_state.py
# 인증 상태 관리 — 로그인/로그아웃/세션 유지
# Phase 0-B: 공통 상수 및 유틸리티 메서드 추가
import reflex as rx
from datetime import datetime
from zeroda_reflex.utils.database import authenticate_user


# ══════════════════════════════════════════
#  공통 상수 — 모든 역할에서 사용
# ══════════════════════════════════════════

def get_year_options() -> list[str]:
    """현재 연도 기준으로 동적 연도 옵션 생성 (하드코딩 제거)
    예: 2026년이면 ["2024", "2025", "2026", "2027"] 반환
    """
    current = datetime.now().year
    return [str(y) for y in range(current - 2, current + 2)]


# 월 옵션은 고정이므로 상수로 정의
MONTH_OPTIONS: list[str] = [str(m) for m in range(1, 13)]


class AuthState(rx.State):
    """전체 앱 인증 상태
    모든 역할별 State의 부모 클래스입니다.
    """

    # ── 세션 데이터 ──
    user_id: str = ""
    user_name: str = ""
    user_role: str = ""
    user_vendor: str = ""
    user_schools: str = ""      # 쉼표 구분 학교 목록 (school/edu_office 역할)
    user_edu_office: str = ""   # 교육청명 (edu_office 역할)
    is_authenticated: bool = False

    # ── 로그인 폼 ──
    login_error: str = ""
    login_loading: bool = False

    def login(self, form_data: dict):
        """로그인 처리"""
        self.login_loading = True
        self.login_error = ""

        uid = form_data.get("user_id", "").strip()
        pw = form_data.get("password", "").strip()

        if not uid or not pw:
            self.login_error = "아이디와 비밀번호를 모두 입력하세요."
            self.login_loading = False
            return

        user = authenticate_user(uid, pw)
        if user is None:
            self.login_error = "아이디 또는 비밀번호가 올바르지 않습니다."
            self.login_loading = False
            return

        # 로그인 성공
        self.user_id = user.get("user_id", "")
        self.user_name = user.get("name", "")
        self.user_role = user.get("role", "")
        self.user_vendor = user.get("vendor", "")
        self.user_schools = user.get("schools", "")
        self.user_edu_office = user.get("edu_office", "")
        self.is_authenticated = True
        self.login_loading = False
        self.login_error = ""

        # 역할별 페이지로 이동
        return self._redirect_by_role()

    def logout(self):
        """로그아웃"""
        self.user_id = ""
        self.user_name = ""
        self.user_role = ""
        self.user_vendor = ""
        self.user_schools = ""
        self.user_edu_office = ""
        self.is_authenticated = False
        return rx.redirect("/")

    def check_auth(self):
        """페이지 로드 시 인증 확인. 미인증 시 로그인으로 리다이렉트"""
        if not self.is_authenticated:
            return rx.redirect("/")

    def _redirect_by_role(self):
        """역할별 리다이렉트"""
        if self.user_role == "driver":
            return rx.redirect("/driver")
        elif self.user_role == "vendor_admin":
            return rx.redirect("/vendor")
        elif self.user_role == "admin":
            return rx.redirect("/admin")
        elif self.user_role == "school":
            return rx.redirect("/school")
        elif self.user_role == "edu_office":
            return rx.redirect("/edu")
        elif self.user_role in ("meal_manager", "school_nutrition"):
            return rx.redirect("/meal")
        else:
            return rx.redirect("/driver")  # 기본값
