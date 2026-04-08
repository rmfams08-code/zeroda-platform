# zeroda_reflex/state/auth_state.py
# 인증 상태 관리 — 로그인/로그아웃/세션 유지
# Phase 0-B: 공통 상수 및 유틸리티 메서드 추가
# 2026-04-08 회원가입 복구 — _do_register 본문 완성
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
        """회원가입 폼 제출 핸들러 (외부 진입점).
        예외는 모두 잡아서 reg_error로 표시한다."""
        self.reg_error = ""
        self.reg_success = ""
        self.reg_loading = True
        try:
            self._do_register()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"[submit_register] 예외: {e}", exc_info=True
            )
            self.reg_error = f"가입 처리 중 오류가 발생했습니다: {e}"
        finally:
            self.reg_loading = False

    def _do_register(self):
        """회원가입 본 처리.
        1) 입력 검증 → 2) 비밀번호 강도 검증 → 3) 역할별 필수 필드 검증
        4) DB INSERT (create_user) → 5) 성공/실패 메시지 설정
        실패는 self.reg_error 에 메시지 세팅 후 return.
        성공은 self.reg_success + 폼 초기화."""
        from zeroda_reflex.utils.database import create_user, validate_password

        # 1) 기본 필수값
        if not self.reg_id or not self.reg_id.strip():
            self.reg_error = "아이디를 입력해주세요."
            return
        if not self.reg_name or not self.reg_name.strip():
            self.reg_error = "이름을 입력해주세요."
            return
        if not self.reg_pw:
            self.reg_error = "비밀번호를 입력해주세요."
            return
        if self.reg_pw != self.reg_pw2:
            self.reg_error = "비밀번호가 일치하지 않습니다."
            return

        # 2) 비밀번호 강도
        ok, msg = validate_password(self.reg_pw)
        if not ok:
            self.reg_error = msg
            return

        # 3) 역할별 필수 필드
        role = (self.reg_role or "").strip()
        if not role:
            self.reg_error = "역할을 선택해주세요."
            return

        vendor = ""
        schools = ""
        edu_office = ""
        pending_vendor = None
        pending_school_name = None
        neis_edu_pending = None
        neis_school_pending = None

        if role in ("driver", "vendor_admin"):
            vendor = (self.reg_vendor or "").strip()
            # 업체명은 권장이지만 필수는 아님(가입 후 본사가 배정 가능)

        elif role in ("school", "meal_manager"):
            v = (self.reg_vendor_select or "").strip()
            s = (self.reg_school_name_neis or "").strip()
            ne = (self.reg_neis_edu or "").strip()
            ns = (self.reg_neis_school or "").strip()
            if not v:
                self.reg_error = "소속 업체를 선택해주세요."
                return
            if not s:
                self.reg_error = "학교명(NEIS 등록명)을 입력해주세요."
                return
            if not (ne.isdigit() and len(ne) == 7):
                self.reg_error = "NEIS 교육청코드는 7자리 숫자입니다."
                return
            if not (ns.isdigit() and len(ns) == 7):
                self.reg_error = "NEIS 학교코드는 7자리 숫자입니다."
                return
            # 승인 시점에 customer_info로 반영하므로 pending_*에 보관
            pending_vendor = v
            pending_school_name = s
            neis_edu_pending = ne
            neis_school_pending = ns
            # 표시용 (조회 편의)
            schools = s

        elif role == "edu_office":
            edu_office = (self.reg_edu_office or "").strip()
            if not edu_office:
                self.reg_error = "교육청명을 입력해주세요."
                return

        # 4) DB INSERT
        ok, msg = create_user(
            user_id=self.reg_id.strip(),
            password=self.reg_pw,
            role=role,
            name=self.reg_name.strip(),
            vendor=vendor,
            schools=schools,
            edu_office=edu_office,
            approval_status="pending",
            is_active=1,
            pending_vendor=pending_vendor,
            pending_school_name=pending_school_name,
            neis_edu_pending=neis_edu_pending,
            neis_school_pending=neis_school_pending,
        )
        if not ok:
            self.reg_error = msg
            return

        # 5) 성공 — 폼 초기화 + 안내 메시지
        self.reg_success = (
            "가입 신청이 완료되었습니다. 본사 관리자 승인 후 로그인하실 수 있습니다."
        )
        self.reg_id = ""
        self.reg_name = ""
        self.reg_pw = ""
        self.reg_pw2 = ""
        self.reg_vendor = ""
        self.reg_vendor_select = ""
        self.reg_school_name_neis = ""
        self.reg_neis_edu = ""
        self.reg_neis_school = ""
        self.reg_edu_office = ""
