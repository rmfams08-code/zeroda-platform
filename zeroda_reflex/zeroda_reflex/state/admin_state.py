# zeroda_reflex/state/admin_state.py
# 본사관리자(HQ Admin) 상태 관리
import reflex as rx
import logging
from datetime import datetime
from zeroda_reflex.state.auth_state import AuthState

logger = logging.getLogger(__name__)
from zeroda_reflex.utils.database import (
    db_get, db_insert, db_upsert,
    get_all_collections, get_all_vendors_list,
    get_all_users, update_user_approval, update_user_active,
    reset_user_password,
    # 섹션B: 수거데이터
    get_pending_collections, confirm_all_pending, reject_collection_by_id,
    get_filtered_collections, get_all_schools_list,
    get_hq_processing_confirms, confirm_processing_item, reject_processing_item,
    get_processing_vendors, get_processing_drivers,
    # 섹션C: 외주업체관리
    get_all_vendor_info, save_hq_vendor_info,
    get_school_master_all, update_school_alias,
    hq_add_violation, hq_get_violations,
    hq_get_safety_scores, hq_calculate_safety_score,
    # 섹션D: 수거일정 + NEIS
    get_hq_schedules, hq_save_schedule, hq_delete_schedule,
    get_neis_schools_by_vendor, save_neis_meal_schedule,
    # 섹션E: 정산+탄소
    get_settlement_data, get_hq_settlement_summary,
    get_carbon_data,
    # 섹션F: 안전관리+폐기물분석
    get_hq_safety_education, get_hq_accident_reports,
    get_waste_analytics,
)

# ── 본사관리자 메뉴 목록 ──
HQ_TABS = [
    "대시보드", "수거데이터", "외주업체관리", "수거일정",
    "정산관리", "안전관리", "탄소감축", "폐기물분석", "계정관리",
]


