# zeroda_reflex/state/edu_state.py
# 교육청 사용자 상태 관리
import reflex as rx
import logging
from datetime import datetime
from zeroda_reflex.state.auth_state import AuthState
from zeroda_reflex.utils.filters import safe_int

logger = logging.getLogger(__name__)
from zeroda_reflex.utils.database import (
    edu_get_managed_schools,
    edu_get_vendors_for_schools,
    edu_get_overview,
    edu_get_by_school,
    edu_get_by_vendor,
    edu_get_carbon,
    edu_get_safety,
    school_get_esg,
)


# ── 탭 목록 ──
EDU_TABS = ["전체현황", "학교별조회", "업체별현황", "탄소감축", "ESG보고서", "안전관리"]


class EduState(AuthState):
    """교육청 사용자 전체 상태"""

    # ══════════════════════════════
    #  공통
    # ══════════════════════════════
    active_tab: str = "전체현황"
    selected_year: str = str(datetime.now().year)
    selected_month: str = str(datetime.now().month)

    managed_schools: list[str] = []
    managed_vendors: list[str] = []

    # ══════════════════════════════
    #  탭1: 전체현황
    # ══════════════════════════════
    overview_data: dict = {}
    overview_school_list: list[dict] = []

    # ══════════════════════════════
    #  탭2: 학교별조회
    # ══════════════════════════════
    sel_school: str = ""
    school_rows: list[dict] = []

    # ══════════════════════════════
    #  탭3: 업체별현황
    # ══════════════════════════════
    sel_vendor: str = ""
    vendor_data: dict = {}
    vendor_school_list: list[dict] = []

    # ══════════════════════════════
    #  탭4: 탄소감축
    # ══════════════════════════════
    carbon_data: dict = {}
    carbon_ranking: list[dict] = []

    # ══════════════════════════════
    #  탭5: ESG보고서
    # ══════════════════════════════
    esg_school: str = ""
    esg_data: dict = {}
    ai_esg_text: str = ""
    ai_esg_loading: bool = False
    ai_esg_error: str = ""

    # ══════════════════════════════
    #  탭6: 안전관리
    # ══════════════════════════════
    safety_data: dict = {}
    safety_scores: list[dict] = []
    safety_violations: list[dict] = []
    safety_education: list[dict] = []
    safety_accidents: list[dict] = []

    # ══════════════════════════════
    #  Computed vars
    # ══════════════════════════════

    @rx.var
    def has_overview(self) -> bool:
        return bool(self.overview_data) and safe_int(self.overview_data.get("total_count", 0)) > 0

    @rx.var
    def has_overview_schools(self) -> bool:
        return len(self.overview_school_list) > 0

    @rx.var
    def has_school_rows(self) -> bool:
        return len(self.school_rows) > 0

    @rx.var
    def has_vendor_data(self) -> bool:
        return bool(self.vendor_data) and safe_int(self.vendor_data.get("total_weight", 0)) > 0

    @rx.var
    def has_vendor_schools(self) -> bool:
        return len(self.vendor_school_list) > 0

    @rx.var
    def has_carbon(self) -> bool:
        return bool(self.carbon_data) and safe_int(self.carbon_data.get("total_kg", 0)) > 0

    @rx.var
    def has_carbon_ranking(self) -> bool:
        return len(self.carbon_ranking) > 0

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
    def has_safety_accidents(self) -> bool:
        return len(self.safety_accidents) > 0

    @rx.var
    def school_name_options(self) -> list[str]:
        return self.managed_schools

    @rx.var
    def vendor_name_options(self) -> list[str]:
        return self.managed_vendors

    # ══════════════════════════════
    #  초기화
    # ══════════════════════════════

    def on_edu_load(self):
        """교육청 페이지 로드 시"""
        if not self.is_authenticated:
            return rx.redirect("/")
        if self.user_role != "edu_office":
            return rx.redirect("/")
        # 관할 학교 + 업체
        self.managed_schools = edu_get_managed_schools(self.user_schools)
        self.managed_vendors = edu_get_vendors_for_schools(self.managed_schools)
        if self.managed_schools and not self.sel_school:
            self.sel_school = self.managed_schools[0]
        if self.managed_vendors and not self.sel_vendor:
            self.sel_vendor = self.managed_vendors[0]
        if self.managed_schools and not self.esg_school:
            self.esg_school = self.managed_schools[0]
        self.load_tab_data()

    # ══════════════════════════════
    #  탭 전환 / 필터
    # ══════════════════════════════

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.load_tab_data()

    def set_selected_year(self, y: str):
        self.selected_year = y
        self.load_tab_data()

    def set_selected_month(self, m: str):
        self.selected_month = m
        self.load_tab_data()

    def set_sel_school(self, s: str):
        self.sel_school = s
        if self.active_tab == "학교별조회":
            self.load_by_school()

    def set_sel_vendor(self, v: str):
        self.sel_vendor = v
        if self.active_tab == "업체별현황":
            self.load_by_vendor()

    def set_esg_school(self, s: str):
        self.esg_school = s
        self.load_esg()

    def load_tab_data(self):
        if not self.managed_schools:
            return
        tab = self.active_tab
        if tab == "전체현황":
            self.load_overview()
        elif tab == "학교별조회":
            self.load_by_school()
        elif tab == "업체별현황":
            self.load_by_vendor()
        elif tab == "탄소감축":
            self.load_carbon()
        elif tab == "ESG보고서":
            self.load_esg()
        elif tab == "안전관리":
            self.load_safety()

    # ══════════════════════════════
    #  탭1: 전체현황
    # ══════════════════════════════

    def load_overview(self):
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        result = edu_get_overview(self.managed_schools, y, m)
        self.overview_school_list = result.pop("school_list", [])
        self.overview_data = result

    # ══════════════════════════════
    #  탭2: 학교별조회
    # ══════════════════════════════

    def load_by_school(self):
        if not self.sel_school:
            return
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        self.school_rows = edu_get_by_school(self.managed_schools, self.sel_school, y, m)

    # ══════════════════════════════
    #  탭3: 업체별현황
    # ══════════════════════════════

    def load_by_vendor(self):
        if not self.sel_vendor:
            return
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return
        result = edu_get_by_vendor(self.managed_schools, self.sel_vendor, y)
        self.vendor_school_list = result.pop("school_list", [])
        self.vendor_data = result

    # ══════════════════════════════
    #  탭4: 탄소감축
    # ══════════════════════════════

    def load_carbon(self):
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
        result = edu_get_carbon(self.managed_schools, y, m)
        self.carbon_ranking = result.pop("school_ranking", [])
        self.carbon_data = result

    # ══════════════════════════════
    #  탭5: ESG보고서
    # ══════════════════════════════

    def load_esg(self):
        if not self.esg_school:
            return
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return
        self.esg_data = school_get_esg(self.esg_school, y)

    # ══════════════════════════════
    #  탭6: 안전관리
    # ══════════════════════════════

    def load_safety(self):
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        ym = f"{y}-{str(m).zfill(2)}"
        data = edu_get_safety(self.managed_schools, ym)
        self.safety_scores = data.get("scores", [])
        self.safety_violations = data.get("violations", [])
        self.safety_education = data.get("education", [])
        self.safety_accidents = data.get("accidents", [])

    # ══════════════════════════════
    #  PDF 다운로드 핸들러
    # ══════════════════════════════

    def download_esg_pdf(self):
        """교육청 ESG 보고서 PDF 다운로드 (관할 학교 통합 또는 선택 학교 단건)."""
        from zeroda_reflex.utils.pdf_export import (
            build_edu_office_esg_pdf, build_school_esg_pdf,
        )
        from zeroda_reflex.utils.database import school_filter_collections
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return None
        month_label = f"{y}년 전체"

        # 1) 특정 학교가 선택된 경우 → 단일 학교 보고서
        if self.esg_school:
            rows = school_filter_collections(self.esg_school, y, 0)
            if not rows:
                return None
            pdf_bytes = build_school_esg_pdf(
                self.esg_school, y, month_label, rows, "",
            )
            if pdf_bytes:
                return rx.download(
                    data=pdf_bytes,
                    filename=f"ESG보고서_{self.esg_school}_{y}.pdf",
                )
            return None

        # 2) 학교 미선택 → 관할 학교 통합 보고서
        schools = list(self.managed_schools or [])
        if not schools:
            return None
        school_data = []
        for sch in schools:
            rows = school_filter_collections(sch, y, 0)
            if rows:
                school_data.append({"school": sch, "rows": rows})
        if not school_data:
            return None
        edu_name = self.user_edu_office or "교육청"
        pdf_bytes = build_edu_office_esg_pdf(
            edu_name, y, month_label, school_data, "",
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"ESG보고서_교육청_{edu_name}_{y}.pdf",
            )
        return None

    async def run_ai_esg(self):
        """교육청 AI ESG 보고서 생성 (선택 학교 단건 또는 관할 통합)."""
        from zeroda_reflex.utils.ai_service import build_esg_ai_prompt, call_claude_api
        from zeroda_reflex.utils.database import school_filter_collections
        if not self.has_esg:
            self.ai_esg_error = "ESG 데이터가 없습니다."
            return
        self.ai_esg_loading = True
        self.ai_esg_error = ""
        self.ai_esg_text = ""
        yield
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            self.ai_esg_loading = False
            return
        month_label = f"{y}년 전체"
        target = self.esg_school or self.user_edu_office or "교육청"
        rows = []
        if self.esg_school:
            rows = school_filter_collections(self.esg_school, y, 0)
        prompt = build_esg_ai_prompt(
            org_name=target,
            org_type="학교" if self.esg_school else "교육청",
            year=y, month_label=month_label,
            esg_data=dict(self.esg_data), rows=rows, vendor="",
        )
        result = call_claude_api(prompt, "")
        self.ai_esg_loading = False
        if result.startswith("[ERROR]"):
            self.ai_esg_error = result.replace("[ERROR] ", "")
        else:
            self.ai_esg_text = result

    def download_ai_esg_pdf(self):
        """교육청 AI ESG PDF 다운로드."""
        from zeroda_reflex.utils.pdf_export import build_ai_esg_pdf
        if not self.ai_esg_text:
            return None
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return None
        target = self.esg_school or self.user_edu_office or "교육청"
        pdf_bytes = build_ai_esg_pdf(
            org_name=target,
            org_type="학교" if self.esg_school else "교육청",
            year=y, month_label=f"{y}년 전체",
            ai_markdown=self.ai_esg_text,
            esg_summary=dict(self.esg_data),
            vendor="",
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"AI_ESG보고서_{target}_{y}.pdf",
            )
        return None

    def download_safety_pdf(self):
        """교육청 안전관리 보고서 PDF 다운로드"""
        from zeroda_reflex.utils.pdf_export import build_safety_report_pdf
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return None
        ym = f"{y}-{str(m).zfill(2)}"
        pdf_bytes = build_safety_report_pdf(
            org_name=self.edu_office_name,
            org_type="교육청",
            year=y,
            month=m,
            vendor_scores=self.safety_scores,
            violations=self.safety_violations,
            education_records=self.safety_education,
            checklist_records=[],
            accident_records=self.safety_accidents,
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"안전관리보고서_{self.edu_office_name}_{ym}.pdf",
            )
        return None
