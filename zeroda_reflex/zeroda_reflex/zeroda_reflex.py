# zeroda_reflex/zeroda_reflex.py
# 메인 앱 엔트리 — 페이지 등록 및 라우팅
import reflex as rx
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from zeroda_reflex.pages.login import login_page
from zeroda_reflex.pages.register import register_page
from zeroda_reflex.pages.driver import driver_page
from zeroda_reflex.pages.vendor_admin import vendor_admin_page
from zeroda_reflex.pages.hq_admin import hq_admin_page
from zeroda_reflex.pages.school import school_page
from zeroda_reflex.pages.edu_office import edu_office_page
from zeroda_reflex.pages.meal_manager import meal_manager_page
from zeroda_reflex.pages.privacy import privacy_page
from zeroda_reflex.pages.terms import terms_page
from zeroda_reflex.state.auth_state import AuthState
from zeroda_reflex.state.driver_state import DriverState
from zeroda_reflex.state.vendor_state import VendorState
from zeroda_reflex.state.admin_state import AdminState
from zeroda_reflex.state.school_state import SchoolState
from zeroda_reflex.state.edu_state import EduState
from zeroda_reflex.state.meal_state import MealState


# ── 앱 생성 ──
app = rx.App(
    theme=rx.theme(appearance="light"),
    style={
        "font_family": "'Pretendard', 'Apple SD Gothic Neo', sans-serif",
    },
)

# ── 페이지 등록 ──
app.add_page(login_page, route="/", title="ZERODA 로그인",
             on_load=AuthState.check_cookie_login)
app.add_page(register_page, route="/register", title="ZERODA 회원가입",
             on_load=AuthState.load_signup_vendor_options)
app.add_page(
    driver_page,
    route="/driver",
    title="ZERODA 기사앱",
    on_load=DriverState.on_driver_load,
)
app.add_page(
    vendor_admin_page,
    route="/vendor",
    title="ZERODA 업체관리자",
    on_load=VendorState.on_vendor_load,
)
app.add_page(
    hq_admin_page,
    route="/admin",
    title="ZERODA 본사관리자",
    on_load=AdminState.on_admin_load,
)
app.add_page(
    school_page,
    route="/school",
    title="ZERODA 학교",
    on_load=SchoolState.on_school_load,
)
app.add_page(
    edu_office_page,
    route="/edu",
    title="ZERODA 교육청",
    on_load=EduState.on_edu_load,
)
app.add_page(
    meal_manager_page,
    route="/meal",
    title="ZERODA 급식담당",
    on_load=MealState.on_meal_load,
)
app.add_page(privacy_page, route="/privacy", title="ZERODA 개인정보처리방침")
app.add_page(terms_page, route="/terms", title="ZERODA 이용약관")


# ── driver 자동로그인 FastAPI 엔드포인트 ──────────────────────────────────
_COOKIE_NAME = "zeroda_driver_token"
_COOKIE_MAX_AGE = 90 * 24 * 3600   # 90일
_COOKIE_OPTS = dict(
    httponly=True,
    secure=True,
    samesite="lax",
    path="/",
)


async def _driver_set_token(request: Request) -> JSONResponse:
    """POST /api/driver/set-token
    Body: {"user_id": "...", "token": "..."}
    응답: Set-Cookie (HttpOnly; Secure; SameSite=Lax; Max-Age=90d)
    """
    try:
        body = await request.json()
        token = body.get("token", "")
        user_id = body.get("user_id", "")
        if not token or not user_id:
            return JSONResponse({"ok": False, "error": "missing fields"}, status_code=400)
        resp = JSONResponse({"ok": True})
        resp.set_cookie(
            key=_COOKIE_NAME,
            value=token,
            max_age=_COOKIE_MAX_AGE,
            **_COOKIE_OPTS,
        )
        return resp
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


async def _driver_check_token(request: Request) -> JSONResponse:
    """GET /api/driver/check-token
    쿠키 zeroda_driver_token 자동 포함 → verify_driver_token 호출.
    유효: {"ok": true, "user_id": "..."}
    무효: {"ok": false} + 쿠키 삭제
    """
    from zeroda_reflex.utils.database import verify_driver_token
    token = request.cookies.get(_COOKIE_NAME, "")
    user_id = verify_driver_token(token) if token else None
    if user_id:
        return JSONResponse({"ok": True, "user_id": user_id})
    # 무효 — 쿠키 삭제
    resp = JSONResponse({"ok": False})
    resp.delete_cookie(key=_COOKIE_NAME, path="/")
    return resp


async def _driver_revoke_token(request: Request) -> JSONResponse:
    """POST /api/driver/revoke-token
    쿠키 zeroda_driver_token → revoke_driver_token(reason='logout') + 쿠키 삭제.
    """
    from zeroda_reflex.utils.database import revoke_driver_token
    token = request.cookies.get(_COOKIE_NAME, "")
    if token:
        revoke_driver_token(token, reason="logout")
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(key=_COOKIE_NAME, path="/")
    return resp


# Reflex 내부 Starlette/FastAPI 인스턴스에 라우트 등록
# Reflex 0.8.x: app._api 는 Starlette → add_route 사용
# Reflex 0.9+:  app.api  는 FastAPI   → add_api_route 사용 가능
_inner_app = getattr(app, "api", None) or getattr(app, "_api", None)
if _inner_app is not None:
    if hasattr(_inner_app, "add_api_route"):
        # FastAPI (0.9+)
        _inner_app.add_api_route("/api/driver/set-token",    _driver_set_token,    methods=["POST"])
        _inner_app.add_api_route("/api/driver/check-token",  _driver_check_token,  methods=["GET"])
        _inner_app.add_api_route("/api/driver/revoke-token", _driver_revoke_token, methods=["POST"])
    else:
        # Starlette (0.8.x)
        _inner_app.add_route("/api/driver/set-token",    _driver_set_token,    methods=["POST"])
        _inner_app.add_route("/api/driver/check-token",  _driver_check_token,  methods=["GET"])
        _inner_app.add_route("/api/driver/revoke-token", _driver_revoke_token, methods=["POST"])