class AdminState(AuthState):
    """본사관리자 전체 상태"""

    # ══════════════════════════════
    #  공통
    # ══════════════════════════════
    active_tab: str = "대시보드"
    selected_year: str = str(datetime.now().year)
    selected_month: str = str(datetime.now().month)

    # ══════════════════════════════
    #  대시보드
    # ══════════════════════════════
    dash_vendor_summary: list[dict] = []
    dash_top5_schools: list[dict] = []
    dash_total_weight: float = 0.0
    dash_total_count: int = 0
    dash_vendor_count: int = 0
    dash_school_count: int = 0

    # ══════════════════════════════
    #  계정관리
    # ══════════════════════════════
    all_users: list[dict] = []
    acct_filter_role: str = "전체"
    acct_filter_status: str = "전체"
    acct_msg: str = ""
    acct_ok: bool = False

    # ══════════════════════════════
    #  수거데이터 (섹션B)
    # ══════════════════════════════
    data_sub_tab: str = "전송대기"

    # 전송 대기
    pending_rows: list[dict] = []
    data_msg: str = ""
    data_ok: bool = False

    # 전체 수거 내역 / 시뮬레이션 필터
    data_vendor_filter: str = "전체"
    data_month_filter: str = "전체"
    data_school_filter: str = "전체"
    data_collection_rows: list[dict] = []
    data_vendor_options: list[str] = []
    data_school_options: list[str] = []

    # 처리확인
    proc_vendor_filter: str = "전체"
    proc_driver_filter: str = "전체"
    proc_status_filter: str = "전체"
    proc_rows: list[dict] = []
    proc_vendor_options: list[str] = []
    proc_driver_options: list[str] = []
    proc_total_count: int = 0
    proc_pending_count: int = 0
    proc_confirmed_count: int = 0
    proc_total_weight: float = 0.0

    # ══════════════════════════════
    #  외주업체관리 (섹션C)
    # ══════════════════════════════
    vendor_sub_tab: str = "업체목록"
    vendor_list: list[dict] = []
    vendor_msg: str = ""
    vendor_ok: bool = False

    # 업체 등록/수정 폼
    vf_vendor: str = ""
    vf_biz_name: str = ""
    vf_rep: str = ""
    vf_biz_no: str = ""
    vf_address: str = ""
    vf_contact: str = ""
    vf_email: str = ""
    vf_vehicle_no: str = ""

    # 학교 별칭
    school_master_list: list[dict] = []
    alias_school_sel: str = ""
    alias_input: str = ""

    # 안전관리 평가
    eval_vendor_sel: str = ""
    eval_year: str = str(datetime.now().year)
    eval_month: str = str(datetime.now().month)
    eval_result: dict = {}
    safety_scores_list: list[dict] = []
    violations_list: list[dict] = []
    viol_vendor_filter: str = "전체"

    # 위반 기록 입력
    viol_vendor: str = ""
    viol_driver: str = ""
    viol_date: str = ""
    viol_type: str = "과속"
    viol_location: str = ""
    viol_fine: str = "0"
    viol_memo: str = ""

    # ══════════════════════════════
    #  수거일정 (섹션D)
    # ══════════════════════════════
    sched_sub_tab: str = "일정조회"
    sched_vendor_filter: str = "전체"
    sched_month_filter: str = ""
    sched_rows: list[dict] = []
    sched_msg: str = ""
    sched_ok: bool = False

    # 일정 등록 폼
    sf_vendor: str = ""
    sf_month_key: str = ""
    sf_weekdays: str = ""
    sf_schools: str = ""
    sf_items: str = "음식물"
    sf_driver: str = ""

    # NEIS
    neis_vendor: str = ""
    neis_month: str = ""
    neis_school_list: list[dict] = []
    neis_school_sel: str = ""
    neis_result_msg: str = ""
    neis_meal_dates: list[str] = []
    neis_collect_offset: str = "0"
    neis_item_type: str = "음식물"
    neis_driver: str = ""

    # ══════════════════════════════
    #  정산관리 + 탄소감축 (섹션E)
    # ══════════════════════════════
    settle_year: str = str(datetime.now().year)
    settle_month: str = str(datetime.now().month)
    settle_vendor: str = "전체"
    settle_summary: dict = {}
    settle_rows: list[dict] = []

    # ── [이메일 발송] (Phase 6) ──
    email_to: str = ""
    email_msg: str = ""
    email_ok: bool = False
    email_sending: bool = False

    # ── SMS 발송 (Phase 8) ──
    sms_to: str = ""
    sms_msg: str = ""
    sms_ok: bool = False
    sms_sending: bool = False

    carbon_year: str = str(datetime.now().year)
    carbon_month: str = "전체"
    carbon_data: dict = {}
    carbon_school_ranking: list[dict] = []

    # ══════════════════════════════
    #  안전관리 + 폐기물분석 (섹션F)
    # ══════════════════════════════
    safety_vendor_filter: str = "전체"
    safety_edu_rows: list[dict] = []
    safety_accident_rows: list[dict] = []

    analytics_year: str = str(datetime.now().year)
    analytics_month: str = "전체"
    analytics_data: dict = {}
    analytics_by_item: list[dict] = []
    analytics_by_school: list[dict] = []
    analytics_by_vendor: list[dict] = []
    analytics_by_month: list[dict] = []

    # ══════════════════════════════
    #  Computed Vars — 대시보드
    # ══════════════════════════════

    @rx.var
    def has_vendor_summary(self) -> bool:
        return len(self.dash_vendor_summary) > 0

    @rx.var
    def has_top5(self) -> bool:
        return len(self.dash_top5_schools) > 0

    @rx.var
    def year_month_str(self) -> str:
        return f"{self.selected_year}-{self.selected_month.zfill(2)}"

    # ══════════════════════════════
    #  Computed Vars — 계정관리
    # ══════════════════════════════

    @rx.var
    def filtered_users(self) -> list[dict]:
        result = self.all_users
        if self.acct_filter_role != "전체":
            result = [u for u in result if u.get("role") == self.acct_filter_role]
        if self.acct_filter_status == "승인대기":
            result = [u for u in result if u.get("approval_status") == "pending"]
        elif self.acct_filter_status == "승인완료":
            result = [u for u in result if u.get("approval_status") == "approved"]
        elif self.acct_filter_status == "반려":
            result = [u for u in result if u.get("approval_status") == "rejected"]
        elif self.acct_filter_status == "비활성":
            result = [u for u in result if str(u.get("is_active", "1")) == "0"]
        return result

    @rx.var
    def has_users(self) -> bool:
        return len(self.filtered_users) > 0

    @rx.var
    def pending_count(self) -> int:
        return sum(1 for u in self.all_users if u.get("approval_status") == "pending")

    @rx.var
    def acct_has_msg(self) -> bool:
        return self.acct_msg != ""

    # ══════════════════════════════
    #  Computed Vars — 수거데이터
    # ══════════════════════════════

    @rx.var
    def has_pending(self) -> bool:
        return len(self.pending_rows) > 0

    @rx.var
    def pending_row_count(self) -> int:
        return len(self.pending_rows)

    @rx.var
    def data_has_msg(self) -> bool:
        return self.data_msg != ""

    @rx.var
    def has_collection_rows(self) -> bool:
        return len(self.data_collection_rows) > 0

    @rx.var
    def has_proc_rows(self) -> bool:
        return len(self.proc_rows) > 0

    # ══════════════════════════════
    #  Computed Vars — 외주업체
    # ══════════════════════════════

    @rx.var
    def has_vendors(self) -> bool:
        return len(self.vendor_list) > 0

    @rx.var
    def vendor_has_msg(self) -> bool:
        return self.vendor_msg != ""

    @rx.var
    def has_school_master(self) -> bool:
        return len(self.school_master_list) > 0

    @rx.var
    def school_name_options(self) -> list[str]:
        return [s["school_name"] for s in self.school_master_list if s.get("school_name")]

    @rx.var
    def has_eval_result(self) -> bool:
        return bool(self.eval_result)

    @rx.var
    def has_safety_scores(self) -> bool:
        return len(self.safety_scores_list) > 0

    @rx.var
    def has_violations(self) -> bool:
        return len(self.violations_list) > 0

    @rx.var
    def vendor_name_options(self) -> list[str]:
        return [v["vendor"] for v in self.vendor_list if v.get("vendor")]

    @rx.var
    def vendor_name_options_all(self) -> list[str]:
        """'전체' 포함 업체 목록 (UI selectbox용)"""
        return ["전체"] + [v["vendor"] for v in self.vendor_list if v.get("vendor")]

    @rx.var
    def data_vendor_options_all(self) -> list[str]:
        return ["전체"] + list(self.data_vendor_options)

    @rx.var
    def data_school_options_all(self) -> list[str]:
        return ["전체"] + list(self.data_school_options)

    @rx.var
    def proc_vendor_options_all(self) -> list[str]:
        return ["전체"] + list(self.proc_vendor_options)

    @rx.var
    def proc_driver_options_all(self) -> list[str]:
        return ["전체"] + list(self.proc_driver_options)

    # ══════════════════════════════
    #  Computed Vars — 수거일정
    # ══════════════════════════════

    @rx.var
    def has_sched_rows(self) -> bool:
        return len(self.sched_rows) > 0

    @rx.var
    def sched_has_msg(self) -> bool:
        return self.sched_msg != ""

    @rx.var
    def has_neis_schools(self) -> bool:
        return len(self.neis_school_list) > 0

    @rx.var
    def neis_school_name_options(self) -> list[str]:
        return [s["name"] for s in self.neis_school_list if s.get("name")]

    @rx.var
    def has_neis_meal_dates(self) -> bool:
        return len(self.neis_meal_dates) > 0

    @rx.var
    def neis_meal_count(self) -> int:
        return len(self.neis_meal_dates)

    # ══════════════════════════════
    #  Computed Vars — 정산/탄소
    # ══════════════════════════════

    @rx.var
    def has_settle_rows(self) -> bool:
        return len(self.settle_rows) > 0

    @rx.var
    def has_settle_summary(self) -> bool:
        return bool(self.settle_summary)

    @rx.var
    def has_carbon_data(self) -> bool:
        return bool(self.carbon_data)

    @rx.var
    def has_carbon_ranking(self) -> bool:
        return len(self.carbon_school_ranking) > 0

    # ══════════════════════════════
    #  Computed Vars — 안전/분석
    # ══════════════════════════════

    @rx.var
    def has_edu_rows(self) -> bool:
        return len(self.safety_edu_rows) > 0

    @rx.var
    def has_accident_rows(self) -> bool:
        return len(self.safety_accident_rows) > 0

    @rx.var
    def has_analytics(self) -> bool:
        return bool(self.analytics_data)

    @rx.var
    def has_by_item(self) -> bool:
        return len(self.analytics_by_item) > 0

    @rx.var
    def has_by_school(self) -> bool:
        return len(self.analytics_by_school) > 0

    # ══════════════════════════════
    #  이벤트 — 공통
    # ══════════════════════════════

    def on_admin_load(self):
        """페이지 로드 시"""
        if not self.is_authenticated or self.user_role != "admin":
            return rx.redirect("/")
        self.load_dashboard()

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        if tab == "대시보드":
            self.load_dashboard()
        elif tab == "수거데이터":
            self.load_data_tab()
        elif tab == "외주업체관리":
            self.load_vendor_tab()
        elif tab == "수거일정":
            self.load_schedule_tab()
        elif tab == "정산관리":
            self.load_settlement()
        elif tab == "탄소감축":
            self.load_carbon()
        elif tab == "안전관리":
            self.load_safety()
        elif tab == "폐기물분석":
            self.load_analytics()
        elif tab == "계정관리":
            self.load_users()

    def set_selected_year(self, y: str):
        self.selected_year = y
        self.load_dashboard()

    def set_selected_month(self, m: str):
        self.selected_month = m
        self.load_dashboard()

    # ══════════════════════════════
    #  이벤트 — 대시보드
    # ══════════════════════════════

    def load_dashboard(self):
        """대시보드 데이터 로드"""
        ym = self.year_month_str
        rows = get_all_collections(year_month=ym)
        self.dash_total_count = len(rows)
        total_w = 0.0
        vendor_map: dict[str, float] = {}
        school_map: dict[str, float] = {}
        for r in rows:
            try:
                w = float(r.get("weight", 0))
            except (ValueError, TypeError):
                w = 0.0
            total_w += w
            v = r.get("vendor", "")
            s = r.get("school_name", "")
            if v:
                vendor_map[v] = vendor_map.get(v, 0.0) + w
            if s:
                school_map[s] = school_map.get(s, 0.0) + w

        self.dash_total_weight = round(total_w, 1)
        self.dash_vendor_count = len(vendor_map)
        self.dash_school_count = len(school_map)

        # 업체별 요약
        self.dash_vendor_summary = [
            {"vendor": k, "total_weight": round(v, 1)}
            for k, v in sorted(vendor_map.items(), key=lambda x: -x[1])
        ]

        # 학교별 TOP5
        sorted_schools = sorted(school_map.items(), key=lambda x: -x[1])[:5]
        self.dash_top5_schools = [
            {"school_name": k, "total_weight": round(v, 1)}
            for k, v in sorted_schools
        ]

    def refresh_dashboard(self):
        self.load_dashboard()

    # ══════════════════════════════
    #  이벤트 — 계정관리
    # ══════════════════════════════

    def load_users(self):
        self.all_users = get_all_users()
        self.acct_msg = ""

    def set_acct_filter_role(self, v: str):
        self.acct_filter_role = v

    def set_acct_filter_status(self, v: str):
        self.acct_filter_status = v

    def approve_user(self, user_id: str):
        """사용자 승인"""
        ok = update_user_approval(user_id, "approved")
        if ok:
            self.acct_msg = f"{user_id} 승인 완료"
            self.acct_ok = True
        else:
            self.acct_msg = "승인 처리 실패"
            self.acct_ok = False
        self.load_users()

    def reject_user(self, user_id: str):
        """사용자 반려"""
        ok = update_user_approval(user_id, "rejected")
        if ok:
            self.acct_msg = f"{user_id} 반려 완료"
            self.acct_ok = True
        else:
            self.acct_msg = "반려 처리 실패"
            self.acct_ok = False
        self.load_users()

    def toggle_user_active(self, user_id: str):
        """사용자 활성/비활성 전환"""
        user = next((u for u in self.all_users if u.get("user_id") == user_id), None)
        if not user:
            return
        current = str(user.get("is_active", "1"))
        new_val = 0 if current == "1" else 1
        ok = update_user_active(user_id, new_val)
        if ok:
            self.acct_msg = f"{user_id} {'활성화' if new_val else '비활성화'} 완료"
            self.acct_ok = True
        else:
            self.acct_msg = "처리 실패"
            self.acct_ok = False
        self.load_users()

    def reset_password(self, user_id: str):
        """비밀번호 초기화 — 랜덤 8자리 임시비번 생성 (Phase 1-2 보안 강화)"""
        import secrets
        import string
        # 영문+숫자 조합 8자리 임시 비밀번호 생성
        alphabet = string.ascii_letters + string.digits
        temp_pw = ''.join(secrets.choice(alphabet) for _ in range(8))
        ok = reset_user_password(user_id, temp_pw)
        if ok:
            # 관리자에게 임시 비밀번호를 표시하여 사용자에게 전달할 수 있게 함
            self.acct_msg = f"{user_id} 임시비밀번호: {temp_pw} (사용자에게 전달하세요)"
            self.acct_ok = True
        else:
            self.acct_msg = "초기화 실패"
            self.acct_ok = False

    # ══════════════════════════════
    #  이벤트 — 수거데이터 (섹션B)
    # ══════════════════════════════

    def load_data_tab(self):
        """수거데이터 탭 진입 시 초기 로드"""
        self.data_msg = ""
        self.data_vendor_options = get_all_vendors_list()
        self.data_school_options = get_all_schools_list()
        self.proc_vendor_options = get_processing_vendors()
        self.proc_driver_options = get_processing_drivers()
        if self.data_sub_tab == "전송대기":
            self.load_pending()
        elif self.data_sub_tab in ("전체수거", "시뮬레이션"):
            self.load_collection_data()
        elif self.data_sub_tab == "처리확인":
            self.load_processing()

    def set_data_sub_tab(self, tab: str):
        self.data_sub_tab = tab
        self.data_msg = ""
        if tab == "전송대기":
            self.load_pending()
        elif tab in ("전체수거", "시뮬레이션"):
            self.load_collection_data()
        elif tab == "처리확인":
            self.load_processing()

    # ── 전송 대기 ──

    def load_pending(self):
        self.pending_rows = get_pending_collections()

    def confirm_all_pending_data(self):
        """미확인 전송 데이터 전체 확인"""
        cnt = confirm_all_pending()
        if cnt > 0:
            self.data_msg = f"{cnt}건 확인 완료"
            self.data_ok = True
        else:
            self.data_msg = "처리할 데이터가 없습니다"
            self.data_ok = False
        self.load_pending()

    def reject_single_collection(self, row_id: str):
        """특정 수거 데이터 반려"""
        ok = reject_collection_by_id(int(row_id))
        if ok:
            self.data_msg = f"ID {row_id} 반려 완료"
            self.data_ok = True
        else:
            self.data_msg = "반려 처리 실패"
            self.data_ok = False
        self.load_pending()

    # ── 전체 수거 내역 / 시뮬레이션 ──

    def set_data_vendor_filter(self, v: str):
        self.data_vendor_filter = v
        self.load_collection_data()

    def set_data_month_filter(self, m: str):
        self.data_month_filter = m
        self.load_collection_data()

    def set_data_school_filter(self, s: str):
        self.data_school_filter = s
        self.load_collection_data()

    def load_collection_data(self):
        """필터 적용하여 수거 데이터 로드"""
        tbl = "sim_collection" if self.data_sub_tab == "시뮬레이션" else "real_collection"
        vendor = self.data_vendor_filter if self.data_vendor_filter != "전체" else ""
        ym = self.data_month_filter if self.data_month_filter != "전체" else ""
        school = self.data_school_filter if self.data_school_filter != "전체" else ""
        self.data_collection_rows = get_filtered_collections(
            table=tbl, vendor=vendor, year_month=ym, school=school,
        )

    # ── 처리확인 ──

    def set_proc_vendor_filter(self, v: str):
        self.proc_vendor_filter = v
        self.load_processing()

    def set_proc_driver_filter(self, d: str):
        self.proc_driver_filter = d
        self.load_processing()

    def set_proc_status_filter(self, s: str):
        self.proc_status_filter = s
        self.load_processing()

    def load_processing(self):
        """처리확인 데이터 로드"""
        vendor = self.proc_vendor_filter if self.proc_vendor_filter != "전체" else ""
        driver = self.proc_driver_filter if self.proc_driver_filter != "전체" else ""
        status = self.proc_status_filter if self.proc_status_filter != "전체" else ""
        rows = get_hq_processing_confirms(vendor=vendor, driver=driver, status=status)
        self.proc_rows = rows
        self.proc_total_count = len(rows)
        self.proc_pending_count = sum(1 for r in rows if r.get("status") == "submitted")
        self.proc_confirmed_count = sum(1 for r in rows if r.get("status") == "confirmed")
        try:
            self.proc_total_weight = round(
                sum(float(r.get("total_weight", 0)) for r in rows), 1
            )
        except (ValueError, TypeError):
            self.proc_total_weight = 0.0

    def confirm_proc_item(self, row_id: str):
        """처리확인 건 확인"""
        ok = confirm_processing_item(int(row_id))
        if ok:
            self.data_msg = f"처리확인 ID {row_id} 확인 완료"
            self.data_ok = True
        else:
            self.data_msg = "확인 처리 실패"
            self.data_ok = False
        self.load_processing()

    def reject_proc_item(self, row_id: str):
        """처리확인 건 반려"""
        ok = reject_processing_item(int(row_id))
        if ok:
            self.data_msg = f"처리확인 ID {row_id} 반려 완료"
            self.data_ok = True
        else:
            self.data_msg = "반려 처리 실패"
            self.data_ok = False
        self.load_processing()

    # ══════════════════════════════
    #  이벤트 — 외주업체관리 (섹션C)
    # ══════════════════════════════

    def load_vendor_tab(self):
        """외주업체 탭 진입 시 로드"""
        self.vendor_msg = ""
        self.vendor_list = get_all_vendor_info()
        self.school_master_list = get_school_master_all()

    def set_vendor_sub_tab(self, tab: str):
        self.vendor_sub_tab = tab
        self.vendor_msg = ""
        if tab == "업체목록":
            self.vendor_list = get_all_vendor_info()
        elif tab == "학교별칭":
            self.school_master_list = get_school_master_all()
        elif tab == "안전평가":
            self.load_safety_data()

    # ── 업체 등록/수정 폼 세터 ──

    def set_vf_vendor(self, v: str):
        self.vf_vendor = v

    def set_vf_biz_name(self, v: str):
        self.vf_biz_name = v

    def set_vf_rep(self, v: str):
        self.vf_rep = v

    def set_vf_biz_no(self, v: str):
        self.vf_biz_no = v

    def set_vf_address(self, v: str):
        self.vf_address = v

    def set_vf_contact(self, v: str):
        self.vf_contact = v

    def set_vf_email(self, v: str):
        self.vf_email = v

    def set_vf_vehicle_no(self, v: str):
        self.vf_vehicle_no = v

    def save_vendor(self):
        """업체 정보 저장 (등록/수정)"""
        if not self.vf_vendor or not self.vf_biz_name:
            self.vendor_msg = "업체 ID와 상호명은 필수입니다."
            self.vendor_ok = False
            return
        ok = save_hq_vendor_info({
            "vendor": self.vf_vendor,
            "biz_name": self.vf_biz_name,
            "rep": self.vf_rep,
            "biz_no": self.vf_biz_no,
            "address": self.vf_address,
            "contact": self.vf_contact,
            "email": self.vf_email,
            "vehicle_no": self.vf_vehicle_no,
        })
        if ok:
            self.vendor_msg = f"'{self.vf_biz_name}' 저장 완료"
            self.vendor_ok = True
            self.vendor_list = get_all_vendor_info()
            # 폼 초기화
            self.vf_vendor = ""
            self.vf_biz_name = ""
            self.vf_rep = ""
            self.vf_biz_no = ""
            self.vf_address = ""
            self.vf_contact = ""
            self.vf_email = ""
            self.vf_vehicle_no = ""
        else:
            self.vendor_msg = "저장 실패"
            self.vendor_ok = False

    def load_vendor_for_edit(self, vendor_id: str):
        """업체 정보 편집을 위해 로드"""
        v = next((x for x in self.vendor_list if x.get("vendor") == vendor_id), None)
        if v:
            self.vf_vendor = v.get("vendor", "")
            self.vf_biz_name = v.get("biz_name", "")
            self.vf_rep = v.get("rep", "")
            self.vf_biz_no = v.get("biz_no", "")
            self.vf_address = v.get("address", "")
            self.vf_contact = v.get("contact", "")
            self.vf_email = v.get("email", "")
            self.vf_vehicle_no = v.get("vehicle_no", "")
            self.vendor_sub_tab = "업체등록"

    # ── 학교 별칭 ──

    def set_alias_school_sel(self, s: str):
        self.alias_school_sel = s
        # 현재 별칭 로드
        row = next((x for x in self.school_master_list if x.get("school_name") == s), None)
        self.alias_input = row.get("alias", "") if row else ""

    def set_alias_input(self, v: str):
        self.alias_input = v

    def save_alias(self):
        """학교 별칭 저장"""
        if not self.alias_school_sel:
            self.vendor_msg = "학교를 선택하세요."
            self.vendor_ok = False
            return
        cleaned = ",".join([a.strip() for a in self.alias_input.split(",") if a.strip()])
        ok = update_school_alias(self.alias_school_sel, cleaned)
        if ok:
            self.vendor_msg = f"'{self.alias_school_sel}' 별칭 저장 완료"
            self.vendor_ok = True
            self.school_master_list = get_school_master_all()
        else:
            self.vendor_msg = "별칭 저장 실패"
            self.vendor_ok = False

    # ── 안전관리 평가 ──

    def set_eval_vendor_sel(self, v: str):
        self.eval_vendor_sel = v

    def set_eval_year(self, y: str):
        self.eval_year = y

    def set_eval_month(self, m: str):
        self.eval_month = m

    def calculate_eval(self):
        """안전관리 평가 점수 계산"""
        if not self.eval_vendor_sel:
            self.vendor_msg = "업체를 선택하세요."
            self.vendor_ok = False
            return
        ym = f"{self.eval_year}-{self.eval_month.zfill(2)}"
        result = hq_calculate_safety_score(self.eval_vendor_sel, ym)
        self.eval_result = {
            "vendor": str(result.get("vendor", "")),
            "year_month": str(result.get("year_month", "")),
            "violation_score": str(result.get("violation_score", 0)),
            "checklist_score": str(result.get("checklist_score", 0)),
            "daily_check_score": str(result.get("daily_check_score", 0)),
            "education_score": str(result.get("education_score", 0)),
            "total_score": str(result.get("total_score", 0)),
            "grade": str(result.get("grade", "")),
        }
        self.vendor_msg = f"{self.eval_vendor_sel} 평가 완료: {result['grade']}등급 ({result['total_score']}점)"
        self.vendor_ok = True
        self.safety_scores_list = hq_get_safety_scores()

    def load_safety_data(self):
        """안전 평가 데이터 로드"""
        self.safety_scores_list = hq_get_safety_scores()
        self.violations_list = hq_get_violations()

    # ── 위반 기록 ──

    def set_viol_vendor(self, v: str):
        self.viol_vendor = v

    def set_viol_driver(self, v: str):
        self.viol_driver = v

    def set_viol_date(self, v: str):
        self.viol_date = v

    def set_viol_type(self, v: str):
        self.viol_type = v

    def set_viol_location(self, v: str):
        self.viol_location = v

    def set_viol_fine(self, v: str):
        self.viol_fine = v

    def set_viol_memo(self, v: str):
        self.viol_memo = v

    def set_viol_vendor_filter(self, v: str):
        self.viol_vendor_filter = v
        vendor = v if v != "전체" else ""
        self.violations_list = hq_get_violations(vendor=vendor)

    def save_violation(self):
        """위반 기록 저장"""
        if not self.viol_vendor or not self.viol_driver or not self.viol_date:
            self.vendor_msg = "업체, 기사, 위반일은 필수입니다."
            self.vendor_ok = False
            return
        try:
            fine = int(self.viol_fine)
        except (ValueError, TypeError):
            fine = 0
        ok = hq_add_violation(
            vendor=self.viol_vendor, driver=self.viol_driver,
            violation_date=self.viol_date, violation_type=self.viol_type,
            location=self.viol_location, fine_amount=fine,
            memo=self.viol_memo,
        )
        if ok:
            self.vendor_msg = f"위반 기록 저장 완료 ({self.viol_type} / {self.viol_date})"
            self.vendor_ok = True
            self.violations_list = hq_get_violations()
            self.viol_driver = ""
            self.viol_date = ""
            self.viol_location = ""
            self.viol_fine = "0"
            self.viol_memo = ""
        else:
            self.vendor_msg = "저장 실패"
            self.vendor_ok = False

    # ══════════════════════════════
    #  이벤트 — 수거일정 (섹션D)
    # ══════════════════════════════

    def load_schedule_tab(self):
        """수거일정 탭 진입 시 로드"""
        self.sched_msg = ""
        if not self.vendor_list:
            self.vendor_list = get_all_vendor_info()
        self.load_schedules()

    def set_sched_sub_tab(self, tab: str):
        self.sched_sub_tab = tab
        self.sched_msg = ""
        if tab == "일정조회":
            self.load_schedules()
        elif tab == "NEIS연동":
            self.neis_meal_dates = []
            self.neis_result_msg = ""

    def set_sched_vendor_filter(self, v: str):
        self.sched_vendor_filter = v
        self.load_schedules()

    def set_sched_month_filter(self, m: str):
        self.sched_month_filter = m
        self.load_schedules()

    def load_schedules(self):
        vendor = self.sched_vendor_filter if self.sched_vendor_filter != "전체" else ""
        ym = self.sched_month_filter if self.sched_month_filter != "전체" else ""
        self.sched_rows = get_hq_schedules(vendor=vendor, year_month=ym)

    # 일정 등록 폼 세터
    def set_sf_vendor(self, v: str):
        self.sf_vendor = v

    def set_sf_month_key(self, v: str):
        self.sf_month_key = v

    def set_sf_weekdays(self, v: str):
        self.sf_weekdays = v

    def set_sf_schools(self, v: str):
        self.sf_schools = v

    def set_sf_items(self, v: str):
        self.sf_items = v

    def set_sf_driver(self, v: str):
        self.sf_driver = v

    def save_sched(self):
        """일정 저장"""
        import json as _json
        if not self.sf_vendor or not self.sf_month_key:
            self.sched_msg = "업체와 월(또는 날짜)은 필수입니다."
            self.sched_ok = False
            return
        weekdays = [w.strip() for w in self.sf_weekdays.split(",") if w.strip()]
        schools = [s.strip() for s in self.sf_schools.split(",") if s.strip()]
        items = [i.strip() for i in self.sf_items.split(",") if i.strip()]
        ok = hq_save_schedule({
            "vendor": self.sf_vendor,
            "month": self.sf_month_key,
            "weekdays": _json.dumps(weekdays),
            "schools": _json.dumps(schools),
            "items": _json.dumps(items),
            "driver": self.sf_driver,
            "registered_by": "admin",
        })
        if ok:
            self.sched_msg = f"일정 저장 완료 ({self.sf_month_key})"
            self.sched_ok = True
            self.load_schedules()
        else:
            self.sched_msg = "저장 실패"
            self.sched_ok = False

    def delete_sched(self, sched_id: str):
        """일정 삭제"""
        ok = hq_delete_schedule(sched_id)
        if ok:
            self.sched_msg = f"일정 ID {sched_id} 삭제 완료"
            self.sched_ok = True
        else:
            self.sched_msg = "삭제 실패"
            self.sched_ok = False
        self.load_schedules()

    # ── NEIS 급식연동 ──

    def set_neis_vendor(self, v: str):
        self.neis_vendor = v
        self.neis_school_list = get_neis_schools_by_vendor(v)
        self.neis_meal_dates = []
        self.neis_result_msg = ""

    def set_neis_month(self, m: str):
        self.neis_month = m

    def set_neis_school_sel(self, s: str):
        self.neis_school_sel = s

    def set_neis_collect_offset(self, v: str):
        self.neis_collect_offset = v

    def set_neis_item_type(self, v: str):
        self.neis_item_type = v

    def set_neis_driver(self, v: str):
        self.neis_driver = v

    def fetch_neis_meals(self):
        """NEIS API로 급식일 조회"""
        from zeroda_reflex.utils.neis_api import fetch_meal_dates
        if not self.neis_school_sel or not self.neis_month:
            self.sched_msg = "학교와 조회월을 선택하세요."
            self.sched_ok = False
            return
        school_info = next(
            (s for s in self.neis_school_list if s["name"] == self.neis_school_sel), None
        )
        if not school_info:
            self.sched_msg = "NEIS 학교코드가 없습니다."
            self.sched_ok = False
            return
        try:
            year = int(self.neis_month[:4])
            month = int(self.neis_month[5:7])
        except (ValueError, IndexError):
            self.sched_msg = "월 형식이 올바르지 않습니다."
            self.sched_ok = False
            return
        result = fetch_meal_dates(
            school_info["neis_edu_code"],
            school_info["neis_school_code"],
            year, month,
        )
        if result["success"]:
            self.neis_meal_dates = result.get("meal_dates", [])
            self.neis_result_msg = result["message"]
            self.sched_msg = result["message"]
            self.sched_ok = True
        else:
            self.neis_meal_dates = []
            self.neis_result_msg = result["message"]
            self.sched_msg = result["message"]
            self.sched_ok = False

    def create_neis_schedules(self):
        """NEIS 급식일 기반 수거일정 일괄 생성"""
        from datetime import timedelta
        if not self.neis_meal_dates:
            self.sched_msg = "먼저 NEIS 급식일을 조회하세요."
            self.sched_ok = False
            return
        try:
            offset = int(self.neis_collect_offset)
        except (ValueError, TypeError):
            offset = 0
        success = 0
        fail = 0
        for md in self.neis_meal_dates:
            try:
                dt = datetime.strptime(md, "%Y-%m-%d")
                collect_dt = dt + timedelta(days=offset)
                collect_date = collect_dt.strftime("%Y-%m-%d")
                ok = save_neis_meal_schedule(
                    school_name=self.neis_school_sel,
                    vendor=self.neis_vendor,
                    meal_date=md,
                    collect_date=collect_date,
                    item_type=self.neis_item_type,
                    driver=self.neis_driver,
                )
                if ok:
                    success += 1
                else:
                    fail += 1
            except Exception as e:
                logger.warning("NEIS 일정 저장 실패: %s", e)
                fail += 1
        self.sched_msg = f"수거일정 생성 완료: 성공 {success}건, 실패 {fail}건"
        self.sched_ok = success > 0
        self.load_schedules()

    # ══════════════════════════════
    #  이벤트 — 정산관리 (섹션E)
    # ══════════════════════════════

    def set_settle_year(self, y: str):
        self.settle_year = y
        self.load_settlement()

    def set_settle_month(self, m: str):
        self.settle_month = m
        self.load_settlement()

    def set_settle_vendor(self, v: str):
        self.settle_vendor = v
        self.load_settlement()

    def load_settlement(self):
        try:
            y = int(self.settle_year)
            m = int(self.settle_month)
        except (ValueError, TypeError):
            return
        vendor = self.settle_vendor if self.settle_vendor != "전체" else ""
        self.settle_rows = get_settlement_data(y, m, vendor)
        self.settle_summary = get_hq_settlement_summary(y, m, vendor)

    # ══════════════════════════════
    #  이벤트 — 탄소감축 (섹션E)
    # ══════════════════════════════

    def set_carbon_year(self, y: str):
        self.carbon_year = y
        self.load_carbon()

    def set_carbon_month(self, m: str):
        self.carbon_month = m
        self.load_carbon()

    def load_carbon(self):
        try:
            y = int(self.carbon_year)
        except (ValueError, TypeError):
            return
        m = 0
        if self.carbon_month != "전체":
            try:
                m = int(self.carbon_month)
            except (ValueError, TypeError):
                pass
        data = get_carbon_data(y, m)
        ranking = data.pop("school_ranking", [])
        # 차트용 숫자 필드 추가
        for r in ranking:
            r["weight_num"] = float(r.get("total_weight", 0) or 0)
            r["carbon_num"] = float(r.get("carbon", 0) or 0)
        self.carbon_school_ranking = ranking
        self.carbon_data = data

    # ══════════════════════════════
    #  이벤트 — 안전관리 (섹션F)
    # ══════════════════════════════

    def set_safety_vendor_filter(self, v: str):
        self.safety_vendor_filter = v
        self.load_safety()

    def load_safety(self):
        """안전교육 이력 + 사고 보고 데이터 로드"""
        vendor = self.safety_vendor_filter if self.safety_vendor_filter != "전체" else ""
        self.safety_edu_rows = get_hq_safety_education(vendor)
        self.safety_accident_rows = get_hq_accident_reports(vendor)

    # ══════════════════════════════
    #  이벤트 — 폐기물분석 (섹션F)
    # ══════════════════════════════

    def set_analytics_year(self, y: str):
        self.analytics_year = y
        self.load_analytics()

    def set_analytics_month(self, m: str):
        self.analytics_month = m
        self.load_analytics()

    def load_analytics(self):
        """폐기물 발생 분석 데이터 로드"""
        try:
            y = int(self.analytics_year)
        except (ValueError, TypeError):
            return
        m = 0
        if self.analytics_month != "전체":
            try:
                m = int(self.analytics_month)
            except (ValueError, TypeError):
                pass
        result = get_waste_analytics(y, m)
        # 차트용 숫자 필드 추가 (recharts는 숫자 데이터 필요)
        by_item = result.get("by_item", [])
        for r in by_item:
            r["weight_num"] = float(r.get("weight", 0) or 0)
            r["count_num"] = int(r.get("count", 0) or 0)
        self.analytics_by_item = by_item

        by_school = result.get("by_school", [])
        for r in by_school:
            r["weight_num"] = float(r.get("weight", 0) or 0)
        self.analytics_by_school = by_school

        by_vendor = result.get("by_vendor", [])
        for r in by_vendor:
            r["weight_num"] = float(r.get("weight", 0) or 0)
        self.analytics_by_vendor = by_vendor

        by_month = result.get("by_month", [])
        for r in by_month:
            r["weight_num"] = float(r.get("weight", 0) or 0)
            r["count_num"] = int(r.get("count", 0) or 0)
        self.analytics_by_month = by_month

        self.analytics_data = {
            "total_weight": str(result.get("total_weight", 0)),
            "total_count": str(result.get("total_count", 0)),
            "avg_weight": str(result.get("avg_weight", 0)),
        }

    # ══════════════════════════════
    #  PDF 다운로드 핸들러
    # ══════════════════════════════

    def download_statement_pdf(self):
        """정산 거래명세서 PDF 다운로드 (본사관리자)"""
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.database import (
            get_vendor_info, get_settlement_data, get_customer_details,
        )
        try:
            y = int(self.settle_year)
            m = int(self.settle_month)
        except (ValueError, TypeError):
            return None
        vendor = self.settle_vendor if self.settle_vendor else ""
        if not vendor or not self.settlement_list:
            return None
        vendor_info = get_vendor_info(vendor)
        rows = get_settlement_data(y, m, vendor)
        if not rows:
            return None
        first_school = self.settlement_list[0].get("name", "") if self.settlement_list else ""
        cust_list = get_customer_details(vendor)
        cust_info = next((c for c in cust_list if c["name"] == first_school), {})
        biz_info = {
            "biz_no": str(cust_info.get("biz_no", "")),
            "representative": str(cust_info.get("representative", "")),
            "address": str(cust_info.get("address", "")),
        }
        cust_type = str(cust_info.get("cust_type", ""))
        fixed_fee = float(cust_info.get("fixed_fee", 0) or 0)
        pdf_bytes = build_statement_pdf(
            vendor, first_school, y, m,
            rows, biz_info, vendor_info,
            cust_type, fixed_fee,
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"거래명세서_{vendor}_{y}-{str(m).zfill(2)}.pdf",
            )
        return None

    # ══════════════════════════════
    #  이메일 발송 핸들러 (Phase 6)
    # ══════════════════════════════

    def set_email_to(self, v: str):
        self.email_to = v
        self.email_msg = ""

    async def send_statement_email(self):
        """거래명세서 PDF를 이메일로 발송 (본사관리자)"""
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.email_service import send_email_with_pdf
        from zeroda_reflex.utils.database import get_vendor_info, get_customer_details
        if not self.email_to or "@" not in self.email_to:
            self.email_msg = "유효한 이메일 주소를 입력하세요."
            self.email_ok = False
            return
        self.email_sending = True
        self.email_msg = ""
        yield
        try:
            y = int(self.settle_year)
            m = int(self.settle_month)
        except (ValueError, TypeError):
            self.email_msg = "연/월을 선택하세요."
            self.email_ok = False
            self.email_sending = False
            return
        vendor = self.settle_vendor
        if not vendor or vendor == "전체" or not self.settlement_list:
            self.email_msg = "업체를 선택하세요."
            self.email_ok = False
            self.email_sending = False
            return
        vendor_info = get_vendor_info(vendor)
        rows = get_settlement_data(y, m, vendor)
        first_school = self.settlement_list[0].get("name", "") if self.settlement_list else ""
        cust_list = get_customer_details(vendor)
        cust_info = next((c for c in cust_list if c["name"] == first_school), {})
        biz_info = {
            "biz_no": str(cust_info.get("biz_no", "")),
            "representative": str(cust_info.get("representative", "")),
            "address": str(cust_info.get("address", "")),
        }
        cust_type = str(cust_info.get("cust_type", ""))
        fixed_fee = float(cust_info.get("fixed_fee", 0) or 0)
        pdf_bytes = build_statement_pdf(
            vendor, first_school, y, m, rows, biz_info, vendor_info, cust_type, fixed_fee,
        )
        if not pdf_bytes:
            self.email_msg = "PDF 생성 실패"
            self.email_ok = False
            self.email_sending = False
            return
        filename = f"거래명세서_{vendor}_{y}-{str(m).zfill(2)}.pdf"
        subject = f"[ZERODA] {y}년 {m}월 거래명세서 — {vendor}"
        body = (
            f"안녕하세요.\n\n"
            f"{vendor}의 {y}년 {m}월 거래명세서를 첨부하여 보내드립니다.\n\n"
            f"확인 부탁드립니다.\n감사합니다.\n\n"
            f"— ZERODA 폐기물데이터플랫폼"
        )
        ok, msg = send_email_with_pdf(self.email_to, subject, body, pdf_bytes, filename)
        self.email_ok = ok
        self.email_msg = msg
        self.email_sending = False

    # ══════════════════════════════
    #  SMS 발송 핸들러 (Phase 8)
    # ══════════════════════════════

    def set_sms_to(self, v: str):
        self.sms_to = v
        self.sms_msg = ""

    async def send_statement_sms(self):
        """거래명세서 요약을 SMS로 발송 (본사관리자)"""
        from zeroda_reflex.utils.sms_service import (
            send_statement_sms as _send_sms,
            build_summary_sms_text,
        )
        from zeroda_reflex.utils.database import (
            get_vendor_info, get_settlement_data,
        )

        if not self.sms_to or len(self.sms_to.replace("-", "")) < 10:
            self.sms_msg = "유효한 전화번호를 입력하세요."
            self.sms_ok = False
            return

        self.sms_sending = True
        self.sms_msg = ""
        yield

        try:
            y = int(self.settle_year)
            m = int(self.settle_month)
        except (ValueError, TypeError):
            self.sms_msg = "연/월을 선택하세요."
            self.sms_ok = False
            self.sms_sending = False
            return

        vendor = self.settle_vendor
        if vendor == "전체" or not self.settle_rows:
            self.sms_msg = "업체를 선택하고 정산 데이터를 확인하세요."
            self.sms_ok = False
            self.sms_sending = False
            return

        first = self.settle_rows[0] if self.settle_rows else {}
        school = first.get("name", "")
        total_weight = float(first.get("total_weight", 0))
        total_amount = float(first.get("amount", 0))

        vendor_info = get_vendor_info(vendor) or {}
        contact = vendor_info.get("contact", "")

        text = build_summary_sms_text(
            vendor_name=vendor,
            school=school,
            year=y,
            month=m,
            total_weight=total_weight,
            total_amount=total_amount,
            contact=contact,
        )

        ok, msg = _send_sms(
            to_phone=self.sms_to,
            message=text,
            vendor_name=vendor,
            vendor_contact=contact,
        )
        self.sms_ok = ok
        self.sms_msg = msg
        self.sms_sending = False

    # ══════════════════════════════
    #  Excel 다운로드 핸들러
    # ══════════════════════════════

    def download_collection_excel(self):
        """수거데이터 Excel 다운로드 (본사관리자 대시보드)"""
        # data_collection_rows에서 현재 필터링된 수거 데이터 추출
        from zeroda_reflex.utils.excel_export import export_collection_data
        data = self.data_collection_rows
        if not data:
            return None
        xlsx = export_collection_data(data, self.selected_year, self.selected_month)
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"수거데이터_{self.selected_year}-{self.selected_month.zfill(2)}.xlsx"
            )
        return None

    def download_settlement_excel(self):
        """정산내역 Excel 다운로드 (본사관리자 정산관리)"""
        # settle_rows와 settle_summary에서 정산 데이터 추출
        from zeroda_reflex.utils.excel_export import export_settlement
        data = self.settle_rows
        summary = self.settle_summary if self.settle_summary else {}
        if not data:
            return None
        xlsx = export_settlement(
            data,
            summary,
            self.selected_year,
            self.selected_month
        )
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"정산내역_{self.selected_year}-{self.selected_month.zfill(2)}.xlsx"
            )
        return None

    def download_carbon_excel(self):
        """탄소감축 데이터 Excel 다운로드 (본사관리자 탄소감축)"""
        # carbon_data와 carbon_school_ranking에서 탄소 감축 데이터 추출
        from zeroda_reflex.utils.excel_export import export_carbon_data
        if not self.carbon_data:
            return None
        xlsx = export_carbon_data(
            self.carbon_data,
            self.carbon_school_ranking,
            self.selected_year
        )
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"탄소감축_{self.selected_year}.xlsx"
            )
        return None
