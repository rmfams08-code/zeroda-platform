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
    is_user_active: bool = False

    # ── 로그인 폼 ──
    login_error: str = ""
    login_loading: bool = False
    remember_me_checkbox: bool = True   # 자동 로그인 (기사 전용, 90일 쿠키)

    # ── 회원가입 폼 ──
    reg_id: str = ""
    reg_name: str = ""
    reg_pw: str = ""
    reg_pw2: str = ""
    reg_role: str = "driver"
    reg_vendor: str = ""
    reg_schools: str = ""
    reg_edu_office: str = ""
    reg_error: str = ""
    reg_success: str = ""
    reg_loading: bool = False

    # ── 회원가입 NEIS 필드 (school/meal_manager 전용) ──
    reg_vendor_select: str = ""         # 소속 업체 드롭다운 선택값
    reg_school_name_neis: str = ""      # NEIS용 학교명 (정확한 이름 필요)
    reg_neis_edu: str = ""              # 교육청코드 7자리
    reg_neis_school: str = ""           # 학교코드 7자리
    reg_vendor_options: list[str] = []  # 드롭다운 옵션 (승인된 업체 목록)

    def set_reg_id(self, v: str): self.reg_id = v
    def set_reg_name(self, v: str): self.reg_name = v
    def set_reg_pw(self, v: str): self.reg_pw = v
    def set_reg_pw2(self, v: str): self.reg_pw2 = v
    def set_reg_role(self, v: str):
        self.reg_role = v
        self.reg_vendor = ""
        self.reg_schools = ""
        self.reg_edu_office = ""
    def set_reg_vendor(self, v: str): self.reg_vendor = v
    def set_reg_schools(self, v: str): self.reg_schools = v
    def set_reg_edu_office(self, v: str): self.reg_edu_office = v
    def set_reg_vendor_select(self, v: str): self.reg_vendor_select = v
    def set_reg_school_name_neis(self, v: str): self.reg_school_name_neis = v
    def set_reg_neis_edu(self, v: str): self.reg_neis_edu = v
    def set_reg_neis_school(self, v: str): self.reg_neis_school = v

    def load_signup_vendor_options(self):
        """회원가입 페이지 on_mount: 승인된 업체 목록 로드."""
        from zeroda_reflex.utils.database import get_active_vendor_names
        try:
            self.reg_vendor_options = get_active_vendor_names()
        except Exception:
            self.reg_vendor_options = []

    def submit_register(self):
        try:
            self._do_register()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"[submit_register] 예외: {e}", exc_info=True)
            self.reg_error = f"가입 처리 중 오류가 발생했습니다: {e}"
            self.reg_loading = False

    def _do_register(self):
        from zeroda_reflex.utils.database import create_user, validate_password
        self.reg_loading = True
        self.reg_error = ""
        self.reg_success = ""
        if not self.reg_id or not self.reg_name or not self.reg_pw:
            self.reg_error = "아이디, 이름, 비밀번호는 필수입니다."
            self.reg_loading = False
            return
        if self.reg_pw != self.reg_pw2:
            self.reg_error = "비밀번호가 일치하지 않습니다."
            self.reg_loading = False
            return
        if self.reg_role == "admin":
            self.reg_error = "본사관리자 계정은 자가 가입이 불가합니다."
            self.reg_loading = False
            return
        ok, msg = validate_password(self.reg_pw)
        if not ok:
            self.reg_error = msg
            self.reg_loading = False
            return
        # school / meal_manager 추가 검증
        if self.reg_role in ("school", "meal_manager"):
            if not self.reg_vendor_select:
                self.reg_error = "소속 업체를 선택해주세요."
                self.reg_loading = False
                return
            if not self.reg_school_name_neis:
                self.reg_error = "학교명을 입력해주세요."
                self.reg_loading = False
                return
            # NEIS 코드는 선택사항 — 빈 값이어도 가입 가능 (본사 관리자가 나중에 등록)
            if self.reg_neis_edu.strip() and len(self.reg_neis_edu.strip()) != 7:
                self.reg_error = "NEIS 교육청코드를 입력할 경우 7자리여야 합니다."
                self.reg_loading = False
                return
            if self.reg_neis_school.strip() and len(self.reg_neis_school.strip()) != 7:
                self.reg_error = "NEIS 학교코드를 입력할 경우 7자리여야 합니다."
                self.reg_loading = False
                return
        created, msg = create_user(
            user_id=self.reg_id.strip(),
            password=self.reg_pw,
            role=self.reg_role,
            name=self.reg_name.strip(),
            vendor=self.reg_vendor.strip(),
            schools=self.reg_schools.strip(),
            edu_office=self.reg_edu_office.strip(),
            approval_status="pending",
            is_active=1,
            pending_vendor=self.reg_vendor_select.strip() or None,
            pending_school_name=self.reg_school_name_neis.strip() or None,
            neis_edu_pending=self.reg_neis_edu.strip() or None,
            neis_school_pending=self.reg_neis_school.strip() or None,
        )
        if not created:
            self.reg_error = msg
            self.reg_loading = False
            return
        self.reg_success = "가입 신청 완료! 본사 관리자 승인 후 로그인할 수 있습니다."
        self.reg_id = ""
        self.reg_name = ""
        self.reg_pw = ""
        self.reg_pw2 = ""
        self.reg_vendor = ""
        self.reg_schools = ""
        self.reg_edu_office = ""
        self.reg_vendor_select = ""
        self.reg_school_name_neis = ""
        self.reg_neis_edu = ""
        self.reg_neis_school = ""
        self.reg_loading = False

    def goto_login(self):
        self.reg_error = ""
        self.reg_success = ""
        return rx.redirect("/")

    async def login(self, form_data: dict):
        """로그인 처리"""
        self.login_loading = True
        self.login_error = ""

        uid = form_data.get("user_id", "").strip()
        pw = form_data.get("password", "").strip()

        if not uid or not pw:
            self.login_error = "아이디와 비밀번호를 모두 입력하세요."
            self.login_loading = False
            return

        from zeroda_reflex.utils.database import db_get
        rows = db_get("users", {"user_id": uid})
        if not rows:
            self.login_error = "아이디 또는 비밀번호가 올바르지 않습니다."
            self.login_loading = False
            return
        _u = rows[0]
        if _u.get("approval_status") == "pending":
            self.login_error = "회원가입 승인 대기 중입니다. 본사 관리자 승인 후 로그인할 수 있습니다."
            self.login_loading = False
            return
        if _u.get("approval_status") == "rejected":
            self.login_error = "회원가입이 거부되었습니다. 관리자에게 문의하세요."
            self.login_loading = False
            return
        user = authenticate_user(uid, pw)
        if user is None:
            self.login_error = "아이디 또는 비밀번호가 올바르지 않습니다."
            self.login_loading = False
            return

        # 로그인 성공 — DB NULL 값을 빈 문자열로 안전 변환 (None → "" 방지)
        self.user_id = user.get("user_id") or ""
        self.user_name = user.get("name") or ""
        self.user_role = user.get("role") or ""
        self.user_vendor = user.get("vendor") or ""
        self.user_schools = user.get("schools") or ""
        self.user_edu_office = user.get("edu_office") or ""
        self.is_authenticated = True
        self.is_user_active = (int(_u.get("is_active", 0) or 0) == 1)
        self.login_loading = False
        self.login_error = ""

        # 탭 초기화 (이전 세션 복원 방지) — 로그인 성공 시점
        from zeroda_reflex.state.admin_state import AdminState
        from zeroda_reflex.state.vendor_state import VendorState
        from zeroda_reflex.state.school_state import SchoolState
        from zeroda_reflex.state.edu_state import EduState
        from zeroda_reflex.state.meal_state import MealState
        admin_s = await self.get_state(AdminState)
        admin_s.active_tab = "대시보드"
        vendor_s = await self.get_state(VendorState)
        vendor_s.active_tab = "수거현황"
        school_s = await self.get_state(SchoolState)
        school_s.active_tab = "월별현황"
        edu_s = await self.get_state(EduState)
        edu_s.active_tab = "전체현황"
        meal_s = await self.get_state(MealState)
        meal_s.active_tab = "식단등록"

        # 기사 자동 로그인 쿠키 발급 (remember_me_checkbox == True 일 때)
        if self.user_role == "driver" and self.remember_me_checkbox:
            from zeroda_reflex.utils.database import create_driver_token
            try:
                token = create_driver_token(self.user_id, device_hint="")
                yield rx.call_script(
                    f"""
                    (async () => {{
                        try {{
                            await fetch('/api/driver/set-token', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                body: JSON.stringify({{user_id: '{self.user_id}', token: '{token}'}})
                            }});
                        }} catch(e) {{ console.warn('[auth] set-token fetch 실패:', e); }}
                    }})();
                    """
                )
            except Exception as _e:
                import logging
                logging.getLogger(__name__).warning("[auth] 드라이버 토큰 발급 실패: %s", _e)

        yield self._redirect_by_role()

    def set_remember_me_checkbox(self, v: bool):
        self.remember_me_checkbox = v

    def logout(self):
        """로그아웃 — 기사의 경우 HttpOnly 자동 로그인 쿠키도 삭제"""
        was_driver = (self.user_role == "driver")
        self.user_id = ""
        self.user_name = ""
        self.user_role = ""
        self.user_vendor = ""
        self.user_schools = ""
        self.user_edu_office = ""
        self.is_authenticated = False
        self.is_user_active = False
        if was_driver:
            yield rx.call_script(
                """
                (async () => {
                    try {
                        await fetch('/api/driver/revoke-token', {method: 'POST'});
                    } catch(e) { console.warn('[auth] revoke-token fetch 실패:', e); }
                })();
                """
            )
        yield rx.redirect("/")

    def restore_driver_session(self, data: dict):
        """JS fetch /api/driver/check-token 결과를 받아 세션 복원.
        JS 쪽에서: if ok → rx.call_event(AuthState.restore_driver_session, {user_id, ...})
        실제로는 check_cookie_login 에서 호출됨.
        """
        uid = (data or {}).get("user_id", "")
        if not uid:
            return
        from zeroda_reflex.utils.database import db_get
        rows = db_get("users", {"user_id": uid})
        if not rows:
            return
        u = rows[0]
        if u.get("approval_status") != "approved" or not int(u.get("is_active", 0) or 0):
            return
        self.user_id = u.get("user_id") or ""
        self.user_name = u.get("name") or ""
        self.user_role = u.get("role") or ""
        self.user_vendor = u.get("vendor") or ""
        self.user_schools = u.get("schools") or ""
        self.user_edu_office = u.get("edu_office") or ""
        self.is_authenticated = True
        self.is_user_active = True
        yield rx.redirect("/driver")

    async def check_cookie_login(self):
        """로그인 페이지(/) on_load — HttpOnly 쿠키 자동로그인 시도.
        이미 인증된 상태면 역할별 페이지로 리다이렉트.
        미인증이면 /api/driver/check-token fetch → ok이면 window.location.href='/driver'.
        """
        if self.is_authenticated:
            yield self._redirect_by_role()
            return
        yield rx.call_script(
            "fetch('/api/driver/check-token',{credentials:'same-origin'})"
            ".then(r=>r.json())"
            ".then(d=>{if(d&&d.ok)window.location.href='/driver';});"
        )

    async def restore_driver_session_silent(self, data: dict):
        """on_driver_load cookie 검증 콜백 — 세션 복원 후 /driver 재진입.
        data: fetch('/api/driver/check-token') JSON 응답 {ok, user_id}.
        복원 성공 → redirect('/driver') (이때 is_authenticated=True 이므로 루프 없음).
        복원 실패 → redirect('/').
        """
        uid = (data or {}).get("user_id", "")
        if not uid:
            yield rx.redirect("/")
            return
        from zeroda_reflex.utils.database import db_get
        rows = db_get("users", {"user_id": uid})
        if not rows:
            yield rx.redirect("/")
            return
        u = rows[0]
        if u.get("approval_status") != "approved" or not int(u.get("is_active", 0) or 0):
            yield rx.redirect("/")
            return
        self.user_id = u.get("user_id") or ""
        self.user_name = u.get("name") or ""
        self.user_role = u.get("role") or ""
        self.user_vendor = u.get("vendor") or ""
        self.user_schools = u.get("schools") or ""
        self.user_edu_office = u.get("edu_office") or ""
        self.is_authenticated = True
        self.is_user_active = True
        # is_authenticated=True 이므로 on_driver_load 재실행 시 무한루프 없음
        yield rx.redirect("/driver")

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
