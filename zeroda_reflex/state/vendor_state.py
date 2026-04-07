# zeroda_reflex/state/vendor_state.py
# 업체관리자 대시보드 상태 관리
import reflex as rx
import logging
from datetime import datetime
from zeroda_reflex.state.auth_state import AuthState

logger = logging.getLogger(__name__)


class VendorState(AuthState):
    """업체관리자 대시보드 상태"""

    # ── 연/월 필터 ──
    selected_year: str = str(datetime.now().year)
    selected_month: str = str(datetime.now().month)

    # ── 현재 활성 탭 ──
    active_tab: str = "수거현황"

    # ── [수거현황] 데이터 ──
    monthly_collections: list[dict] = []
    school_summary: list[dict] = []
    vendor_schools: list[dict] = []
    total_weight: float = 0.0
    total_count: int = 0
    school_count: int = 0

    # ── [수거데이터] 탭 ──
    col_school_filter: str = "전체"
    col_active_subtab: str = "수거내역"

    # ── [수거데이터] 수거입력 폼 ──
    form_school: str = ""
    form_date: str = ""
    form_item_type: str = "음식물"
    form_weight: str = "0"
    form_driver: str = ""
    form_memo: str = ""
    form_save_msg: str = ""
    form_save_ok: bool = False

    # ── [수거데이터] 처리확인 ──
    processing_confirms: list[dict] = []
    proc_status_filter: str = "전체"

    # ── [거래처관리] 탭 ──
    customers_list: list[dict] = []
    filter_cust_type: str = "전체"
    cust_active_subtab: str = "목록"
    # 거래처 폼 상태
    cust_name: str = ""
    cust_biz_no: str = ""
    cust_ceo: str = ""
    cust_addr: str = ""
    cust_biz_type: str = ""
    cust_biz_item: str = ""
    cust_email: str = ""
    cust_phone: str = ""
    cust_type: str = "학교"
    cust_recycler: str = ""
    cust_price_food: str = "0"
    cust_price_recycle: str = "0"
    cust_price_general: str = "0"
    cust_fixed_fee: str = "0"
    cust_neis_edu: str = ""
    cust_neis_school: str = ""
    edit_mode: bool = False
    selected_customer: str = ""
    cust_save_msg: str = ""
    cust_save_ok: bool = False
    cust_delete_msg: str = ""

    # ── [일정관리] 탭 ──
    all_schedules: list[dict] = []
    sched_day_filter: str = "전체"
    sched_item_filter: str = "전체"
    sched_active_subtab: str = "조회"
    schedule_mode: str = "monthly"
    drivers_list: list[str] = []
    sched_form_schools: list[str] = []
    sched_form_weekdays: list[str] = []
    sched_form_items: list[str] = []
    sched_form_driver: str = "(미배정)"
    sched_form_year: str = str(datetime.now().year)
    sched_form_month: str = str(datetime.now().month)
    sched_form_date: str = ""
    sched_save_msg: str = ""
    sched_save_ok: bool = False

    # ── [정산관리] 탭 ──
    item_breakdown: list[dict] = []
    settlement_data: list[dict] = []
    expenses_list: list[dict] = []
    total_revenue: float = 0.0
    total_expense: float = 0.0
    settle_active_subtab: str = "정산현황"
    settle_filter_type: str = "전체"
    exp_name: str = ""
    exp_amount: str = "0"
    exp_date: str = ""
    exp_memo: str = ""
    exp_save_msg: str = ""
    exp_save_ok: bool = False

    # ── [이메일 발송] (Phase 6) ──
    email_to: str = ""          # 수신 이메일 주소
    email_msg: str = ""         # 발송 결과 메시지
    email_ok: bool = False      # 성공 여부
    email_sending: bool = False # 발송 중 플래그

    # ── SMS 발송 (Phase 8) ──
    sms_to: str = ""            # 수신 전화번호
    sms_msg: str = ""           # 발송 결과 메시지
    sms_ok: bool = False        # 성공 여부
    sms_sending: bool = False   # 발송 중 플래그

    # ── [안전관리] 탭 ──
    safety_edu_rows: list[dict] = []
    safety_check_rows: list[dict] = []
    safety_daily_rows: list[dict] = []
    safety_daily_ym: str = ""
    safety_active_subtab: str = "안전교육"
    accident_list: list[dict] = []
    # 일일점검 조회 요약
    daily_check_items: list[dict] = []
    daily_check_total_ok: int = 0
    daily_check_total_fail: int = 0
    daily_check_count: int = 0
    daily_check_rate_str: str = "0.0"
    daily_check_category: str = "전체"
    # 안전교육 폼
    edu_driver: str = ""
    edu_date: str = ""
    edu_type: str = "정기교육"
    edu_hours: str = "2"
    edu_instructor: str = ""
    edu_result: str = "이수"
    edu_memo: str = ""
    edu_save_msg: str = ""
    edu_save_ok: bool = False
    # 차량점검 폼 (8항목)
    chk_driver: str = ""
    chk_date: str = ""
    chk_vehicle_no: str = ""
    chk_inspector: str = ""
    chk_item_0: str = "양호"
    chk_item_1: str = "양호"
    chk_item_2: str = "양호"
    chk_item_3: str = "양호"
    chk_item_4: str = "양호"
    chk_item_5: str = "양호"
    chk_item_6: str = "양호"
    chk_item_7: str = "양호"
    chk_memo: str = ""
    chk_save_msg: str = ""
    chk_save_ok: bool = False
    # 사고신고 폼
    acc_driver: str = ""
    acc_date: str = ""
    acc_location: str = ""
    acc_type: str = "교통사고"
    acc_severity: str = "재산피해"
    acc_desc: str = ""
    acc_action: str = ""
    acc_save_msg: str = ""

    # ── [설정] 탭 ──
    settings_old_pw: str = ""
    settings_new_pw: str = ""
    settings_confirm_pw: str = ""
    settings_msg: str = ""
    settings_ok: bool = False
    settings_active_subtab: str = "업장관리"
    # 업장관리
    biz_customers_list: list[str] = []
    new_biz_name: str = ""
    bulk_biz_names: str = ""
    biz_save_msg: str = ""
    biz_save_ok: bool = False
    # 업체정보 폼
    vinfo_biz_name: str = ""
    vinfo_rep: str = ""
    vinfo_biz_no: str = ""
    vinfo_address: str = ""
    vinfo_contact: str = ""
    vinfo_email: str = ""
    vinfo_account: str = ""
    info_save_msg: str = ""
    info_save_ok: bool = False

    # ════════════════════════════════════════════
    #  수거현황 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def vendor_school_count(self) -> int:
        return len(self.vendor_schools)

    @rx.var
    def avg_weight_per_school(self) -> float:
        if not self.school_summary:
            return 0.0
        total = sum(float(r.get("total_weight") or 0) for r in self.school_summary)
        return round(total / len(self.school_summary), 1)

    @rx.var
    def has_summary(self) -> bool:
        return len(self.school_summary) > 0

    @rx.var
    def has_schools(self) -> bool:
        return len(self.vendor_schools) > 0

    # ════════════════════════════════════════════
    #  수거데이터 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def col_school_names(self) -> list[str]:
        names = [s.get("name", "") for s in self.vendor_schools if s.get("name")]
        return ["전체"] + names

    @rx.var
    def filtered_collections(self) -> list[dict]:
        if self.col_school_filter == "전체":
            return self.monthly_collections
        return [
            r for r in self.monthly_collections
            if r.get("school_name") == self.col_school_filter
        ]

    @rx.var
    def has_collections(self) -> bool:
        return len(self.filtered_collections) > 0

    @rx.var
    def filtered_processing_confirms(self) -> list[dict]:
        if self.proc_status_filter == "전체":
            return self.processing_confirms
        return [
            r for r in self.processing_confirms
            if r.get("status") == self.proc_status_filter
        ]

    @rx.var
    def has_processing_confirms(self) -> bool:
        return len(self.filtered_processing_confirms) > 0

    @rx.var
    def form_save_has_msg(self) -> bool:
        return self.form_save_msg != ""

    # ════════════════════════════════════════════
    #  거래처관리 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def has_customers(self) -> bool:
        return len(self.customers_list) > 0

    @rx.var
    def filtered_customers(self) -> list[dict]:
        if self.filter_cust_type == "전체":
            return self.customers_list
        return [
            r for r in self.customers_list
            if r.get("cust_type") == self.filter_cust_type
        ]

    @rx.var
    def has_filtered_customers(self) -> bool:
        return len(self.filtered_customers) > 0

    @rx.var
    def cust_is_other_type(self) -> bool:
        """기타/기타2 구분 — 월정액 필드 표시 여부"""
        return self.cust_type == "기타" or self.cust_type == "기타2(부가세포함)"

    @rx.var
    def cust_is_school_type(self) -> bool:
        """학교 구분 — NEIS 코드 필드 표시 여부"""
        return self.cust_type == "학교"

    @rx.var
    def cust_save_has_msg(self) -> bool:
        return self.cust_save_msg != ""

    @rx.var
    def cust_delete_has_msg(self) -> bool:
        return self.cust_delete_msg != ""

    @rx.var
    def cust_form_mode_label(self) -> str:
        return "수정 모드" if self.edit_mode else "신규 등록"

    # ════════════════════════════════════════════
    #  일정관리 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def filtered_schedules(self) -> list[dict]:
        result = self.all_schedules
        if self.sched_day_filter != "전체":
            result = [r for r in result if self.sched_day_filter in r.get("weekdays", "")]
        if self.sched_item_filter != "전체":
            result = [r for r in result if self.sched_item_filter in r.get("items", "")]
        return result

    @rx.var
    def has_schedules(self) -> bool:
        return len(self.filtered_schedules) > 0

    @rx.var
    def sched_save_has_msg(self) -> bool:
        return self.sched_save_msg != ""

    @rx.var
    def sched_is_daily_mode(self) -> bool:
        return self.schedule_mode == "daily"

    @rx.var
    def sched_driver_options(self) -> list[str]:
        return ["(미배정)"] + self.drivers_list

    @rx.var
    def has_drivers(self) -> bool:
        return len(self.drivers_list) > 0

    # ════════════════════════════════════════════
    #  정산관리 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def has_item_breakdown(self) -> bool:
        return len(self.item_breakdown) > 0

    @rx.var
    def filtered_settlement(self) -> list[dict]:
        if self.settle_filter_type == "전체":
            return self.settlement_data
        return [
            r for r in self.settlement_data
            if r.get("cust_type") == self.settle_filter_type
        ]

    @rx.var
    def has_settlement_data(self) -> bool:
        return len(self.settlement_data) > 0

    @rx.var
    def has_filtered_settlement(self) -> bool:
        return len(self.filtered_settlement) > 0

    @rx.var
    def has_expenses(self) -> bool:
        return len(self.expenses_list) > 0

    @rx.var
    def exp_save_has_msg(self) -> bool:
        return self.exp_save_msg != ""

    @rx.var
    def net_profit(self) -> float:
        return round(self.total_revenue - self.total_expense, 0)

    # ════════════════════════════════════════════
    #  안전관리 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def has_edu(self) -> bool:
        return len(self.safety_edu_rows) > 0

    @rx.var
    def has_safety_checks(self) -> bool:
        return len(self.safety_check_rows) > 0

    @rx.var
    def has_daily_checks(self) -> bool:
        return len(self.safety_daily_rows) > 0

    @rx.var
    def safety_check_fail_count(self) -> int:
        count = 0
        for r in self.safety_check_rows:
            try:
                count += int(r.get("total_fail", 0) or 0)
            except (ValueError, TypeError):
                pass
        return count

    @rx.var
    def has_accidents(self) -> bool:
        return len(self.accident_list) > 0

    @rx.var
    def has_daily_check_items(self) -> bool:
        return len(self.daily_check_items) > 0

    @rx.var
    def edu_save_has_msg(self) -> bool:
        return self.edu_save_msg != ""

    @rx.var
    def chk_save_has_msg(self) -> bool:
        return self.chk_save_msg != ""

    @rx.var
    def acc_save_has_msg(self) -> bool:
        return self.acc_save_msg != ""

    # ════════════════════════════════════════════
    #  설정 computed vars
    # ════════════════════════════════════════════

    @rx.var
    def settings_has_msg(self) -> bool:
        return self.settings_msg != ""

    @rx.var
    def has_biz_customers(self) -> bool:
        return len(self.biz_customers_list) > 0

    @rx.var
    def biz_save_has_msg(self) -> bool:
        return self.biz_save_msg != ""

    @rx.var
    def info_save_has_msg(self) -> bool:
        return self.info_save_msg != ""

    # ════════════════════════════════════════════
    #  이벤트 핸들러 — 탭 전환 & 필터
    # ════════════════════════════════════════════

    def set_active_tab(self, tab_name: str):
        """탭 전환 + 해당 탭 데이터 로드"""
        self.active_tab = tab_name
        if tab_name == "수거현황":
            self.load_dashboard_data()
        elif tab_name == "수거데이터":
            self.col_school_filter = "전체"
            self.col_active_subtab = "수거내역"
            self.form_save_msg = ""
            if not self.monthly_collections:
                self.load_dashboard_data()
        elif tab_name == "거래처관리":
            self.cust_active_subtab = "목록"
            self.cust_save_msg = ""
            self.cust_delete_msg = ""
            self.load_customers()
        elif tab_name == "일정관리":
            self.sched_active_subtab = "조회"
            self.sched_save_msg = ""
            self.load_schedules()
            self.load_drivers()
            if not self.vendor_schools:
                self.load_dashboard_data()
        elif tab_name == "정산관리":
            self.settle_active_subtab = "정산현황"
            self.settle_filter_type = "전체"
            if not self.monthly_collections:
                self.load_dashboard_data()
            self._compute_settlement()
            self.load_settlement()
            self.load_expenses()
        elif tab_name == "안전관리":
            self.safety_active_subtab = "안전교육"
            self.edu_save_msg = ""
            self.chk_save_msg = ""
            self.acc_save_msg = ""
            self.load_safety_data()
        elif tab_name == "설정":
            self.settings_active_subtab = "업장관리"
            self.biz_save_msg = ""
            self.info_save_msg = ""
            self.load_biz_customers()
            self.load_vendor_info()

    def set_selected_year(self, year: str):
        self.selected_year = year
        self.load_dashboard_data()
        self._compute_settlement()
        self.load_settlement()
        self.load_expenses()

    def set_selected_month(self, month: str):
        self.selected_month = month
        self.load_dashboard_data()
        self._compute_settlement()
        self.load_settlement()
        self.load_expenses()

    def set_col_school_filter(self, school: str):
        self.col_school_filter = school

    def set_col_subtab(self, subtab: str):
        """수거데이터 서브탭 전환"""
        self.col_active_subtab = subtab
        if subtab == "처리확인":
            self.load_processing_confirms()

    def set_form_school(self, val: str):
        self.form_school = val

    def set_form_date(self, val: str):
        self.form_date = val

    def set_form_item_type(self, val: str):
        self.form_item_type = val

    def set_form_weight(self, val: str):
        self.form_weight = val

    def set_form_driver(self, val: str):
        self.form_driver = val

    def set_form_memo(self, val: str):
        self.form_memo = val

    def set_proc_status_filter(self, val: str):
        self.proc_status_filter = val

    def set_cust_subtab(self, subtab: str):
        self.cust_active_subtab = subtab
        self.cust_save_msg = ""
        self.cust_delete_msg = ""

    def set_filter_cust_type(self, t: str):
        self.filter_cust_type = t
        self.cust_delete_msg = ""

    def set_cust_name(self, v: str):
        self.cust_name = v

    def set_cust_biz_no(self, v: str):
        self.cust_biz_no = v

    def set_cust_ceo(self, v: str):
        self.cust_ceo = v

    def set_cust_addr(self, v: str):
        self.cust_addr = v

    def set_cust_biz_type(self, v: str):
        self.cust_biz_type = v

    def set_cust_biz_item(self, v: str):
        self.cust_biz_item = v

    def set_cust_email(self, v: str):
        self.cust_email = v

    def set_cust_phone(self, v: str):
        self.cust_phone = v

    def set_cust_type(self, v: str):
        self.cust_type = v

    def set_cust_recycler(self, v: str):
        self.cust_recycler = v

    def set_cust_price_food(self, v: str):
        self.cust_price_food = v

    def set_cust_price_recycle(self, v: str):
        self.cust_price_recycle = v

    def set_cust_price_general(self, v: str):
        self.cust_price_general = v

    def set_cust_fixed_fee(self, v: str):
        self.cust_fixed_fee = v

    def set_cust_neis_edu(self, v: str):
        self.cust_neis_edu = v

    def set_cust_neis_school(self, v: str):
        self.cust_neis_school = v

    def set_settle_subtab(self, subtab: str):
        self.settle_active_subtab = subtab
        self.exp_save_msg = ""

    def set_settle_filter_type(self, t: str):
        self.settle_filter_type = t

    def set_exp_name(self, v: str):
        self.exp_name = v

    def set_exp_amount(self, v: str):
        self.exp_amount = v

    def set_exp_date(self, v: str):
        self.exp_date = v

    def set_exp_memo(self, v: str):
        self.exp_memo = v

    def set_sched_day_filter(self, day: str):
        self.sched_day_filter = day

    def set_sched_item_filter(self, v: str):
        self.sched_item_filter = v

    def set_sched_subtab(self, subtab: str):
        self.sched_active_subtab = subtab
        self.sched_save_msg = ""

    def set_schedule_mode(self, mode: str):
        self.schedule_mode = mode
        self.sched_form_weekdays = []
        self.sched_form_date = ""

    def set_sched_form_driver(self, v: str):
        self.sched_form_driver = v

    def set_sched_form_year(self, v: str):
        self.sched_form_year = v

    def set_sched_form_month(self, v: str):
        self.sched_form_month = v

    def set_sched_form_date(self, v: str):
        self.sched_form_date = v

    def toggle_sched_school(self, name: str):
        if name in self.sched_form_schools:
            self.sched_form_schools = [s for s in self.sched_form_schools if s != name]
        else:
            self.sched_form_schools = self.sched_form_schools + [name]

    def toggle_sched_weekday(self, day: str):
        if day in self.sched_form_weekdays:
            self.sched_form_weekdays = [d for d in self.sched_form_weekdays if d != day]
        else:
            self.sched_form_weekdays = self.sched_form_weekdays + [day]

    def toggle_sched_item(self, item: str):
        if item in self.sched_form_items:
            self.sched_form_items = [i for i in self.sched_form_items if i != item]
        else:
            self.sched_form_items = self.sched_form_items + [item]

    def set_safety_daily_ym(self, ym: str):
        self.safety_daily_ym = ym

    def set_safety_subtab(self, subtab: str):
        self.safety_active_subtab = subtab
        self.edu_save_msg = ""
        self.chk_save_msg = ""
        self.acc_save_msg = ""
        if subtab == "일일안전점검":
            if not self.safety_daily_ym:
                self.safety_daily_ym = datetime.now().strftime("%Y-%m")
            self.load_daily_check_summary()

    def set_daily_check_category(self, v: str):
        self.daily_check_category = v
        self.load_daily_check_summary()

    def set_edu_driver(self, v: str): self.edu_driver = v
    def set_edu_date(self, v: str): self.edu_date = v
    def set_edu_type(self, v: str): self.edu_type = v
    def set_edu_hours(self, v: str): self.edu_hours = v
    def set_edu_instructor(self, v: str): self.edu_instructor = v
    def set_edu_result(self, v: str): self.edu_result = v
    def set_edu_memo(self, v: str): self.edu_memo = v

    def set_chk_driver(self, v: str): self.chk_driver = v
    def set_chk_date(self, v: str): self.chk_date = v
    def set_chk_vehicle_no(self, v: str): self.chk_vehicle_no = v
    def set_chk_inspector(self, v: str): self.chk_inspector = v
    def set_chk_item_0(self, v: str): self.chk_item_0 = v
    def set_chk_item_1(self, v: str): self.chk_item_1 = v
    def set_chk_item_2(self, v: str): self.chk_item_2 = v
    def set_chk_item_3(self, v: str): self.chk_item_3 = v
    def set_chk_item_4(self, v: str): self.chk_item_4 = v
    def set_chk_item_5(self, v: str): self.chk_item_5 = v
    def set_chk_item_6(self, v: str): self.chk_item_6 = v
    def set_chk_item_7(self, v: str): self.chk_item_7 = v
    def set_chk_memo(self, v: str): self.chk_memo = v

    def set_acc_driver(self, v: str): self.acc_driver = v
    def set_acc_date(self, v: str): self.acc_date = v
    def set_acc_location(self, v: str): self.acc_location = v
    def set_acc_type(self, v: str): self.acc_type = v
    def set_acc_severity(self, v: str): self.acc_severity = v
    def set_acc_desc(self, v: str): self.acc_desc = v
    def set_acc_action(self, v: str): self.acc_action = v

    def set_settings_old_pw(self, val: str):
        self.settings_old_pw = val

    def set_settings_new_pw(self, val: str):
        self.settings_new_pw = val

    def set_settings_confirm_pw(self, val: str):
        self.settings_confirm_pw = val

    def set_settings_subtab(self, subtab: str):
        self.settings_active_subtab = subtab
        self.biz_save_msg = ""
        self.info_save_msg = ""
        if subtab == "업체정보":
            self.load_vendor_info()

    def set_new_biz_name(self, v: str): self.new_biz_name = v
    def set_bulk_biz_names(self, v: str): self.bulk_biz_names = v
    def set_vinfo_biz_name(self, v: str): self.vinfo_biz_name = v
    def set_vinfo_rep(self, v: str): self.vinfo_rep = v
    def set_vinfo_biz_no(self, v: str): self.vinfo_biz_no = v
    def set_vinfo_address(self, v: str): self.vinfo_address = v
    def set_vinfo_contact(self, v: str): self.vinfo_contact = v
    def set_vinfo_email(self, v: str): self.vinfo_email = v
    def set_vinfo_account(self, v: str): self.vinfo_account = v

    # ════════════════════════════════════════════
    #  데이터 로드 핸들러
    # ════════════════════════════════════════════

    def save_collection_form(self):
        """수거입력 폼 저장"""
        from zeroda_reflex.utils.database import upsert_collection
        self.form_save_msg = ""
        self.form_save_ok = False

        school = self.form_school.strip()
        if not school:
            self.form_save_msg = "거래처를 선택하세요."
            return
        try:
            weight = float(self.form_weight)
        except (ValueError, TypeError):
            self.form_save_msg = "수거량을 올바르게 입력하세요."
            return
        # ── 수거량 범위 검증 (0~9999kg) ──
        if weight < 0:
            self.form_save_msg = "수거량은 0 이상이어야 합니다."
            return
        if weight > 9999:
            self.form_save_msg = "수거량이 너무 큽니다. (최대 9,999kg)"
            return
        if weight <= 0:
            self.form_save_msg = "수거량은 0보다 커야 합니다."
            return

        date_str = self.form_date or datetime.now().strftime("%Y-%m-%d")
        ok = upsert_collection({
            "vendor":      self.user_vendor,
            "school_name": school,
            "collect_date": date_str,
            "item_type":   self.form_item_type,
            "weight":      weight,
            "driver":      self.form_driver.strip(),
            "memo":        self.form_memo.strip(),
            "status":      "confirmed",
        })
        if ok:
            self.form_save_msg = f"{school} 수거 데이터가 저장되었습니다."
            self.form_save_ok = True
            self.form_school = ""
            self.form_weight = "0"
            self.form_driver = ""
            self.form_memo = ""
            # 수거내역에 즉시 반영
            self.load_dashboard_data()
        else:
            self.form_save_msg = "저장에 실패했습니다. 다시 시도해주세요."

    def load_processing_confirms(self):
        """처리확인(계근표) 데이터 로드"""
        from zeroda_reflex.utils.database import get_processing_confirms
        self.processing_confirms = get_processing_confirms(self.user_vendor)

    def confirm_processing(self, record_id: str):
        """처리확인 승인"""
        from zeroda_reflex.utils.database import update_processing_confirm_status
        update_processing_confirm_status(record_id, "confirmed", self.user_id)
        self.load_processing_confirms()

    def reject_processing(self, record_id: str):
        """처리확인 반려"""
        from zeroda_reflex.utils.database import update_processing_confirm_status
        update_processing_confirm_status(record_id, "rejected", self.user_id)
        self.load_processing_confirms()

    def load_dashboard_data(self):
        """수거현황 + 공유 데이터 로드 (monthly_collections, school_summary, vendor_schools)"""
        from zeroda_reflex.utils.database import (
            get_monthly_collections,
            get_collection_summary_by_school,
            get_vendor_schools,
        )
        vendor = self.user_vendor
        year = int(self.selected_year) if self.selected_year else datetime.now().year
        month = int(self.selected_month) if self.selected_month else datetime.now().month

        raw = get_monthly_collections(vendor, year, month)
        # 정규화 — foreach 컴포넌트에서 일관된 키 보장
        self.monthly_collections = [
            {
                "school_name": str(r.get("school_name", "") or ""),
                "collect_date": str(r.get("collect_date", "") or ""),
                "item_type": str(r.get("item_type", "") or ""),
                "weight": float(r.get("weight", 0) or 0),
                "driver": str(r.get("driver", "") or ""),
                "status": str(r.get("status", "") or ""),
            }
            for r in raw
        ]
        summary = get_collection_summary_by_school(vendor, year, month)
        # 차트용 숫자 필드 추가 (Phase 9)
        for r in summary:
            r["weight_num"] = float(r.get("total_weight", 0) or 0)
        self.school_summary = summary
        self.vendor_schools = get_vendor_schools(vendor)

        self.total_weight = round(
            sum(r["weight"] for r in self.monthly_collections), 1
        )
        self.total_count = len(self.monthly_collections)
        self.school_count = len(self.school_summary)

    def load_customers(self):
        """거래처관리 탭 데이터 로드"""
        from zeroda_reflex.utils.database import get_customers_by_vendor
        self.customers_list = get_customers_by_vendor(self.user_vendor)

    def clear_cust_form(self):
        """거래처 폼 초기화"""
        self.cust_name = ""
        self.cust_biz_no = ""
        self.cust_ceo = ""
        self.cust_addr = ""
        self.cust_biz_type = ""
        self.cust_biz_item = ""
        self.cust_email = ""
        self.cust_phone = ""
        self.cust_type = "학교"
        self.cust_recycler = ""
        self.cust_price_food = "0"
        self.cust_price_recycle = "0"
        self.cust_price_general = "0"
        self.cust_fixed_fee = "0"
        self.cust_neis_edu = ""
        self.cust_neis_school = ""
        self.edit_mode = False
        self.selected_customer = ""
        self.cust_save_msg = ""
        self.cust_save_ok = False

    def select_cust_for_edit(self, name: str):
        """거래처 선택 → 폼에 기존 데이터 로드 후 등록수정 서브탭 전환"""
        cust = next((r for r in self.customers_list if r.get("name") == name), None)
        if cust is None:
            return
        self.cust_name = cust.get("name", "")
        self.cust_biz_no = cust.get("biz_no", "")
        self.cust_ceo = cust.get("ceo", "")
        self.cust_addr = cust.get("address", "")
        self.cust_biz_type = cust.get("biz_type", "")
        self.cust_biz_item = cust.get("biz_item", "")
        self.cust_email = cust.get("email", "")
        self.cust_phone = cust.get("phone", "")
        self.cust_type = cust.get("cust_type", "학교")
        self.cust_recycler = cust.get("recycler", "")
        self.cust_price_food = cust.get("price_food", "0")
        self.cust_price_recycle = cust.get("price_recycle", "0")
        self.cust_price_general = cust.get("price_general", "0")
        self.cust_fixed_fee = cust.get("fixed_fee", "0")
        self.cust_neis_edu = cust.get("neis_edu", "")
        self.cust_neis_school = cust.get("neis_school", "")
        self.edit_mode = True
        self.selected_customer = name
        self.cust_save_msg = ""
        self.cust_save_ok = False
        self.cust_active_subtab = "등록수정"

    def save_cust_form(self):
        """거래처 폼 저장"""
        import re
        from zeroda_reflex.utils.database import save_customer as db_save
        self.cust_save_msg = ""
        self.cust_save_ok = False

        name = self.cust_name.strip()
        if not name:
            self.cust_save_msg = "거래처명은 필수입니다."
            return
        if not self.edit_mode:
            dup = [r for r in self.customers_list if r.get("name") == name]
            if dup:
                self.cust_save_msg = f"'{name}'은(는) 이미 등록된 거래처입니다."
                return
        try:
            pf = float(self.cust_price_food or 0)
            pr = float(self.cust_price_recycle or 0)
            pg = float(self.cust_price_general or 0)
            ff = float(self.cust_fixed_fee or 0)
        except (ValueError, TypeError):
            self.cust_save_msg = "단가를 올바르게 입력하세요."
            return

        # ── 사업자번호 검증: 빈 값이 아닐 때 숫자와 하이픈만 허용 ──
        biz_no = self.cust_biz_no.strip()
        if biz_no and not re.match(r'^[0-9\-]*$', biz_no):
            self.cust_save_msg = "사업자번호는 숫자와 하이픈(-)만 입력 가능합니다."
            return

        # ── 전화번호 검증: 빈 값이 아닐 때 숫자와 하이픈만 허용 ──
        phone = self.cust_phone.strip()
        if phone and not re.match(r'^[0-9\-]*$', phone):
            self.cust_save_msg = "전화번호는 숫자와 하이픈(-)만 입력 가능합니다."
            return

        # ── 이메일 검증: 빈 값이 아닐 때 @ 포함 여부 확인 ──
        email = self.cust_email.strip()
        if email and '@' not in email:
            self.cust_save_msg = "이메일은 올바른 형식이어야 합니다. (@가 포함되어야 함)"
            return

        ok = db_save({
            "vendor":       self.user_vendor,
            "name":         name,
            "cust_type":    self.cust_type,
            "biz_no":       self.cust_biz_no.strip(),
            "ceo":          self.cust_ceo.strip(),
            "address":      self.cust_addr.strip(),
            "biz_type":     self.cust_biz_type.strip(),
            "biz_item":     self.cust_biz_item.strip(),
            "email":        self.cust_email.strip(),
            "phone":        self.cust_phone.strip(),
            "recycler":     self.cust_recycler.strip(),
            "price_food":   pf,
            "price_recycle": pr,
            "price_general": pg,
            "fixed_fee":    ff,
            "neis_edu":     self.cust_neis_edu.strip(),
            "neis_school":  self.cust_neis_school.strip(),
        })
        if ok:
            action = "수정" if self.edit_mode else "등록"
            self.cust_save_msg = f"'{name}' {action} 완료!"
            self.cust_save_ok = True
            self.edit_mode = True
            self.selected_customer = name
            self.load_customers()
        else:
            self.cust_save_msg = "저장에 실패했습니다. 다시 시도해주세요."

    def delete_cust(self, name: str):
        """거래처 삭제"""
        from zeroda_reflex.utils.database import delete_customer as db_delete
        ok = db_delete(self.user_vendor, name)
        if ok:
            self.cust_delete_msg = f"'{name}' 삭제 완료"
            if self.selected_customer == name:
                self.clear_cust_form()
            self.load_customers()
        else:
            self.cust_delete_msg = f"'{name}' 삭제 실패"

    def load_schedules(self):
        """일정관리 탭 데이터 로드"""
        from zeroda_reflex.utils.database import get_schedules
        self.all_schedules = get_schedules(self.user_vendor)

    def load_drivers(self):
        """기사 목록 로드"""
        from zeroda_reflex.utils.database import get_drivers_by_vendor
        self.drivers_list = get_drivers_by_vendor(self.user_vendor)

    def clear_sched_form(self):
        """일정 폼 초기화"""
        self.sched_form_schools = []
        self.sched_form_weekdays = []
        self.sched_form_items = []
        self.sched_form_driver = "(미배정)"
        self.sched_form_year = str(datetime.now().year)
        self.sched_form_month = str(datetime.now().month)
        self.sched_form_date = ""
        self.sched_save_msg = ""
        self.sched_save_ok = False
        self.schedule_mode = "monthly"

    def save_schedule_form(self):
        """일정 등록 폼 저장 (중복 체크 포함)"""
        from zeroda_reflex.utils.database import (
            get_schedules,
            save_schedule as db_save_sched,
        )
        self.sched_save_msg = ""
        self.sched_save_ok = False

        if not self.sched_form_schools:
            self.sched_save_msg = "담당 거래처를 선택하세요."
            return
        if not self.sched_form_items:
            self.sched_save_msg = "수거 품목을 선택하세요."
            return

        if self.schedule_mode == "daily":
            if not self.sched_form_date:
                self.sched_save_msg = "수거 날짜를 입력하세요."
                return
            month_key = self.sched_form_date
            weekdays: list = []
        else:
            if not self.sched_form_weekdays:
                self.sched_save_msg = "수거 요일을 선택하세요."
                return
            year = self.sched_form_year or str(datetime.now().year)
            month = self.sched_form_month or str(datetime.now().month)
            month_key = f"{year}-{month.zfill(2)}"
            weekdays = list(self.sched_form_weekdays)

        # 중복 체크 — 같은 월+거래처 조합
        existing = get_schedules(self.user_vendor, month_key)
        dup_schools = []
        for ex in existing:
            ex_school_str = ex.get("schools", "")
            for s in self.sched_form_schools:
                if s in ex_school_str and s not in dup_schools:
                    dup_schools.append(s)
        new_schools = [s for s in self.sched_form_schools if s not in dup_schools]

        if not new_schools:
            self.sched_save_msg = f"{month_key}에 선택한 모든 거래처가 이미 등록되어 있습니다."
            return

        driver = self.sched_form_driver
        if driver == "(미배정)":
            driver = ""

        ok = db_save_sched({
            "vendor":   self.user_vendor,
            "month":    month_key,
            "weekdays": weekdays,
            "schools":  new_schools,
            "items":    list(self.sched_form_items),
            "driver":   driver,
        })
        if ok:
            msg = f"일정 저장 완료 ({len(new_schools)}개 거래처)"
            if dup_schools:
                msg += f" | 중복 건너뜀: {', '.join(dup_schools)}"
            self.sched_save_msg = msg
            self.sched_save_ok = True
            self.sched_form_schools = []
            self.sched_form_weekdays = []
            self.sched_form_items = []
            self.load_schedules()
        else:
            self.sched_save_msg = "저장에 실패했습니다."

    def delete_schedule_handler(self, sched_id: str):
        """일정 삭제"""
        from zeroda_reflex.utils.database import delete_schedule as db_del_sched
        db_del_sched(sched_id)
        self.load_schedules()

    def _compute_settlement(self):
        """정산관리 — monthly_collections 에서 품목별 집계 산출"""
        breakdown: dict = {}
        for r in self.monthly_collections:
            it = str(r.get("item_type", "기타") or "기타")
            w = float(r.get("weight", 0) or 0)
            if it not in breakdown:
                breakdown[it] = {"item_type": it, "total_weight": 0.0, "count": 0}
            breakdown[it]["total_weight"] = round(breakdown[it]["total_weight"] + w, 1)
            breakdown[it]["count"] += 1
        self.item_breakdown = list(breakdown.values())

    def load_settlement(self):
        """거래처별 정산 집계 로드"""
        from zeroda_reflex.utils.database import get_settlement_summary
        year = int(self.selected_year) if self.selected_year else datetime.now().year
        month = int(self.selected_month) if self.selected_month else datetime.now().month
        raw = get_settlement_summary(self.user_vendor, year, month)
        self.total_revenue = round(sum(r["total"] for r in raw), 0)
        self.settlement_data = [
            {
                "name":      str(r["name"]),
                "cust_type": str(r["cust_type"]),
                "weight":    str(r["weight"]),
                "count":     str(r["count"]),
                "supply":    str(int(r["supply"])),
                "vat":       str(int(r["vat"])),
                "total":     str(int(r["total"])),
            }
            for r in raw
        ]

    def load_expenses(self):
        """지출 내역 로드"""
        from zeroda_reflex.utils.database import get_expenses
        month = self.selected_month.zfill(2) if self.selected_month else "01"
        ym = f"{self.selected_year}-{month}"
        raw = get_expenses(self.user_vendor, ym)
        self.total_expense = round(sum(abs(r["amount"]) for r in raw), 0)
        self.expenses_list = [
            {
                "id":       str(r["id"]),
                "item":     str(r["item"]),
                "amount":   str(int(abs(r["amount"]))),
                "pay_date": str(r["pay_date"]),
                "memo":     str(r["memo"]),
            }
            for r in raw
        ]

    def save_expense_form(self):
        """지출 폼 저장"""
        from zeroda_reflex.utils.database import save_expense as db_save_exp
        self.exp_save_msg = ""
        self.exp_save_ok = False
        name = self.exp_name.strip()
        if not name:
            self.exp_save_msg = "지출 항목명을 입력하세요."
            return
        try:
            amount = float(self.exp_amount or 0)
        except (ValueError, TypeError):
            self.exp_save_msg = "금액을 올바르게 입력하세요."
            return
        month = self.selected_month.zfill(2) if self.selected_month else "01"
        ym = f"{self.selected_year}-{month}"
        ok = db_save_exp({
            "vendor":     self.user_vendor,
            "year_month": ym,
            "item":       name,
            "amount":     amount,
            "pay_date":   self.exp_date.strip(),
            "memo":       self.exp_memo.strip(),
        })
        if ok:
            self.exp_save_msg = f"'{name}' 지출 등록 완료!"
            self.exp_save_ok = True
            self.exp_name = ""
            self.exp_amount = "0"
            self.exp_date = ""
            self.exp_memo = ""
            self.load_expenses()
        else:
            self.exp_save_msg = "저장에 실패했습니다."

    def delete_expense_handler(self, exp_id: str):
        """지출 항목 삭제"""
        from zeroda_reflex.utils.database import delete_expense as db_del_exp
        db_del_exp(exp_id)
        self.load_expenses()

    def load_accident_reports(self):
        """사고 신고 이력 로드"""
        from zeroda_reflex.utils.database import get_accident_reports as db_get_acc
        self.accident_list = db_get_acc(self.user_vendor)

    def load_daily_check_summary(self):
        """일일안전보건 점검 요약 로드"""
        from zeroda_reflex.utils.database import get_daily_check_summary as db_get_dcs
        ym = self.safety_daily_ym or datetime.now().strftime("%Y-%m")
        result = db_get_dcs(self.user_vendor, ym, self.daily_check_category)
        self.daily_check_items = result.get("items", [])
        self.daily_check_total_ok = int(result.get("total_ok", 0))
        self.daily_check_total_fail = int(result.get("total_fail", 0))
        self.daily_check_count = int(result.get("count", 0))
        self.daily_check_rate_str = str(result.get("rate_str", "0.0"))

    def save_edu_form(self):
        """안전교육 폼 저장"""
        from zeroda_reflex.utils.database import save_safety_education as db_save_edu
        self.edu_save_msg = ""
        self.edu_save_ok = False
        driver = self.edu_driver.strip()
        if not driver:
            self.edu_save_msg = "기사명을 입력하세요."
            return
        if not self.edu_date.strip():
            self.edu_save_msg = "교육일을 입력하세요."
            return
        try:
            hours = int(self.edu_hours or 2)
        except (ValueError, TypeError):
            hours = 2
        ok = db_save_edu({
            "vendor":     self.user_vendor,
            "driver":     driver,
            "edu_date":   self.edu_date.strip(),
            "edu_type":   self.edu_type,
            "edu_hours":  hours,
            "instructor": self.edu_instructor.strip(),
            "result":     self.edu_result,
            "memo":       self.edu_memo.strip(),
        })
        if ok:
            self.edu_save_msg = f"{driver} 안전교육 이력이 저장되었습니다."
            self.edu_save_ok = True
            self.edu_driver = ""
            self.edu_date = ""
            self.edu_hours = "2"
            self.edu_instructor = ""
            self.edu_memo = ""
            self.load_safety_data()
        else:
            self.edu_save_msg = "저장에 실패했습니다."

    def save_checklist_form(self):
        """차량점검 폼 저장"""
        from zeroda_reflex.utils.database import save_safety_checklist as db_save_chk
        self.chk_save_msg = ""
        self.chk_save_ok = False
        driver = self.chk_driver.strip()
        if not driver:
            self.chk_save_msg = "기사명을 입력하세요."
            return
        if not self.chk_date.strip():
            self.chk_save_msg = "점검일을 입력하세요."
            return
        items = {
            "타이어·제동장치·오일류": self.chk_item_0,
            "리프트 유압호스·연결부": self.chk_item_1,
            "리프트 비상정지 스위치": self.chk_item_2,
            "리프트 승강구간 이물질": self.chk_item_3,
            "체인·와이어로프 상태":  self.chk_item_4,
            "적재함 도어 잠금장치":  self.chk_item_5,
            "후진경보음·경광등":    self.chk_item_6,
            "사이드브레이크·고임목": self.chk_item_7,
        }
        total_ok = sum(1 for v in items.values() if v == "양호")
        total_fail = 8 - total_ok
        ok = db_save_chk({
            "vendor":      self.user_vendor,
            "driver":      driver,
            "check_date":  self.chk_date.strip(),
            "vehicle_no":  self.chk_vehicle_no.strip(),
            "check_items": items,
            "total_ok":    total_ok,
            "total_fail":  total_fail,
            "inspector":   self.chk_inspector.strip(),
            "memo":        self.chk_memo.strip(),
        })
        if ok:
            msg = f"{driver} 차량점검 결과 저장 완료 (양호 {total_ok}/8)"
            if total_fail > 0:
                msg += f" — 불량 {total_fail}개 확인 필요"
            self.chk_save_msg = msg
            self.chk_save_ok = (total_fail == 0)
            self.chk_driver = ""
            self.chk_date = ""
            self.chk_vehicle_no = ""
            self.chk_inspector = ""
            for i in range(8):
                setattr(self, f"chk_item_{i}", "양호")
            self.chk_memo = ""
            self.load_safety_data()
        else:
            self.chk_save_msg = "저장에 실패했습니다."

    def save_accident_form(self):
        """사고신고 폼 저장"""
        from zeroda_reflex.utils.database import save_accident_report as db_save_acc
        self.acc_save_msg = ""
        driver = self.acc_driver.strip()
        if not driver:
            self.acc_save_msg = "기사명을 입력하세요."
            return
        if not self.acc_desc.strip():
            self.acc_save_msg = "사고 경위를 입력하세요."
            return
        if not self.acc_date.strip():
            self.acc_save_msg = "발생일을 입력하세요."
            return
        ok = db_save_acc({
            "vendor":         self.user_vendor,
            "driver":         driver,
            "occur_date":     self.acc_date.strip(),
            "occur_location": self.acc_location.strip(),
            "accident_type":  self.acc_type,
            "severity":       self.acc_severity,
            "description":    self.acc_desc.strip(),
            "action_taken":   self.acc_action.strip(),
        })
        if ok:
            self.acc_save_msg = "사고 신고가 완료되었습니다."
            self.acc_driver = ""
            self.acc_date = ""
            self.acc_location = ""
            self.acc_desc = ""
            self.acc_action = ""
            self.load_accident_reports()
        else:
            self.acc_save_msg = "신고에 실패했습니다."

    def load_safety_data(self):
        """안전관리 탭 데이터 로드"""
        from zeroda_reflex.utils.database import (
            get_safety_education,
            get_safety_checklist,
        )
        self.safety_edu_rows = get_safety_education(self.user_vendor)
        self.safety_check_rows = get_safety_checklist(self.user_vendor)
        if not self.safety_daily_ym:
            self.safety_daily_ym = datetime.now().strftime("%Y-%m")
        self.load_safety_daily()
        self.load_accident_reports()

    def load_safety_daily(self):
        """일일안전보건 점검 — safety_daily_ym 기준 재조회"""
        from zeroda_reflex.utils.database import get_daily_checks_by_month
        if self.safety_daily_ym:
            self.safety_daily_rows = get_daily_checks_by_month(
                self.user_vendor, self.safety_daily_ym
            )

    def load_biz_customers(self):
        """업장 목록 로드"""
        from zeroda_reflex.utils.database import get_biz_customers as db_get_biz
        self.biz_customers_list = db_get_biz(self.user_vendor)

    def save_biz_customer_form(self):
        """업장 단건 등록"""
        from zeroda_reflex.utils.database import save_biz_customer as db_save_biz
        self.biz_save_msg = ""
        self.biz_save_ok = False
        name = self.new_biz_name.strip()
        if not name:
            self.biz_save_msg = "업장명을 입력하세요."
            return
        ok = db_save_biz(self.user_vendor, name)
        if ok:
            self.biz_save_msg = f"'{name}' 등록 완료!"
            self.biz_save_ok = True
            self.new_biz_name = ""
            self.load_biz_customers()
        else:
            self.biz_save_msg = f"'{name}'은(는) 이미 등록된 업장입니다."

    def bulk_save_biz_customers(self):
        """업장 일괄 등록 (줄바꿈 구분)"""
        from zeroda_reflex.utils.database import save_biz_customer as db_save_biz
        self.biz_save_msg = ""
        self.biz_save_ok = False
        names = [n.strip() for n in self.bulk_biz_names.split("\n") if n.strip()]
        if not names:
            self.biz_save_msg = "업장명을 입력하세요."
            return
        count = 0
        for name in names:
            if db_save_biz(self.user_vendor, name):
                count += 1
        dup = len(names) - count
        self.biz_save_msg = f"{count}개 업장 등록 완료" + (f" (중복 {dup}개 제외)" if dup else "")
        self.biz_save_ok = count > 0
        self.bulk_biz_names = ""
        self.load_biz_customers()

    def delete_biz_customer_handler(self, name: str):
        """업장 삭제"""
        from zeroda_reflex.utils.database import delete_biz_customer as db_del_biz
        db_del_biz(self.user_vendor, name)
        self.load_biz_customers()

    def load_vendor_info(self):
        """업체 정보 로드"""
        from zeroda_reflex.utils.database import get_vendor_info as db_get_vinfo
        info = db_get_vinfo(self.user_vendor)
        self.vinfo_biz_name = info.get("biz_name", "")
        self.vinfo_rep = info.get("rep", "")
        self.vinfo_biz_no = info.get("biz_no", "")
        self.vinfo_address = info.get("address", "")
        self.vinfo_contact = info.get("contact", "")
        self.vinfo_email = info.get("email", "")
        self.vinfo_account = info.get("account", "")

    def save_vendor_info_form(self):
        """업체 정보 저장"""
        from zeroda_reflex.utils.database import save_vendor_info as db_save_vinfo
        self.info_save_msg = ""
        self.info_save_ok = False
        ok = db_save_vinfo({
            "vendor":   self.user_vendor,
            "biz_name": self.vinfo_biz_name.strip(),
            "rep":      self.vinfo_rep.strip(),
            "biz_no":   self.vinfo_biz_no.strip(),
            "address":  self.vinfo_address.strip(),
            "contact":  self.vinfo_contact.strip(),
            "email":    self.vinfo_email.strip(),
            "account":  self.vinfo_account.strip(),
        })
        if ok:
            self.info_save_msg = "업체 정보가 저장되었습니다."
            self.info_save_ok = True
        else:
            self.info_save_msg = "저장에 실패했습니다."

    def do_change_password(self):
        """비밀번호 변경"""
        self.settings_msg = ""
        self.settings_ok = False
        old_pw = self.settings_old_pw.strip()
        new_pw = self.settings_new_pw.strip()
        confirm = self.settings_confirm_pw.strip()

        if not old_pw or not new_pw or not confirm:
            self.settings_msg = "모든 항목을 입력하세요."
            return
        if new_pw != confirm:
            self.settings_msg = "새 비밀번호가 일치하지 않습니다."
            return
        if len(new_pw) < 6:
            self.settings_msg = "비밀번호는 6자 이상이어야 합니다."
            return

        from zeroda_reflex.utils.database import authenticate_user, update_user_password
        user = authenticate_user(self.user_id, old_pw)
        if user is None:
            self.settings_msg = "현재 비밀번호가 올바르지 않습니다."
            return

        # Phase 1-3: bcrypt 필수화 — SHA256 폴백 제거
        try:
            import bcrypt
            new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
        except Exception as e:
            logger.error("bcrypt 해싱 실패: %s", e)
            self.settings_msg = "비밀번호 암호화 중 오류가 발생했습니다. 관리자에게 문의하세요."
            return

        ok = update_user_password(self.user_id, new_hash)
        if ok:
            self.settings_msg = "비밀번호가 성공적으로 변경되었습니다."
            self.settings_ok = True
            self.settings_old_pw = ""
            self.settings_new_pw = ""
            self.settings_confirm_pw = ""
        else:
            self.settings_msg = "비밀번호 변경에 실패했습니다."

    # ════════════════════════════════════════════
    #  PDF 다운로드 핸들러
    # ════════════════════════════════════════════

    def download_statement_pdf(self):
        """정산 거래명세서 PDF 다운로드 (전체 거래처 합산)"""
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.database import (
            get_vendor_info, get_settlement_data, get_customer_details,
        )
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return None
        vendor = self.user_vendor
        if not self.settlement_data:
            return None
        vendor_info = get_vendor_info(vendor)
        rows = get_settlement_data(y, m, vendor)
        if not rows:
            return None
        # 첫 번째 거래처 정보로 거래명세서 생성
        first_school = self.settlement_data[0]["name"] if self.settlement_data else ""
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

    # ════════════════════════════════════════════
    #  이메일 발송 핸들러 (Phase 6)
    # ════════════════════════════════════════════

    def set_email_to(self, v: str):
        self.email_to = v
        self.email_msg = ""

    async def send_statement_email(self):
        """거래명세서 PDF를 이메일로 발송"""
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.email_service import send_email_with_pdf
        from zeroda_reflex.utils.database import (
            get_vendor_info, get_settlement_data, get_customer_details,
        )
        if not self.email_to or "@" not in self.email_to:
            self.email_msg = "유효한 이메일 주소를 입력하세요."
            self.email_ok = False
            return

        self.email_sending = True
        self.email_msg = ""
        yield  # UI 업데이트 (발송 중 표시)

        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            self.email_msg = "연/월을 선택하세요."
            self.email_ok = False
            self.email_sending = False
            return

        vendor = self.user_vendor
        if not self.settlement_data:
            self.email_msg = "정산 데이터가 없습니다."
            self.email_ok = False
            self.email_sending = False
            return

        # PDF 생성
        vendor_info = get_vendor_info(vendor)
        rows = get_settlement_data(y, m, vendor)
        first_school = self.settlement_data[0]["name"] if self.settlement_data else ""
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

        # 이메일 발송
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

    # ════════════════════════════════════════════
    #  SMS 발송 핸들러 (Phase 8)
    # ════════════════════════════════════════════

    def set_sms_to(self, v: str):
        self.sms_to = v
        self.sms_msg = ""

    async def send_statement_sms(self):
        """거래명세서 요약을 SMS로 발송"""
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
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            self.sms_msg = "연/월을 선택하세요."
            self.sms_ok = False
            self.sms_sending = False
            return

        vendor = self.user_vendor
        if not self.settlement_data:
            self.sms_msg = "정산 데이터가 없습니다."
            self.sms_ok = False
            self.sms_sending = False
            return

        # 첫 번째 거래처 정산 요약
        first = self.settlement_data[0]
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

    # ════════════════════════════════════════════
    #  Excel 다운로드 핸들러
    # ════════════════════════════════════════════

    def download_collection_excel(self):
        """수거현황 Excel 다운로드 (업체관리자)"""
        # monthly_collections에서 월별 수거 데이터 추출
        from zeroda_reflex.utils.excel_export import export_collection_data
        data = self.monthly_collections
        if not data:
            return None
        xlsx = export_collection_data(data, self.selected_year, self.selected_month)
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"수거현황_{self.selected_year}-{self.selected_month.zfill(2)}.xlsx"
            )
        return None

    def download_settlement_excel(self):
        """정산내역 Excel 다운로드 (업체관리자)"""
        # monthly_collections에서 정산 데이터 추출 + expenses_list 포함
        from zeroda_reflex.utils.excel_export import export_settlement
        data = self.monthly_collections
        summary = {
            "total_revenue": str(self.total_revenue),
            "total_expense": str(self.total_expense),
            "net_profit": str(self.net_profit),
        }
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

    def download_customer_excel(self):
        """거래처 정보 Excel 다운로드 (업체관리자 거래처관리)"""
        # customers_list에서 거래처 데이터 추출
        from zeroda_reflex.utils.excel_export import export_customers
        data = self.customers_list
        if not data:
            return None
        xlsx = export_customers(data)
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"거래처_{self.user_vendor}.xlsx"
            )
        return None

    def download_safety_excel(self):
        """안전관리 데이터 Excel 다운로드 (업체관리자 안전관리)"""
        # 안전교육 + 체크리스트 + 일일점검 데이터 통합
        from zeroda_reflex.utils.excel_export import export_safety_data
        safety_data = {
            "education": self.safety_edu_rows,
            "checklist": self.safety_check_rows,
            "daily_checks": self.safety_daily_rows,
        }
        if not any(safety_data.values()):
            return None
        xlsx = export_safety_data(safety_data, self.user_vendor)
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"안전관리_{self.user_vendor}.xlsx"
            )
        return None

    # ════════════════════════════════════════════
    #  페이지 로드
    # ════════════════════════════════════════════

    def on_vendor_load(self):
        """업체관리자 페이지 로드: 인증 확인 + 초기 데이터 로드"""
        if not self.is_authenticated:
            return rx.redirect("/")
        if self.user_role not in ("vendor_admin", "admin"):
            return rx.redirect("/")
        self.load_dashboard_data()
