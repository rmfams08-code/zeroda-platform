# zeroda_reflex/state/school_state.py
# 학교 사용자 상태 관리
import reflex as rx
import logging
from datetime import datetime
from zeroda_reflex.state.auth_state import AuthState
from zeroda_reflex.utils.filters import safe_int

logger = logging.getLogger(__name__)
from zeroda_reflex.utils.database import (
    school_filter_collections,
    school_get_monthly_summary,
    school_get_settlement,
    school_get_esg,
    school_get_safety_report,
    school_get_vendors,
)


# ── 탭 목록 ──
SCHOOL_TABS = ["월별현황", "수거내역", "정산확인", "ESG보고서", "안전관리보고서"]


class SchoolState(AuthState):
    """학교 사용자 전체 상태"""

    # ══════════════════════════════
    #  공통
    # ══════════════════════════════
    active_tab: str = "월별현황"
    selected_year: str = str(datetime.now().year)
    selected_month: str = str(datetime.now().month)

    # 학교 선택 (여러 학교를 담당할 수 있음)
    school_list: list[str] = []
    current_school: str = ""

    # ══════════════════════════════
    #  월별현황 (탭1)
    # ══════════════════════════════
    monthly_rows: list[dict] = []
    monthly_total_weight: str = "0"
    monthly_total_count: str = "0"

    # ══════════════════════════════
    #  수거내역 (탭2)
    # ══════════════════════════════
    detail_rows: list[dict] = []

    # ══════════════════════════════
    #  정산확인 (탭3)
    # ══════════════════════════════
    settle_data: dict = {}
    settle_items: list[dict] = []

    # ══════════════════════════════
    #  ESG보고서 (탭4)
    # ══════════════════════════════
    esg_data: dict = {}

    # ══════════════════════════════
    #  안전관리보고서 (탭5)
    # ══════════════════════════════
    safety_data: dict = {}
    safety_scores: list[dict] = []
    safety_violations: list[dict] = []
    safety_education: list[dict] = []
    safety_vendors: list[str] = []

    # ══════════════════════════════
    #  Computed vars
    # ══════════════════════════════

    @rx.var
    def has_monthly(self) -> bool:
        return any(float(r.get("weight", 0)) > 0 for r in self.monthly_rows)

    @rx.var
    def has_detail(self) -> bool:
        return len(self.detail_rows) > 0

    @rx.var
    def has_settle(self) -> bool:
        return bool(self.settle_data) and safe_int(self.settle_data.get("row_count", 0)) > 0

    @rx.var
    def has_settle_items(self) -> bool:
        return len(self.settle_items) > 0

    @rx.var
    def has_esg(self) -> bool:
        return bool(self.esg_data) and safe_int(self.esg_data.get("count", 0)) > 0

    @rx.var
    def has_safety_scores(self) -> bool:
        return len(self.safety_scores) > 0

    @rx.var
    def has_safety_violations(self) -> bool:
        return len(self.safety_violations) > 0

    @rx.var
    def has_safety_education(self) -> bool:
        return len(self.safety_education) > 0

    @rx.var
    def has_schools(self) -> bool:
        return len(self.school_list) > 1

    # ══════════════════════════════
    #  초기화
    # ══════════════════════════════

    def on_school_load(self):
        """학교 페이지 로드 시"""
        if not self.is_authenticated:
            return rx.redirect("/")
        if self.user_role != "school":
            return rx.redirect("/")
        # 학교 목록 파싱
        schools = [s.strip() for s in self.user_schools.split(",") if s.strip()]
        self.school_list = schools
        if schools and not self.current_school:
            self.current_school = schools[0]
        self.load_tab_data()

    # ══════════════════════════════
    #  탭 전환
    # ══════════════════════════════

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.load_tab_data()

    def set_current_school(self, s: str):
        self.current_school = s
        self.load_tab_data()

    def set_selected_year(self, y: str):
        self.selected_year = y
        self.load_tab_data()

    def set_selected_month(self, m: str):
        self.selected_month = m
        self.load_tab_data()

    def load_tab_data(self):
        """현재 탭에 맞는 데이터 로드"""
        if not self.current_school:
            return
        tab = self.active_tab
        if tab == "월별현황":
            self.load_monthly()
        elif tab == "수거내역":
            self.load_detail()
        elif tab == "정산확인":
            self.load_settlement()
        elif tab == "ESG보고서":
            self.load_esg()
        elif tab == "안전관리보고서":
            self.load_safety()

    # ══════════════════════════════
    #  탭1: 월별현황
    # ══════════════════════════════

    def load_monthly(self):
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return
        self.monthly_rows = school_get_monthly_summary(self.current_school, y)
        total_w = 0.0
        total_c = 0
        for r in self.monthly_rows:
            total_w += float(r.get("weight", 0))
            total_c += int(r.get("count", 0))
        self.monthly_total_weight = str(round(total_w, 1))
        self.monthly_total_count = str(total_c)

    # ══════════════════════════════
    #  탭2: 수거내역
    # ══════════════════════════════

    def load_detail(self):
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        self.detail_rows = school_filter_collections(self.current_school, y, m)

    # ══════════════════════════════
    #  탭3: 정산확인
    # ══════════════════════════════

    def load_settlement(self):
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        result = school_get_settlement(self.current_school, y, m)
        self.settle_items = result.pop("items", [])
        self.settle_data = result

    # ══════════════════════════════
    #  탭4: ESG보고서
    # ══════════════════════════════

    def load_esg(self):
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return
        m = 0
        if self.selected_month != "전체":
            try:
                m = int(self.selected_month)
            except (ValueError, TypeError):
                pass
        self.esg_data = school_get_esg(self.current_school, y, m)

    # ══════════════════════════════
    #  탭5: 안전관리보고서
    # ══════════════════════════════

    def load_safety(self):
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        ym = f"{y}-{str(m).zfill(2)}"
        data = school_get_safety_report(self.current_school, ym)
        self.safety_vendors = data.get("vendors", [])
        self.safety_scores = data.get("scores", [])
        self.safety_violations = data.get("violations", [])
        self.safety_education = data.get("education", [])

    # ══════════════════════════════
    #  PDF 다운로드 핸들러
    # ══════════════════════════════

    def download_esg_pdf(self):
        """ESG 보고서 PDF 다운로드"""
        from zeroda_reflex.utils.pdf_export import build_school_esg_pdf
        try:
            y = int(self.selected_year)
            m = int(self.selected_month) if self.selected_month != "전체" else 0
        except (ValueError, TypeError):
            return None
        # 수거 데이터 조회
        rows = school_filter_collections(self.current_school, y, m)
        if not rows:
            return None
        # 월 레이블 생성
        month_label = f"{y}년 {m}월" if m > 0 else f"{y}년 전체"
        vendors = school_get_vendors(self.current_school)
        vendor = vendors[0] if vendors else ""
        pdf_bytes = build_school_esg_pdf(
            self.current_school, y, month_label, rows, vendor,
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"ESG보고서_{self.current_school}_{y}-{str(m).zfill(2) if m else '전체'}.pdf",
            )
        return None

    def download_safety_pdf(self):
        """안전관리 보고서 PDF 다운로드"""
        from zeroda_reflex.utils.pdf_export import build_safety_report_pdf
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return None
        ym = f"{y}-{str(m).zfill(2)}"
        data = school_get_safety_report(self.current_school, ym)
        vendors = school_get_vendors(self.current_school)
        vendor = vendors[0] if vendors else ""
        pdf_bytes = build_safety_report_pdf(
            org_name=self.current_school,
            org_type="학교",
            year=y,
            month=m,
            vendor_scores=data.get("scores", []),
            violations=data.get("violations", []),
            education_records=data.get("education", []),
            checklist_records=data.get("checklist", []),
            accident_records=data.get("accident", []),
            vendor_name=vendor,
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"안전관리보고서_{self.current_school}_{ym}.pdf",
            )
        return None

    # ══════════════════════════════
    #  Excel 다운로드 핸들러
    # ══════════════════════════════

    def download_collection_excel(self):
        """수거내역 Excel 다운로드 (학교)"""
        # detail_rows에서 학교 수거 내역 추출
        from zeroda_reflex.utils.excel_export import export_school_collections
        data = self.detail_rows
        if not data:
            return None
        xlsx = export_school_collections(
            data,
            self.current_school,
            self.selected_year,
            self.selected_month
        )
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"수거내역_{self.current_school}_{self.selected_year}-{self.selected_month.zfill(2)}.xlsx"
            )
        return None
