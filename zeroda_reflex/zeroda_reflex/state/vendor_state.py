# zeroda_reflex/state/vendor_state.py
# 업체관리자 대시보드 상태 관리
import reflex as rx
import logging
import json
from datetime import datetime
from zeroda_reflex.state.auth_state import AuthState

logger = logging.getLogger(__name__)


class VendorState(AuthState):
    """업체관리자 대시보드 상태"""

    # ── 연/월 필터 ──
    selected_year: str = str(datetime.now().year)
    selected_month: str = str(datetime.now().month)

    # ── 학사일정 동기화 ──
    sched_sync_msg: str = ""
    sched_sync_running: bool = False

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
    col_item_filter: str = "전체"        # P2-5: 품목 4단 필터
    col_day_filter: str = "전체"
    col_keyword: str = ""
    col_active_subtab: str = "수거내역"

    # ── [수거데이터] 수거입력 폼 ──
    form_school: str = ""
    form_school_search: str = ""         # P2-6: 거래처 검색 텍스트
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
    customer_names: list[str] = []   # 별칭관리 select 용 — load_customers 시 갱신
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
    cust_search_name: str = ""           # P2-9: 수정탭 검색어

    # ── [거래처관리 - 음성별칭] 섹션 3 ──
    alias_customer_sel: str = ""   # 별칭 관리 대상 거래처
    alias_input: str = ""          # 신규 별칭 입력값
    alias_list: list[str] = []     # 현재 거래처의 별칭 목록
    alias_msg: str = ""            # 저장/삭제 결과 메시지

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

    # ── [수거일정 - NEIS 연동] (P1 보강) ──
    neis_month: str = ""                    # YYYY-MM
    neis_school_list: list[dict] = []       # NEIS 코드 등록 학교
    neis_school_sel: str = ""               # 선택된 학교
    neis_meal_dates: list[str] = []         # 급식일 목록
    neis_meal_count: int = 0
    neis_collect_offset: str = "당일"       # "당일"/"다음날"
    neis_item_type: str = "음식물"          # 콤마 구분
    neis_driver: str = "(미배정)"
    neis_msg: str = ""

    # ── [수거일정 - 급식일정 승인] (P1 보강) ──
    meal_apv_month: str = ""                # YYYY-MM
    meal_draft_rows: list[dict] = []
    meal_approved_count: int = 0
    meal_pending_count: int = 0
    meal_apv_driver: str = "(미배정)"
    meal_apv_offset: str = "유지"           # 유지/당일/다음날
    meal_apv_msg: str = ""

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

    # ── [거래명세서 발송] (P1 보강) ──
    stmt_cust_type: str = "학교"
    stmt_cust_sel: str = ""
    stmt_cust_list: list[str] = []
    stmt_rows: list[dict] = []
    stmt_total_weight: float = 0.0
    stmt_total_amount: float = 0.0
    stmt_vat: float = 0.0
    stmt_grand_total: float = 0.0
    stmt_fixed_fee: float = 0.0
    stmt_tax_type: str = ""               # tax_free / fixed_fee / fixed_fee_vat / vat_10
    stmt_load_msg: str = ""

    # 수급자 정보 (자동 채우기 + 편집 가능)
    rcv_email: str = ""
    rcv_rep: str = ""
    rcv_biz_no: str = ""
    rcv_phone: str = ""
    rcv_address: str = ""
    rcv_biz_type: str = ""
    rcv_biz_item: str = ""
    rcv_recycler: str = ""       # 신규: 재활용자(처리자)

    # 미수금
    overdue_amount: str = "0"
    overdue_months: str = ""
    overdue_memo: str = ""

    # 이메일 편집
    stmt_email_subject: str = ""
    stmt_email_body: str = ""

    # 상세 SMS
    detail_sms_sending: bool = False
    detail_sms_msg: str = ""
    detail_sms_ok: bool = False

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
    safety_chk_approve_msg: str = ""     # P1-3: 차량점검 승인 메시지
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
    daily_approve_msg: str = ""          # P1-4: 일일점검 일괄승인 메시지
    daily_safety_grade: str = ""         # P1-4: 안전등급 (S/A/B/C/D)
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

    # ── [수거분석] 탭 (P1 보강) ──
    analytics_sub_tab: str = "종합현황"

    # 종합현황 KPI
    an_total_kg: str = "0"
    an_avg_daily: str = "0"
    an_collection_days: str = "0"
    an_school_count_str: str = "0"
    an_food_kg: str = "0"
    an_recycle_kg: str = "0"
    an_general_kg: str = "0"
    an_top_school: str = "-"
    an_top_school_kg: str = "0"
    an_mom_change: str = "-"

    # 품목별 / 추세 / 이상치
    an_by_item: list[dict] = []
    an_anomaly_rows: list[dict] = []
    an_anomaly_count: int = 0

    # 일별/요일별/계절별
    an_daily_rows: list[dict] = []
    an_weekday_rows: list[dict] = []
    an_season_rows: list[dict] = []

    # 거래처/기사별
    an_by_school: list[dict] = []
    an_by_driver: list[dict] = []

    # 기상분석
    an_weather_start: str = ""
    an_weather_end: str = ""
    an_weather_temp_corr: str = "-"
    an_weather_rain_corr: str = "-"
    an_weather_humidity_corr: str = "-"
    an_weather_wind_corr: str = "-"
    an_weather_rainy_avg: str = "0"
    an_weather_clear_avg: str = "0"
    an_weather_diff_pct: str = "0"
    an_weather_temp_bins: list[dict] = []
    an_weather_msg: str = ""
    an_weather_running: bool = False

    an_load_msg: str = ""

    # ── [현장사진] 탭 (P2 섹션1) ──
    photo_type_filter: str = "전체"
    photo_date_from: str = ""
    photo_date_to: str = ""
    photo_rows: list[dict] = []

    # ── [수거데이터] 편집/삭제 (P2 섹션2) ──
    edit_col_id: str = ""
    edit_col_weight: str = ""
    edit_col_memo: str = ""
    edit_col_msg: str = ""

    # ── [처리확인] 오늘 비교 KPI (P2 섹션3) ──
    proc_today_coll_weight: float = 0.0
    proc_today_proc_weight: float = 0.0
    proc_today_diff: float = 0.0

    # ── [월말정산] 상세 (P2 섹션6) ──
    monthly_settlement_detail: list[dict] = []

    # ── [안전관리] 기사별 이행률 (P2 섹션7) ──
    daily_driver_compliance: list[dict] = []

    # ── [일정관리] 오늘 완료 (P3 섹션8) ──
    today_done_schools: list[str] = []

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

    # customer_names 는 별도 state var 로 관리 (load_customers 호출 시 갱신).
    # 과거에 @rx.var computed 로 정의했으나, 일부 Reflex 버전에서 frontend
    # iteration 시 VarTypeError 가 발생하여 일반 list state 로 전환함.

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
        result = self.monthly_collections
        if self.col_school_filter != "전체":
            result = [r for r in result if r.get("school_name") == self.col_school_filter]
        if self.col_item_filter != "전체":
            result = [r for r in result if r.get("item_type") == self.col_item_filter]
        if self.col_day_filter != "전체":
            day_str = self.col_day_filter.zfill(2)
            result = [r for r in result if str(r.get("collect_date", ""))[-2:] == day_str]
        if self.col_keyword:
            kw = self.col_keyword.strip().lower()
            result = [
                r for r in result
                if kw in str(r.get("school_name", "")).lower()
                or kw in str(r.get("driver", "")).lower()
                or kw in str(r.get("item_type", "")).lower()
                or kw in str(r.get("status", "")).lower()
            ]
        return result

    @rx.var
    def col_input_school_opts(self) -> list[str]:
        """P2-6: 수거입력 거래처 검색 필터 결과"""
        names = [s.get("name", "") for s in self.vendor_schools if s.get("name")]
        q = self.form_school_search.strip().lower()
        if not q:
            return names
        return [n for n in names if q in n.lower()]

    @rx.var
    def cust_edit_search_names(self) -> list[str]:
        """P2-9: 수정탭 검색 필터 결과"""
        q = self.cust_search_name.strip().lower()
        if not q:
            return self.customer_names
        return [n for n in self.customer_names if q in n.lower()]

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
    def cust_is_tax_free_type(self) -> bool:
        """면세 거래처 구분 — 학교/기타1(면세사업장)"""
        return self.cust_type == "학교" or self.cust_type == "기타1(면세사업장)"

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
    def daily_fail_rows(self) -> list[dict]:
        """불량 있는 일일점검 행 (섹션9)"""
        return [r for r in self.safety_daily_rows if int(r.get("total_fail", 0) or 0) > 0]

    @rx.var
    def has_daily_fails(self) -> bool:
        return len(self.daily_fail_rows) > 0

    @rx.var
    def has_driver_compliance(self) -> bool:
        return len(self.daily_driver_compliance) > 0

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
        elif tab_name == "현장사진":
            self.photo_type_filter = "전체"
            self.photo_date_from = ""
            self.photo_date_to = ""
            self.load_photos()
        elif tab_name == "설정":
            self.settings_active_subtab = "업장관리"
            self.biz_save_msg = ""
            self.info_save_msg = ""
            self.load_biz_customers()
            self.load_vendor_info()

    def set_selected_year(self, year: str):
        self.selected_year = year
        self.col_day_filter = "전체"
        self.col_keyword = ""
        self.load_dashboard_data()
        self._compute_settlement()
        self.load_settlement()
        self.load_expenses()

    def set_selected_month(self, month: str):
        self.selected_month = month
        self.col_day_filter = "전체"
        self.col_keyword = ""
        self.load_dashboard_data()
        self._compute_settlement()
        self.load_settlement()
        self.load_expenses()

    def set_col_school_filter(self, school: str):
        self.col_school_filter = school

    def set_col_item_filter(self, v: str):
        """P2-5: 품목 필터"""
        self.col_item_filter = v

    def set_col_day_filter(self, v: str):
        self.col_day_filter = v

    def set_col_keyword(self, v: str):
        self.col_keyword = v

    def set_form_school_search(self, v: str):
        """P2-6: 수거입력 거래처 검색어"""
        self.form_school_search = v

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
        if subtab == "별칭관리":
            self.alias_customer_sel = ""
            self.alias_list = []
            self.alias_input = ""
            self.alias_msg = ""

    # ── 음성 별칭 관리 핸들러 (섹션 3) ──

    def set_alias_customer(self, name: str):
        """별칭 관리 대상 거래처 선택"""
        from zeroda_reflex.utils.database import get_customer_aliases
        self.alias_customer_sel = name
        self.alias_input = ""
        self.alias_msg = ""
        if name:
            self.alias_list = get_customer_aliases(self.user_vendor, name)
        else:
            self.alias_list = []

    def set_alias_input(self, val: str):
        self.alias_input = val

    def add_alias(self):
        """별칭 추가"""
        from zeroda_reflex.utils.database import add_customer_alias, get_customer_aliases
        alias = self.alias_input.strip()
        if not alias:
            self.alias_msg = "별칭을 입력하세요."
            return
        if not self.alias_customer_sel:
            self.alias_msg = "거래처를 먼저 선택하세요."
            return
        ok = add_customer_alias(self.user_vendor, self.alias_customer_sel, alias)
        if ok:
            self.alias_list = get_customer_aliases(self.user_vendor, self.alias_customer_sel)
            self.alias_input = ""
            self.alias_msg = f"✅ '{alias}' 추가됨"
        else:
            self.alias_msg = "추가 실패 (거래처가 등록되지 않은 상태일 수 있습니다)"

    def remove_alias(self, alias: str):
        """별칭 삭제"""
        from zeroda_reflex.utils.database import remove_customer_alias, get_customer_aliases
        if not self.alias_customer_sel:
            return
        ok = remove_customer_alias(self.user_vendor, self.alias_customer_sel, alias)
        if ok:
            self.alias_list = get_customer_aliases(self.user_vendor, self.alias_customer_sel)
            self.alias_msg = f"🗑️ '{alias}' 삭제됨"

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

    # ════════════════════════════════════════════
    #  거래명세서 발송 (P1 보강)
    # ════════════════════════════════════════════

    def _get_tax_type(self, cust_type: str) -> str:
        """거래처 유형 → 세금 분류"""
        if cust_type in ['학교', '기타1(면세사업장)']:
            return 'tax_free'
        elif cust_type == '기타':
            return 'fixed_fee'
        elif cust_type == '기타2(부가세포함)':
            return 'fixed_fee_vat'
        else:  # 기업, 관공서, 일반업장
            return 'vat_10'

    def set_stmt_cust_type(self, v: str):
        self.stmt_cust_type = v
        self.stmt_cust_sel = ""
        self.stmt_rows = []
        self._reload_stmt_cust_list()

    def set_stmt_cust_sel(self, v: str):
        self.stmt_cust_sel = v

    def _reload_stmt_cust_list(self):
        """선택된 유형의 거래처 목록 재구성"""
        try:
            from zeroda_reflex.utils.database import get_customers_by_vendor
            customers = get_customers_by_vendor(self.user_vendor) or []
            if self.stmt_cust_type == '전체':
                self.stmt_cust_list = [c.get('name', '') for c in customers if c.get('name')]
            else:
                self.stmt_cust_list = [
                    c.get('name', '') for c in customers
                    if c.get('cust_type', '') == self.stmt_cust_type and c.get('name')
                ]
        except Exception as e:
            logger.error(f"[load_stmt_cust_list] {e}", exc_info=True)
            self.stmt_cust_list = []
            self.stmt_load_msg = "거래처 목록 로드에 실패했습니다."

    def load_stmt_customers(self):
        """명세서 발송 서브탭 진입 시 호출"""
        self._reload_stmt_cust_list()

    def load_statement_data(self):
        """선택 거래처의 거래명세서 데이터 로드"""
        try:
            from zeroda_reflex.utils.database import (
                get_customers_by_vendor, get_monthly_collections, get_vendor_info,
            )
            year = int(self.selected_year) if self.selected_year else datetime.now().year
            month = int(self.selected_month) if self.selected_month else datetime.now().month
            vendor = self.user_vendor

            customers = get_customers_by_vendor(vendor) or []
            self._reload_stmt_cust_list()

            if not self.stmt_cust_sel or self.stmt_cust_sel not in self.stmt_cust_list:
                self.stmt_load_msg = "거래처를 선택하세요."
                return

            # 수거 데이터
            all_rows = get_monthly_collections(vendor, year, month) or []
            rows = [dict(r) for r in all_rows if r.get('school_name') == self.stmt_cust_sel]

            # 거래처 정보
            cust_info = next((c for c in customers if c.get('name') == self.stmt_cust_sel), {}) or {}
            price_map = {
                '음식물': float(cust_info.get('price_food', 0) or 0),
                '재활용': float(cust_info.get('price_recycle', 0) or 0),
                '일반': float(cust_info.get('price_general', 0) or 0),
            }
            _recycler = cust_info.get('recycler', '') or ''
            _recycle_method_map = {
                '음식물': '퇴비화및비료생산',
                '음식물쓰레기': '퇴비화및비료생산',
                '재활용': '선별 후 재활용',
                '일반': '소각/매립',
                '사업장폐기물': '소각/매립',
            }
            for row in rows:
                item = row.get('item_type', '음식물')
                up = price_map.get(item, 0)
                if up > 0:
                    row['unit_price'] = up
                    row['amount'] = round(float(row.get('weight', 0) or 0) * up)
                else:
                    row['unit_price'] = float(row.get('unit_price', 0) or 0)
                    row['amount'] = float(row.get('amount', 0) or 0)
                row['recycler'] = _recycler
                row['recycle_method'] = _recycle_method_map.get(item, '')
                row['collector'] = vendor
            self.stmt_rows = rows

            # 세금 분류
            self.stmt_tax_type = self._get_tax_type(self.stmt_cust_type)
            self.stmt_total_weight = round(sum(float(r.get('weight', 0) or 0) for r in rows), 1)
            self.stmt_total_amount = round(sum(float(r.get('amount', 0) or 0) for r in rows))
            self.stmt_fixed_fee = float(cust_info.get('fixed_monthly_fee', 0) or 0)

            if self.stmt_tax_type == 'tax_free':
                self.stmt_vat = 0
                self.stmt_grand_total = self.stmt_total_amount
            elif self.stmt_tax_type == 'fixed_fee':
                self.stmt_vat = 0
                self.stmt_grand_total = self.stmt_fixed_fee
            elif self.stmt_tax_type == 'fixed_fee_vat':
                self.stmt_vat = round(self.stmt_fixed_fee * 0.1)
                self.stmt_grand_total = self.stmt_fixed_fee + self.stmt_vat
            else:  # vat_10
                self.stmt_vat = round(self.stmt_total_amount * 0.1)
                self.stmt_grand_total = self.stmt_total_amount + self.stmt_vat

            # 수급자 정보 자동 채우기
            self.rcv_rep = cust_info.get('ceo', '') or ''
            self.rcv_biz_no = cust_info.get('biz_no', '') or ''
            self.rcv_phone = cust_info.get('phone', '') or ''
            self.rcv_address = cust_info.get('address', '') or ''
            self.rcv_email = cust_info.get('email', '') or ''
            self.rcv_biz_type = cust_info.get('biz_type', '') or ''
            self.rcv_biz_item = cust_info.get('biz_item', '') or ''
            self.rcv_recycler = cust_info.get('recycler', '') or ''

            self._build_email_template()
            self.stmt_load_msg = f"{len(rows)}건 로드 완료"
        except Exception as e:
            logger.error(f"[load_statement_data] {e}", exc_info=True)
            self.stmt_load_msg = "데이터 로드에 실패했습니다."

    def _build_biz_info(self) -> dict:
        """pdf_generator가 기대하는 한글 키로 수급자 정보 dict 구성."""
        return {
            '상호':       self.stmt_cust_sel,
            '대표자':     self.rcv_rep,
            '사업자번호':  self.rcv_biz_no,
            '주소':       self.rcv_address,
            '이메일':     self.rcv_email,
            '연락처':     self.rcv_phone,
            '업태':       self.rcv_biz_type,
            '종목':       self.rcv_biz_item,
            '재활용자':   self.rcv_recycler,
            # 영문 키 방어적 함께 제공
            'biz_no':         self.rcv_biz_no,
            'representative': self.rcv_rep,
            'address':        self.rcv_address,
            'email':          self.rcv_email,
            'phone':          self.rcv_phone,
            'recycler':       self.rcv_recycler,
        }

    def _build_email_template(self):
        """이메일 제목/본문 자동 생성"""
        try:
            from zeroda_reflex.utils.database import get_vendor_info
            vinfo = get_vendor_info(self.user_vendor) or {}
        except Exception:
            vinfo = {}
        biz_name = vinfo.get('biz_name', self.user_vendor) or self.user_vendor
        contact = vinfo.get('contact', '') or ''

        self.stmt_email_subject = (
            f"[{biz_name}] {self.selected_year}년 {self.selected_month}월 "
            f"거래명세서 - {self.stmt_cust_sel}"
        )

        overdue_body = ""
        try:
            od_amt = float(self.overdue_amount or 0)
        except Exception:
            od_amt = 0.0
        if od_amt > 0:
            memo_line = f"비고: {self.overdue_memo}\n" if self.overdue_memo else ""
            overdue_body = (
                f"\n※ 미납 안내\n"
                f"미납금액: {int(od_amt):,}원\n"
                f"미납개월: {self.overdue_months or '확인 필요'}\n"
                f"{memo_line}"
                f"조속한 납부 부탁드립니다.\n"
            )

        self.stmt_email_body = (
            f"{self.stmt_cust_sel} 담당자님께,\n\n"
            f"안녕하세요. {biz_name} 입니다.\n\n"
            f"{self.selected_year}년 {self.selected_month}월 거래명세서를 첨부하여 발송드립니다.\n"
            f"확인 후 문의사항이 있으시면 연락 주시기 바랍니다.\n"
            f"{overdue_body}\n"
            f"감사합니다.\n"
            f"{biz_name} 드림\n"
            f"연락처: {contact}"
        )

    # ── 입력 핸들러 ──
    def set_overdue_amount(self, v: str):
        self.overdue_amount = v
    def set_overdue_months(self, v: str):
        self.overdue_months = v
    def set_overdue_memo(self, v: str):
        self.overdue_memo = v
    def set_rcv_email(self, v: str):
        self.rcv_email = v
    def set_rcv_rep(self, v: str):
        self.rcv_rep = v
    def set_rcv_biz_no(self, v: str):
        self.rcv_biz_no = v
    def set_rcv_phone(self, v: str):
        self.rcv_phone = v
    def set_rcv_address(self, v: str):
        self.rcv_address = v
    def set_rcv_recycler(self, v: str):
        self.rcv_recycler = v
    def set_rcv_biz_type(self, v: str):
        self.rcv_biz_type = v
    def set_rcv_biz_item(self, v: str):
        self.rcv_biz_item = v
    def set_stmt_email_subject(self, v: str):
        self.stmt_email_subject = v
    def set_stmt_email_body(self, v: str):
        self.stmt_email_body = v

    def download_stmt_detail_pdf(self):
        """선택 거래처 거래명세서 PDF 다운로드 (명세서발송 서브탭)"""
        if not self.stmt_cust_sel or not self.stmt_rows:
            return None
        try:
            from zeroda_reflex.utils.pdf_export import build_statement_pdf
            from zeroda_reflex.utils.database import get_vendor_info
            y = int(self.selected_year)
            m = int(self.selected_month)
            vinfo = get_vendor_info(self.user_vendor) or {}
            biz_info = self._build_biz_info()
            pdf_bytes = build_statement_pdf(
                self.user_vendor, self.stmt_cust_sel, y, m,
                self.stmt_rows, biz_info, vinfo,
                self.stmt_cust_type, self.stmt_fixed_fee,
            )
            if not pdf_bytes:
                return None
            return rx.download(
                data=pdf_bytes,
                filename=f"거래명세서_{self.stmt_cust_sel}_{y}-{str(m).zfill(2)}.pdf",
            )
        except Exception:
            return None

    async def send_stmt_detail_email(self):
        """거래명세서 발송 — 편집된 제목/본문 + PDF 첨부"""
        import logging
        import traceback
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.email_service import send_email_with_pdf
        from zeroda_reflex.utils.database import get_vendor_info
        _log = logging.getLogger(__name__)

        if not self.rcv_email or "@" not in self.rcv_email:
            self.email_msg = "유효한 수신 이메일을 입력하세요."
            self.email_ok = False
            return
        if not self.stmt_cust_sel or not self.stmt_rows:
            self.email_msg = "거래처를 먼저 조회하세요."
            self.email_ok = False
            return

        self.email_sending = True
        self.email_msg = ""
        yield

        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            self.email_msg = "연/월을 선택하세요."
            self.email_ok = False
            self.email_sending = False
            return

        try:
            # [단계1] PDF 생성
            self.email_msg = "PDF 생성 중..."
            yield
            vinfo = get_vendor_info(self.user_vendor) or {}
            biz_info = self._build_biz_info()
            pdf_bytes = build_statement_pdf(
                self.user_vendor, self.stmt_cust_sel, y, m,
                self.stmt_rows, biz_info, vinfo,
                self.stmt_cust_type, self.stmt_fixed_fee,
            )
            if not pdf_bytes:
                self.email_msg = "❌ [PDF생성] reportlab 미설치 또는 pdf_generator 오류 — 서버 로그 확인"
                self.email_ok = False
                self.email_sending = False
                _log.error("send_stmt_detail_email: build_statement_pdf returned None")
                return

            # [단계2] 이메일 발송
            self.email_msg = "이메일 발송 중..."
            yield
            filename = f"거래명세서_{self.stmt_cust_sel}_{y}-{str(m).zfill(2)}.pdf"
            ok, msg = send_email_with_pdf(
                self.rcv_email, self.stmt_email_subject, self.stmt_email_body,
                pdf_bytes, filename,
            )
            self.email_ok = ok
            self.email_msg = f"✅ {msg}" if ok else f"❌ [SMTP] {msg}"
        except Exception as e:
            self.email_ok = False
            short = str(e).split("\n")[0][:80]
            self.email_msg = f"❌ [예외] {short}"
            _log.exception("send_stmt_detail_email 예외:\n%s", traceback.format_exc())
        finally:
            self.email_sending = False

    async def send_stmt_detail_sms(self):
        """상세 SMS — PDF를 서버에 저장하고 다운로드 링크를 SMS로 발송."""
        import traceback
        from zeroda_reflex.utils.pdf_export import (
            build_statement_pdf,
            save_statement_pdf_to_storage,
        )
        from zeroda_reflex.utils.sms_service import send_statement_sms as _send_sms
        from zeroda_reflex.utils.database import get_vendor_info
        import logging as _logging
        _log = _logging.getLogger(__name__)

        if not self.rcv_phone:
            self.detail_sms_msg = "수신 전화번호를 입력하세요."
            self.detail_sms_ok = False
            return
        if not self.stmt_cust_sel or not self.stmt_rows:
            self.detail_sms_msg = "거래처를 먼저 조회하세요."
            self.detail_sms_ok = False
            return

        self.detail_sms_sending = True
        self.detail_sms_msg = ""
        yield

        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            self.detail_sms_msg = "연/월을 선택하세요."
            self.detail_sms_ok = False
            self.detail_sms_sending = False
            return

        try:
            # [1] PDF 생성
            self.detail_sms_msg = "PDF 생성 중..."
            yield
            vinfo = get_vendor_info(self.user_vendor) or {}
            biz_info = self._build_biz_info()
            pdf_bytes = build_statement_pdf(
                self.user_vendor, self.stmt_cust_sel, y, m,
                self.stmt_rows, biz_info, vinfo,
                self.stmt_cust_type, self.stmt_fixed_fee,
            )
            if not pdf_bytes:
                self.detail_sms_msg = "❌ PDF 생성 실패 — 서버 로그 확인"
                self.detail_sms_ok = False
                self.detail_sms_sending = False
                _log.error("send_stmt_detail_sms: build_statement_pdf returned None")
                return

            # [2] 저장소 업로드
            self.detail_sms_msg = "저장소 업로드 중..."
            yield
            url, fpath = save_statement_pdf_to_storage(pdf_bytes)
            if not url:
                self.detail_sms_msg = "❌ PDF 저장 실패"
                self.detail_sms_ok = False
                self.detail_sms_sending = False
                return

            # [3] 본문 조립
            try:
                od_amt = float(self.overdue_amount or 0)
            except Exception:
                od_amt = 0.0
            overdue_line = f"\n[미납] {int(od_amt):,}원" if od_amt > 0 else ""
            text = (
                f"[{self.user_vendor}]\n"
                f"{y}년 {m}월 거래명세서\n"
                f"거래처: {self.stmt_cust_sel}\n"
                f"합계: {int(self.stmt_grand_total):,}원"
                f"{overdue_line}\n"
                f"\n명세서(PDF): {url}\n"
                f"(링크는 7일간 유효)"
            )

            # [4] SMS 발송 — vendor_name="" 로 footer 자동추가 차단
            # (04 자료 원본 본문 포맷 복원, footer는 URL 뒤에 붙지 않도록 차단)
            self.detail_sms_msg = "SMS 발송 중..."
            yield
            ok, msg = _send_sms(
                to_phone=self.rcv_phone,
                message=text,
                vendor_name="",
                vendor_contact="",
            )
            self.detail_sms_ok = ok
            self.detail_sms_msg = "✅ PDF 링크 SMS 발송 완료" if ok else f"❌ {msg}"
        except Exception as e:
            self.detail_sms_ok = False
            short = str(e).split("\n")[0][:80]
            self.detail_sms_msg = f"❌ [예외] {short}"
            _log.exception("send_stmt_detail_sms 예외:\n%s", traceback.format_exc())
        finally:
            self.detail_sms_sending = False

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
        if subtab == "NEIS연동":
            self.load_neis_schools()
        elif subtab == "급식일정승인":
            self.load_meal_approvals()

    # ════════════════════════════════════════════
    #  NEIS 급식일정 연동 (P1 보강)
    # ════════════════════════════════════════════

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

    def load_neis_schools(self):
        """NEIS 코드 등록된 거래처(학교) 로드"""
        try:
            from zeroda_reflex.utils.database import get_neis_schools_by_vendor
            self.neis_school_list = get_neis_schools_by_vendor(self.user_vendor) or []
            if not self.neis_month:
                self.neis_month = datetime.now().strftime("%Y-%m")
        except Exception as e:
            self.neis_school_list = []
            logger.error(f"[load_neis_schools] {e}", exc_info=True)
            self.neis_msg = "❌ 학교 정보 로드에 실패했습니다."

    @rx.var
    def neis_school_options(self) -> list[str]:
        return [s.get("name", "") for s in self.neis_school_list if s.get("name")]

    @rx.var
    def neis_school_count(self) -> int:
        return len(self.neis_school_list)

    @rx.var
    def has_neis_meals(self) -> bool:
        return len(self.neis_meal_dates) > 0

    async def fetch_neis_meals(self):
        """NEIS API로 급식일 조회"""
        from zeroda_reflex.utils.neis_api import fetch_meal_dates
        school = next(
            (s for s in self.neis_school_list if s.get("name") == self.neis_school_sel),
            None,
        )
        if not school:
            self.neis_msg = "❌ 학교를 선택하세요."
            return
        try:
            ym = self.neis_month or datetime.now().strftime("%Y-%m")
            year = int(ym[:4])
            month = int(ym[5:7])
        except Exception:
            year = datetime.now().year
            month = datetime.now().month

        result = fetch_meal_dates(
            school.get("neis_edu_code", ""),
            school.get("neis_school_code", ""),
            year, month,
        ) or {}

        if result.get("success"):
            self.neis_meal_dates = result.get("meal_dates", []) or []
            self.neis_meal_count = len(self.neis_meal_dates)
            self.neis_msg = f"✅ {self.neis_meal_count}일 급식일 조회 완료"
        else:
            self.neis_meal_dates = []
            self.neis_meal_count = 0
            self.neis_msg = f"❌ {result.get('message', '조회 실패')}"

    def create_neis_schedules(self):
        """NEIS 급식일 기반 수거일정 생성"""
        from datetime import datetime as dt, timedelta
        from zeroda_reflex.utils.database import save_schedule

        if not self.neis_meal_dates:
            self.neis_msg = "❌ 급식일 데이터가 없습니다."
            return

        offset = 1 if self.neis_collect_offset == "다음날" else 0
        items = [it.strip() for it in self.neis_item_type.split(",") if it.strip()]
        driver = "" if self.neis_driver == "(미배정)" else self.neis_driver
        ok, fail = 0, 0
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

        for meal_date in self.neis_meal_dates:
            try:
                md = dt.strptime(meal_date, "%Y-%m-%d")
                collect_date = (md + timedelta(days=offset)).strftime("%Y-%m-%d")
                cd = dt.strptime(collect_date, "%Y-%m-%d")
                wd = weekday_names[cd.weekday()]
                for item in items:
                    save_schedule({
                        "vendor": self.user_vendor,
                        "month": collect_date,
                        "weekdays": json.dumps([wd], ensure_ascii=False),
                        "schools": json.dumps([self.neis_school_sel], ensure_ascii=False),
                        "items": json.dumps([item], ensure_ascii=False),
                        "driver": driver,
                        "registered_by": "neis_api",
                    })
                ok += 1
            except Exception:
                fail += 1

        suffix = f" (실패 {fail}건)" if fail else ""
        self.neis_msg = f"✅ 수거일정 {ok}건 생성 완료{suffix}"
        try:
            self.load_schedules()
        except Exception:
            pass

    # ════════════════════════════════════════════
    #  급식일정 승인 (P1 보강)
    # ════════════════════════════════════════════

    def set_meal_apv_month(self, v: str):
        self.meal_apv_month = v

    def set_meal_apv_driver(self, v: str):
        self.meal_apv_driver = v

    def set_meal_apv_offset(self, v: str):
        self.meal_apv_offset = v

    def load_meal_approvals(self):
        """승인 대기 + 승인 완료 카운트 로드"""
        try:
            from zeroda_reflex.utils.database import get_meal_schedules
            ym = self.meal_apv_month or datetime.now().strftime("%Y-%m")
            self.meal_apv_month = ym
            drafts = get_meal_schedules(
                vendor=self.user_vendor, status="draft", year_month=ym,
            ) or []
            approved = get_meal_schedules(
                vendor=self.user_vendor, status="approved", year_month=ym,
            ) or []
            self.meal_draft_rows = drafts
            self.meal_pending_count = len(drafts)
            self.meal_approved_count = len(approved)
        except Exception as e:
            self.meal_draft_rows = []
            self.meal_pending_count = 0
            self.meal_approved_count = 0
            logger.error(f"[load_meal_approvals] {e}", exc_info=True)
            self.meal_apv_msg = "❌ 데이터 로드에 실패했습니다."

    @rx.var
    def meal_draft_school_groups(self) -> list[dict]:
        """학교별 그룹화 — [{school, count}]"""
        groups: dict = {}
        for r in self.meal_draft_rows:
            sn = r.get("school_name", "")
            groups[sn] = groups.get(sn, 0) + 1
        return [{"school": k, "count": v} for k, v in groups.items()]

    def _meal_offset_value(self) -> int:
        """라벨 → 숫자 (-1 = 유지)"""
        if self.meal_apv_offset == "유지":
            return -1
        if self.meal_apv_offset == "다음날":
            return 1
        return 0  # 당일

    def approve_school_meals(self, school_name: str):
        """학교별 전체 승인"""
        try:
            from zeroda_reflex.utils.database import approve_meal_schedules
            ids = [
                r.get("id") for r in self.meal_draft_rows
                if r.get("school_name") == school_name and r.get("id")
            ]
            if not ids:
                self.meal_apv_msg = f"⚠️ {school_name}: 승인할 일정 없음"
                return
            offset = self._meal_offset_value()
            driver = "" if self.meal_apv_driver == "(미배정)" else self.meal_apv_driver
            success, fail = approve_meal_schedules(
                ids, approved_by="vendor_admin",
                driver=driver,
                collect_offset=(0 if offset < 0 else offset),
            )
            self.meal_apv_msg = f"✅ {school_name}: {success}건 승인" + (
                f" (실패 {fail})" if fail else ""
            )
            self.load_meal_approvals()
            try:
                self.load_schedules()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"[approve_meal] {e}", exc_info=True)
            self.meal_apv_msg = "❌ 승인 처리에 실패했습니다."

    def reject_school_meals(self, school_name: str):
        """학교별 전체 반려"""
        try:
            from zeroda_reflex.utils.database import cancel_meal_schedules
            ids = [
                r.get("id") for r in self.meal_draft_rows
                if r.get("school_name") == school_name and r.get("id")
            ]
            if not ids:
                self.meal_apv_msg = f"⚠️ {school_name}: 반려할 일정 없음"
                return
            success, fail = cancel_meal_schedules(ids, note="업체관리자 반려")
            self.meal_apv_msg = f"⚠️ {school_name}: {success}건 반려"
            self.load_meal_approvals()
        except Exception as e:
            logger.error(f"[reject_meal] {e}", exc_info=True)
            self.meal_apv_msg = "❌ 반려 처리에 실패했습니다."

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
        """처리확인(계근표) 데이터 로드 + 오늘 수거/처리량 비교 KPI"""
        from zeroda_reflex.utils.database import get_processing_confirms
        self.processing_confirms = get_processing_confirms(self.user_vendor)
        # 오늘 날짜 기준 수거량 vs 처리량 비교
        today = datetime.now().strftime("%Y-%m-%d")
        coll_today = sum(
            float(r.get("weight", 0) or 0)
            for r in self.monthly_collections
            if str(r.get("collect_date", "")) == today
        )
        proc_today = sum(
            float(r.get("total_weight", 0) or 0)
            for r in self.processing_confirms
            if str(r.get("confirm_date", "")) == today
        )
        self.proc_today_coll_weight = round(coll_today, 1)
        self.proc_today_proc_weight = round(proc_today, 1)
        self.proc_today_diff = round(coll_today - proc_today, 1)

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
        # 정규화 — foreach 컴포넌트에서 일관된 키 보장 (id 포함 — 편집/삭제용)
        self.monthly_collections = [
            {
                "id": str(r.get("id", r.get("rowid", "")) or ""),
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
        # 별칭관리 select 용 이름 목록 동기화 (Reflex Var iteration 회피)
        self.customer_names = [
            s.get("name", "") for s in self.customers_list if s.get("name")
        ]

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
        self.cust_active_subtab = "수정"   # P2-8: "등록수정" → "수정" 탭으로 변경

    def set_cust_subtab(self, label: str):
        """P2-8: 거래처관리 서브탭 전환 (등록 탭 전환 시 폼 초기화)"""
        self.cust_active_subtab = label
        if label == "등록":
            self.clear_cust_form()
        elif label == "수정":
            self.cust_search_name = ""

    def set_cust_search_name(self, v: str):
        """P2-9: 수정탭 검색어"""
        self.cust_search_name = v

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
        """일정관리 탭 데이터 로드 + 오늘 완료 학교 표시"""
        from zeroda_reflex.utils.database import get_schedules, get_monthly_collections
        schedules = get_schedules(self.user_vendor)

        # 오늘 수거 완료 학교 세트 추출
        today = datetime.now().strftime("%Y-%m-%d")
        if self.monthly_collections:
            today_set = {
                str(r.get("school_name", ""))
                for r in self.monthly_collections
                if str(r.get("collect_date", "")) == today
            }
        else:
            try:
                now = datetime.now()
                raw = get_monthly_collections(self.user_vendor, now.year, now.month)
                today_set = {
                    str(r.get("school_name", ""))
                    for r in raw
                    if str(r.get("collect_date", "")) == today
                }
            except Exception:
                today_set = set()

        self.today_done_schools = list(today_set)

        # 각 일정에 is_done 플래그 추가 ("true"/"false" 문자열)
        result = []
        for s in schedules:
            s_copy = dict(s)
            slist = [x.strip() for x in s_copy.get("schools", "").split(",") if x.strip()]
            s_copy["is_done"] = "true" if any(sc in today_set for sc in slist) else "false"
            result.append(s_copy)
        self.all_schedules = result

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
        db_del_sched(sched_id, vendor=self.user_vendor)
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
        self.compute_monthly_settlement()

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
        # P1-4: 안전등급 계산
        try:
            rate = float(result.get("rate_str", "0") or "0")
        except (ValueError, TypeError):
            rate = 0.0
        fail = self.daily_check_total_fail
        if rate >= 100.0 and fail == 0:
            self.daily_safety_grade = "S"
        elif rate >= 95.0:
            self.daily_safety_grade = "A"
        elif rate >= 85.0:
            self.daily_safety_grade = "B"
        elif rate >= 70.0:
            self.daily_safety_grade = "C"
        else:
            self.daily_safety_grade = "D"
        self.daily_approve_msg = ""

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
        }, vendor=self.user_vendor)
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
        }, vendor=self.user_vendor)
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
        }, vendor=self.user_vendor)
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

    def approve_safety_checklist(self, chk_id: str):
        """P1-3: 차량점검 승인"""
        from zeroda_reflex.utils.database import update_safety_checklist_status
        ok = update_safety_checklist_status(chk_id, "approved", self.user_vendor, vendor=self.user_vendor)
        if ok:
            self.safety_chk_approve_msg = f"✅ 점검 {chk_id} 승인 완료"
            self.load_safety_data()
        else:
            self.safety_chk_approve_msg = "❌ 승인 처리 실패"

    def reject_safety_checklist(self, chk_id: str):
        """P1-3: 차량점검 반려"""
        from zeroda_reflex.utils.database import update_safety_checklist_status
        ok = update_safety_checklist_status(chk_id, "rejected", self.user_vendor, vendor=self.user_vendor)
        if ok:
            self.safety_chk_approve_msg = f"반려 처리 완료 (ID {chk_id})"
            self.load_safety_data()
        else:
            self.safety_chk_approve_msg = "❌ 반려 처리 실패"

    def approve_all_daily_checks(self):
        """P1-4: 해당 월 일일점검 일괄 승인"""
        from zeroda_reflex.utils.database import approve_all_daily_checks_by_vendor
        ym = self.safety_daily_ym or datetime.now().strftime("%Y-%m")
        count = approve_all_daily_checks_by_vendor(self.user_vendor, ym, self.user_vendor)
        self.daily_approve_msg = f"✅ {count}건 일괄승인 완료 ({ym})"
        self.load_daily_check_summary()

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
            self.compute_driver_compliance()

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
        """업체 정보 저장 (2026-04-10 개선: vendor 체크 + 재로드 + 상세 에러)"""
        from zeroda_reflex.utils.database import save_vendor_info as db_save_vinfo
        self.info_save_msg = ""
        self.info_save_ok = False

        # vendor 빈값 방어
        vendor = (self.user_vendor or "").strip()
        if not vendor:
            self.info_save_msg = "업체(vendor) 정보가 없습니다. 다시 로그인해주세요."
            return

        try:
            data = {
                "vendor":   vendor,
                "biz_name": self.vinfo_biz_name.strip(),
                "rep":      self.vinfo_rep.strip(),
                "biz_no":   self.vinfo_biz_no.strip(),
                "address":  self.vinfo_address.strip(),
                "contact":  self.vinfo_contact.strip(),
                "email":    self.vinfo_email.strip(),
                "account":  self.vinfo_account.strip(),
            }
            print(f"[VENDOR SAVE] vendor={vendor}, data keys={list(data.keys())}")
            ok = db_save_vinfo(data)
            if ok:
                self.info_save_msg = "업체 정보가 저장되었습니다."
                self.info_save_ok = True
                # 저장 후 재로드 — UI 반영 + 본사관리자 연동 보장
                self.load_vendor_info()
            else:
                self.info_save_msg = "저장에 실패했습니다 (DB 함수가 False 반환). 서버 로그를 확인하세요."
        except Exception as e:
            logger.error(f"[save_vendor_info] {e}", exc_info=True)
            self.info_save_msg = "저장 중 오류가 발생했습니다."
            self.info_save_ok = False

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
            # 비밀번호 변경 시 해당 사용자의 모든 자동 로그인 토큰 무효화
            try:
                from zeroda_reflex.utils.database import revoke_user_all_tokens
                revoke_user_all_tokens(self.user_id, reason="password_change")
            except Exception as _e:
                logger.warning("[vendor] 토큰 일괄 폐기 실패: %s", _e)
        else:
            self.settings_msg = "비밀번호 변경에 실패했습니다."

    # ════════════════════════════════════════════
    #  PDF 다운로드 핸들러
    # ════════════════════════════════════════════

    def download_statement_pdf(self):
        """선택 거래처 거래명세서 PDF 다운로드 (명세서발송 탭에서 조회한 거래처 기준)"""
        if not self.stmt_cust_sel or not self.stmt_rows:
            return None
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.database import get_vendor_info
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return None
        try:
            vinfo = get_vendor_info(self.user_vendor) or {}
            biz_info = self._build_biz_info()
            pdf_bytes = build_statement_pdf(
                self.user_vendor, self.stmt_cust_sel, y, m,
                self.stmt_rows, biz_info, vinfo,
                self.stmt_cust_type, self.stmt_fixed_fee,
            )
            if pdf_bytes:
                return rx.download(
                    data=pdf_bytes,
                    filename=f"거래명세서_{self.stmt_cust_sel}_{y}-{str(m).zfill(2)}.pdf",
                )
        except Exception:
            pass
        return None

    # ════════════════════════════════════════════
    #  이메일 발송 핸들러 (Phase 6)
    # ════════════════════════════════════════════

    def set_email_to(self, v: str):
        self.email_to = v
        self.email_msg = ""

    async def send_statement_email(self):
        """거래명세서 PDF를 이메일로 발송 (명세서발송 탭에서 조회한 거래처 기준)"""
        import logging
        import traceback
        from zeroda_reflex.utils.pdf_export import build_statement_pdf
        from zeroda_reflex.utils.email_service import send_email_with_pdf
        from zeroda_reflex.utils.database import get_vendor_info
        _log = logging.getLogger(__name__)

        if not self.email_to or "@" not in self.email_to:
            self.email_msg = "유효한 이메일 주소를 입력하세요."
            self.email_ok = False
            return
        if not self.stmt_cust_sel or not self.stmt_rows:
            self.email_msg = "명세서발송 탭에서 거래처를 선택하고 [조회]를 먼저 누르세요."
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

        try:
            # [단계1] PDF 생성
            self.email_msg = "PDF 생성 중..."
            yield
            vendor = self.user_vendor
            vendor_info = get_vendor_info(vendor) or {}
            biz_info = self._build_biz_info()
            pdf_bytes = build_statement_pdf(
                vendor, self.stmt_cust_sel, y, m,
                self.stmt_rows, biz_info, vendor_info,
                self.stmt_cust_type, self.stmt_fixed_fee,
            )
            if not pdf_bytes:
                self.email_msg = "❌ [PDF생성] reportlab 미설치 또는 pdf_generator 오류 — 서버 로그 확인"
                self.email_ok = False
                self.email_sending = False
                _log.error("send_statement_email: build_statement_pdf returned None")
                return

            # [단계2] 이메일 발송
            self.email_msg = "이메일 발송 중..."
            yield
            filename = f"거래명세서_{self.stmt_cust_sel}_{y}-{str(m).zfill(2)}.pdf"
            subject = self.stmt_email_subject or f"[{vendor}] {y}년 {m}월 거래명세서 — {self.stmt_cust_sel}"
            body = self.stmt_email_body or (
                f"{self.stmt_cust_sel} 담당자님께,\n\n"
                f"안녕하세요. {vendor} 입니다.\n\n"
                f"{y}년 {m}월 거래명세서를 첨부하여 보내드립니다.\n\n"
                f"확인 부탁드립니다.\n감사합니다.\n\n"
                f"— ZERODA 폐기물데이터플랫폼"
            )
            ok, msg = send_email_with_pdf(self.email_to, subject, body, pdf_bytes, filename)
            self.email_ok = ok
            self.email_msg = f"✅ {msg}" if ok else f"❌ [SMTP] {msg}"
        except Exception as e:
            self.email_ok = False
            short = str(e).split("\n")[0][:80]
            self.email_msg = f"❌ [예외] {short}"
            _log.exception("send_statement_email 예외:\n%s", traceback.format_exc())
        finally:
            self.email_sending = False

    # ════════════════════════════════════════════
    #  SMS 발송 핸들러 (Phase 8)
    # ════════════════════════════════════════════

    def set_sms_to(self, v: str):
        self.sms_to = v
        self.sms_msg = ""

    async def send_statement_sms(self):
        """거래명세서 요약을 SMS로 발송 (명세서발송 탭에서 조회한 거래처 기준)"""
        from zeroda_reflex.utils.sms_service import (
            send_statement_sms as _send_sms,
            build_summary_sms_text,
        )
        from zeroda_reflex.utils.database import get_vendor_info

        if not self.sms_to or len(self.sms_to.replace("-", "")) < 10:
            self.sms_msg = "유효한 전화번호를 입력하세요."
            self.sms_ok = False
            return
        if not self.stmt_cust_sel or not self.stmt_rows:
            self.sms_msg = "명세서발송 탭에서 거래처를 선택하고 [조회]를 먼저 누르세요."
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

        try:
            vendor = self.user_vendor
            vendor_info = get_vendor_info(vendor) or {}
            contact = vendor_info.get("contact", "")

            text = build_summary_sms_text(
                vendor_name=vendor,
                school=self.stmt_cust_sel,
                year=y,
                month=m,
                total_weight=float(self.stmt_total_weight or 0),
                total_amount=float(self.stmt_total_amount or 0),
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
        except Exception as e:
            logger.error(f"[send_sms] {e}", exc_info=True)
            self.sms_ok = False
            self.sms_msg = "문자 발송에 실패했습니다."
        finally:
            self.sms_sending = False

    # ════════════════════════════════════════════
    #  수거데이터 편집/삭제 (P2 섹션2)
    # ════════════════════════════════════════════

    def set_edit_col_id(self, v: str):
        self.edit_col_id = v

    def set_edit_col_weight(self, v: str):
        self.edit_col_weight = v

    def set_edit_col_memo(self, v: str):
        self.edit_col_memo = v

    def open_col_edit(self, row: dict):
        """수거 행 편집 모드 진입 — 폼에 기존 값 세팅"""
        self.edit_col_id = str(row.get("id", ""))
        self.edit_col_weight = str(row.get("weight", ""))
        self.edit_col_memo = str(row.get("memo", "") or "")
        self.edit_col_msg = ""

    def update_collection_record(self):
        """수거량/메모 수정"""
        if not self.edit_col_id:
            self.edit_col_msg = "❌ 수정할 항목을 선택하세요."
            return
        try:
            from zeroda_reflex.utils.database import update_collection_row
            ok = update_collection_row(
                row_id=int(self.edit_col_id),
                weight=float(self.edit_col_weight or 0),
                unit_price=0,
                memo=self.edit_col_memo,
                vendor=self.user_vendor,
            )
            self.edit_col_msg = "✅ 수정 완료" if ok else "❌ 수정 실패"
            if ok:
                self.edit_col_id = ""
                self.edit_col_weight = ""
                self.edit_col_memo = ""
                self.load_dashboard_data()
        except Exception as e:
            logger.error(f"[edit_collection] {e}", exc_info=True)
            self.edit_col_msg = "❌ 수정 중 오류가 발생했습니다."

    def delete_collection_record(self, row_id: str):
        """수거 데이터 삭제"""
        try:
            from zeroda_reflex.utils.database import delete_collection
            ok = delete_collection(int(row_id), vendor=self.user_vendor)
            self.edit_col_msg = "✅ 삭제 완료" if ok else "❌ 삭제 실패"
            if ok:
                self.load_dashboard_data()
        except Exception as e:
            logger.error(f"[delete_collection] {e}", exc_info=True)
            self.edit_col_msg = "❌ 삭제 중 오류가 발생했습니다."

    # ════════════════════════════════════════════
    #  월말정산 상세화 (P2 섹션6)
    # ════════════════════════════════════════════

    def compute_monthly_settlement(self):
        """settlement_data 기반 월말정산 상세 계산 — 세금분류 레이블 추가"""
        tax_labels = {
            'tax_free':      '면세',
            'fixed_fee':     '월정액',
            'fixed_fee_vat': '월정액+VAT',
            'vat_10':        'VAT10%',
        }
        detail = []
        for r in self.settlement_data:
            cust_type = r.get("cust_type", "")
            tax_type = self._get_tax_type(cust_type)
            detail.append({
                "name":      r.get("name", ""),
                "cust_type": cust_type,
                "tax_label": tax_labels.get(tax_type, ""),
                "weight":    r.get("weight", "0"),
                "count":     r.get("count", "0"),
                "supply":    r.get("supply", "0"),
                "vat":       r.get("vat", "0"),
                "total":     r.get("total", "0"),
            })
        self.monthly_settlement_detail = detail

    # ════════════════════════════════════════════
    #  기사별 이행률 (P2 섹션7)
    # ════════════════════════════════════════════

    def compute_driver_compliance(self):
        """safety_daily_rows에서 기사별 이행률 집계"""
        REQUIRED_CATS = 4
        agg: dict = {}
        for r in self.safety_daily_rows:
            drv = str(r.get("driver", "") or "기타")
            try:
                ok_c = int(r.get("total_ok", 0) or 0)
                fail_c = int(r.get("total_fail", 0) or 0)
            except (ValueError, TypeError):
                ok_c, fail_c = 0, 0
            total_c = ok_c + fail_c
            rate = round(ok_c / total_c * 100, 1) if total_c > 0 else 0.0
            if drv not in agg:
                agg[drv] = {"check_days": 0, "rate_sum": 0.0, "total_fail": 0}
            agg[drv]["check_days"] += 1
            agg[drv]["rate_sum"] += rate
            agg[drv]["total_fail"] += fail_c

        result = []
        for drv, d in sorted(agg.items()):
            days = d["check_days"]
            avg_rate = round(d["rate_sum"] / days, 1) if days > 0 else 0.0
            result.append({
                "driver":      drv,
                "check_days":  str(days),
                "avg_rate":    str(avg_rate),
                "total_fail":  str(d["total_fail"]),
            })
        self.daily_driver_compliance = result

    # ════════════════════════════════════════════
    #  현장사진 (P2 섹션1)
    # ════════════════════════════════════════════

    PHOTO_TYPE_MAP: dict = {
        "전체":    None,
        "수거증빙":  "collection",
        "계근표":   "processing",
        "차량장비":  "vehicle",
        "사고이슈":  "accident",
    }

    def set_photo_type_filter(self, v: str):
        self.photo_type_filter = v

    def set_photo_date_from(self, v: str):
        self.photo_date_from = v

    def set_photo_date_to(self, v: str):
        self.photo_date_to = v

    def load_photos(self):
        """현장사진 조회 — photo_records 테이블 없으면 빈 리스트 반환"""
        from zeroda_reflex.utils.database import get_db
        try:
            conn = get_db()
            photo_type_val = self.PHOTO_TYPE_MAP.get(self.photo_type_filter)
            if photo_type_val:
                rows = conn.execute(
                    "SELECT * FROM photo_records WHERE vendor=? AND photo_type=? "
                    "ORDER BY created_at DESC LIMIT 200",
                    (self.user_vendor, photo_type_val),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM photo_records WHERE vendor=? "
                    "ORDER BY created_at DESC LIMIT 200",
                    (self.user_vendor,),
                ).fetchall()
            conn.close()
            raw = [dict(r) for r in rows]
            # Python 레벨 날짜 필터
            df = self.photo_date_from
            dt = self.photo_date_to
            if df or dt:
                filtered = []
                for r in raw:
                    d = str(r.get("created_at", "") or "")[:10]
                    if df and d < df:
                        continue
                    if dt and d > dt:
                        continue
                    filtered.append(r)
                raw = filtered
            self.photo_rows = [
                {
                    "id":         str(r.get("id", "") or ""),
                    "school_name": str(r.get("school_name", r.get("location_name", "")) or ""),
                    "photo_type": str(r.get("photo_type", "") or ""),
                    "driver":     str(r.get("driver", "") or ""),
                    "memo":       str(r.get("memo", "") or ""),
                    "created_at": str(r.get("created_at", "") or "")[:10],
                    "photo_url":  str(r.get("photo_url", r.get("file_path", "")) or ""),
                }
                for r in raw
            ]
        except Exception as e:
            logger.warning(f"photo_records 테이블 없음 또는 오류: {e}")
            self.photo_rows = []

    # ════════════════════════════════════════════
    #  Excel 다운로드 핸들러
    # ════════════════════════════════════════════

    # ════════════════════════════════════════════
    #  수거 분석 (P1 보강)
    # ════════════════════════════════════════════

    def set_analytics_subtab(self, sub: str):
        self.analytics_sub_tab = sub

    def set_an_weather_start(self, v: str):
        self.an_weather_start = v

    def set_an_weather_end(self, v: str):
        self.an_weather_end = v

    def load_analytics(self):
        """수거 분석 — 종합현황 데이터 로드"""
        import statistics as _stats
        from zeroda_reflex.utils.database import get_monthly_collections

        try:
            year = int(self.selected_year)
            month = int(self.selected_month)
        except Exception:
            self.an_load_msg = "❌ 연/월 선택 오류"
            return

        vendor = self.user_vendor
        try:
            rows = get_monthly_collections(vendor, year, month) or []
        except Exception as e:
            logger.error(f"[load_analysis_data] {e}", exc_info=True)
            self.an_load_msg = "❌ 데이터 로드에 실패했습니다."
            return

        if not rows:
            self.an_total_kg = "0"
            self.an_avg_daily = "0"
            self.an_collection_days = "0"
            self.an_school_count_str = "0"
            self.an_food_kg = "0"
            self.an_recycle_kg = "0"
            self.an_general_kg = "0"
            self.an_top_school = "-"
            self.an_top_school_kg = "0"
            self.an_mom_change = "-"
            self.an_by_item = []
            self.an_by_school = []
            self.an_by_driver = []
            self.an_anomaly_rows = []
            self.an_anomaly_count = 0
            self.an_load_msg = "해당 월의 수거 데이터가 없습니다."
            return

        weights = [float(r.get("weight", 0) or 0) for r in rows]
        total_w = sum(weights)
        self.an_total_kg = f"{total_w:,.1f}"
        dates = sorted(set(r.get("collect_date", "") for r in rows if r.get("collect_date")))
        self.an_collection_days = str(len(dates))
        self.an_avg_daily = f"{(total_w / max(len(dates), 1)):,.1f}"
        schools = sorted(set(r.get("school_name", "") for r in rows if r.get("school_name")))
        self.an_school_count_str = str(len(schools))

        # 품목별
        item_totals: dict = {}
        for r in rows:
            it = r.get("item_type", "음식물") or "음식물"
            item_totals[it] = item_totals.get(it, 0) + float(r.get("weight", 0) or 0)
        self.an_food_kg = f"{item_totals.get('음식물', 0):,.1f}"
        self.an_recycle_kg = f"{item_totals.get('재활용', 0):,.1f}"
        self.an_general_kg = f"{item_totals.get('일반', 0):,.1f}"
        self.an_by_item = [
            {
                "item_type": k,
                "weight": f"{v:,.1f}",
                "ratio": f"{(v / total_w * 100 if total_w > 0 else 0):.1f}",
            }
            for k, v in item_totals.items()
        ]

        # Top 거래처
        school_totals: dict = {}
        for r in rows:
            sn = r.get("school_name", "") or ""
            school_totals[sn] = school_totals.get(sn, 0) + float(r.get("weight", 0) or 0)
        if school_totals:
            top = max(school_totals, key=lambda k: school_totals[k])
            self.an_top_school = top
            self.an_top_school_kg = f"{school_totals[top]:,.1f}"

        # 전월대비
        prev_m = month - 1
        prev_y = year
        if prev_m < 1:
            prev_m = 12
            prev_y -= 1
        try:
            prev_rows = get_monthly_collections(vendor, prev_y, prev_m) or []
            prev_total = sum(float(r.get("weight", 0) or 0) for r in prev_rows)
            if prev_total > 0:
                change = ((total_w - prev_total) / prev_total) * 100
                self.an_mom_change = f"{change:+.1f}%"
            else:
                self.an_mom_change = "-"
        except Exception:
            self.an_mom_change = "-"

        # 이상치 (Z-Score)
        daily_kg: dict = {}
        for r in rows:
            d = r.get("collect_date", "") or ""
            daily_kg[d] = daily_kg.get(d, 0) + float(r.get("weight", 0) or 0)
        anomalies = []
        if len(daily_kg) >= 3:
            values = list(daily_kg.values())
            mean_v = _stats.mean(values)
            try:
                std_v = _stats.stdev(values)
            except _stats.StatisticsError:
                std_v = 0
            for date, kg in sorted(daily_kg.items()):
                z = ((kg - mean_v) / std_v) if std_v > 0 else 0
                if abs(z) > 2.0:
                    anomalies.append({
                        "collect_date": date,
                        "total_kg": f"{kg:,.1f}",
                        "z_score": f"{z:+.2f}",
                    })
        self.an_anomaly_rows = anomalies
        self.an_anomaly_count = len(anomalies)

        # 거래처별 Top 20
        sorted_schools = sorted(school_totals.items(), key=lambda x: x[1], reverse=True)[:20]
        by_school = []
        for sn, tw in sorted_schools:
            food = sum(
                float(r.get("weight", 0) or 0) for r in rows
                if r.get("school_name") == sn and r.get("item_type") == "음식물"
            )
            recy = sum(
                float(r.get("weight", 0) or 0) for r in rows
                if r.get("school_name") == sn and r.get("item_type") == "재활용"
            )
            cnt = sum(1 for r in rows if r.get("school_name") == sn)
            by_school.append({
                "school_name": sn,
                "total_kg": f"{tw:,.1f}",
                "food_kg": f"{food:,.1f}",
                "recycle_kg": f"{recy:,.1f}",
                "count": str(cnt),
            })
        self.an_by_school = by_school

        # 기사별
        driver_data: dict = {}
        for r in rows:
            drv = r.get("driver", "") or "미지정"
            if drv not in driver_data:
                driver_data[drv] = {"kg": 0.0, "count": 0, "schools": set()}
            driver_data[drv]["kg"] += float(r.get("weight", 0) or 0)
            driver_data[drv]["count"] += 1
            driver_data[drv]["schools"].add(r.get("school_name", ""))
        self.an_by_driver = [
            {
                "driver": d,
                "total_kg": f"{v['kg']:,.1f}",
                "count": str(v["count"]),
                "schools": str(len(v["schools"])),
            }
            for d, v in sorted(driver_data.items(), key=lambda x: x[1]["kg"], reverse=True)
        ]

        # 일별/요일별/계절별도 같이 채워넣자
        self.load_analytics_daily()

        self.an_load_msg = f"✅ 분석 완료 ({len(rows)}건)"

    def load_analytics_daily(self):
        """일별/요일별/계절별 분석 (load_analytics에서 자동 호출됨)"""
        from datetime import datetime as _dt
        from zeroda_reflex.utils.database import get_monthly_collections

        try:
            year = int(self.selected_year)
            month = int(self.selected_month)
        except Exception:
            return
        vendor = self.user_vendor
        try:
            rows = get_monthly_collections(vendor, year, month) or []
        except Exception:
            return

        # 일별
        daily: dict = {}
        for r in rows:
            d = r.get("collect_date", "") or ""
            if d not in daily:
                daily[d] = {"food": 0.0, "recycle": 0.0, "general": 0.0}
            it = r.get("item_type", "음식물") or "음식물"
            key = {"음식물": "food", "재활용": "recycle", "일반": "general"}.get(it, "food")
            daily[d][key] += float(r.get("weight", 0) or 0)
        self.an_daily_rows = [
            {
                "date": d,
                "food_kg": f"{v['food']:,.1f}",
                "recycle_kg": f"{v['recycle']:,.1f}",
                "general_kg": f"{v['general']:,.1f}",
                "total": f"{(v['food'] + v['recycle'] + v['general']):,.1f}",
            }
            for d, v in sorted(daily.items())
        ]

        # 요일별
        WD = ["월", "화", "수", "목", "금", "토", "일"]
        wd_data: dict = {d: [] for d in WD}
        for r in rows:
            try:
                date = _dt.strptime(r.get("collect_date", ""), "%Y-%m-%d")
                wd_data[WD[date.weekday()]].append(float(r.get("weight", 0) or 0))
            except Exception:
                continue
        self.an_weekday_rows = [
            {
                "weekday": wd,
                "avg_kg": f"{(sum(vals) / len(vals)):,.1f}" if vals else "0",
                "total_kg": f"{sum(vals):,.1f}",
                "count": str(len(vals)),
            }
            for wd in WD
            for vals in [wd_data[wd]]
            if vals
        ]

        # 계절별
        SEASON = {1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄", 6: "여름",
                  7: "여름", 8: "여름", 9: "가을", 10: "가을", 11: "가을", 12: "겨울"}
        season_data: dict = {}
        for r in rows:
            try:
                m = int(r.get("collect_date", "")[5:7])
                s = SEASON.get(m, "기타")
                if s not in season_data:
                    season_data[s] = {"total": 0.0, "days": set()}
                season_data[s]["total"] += float(r.get("weight", 0) or 0)
                season_data[s]["days"].add(r.get("collect_date", ""))
            except Exception:
                continue
        self.an_season_rows = [
            {
                "season": s,
                "total_kg": f"{v['total']:,.1f}",
                "avg_daily_kg": f"{(v['total'] / max(len(v['days']), 1)):,.1f}",
            }
            for s, v in season_data.items()
        ]

    async def run_weather_analysis(self):
        """기상 상관분석"""
        import statistics as _stats
        from zeroda_reflex.utils.weather_service import fetch_daily_weather
        from zeroda_reflex.utils.database import get_monthly_collections

        if not self.an_weather_start or not self.an_weather_end:
            self.an_weather_msg = "❌ 시작일과 종료일을 입력하세요."
            return

        self.an_weather_running = True
        self.an_weather_msg = "분석 중..."
        yield

        try:
            result = fetch_daily_weather(self.an_weather_start, self.an_weather_end) or {}
            weather = result.get("data", []) if result.get("success") else []
            if not weather:
                self.an_weather_msg = f"❌ {result.get('message', '기상 데이터 없음')}"
                self.an_weather_running = False
                return

            # 기간 내 수거 데이터 (월 경계 가능 → 시작/종료월 합본)
            try:
                sy, sm = int(self.an_weather_start[:4]), int(self.an_weather_start[5:7])
                ey, em = int(self.an_weather_end[:4]), int(self.an_weather_end[5:7])
            except Exception:
                self.an_weather_msg = "❌ 날짜 형식 오류 (YYYY-MM-DD)"
                self.an_weather_running = False
                return

            collected: list = []
            y, m = sy, sm
            while (y, m) <= (ey, em):
                try:
                    collected.extend(get_monthly_collections(self.user_vendor, y, m) or [])
                except Exception:
                    pass
                m += 1
                if m > 12:
                    m = 1
                    y += 1

            daily_kg: dict = {}
            for c in collected:
                d = c.get("collect_date", "") or ""
                if self.an_weather_start <= d <= self.an_weather_end:
                    daily_kg[d] = daily_kg.get(d, 0) + float(c.get("weight", 0) or 0)

            merged = []
            for w in weather:
                dk = w.get("date", "")
                if dk in daily_kg:
                    merged.append({
                        "total_kg": daily_kg[dk],
                        "temp_avg": float(w.get("temp_avg", 0) or 0),
                        "rain": float(w.get("rain", 0) or 0),
                        "humidity": float(w.get("humidity", 0) or 0),
                        "wind": float(w.get("wind", 0) or 0),
                    })

            if len(merged) < 5:
                self.an_weather_msg = f"⚠️ 데이터 부족 ({len(merged)}일, 최소 5일 필요)"
                self.an_weather_running = False
                return

            kgs = [m["total_kg"] for m in merged]

            def pearson(xs, ys):
                n = len(xs)
                if n < 3:
                    return 0
                mx, my = _stats.mean(xs), _stats.mean(ys)
                try:
                    sx, sy_ = _stats.stdev(xs), _stats.stdev(ys)
                except _stats.StatisticsError:
                    return 0
                if sx == 0 or sy_ == 0:
                    return 0
                return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / ((n - 1) * sx * sy_)

            self.an_weather_temp_corr = f"{pearson(kgs, [m['temp_avg'] for m in merged]):.3f}"
            self.an_weather_rain_corr = f"{pearson(kgs, [m['rain'] for m in merged]):.3f}"
            self.an_weather_humidity_corr = f"{pearson(kgs, [m['humidity'] for m in merged]):.3f}"
            self.an_weather_wind_corr = f"{pearson(kgs, [m['wind'] for m in merged]):.3f}"

            rainy = [m["total_kg"] for m in merged if m["rain"] > 0.5]
            clear = [m["total_kg"] for m in merged if m["rain"] <= 0.5]
            r_avg = _stats.mean(rainy) if rainy else 0
            c_avg = _stats.mean(clear) if clear else 0
            self.an_weather_rainy_avg = f"{r_avg:,.1f}"
            self.an_weather_clear_avg = f"{c_avg:,.1f}"
            diff = ((r_avg - c_avg) / c_avg * 100) if c_avg > 0 else 0
            self.an_weather_diff_pct = f"{diff:+.1f}"

            bins = [
                (-100, 0, "영하"),
                (0, 10, "0~10°C"),
                (10, 20, "10~20°C"),
                (20, 30, "20~30°C"),
                (30, 50, "30°C+"),
            ]
            temp_bins = []
            for lo, hi, label in bins:
                subset = [m["total_kg"] for m in merged if lo <= m["temp_avg"] < hi]
                if subset:
                    temp_bins.append({
                        "temp_range": label,
                        "avg_kg": f"{_stats.mean(subset):,.1f}",
                        "count": str(len(subset)),
                    })
            self.an_weather_temp_bins = temp_bins
            self.an_weather_msg = f"✅ {len(merged)}일 분석 완료"
        except Exception as e:
            logger.error(f"[load_weather_analysis] {e}", exc_info=True)
            self.an_weather_msg = "❌ 날씨 데이터 조회에 실패했습니다."
        finally:
            self.an_weather_running = False

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
    #  학사일정 동기화
    # ════════════════════════════════════════════

    @rx.event(background=True)
    async def sync_my_school_schedules(self):
        """소속 업체 학교 학사일정 NEIS 동기화 (백그라운드)."""
        async with self:
            if self.sched_sync_running:
                return
            self.sched_sync_running = True
            self.sched_sync_msg = "학사일정 동기화 중..."
        try:
            from zeroda_reflex.utils.neis_sync_service import sync_all_schools
            vendor = self.user_vendor
            stats = sync_all_schools(vendor=vendor)
            async with self:
                self.sched_sync_msg = (
                    f"완료: {stats['success']}/{stats['total_schools']}교, "
                    f"일정 {stats['events']}건"
                )
        except Exception as e:
            logger.error(f"[sync_my_school_schedules] {e}", exc_info=True)
            async with self:
                self.sched_sync_msg = "일정 동기화에 실패했습니다."
        finally:
            async with self:
                self.sched_sync_running = False

    # ════════════════════════════════════════════
    #  직인 관리 (업체관리자 본인 업체)
    # ════════════════════════════════════════════

    stamp_upload_status: str = ""
    stamp_upload_loading: bool = False
    stamp_current_path: str = ""

    def load_current_stamp(self):
        """본인 업체의 현재 직인 경로 조회."""
        from zeroda_reflex.utils.database import get_vendor_info
        vendor = (self.user_vendor or "").strip()
        if not vendor:
            self.stamp_current_path = ""
            return
        info = get_vendor_info(vendor)
        self.stamp_current_path = info.get("stamp_path", "")

    async def handle_stamp_upload(self, files: list[rx.UploadFile]):
        """업체관리자 직인 업로드 (본인 업체만).

        2026-04-10 수정:
          - f.filename → getattr 안전 접근 (Reflex UploadFile 호환)
          - set_vendor_stamp 행 없을 때 INSERT 보장 (DB 함수 수정됨)
          - PIL 검증 후 파일 재사용 안전 처리
          - 업로드 성공 후 load_current_stamp 재호출
        """
        import os
        import uuid
        from zeroda_reflex.utils.database import set_vendor_stamp

        STAMP_DIR = "/opt/zeroda-platform/storage/stamps"
        MAX_SIZE = 2 * 1024 * 1024
        ALLOWED_EXT = {".png", ".jpg", ".jpeg"}

        vendor = (self.user_vendor or "").strip()
        if not vendor:
            self.stamp_upload_status = "업체 정보를 불러올 수 없습니다. 다시 로그인하세요."
            return
        if not files:
            self.stamp_upload_status = "파일이 없습니다. 이미지를 선택해주세요."
            return

        self.stamp_upload_loading = True
        self.stamp_upload_status = ""

        try:
            f = files[0]
            raw = await f.read()
            if len(raw) > MAX_SIZE:
                self.stamp_upload_status = "파일 크기 2MB 초과."
                self.stamp_upload_loading = False
                return

            # 파일명 안전 추출 — Reflex UploadFile은 .name 사용
            filename = getattr(f, "name", None) or getattr(f, "filename", "stamp.png")
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ALLOWED_EXT:
                self.stamp_upload_status = "PNG/JPG 만 가능합니다."
                self.stamp_upload_loading = False
                return

            os.makedirs(STAMP_DIR, exist_ok=True)
            safe_slug = "".join(c for c in vendor if c.isalnum() or c in "-_")[:20] or "vendor"
            fname = str(safe_slug) + "_" + uuid.uuid4().hex[:8] + ext
            target = os.path.join(STAMP_DIR, fname)

            with open(target, "wb") as w:
                w.write(raw)

            # PIL 이미지 검증 (선택적 — PIL 미설치 환경 대비)
            try:
                from PIL import Image
                img = Image.open(target)
                img.verify()
                img.close()
            except ImportError:
                pass  # PIL 미설치 — 검증 건너뜀
            except Exception:
                try:
                    os.remove(target)
                except Exception:
                    pass
                self.stamp_upload_status = "유효한 이미지가 아닙니다."
                self.stamp_upload_loading = False
                return

            updated_by = self.user_name or self.user_id or "vendor"
            ok = set_vendor_stamp(vendor, target, updated_by)
            if ok:
                self.stamp_upload_status = "직인 등록 완료"
                self.stamp_current_path = target
                # 재로드하여 UI 반영 + 본사관리자 연동 보장
                self.load_current_stamp()
            else:
                self.stamp_upload_status = "DB 저장 실패. 서버 로그를 확인하세요."
        except Exception as e:
            logger.error(f"[upload_stamp_image] {e}", exc_info=True)
            self.stamp_upload_status = "업로드 중 오류가 발생했습니다."
        finally:
            self.stamp_upload_loading = False

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
        self.load_current_stamp()
