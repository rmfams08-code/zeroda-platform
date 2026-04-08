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
    monthly_selected_month: str = str(datetime.now().month)

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
    ai_esg_text: str = ""
    ai_esg_loading: bool = False
    ai_esg_error: str = ""

    # ══════════════════════════════
    #  안전관리보고서 (탭5)
    # ══════════════════════════════
    safety_data: dict = {}
    safety_scores: list[dict] = []
    safety_violations: list[dict] = []
    safety_education: list[dict] = []
    safety_vendors: list[str] = []
    # 차량점검·사고 KPI
    safety_checklist_count: str = "0"
    safety_accident_count: str = "0"
    # 일일안전점검
    daily_checks: list[dict] = []
    daily_check_count: str = "0"
    daily_check_days: str = "0"
    daily_check_ok_rate: str = "0"
    daily_check_fail_count: str = "0"
    # 안전보건 점검 체크리스트 (7항목)
    checklist_results: list[str] = ["예", "예", "예", "예", "예", "예", "예"]

    # ══════════════════════════════
    #  Computed vars
    # ══════════════════════════════

    @rx.var
    def has_monthly(self) -> bool:
        return any(float(r.get("weight", 0)) > 0 for r in self.monthly_rows)

    @rx.var
    def monthly_current_weight(self) -> str:
        """선택된 월의 수거량"""
        for r in self.monthly_rows:
            if str(r.get("month", "")) == self.monthly_selected_month:
                return r.get("weight", "0")
        return "0"

    @rx.var
    def monthly_avg_weight(self) -> str:
        """데이터 있는 월의 평균 수거량"""
        months_with_data = [r for r in self.monthly_rows if float(r.get("weight", 0)) > 0]
        if not months_with_data:
            return "0"
        total = sum(float(r.get("weight", 0)) for r in months_with_data)
        return str(round(total / len(months_with_data), 1))

    @rx.var
    def has_detail(self) -> bool:
        return len(self.detail_rows) > 0

    @rx.var
    def detail_total_weight(self) -> str:
        """수거내역 탭 총 합계 중량"""
        total = sum(float(r.get("weight", 0)) for r in self.detail_rows)
        return str(round(total, 1))

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
    def esg_pine_trees(self) -> str:
        """소나무 환산 (30년생 소나무 1그루 연간 CO2 흡수 4.6kg 기준)"""
        carbon = float(self.esg_data.get("carbon_reduced", 0) or 0)
        if carbon <= 0:
            return "0"
        return str(round(carbon / 4.6, 1))

    @rx.var
    def esg_tree_general(self) -> str:
        """나무(일반) 환산 (일반 나무 1그루 연간 CO2 흡수 6.6kg 기준)"""
        carbon = float(self.esg_data.get("carbon_reduced", 0) or 0)
        if carbon <= 0:
            return "0"
        return str(round(carbon / 6.6, 1))

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
    def has_daily_checks(self) -> bool:
        return len(self.daily_checks) > 0

    @rx.var
    def safety_grade_good(self) -> str:
        """안전등급 양호(S/A) 업체 수"""
        return str(sum(1 for r in self.safety_scores if r.get("grade", "") in ("S", "A")))

    @rx.var
    def safety_grade_caution(self) -> str:
        """안전등급 주의(B) 업체 수"""
        return str(sum(1 for r in self.safety_scores if r.get("grade", "") == "B"))

    @rx.var
    def safety_grade_danger(self) -> str:
        """안전등급 위험(C/D) 업체 수"""
        return str(sum(1 for r in self.safety_scores if r.get("grade", "") in ("C", "D")))

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

    def set_monthly_month(self, m: str):
        """월별현황 탭 전용 월 선택 (데이터 재로드 불필요 — computed var로 처리)"""
        self.monthly_selected_month = m

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

    def set_checklist_item(self, index_value: list):
        idx = int(index_value[0])
        val = index_value[1]
        results = list(self.checklist_results)
        results[idx] = val
        self.checklist_results = results

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
        # 차량점검·사고 KPI
        self.safety_checklist_count = str(len(data.get("checklist", [])))
        self.safety_accident_count = str(len(data.get("accident", [])))
        # 일일안전점검
        dc = data.get("daily_checks", [])
        self.daily_checks = dc
        self.daily_check_count = str(len(dc))
        dates = set()
        for r in dc:
            d = r.get("check_date", "")
            if d:
                dates.add(d)
        self.daily_check_days = str(len(dates))
        total_ok = sum(int(r.get("total_ok", 0)) for r in dc)
        total_fail = sum(int(r.get("total_fail", 0)) for r in dc)
        all_items = total_ok + total_fail
        self.daily_check_ok_rate = f"{(total_ok / all_items * 100):.1f}" if all_items > 0 else "0"
        self.daily_check_fail_count = str(total_fail)

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

    async def run_ai_esg(self):
        """학교 모드 AI ESG 보고서 생성."""
        from zeroda_reflex.utils.ai_service import build_esg_ai_prompt, call_claude_api
        if not self.has_esg:
            self.ai_esg_error = "ESG 데이터가 없습니다. 먼저 KPI 카드를 로드하세요."
            return
        self.ai_esg_loading = True
        self.ai_esg_error = ""
        self.ai_esg_text = ""
        yield
        try:
            y = int(self.selected_year)
            m = int(self.selected_month) if self.selected_month != "전체" else 0
        except (ValueError, TypeError):
            y, m = 0, 0
        month_label = f"{y}년 {m}월" if m > 0 else f"{y}년 전체"
        rows = school_filter_collections(self.current_school, y, m) if y else []
        vendor = ""
        try:
            vendors_list = school_get_vendors(self.current_school)
            vendor = vendors_list[0] if vendors_list else ""
        except Exception:
            pass
        prompt = build_esg_ai_prompt(
            org_name=self.current_school, org_type="학교",
            year=y, month_label=month_label,
            esg_data=dict(self.esg_data), rows=rows, vendor=vendor,
        )
        result = call_claude_api(prompt, "")
        self.ai_esg_loading = False
        if result.startswith("[ERROR]"):
            self.ai_esg_error = result.replace("[ERROR] ", "")
        else:
            self.ai_esg_text = result

    def download_ai_esg_pdf(self):
        """학교 모드 AI ESG PDF 다운로드."""
        from zeroda_reflex.utils.pdf_export import build_ai_esg_pdf
        if not self.ai_esg_text:
            return None
        try:
            y = int(self.selected_year)
            m = int(self.selected_month) if self.selected_month != "전체" else 0
        except (ValueError, TypeError):
            return None
        month_label = f"{y}년 {m}월" if m > 0 else f"{y}년 전체"
        vendor = ""
        try:
            vendors_list = school_get_vendors(self.current_school)
            vendor = vendors_list[0] if vendors_list else ""
        except Exception:
            pass
        pdf_bytes = build_ai_esg_pdf(
            org_name=self.current_school, org_type="학교",
            year=y, month_label=month_label,
            ai_markdown=self.ai_esg_text,
            esg_summary=dict(self.esg_data),
            vendor=vendor,
        )
        if pdf_bytes:
            month_part = str(m).zfill(2) if m else "전체"
            return rx.download(
                data=pdf_bytes,
                filename=f"AI_ESG보고서_{self.current_school}_{y}-{month_part}.pdf",
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
            checklist_results=list(self.checklist_results),
            daily_checks=data.get("daily_checks", []),
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
