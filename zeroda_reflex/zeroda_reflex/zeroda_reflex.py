# zeroda_reflex/zeroda_reflex.py
# 메인 앱 엔트리 — 페이지 등록 및 라우팅
import reflex as rx

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
from zeroda_reflex.pages.documents import documents_page
from zeroda_reflex.state.document_state import DocumentState
from zeroda_reflex.pages.vendor_documents import vendor_documents_page
from zeroda_reflex.state.vendor_document_state import VendorDocumentState
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
app.add_page(login_page, route="/", title="ZERODA 로그인")
from zeroda_reflex.state.auth_state import AuthState
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
app.add_page(documents_page, route="/documents", title="ZERODA 문서함", on_load=DocumentState.on_doc_load)
app.add_page(vendor_documents_page, route="/vendor_documents", title="외주업체 문서함", on_load=VendorDocumentState.on_vendor_doc_load)
