# zeroda_reflex/state/driver_state.py
# 기사 대시보드 상태 관리
import reflex as rx
import logging
from datetime import datetime, date
from zeroda_reflex.state.auth_state import AuthState

logger = logging.getLogger(__name__)
from zeroda_reflex.utils.weather_service import fetch_today_weather_alert
from zeroda_reflex.utils.database import (
    get_daily_safety_checks, save_daily_safety_check,
    save_daily_safety_checks_transaction,
    get_schools_by_vendor, db_get, db_insert,
    get_today_collections, save_collection,
    get_driver_checkout_log, save_driver_checkout,
    delete_collection,
    get_driver_schedule_schools,
    get_today_processing, save_processing_confirm,
    save_photo_record, get_photo_records_today,
    save_customer_gps,
    get_customers_with_gps, haversine, get_school_icons,
)
import os

# ── 안전점검 체크리스트 (기존 settings.py에서 가져옴) ──
SAFETY_CHECKLIST = {
    "1인작업안전": {
        "label": "1인 작업 안전", "icon": "🚨",
        "items": [
            {"id": "solo_01", "text": "작업 시작 전 관리감독자에게 작업 일정 및 위치를 사전 통보하였는가?"},
            {"id": "solo_02", "text": "수거 앱(ZERODA) 로그인 및 데이터 연결 상태를 확인하였는가?"},
            {"id": "solo_03", "text": "각 거래처 수거 완료 시 수거량을 즉시 입력하였는가?"},
            {"id": "solo_04", "text": "작업 현장 반경 내 낙하·협착 위험 구역을 확인하고 안전 구역을 설정하였는가?"},
            {"id": "solo_05", "text": "작업 종료 후 관리감독자에게 작업 완료를 보고하였는가?"},
        ],
    },
    "보호구위생": {
        "label": "보호구 및 위생", "icon": "🦺",
        "items": [
            {"id": "ppe_01", "text": "안전화(안전 인증품) 착용 상태를 확인하였는가?"},
            {"id": "ppe_02", "text": "방수·방오 처리된 장갑 착용 상태를 확인하였는가?"},
            {"id": "ppe_03", "text": "방진 마스크(KF94 이상) 착용 상태를 확인하였는가?"},
            {"id": "ppe_04", "text": "방수 앞치마 또는 방오 작업복 착용 상태를 확인하였는가?"},
            {"id": "ppe_05", "text": "안전모 착용 상태를 확인하였는가?"},
            {"id": "ppe_06", "text": "작업 후 손 씻기 및 위생 처리를 확인하였는가?"},
            {"id": "ppe_07", "text": "기타 필요한 개인보호구 지참 여부를 확인하였는가?"},
        ],
    },
    "차량장비점검": {
        "label": "차량 및 장비 점검", "icon": "🚛",
        "items": [
            {"id": "veh_01", "text": "차량 외관(타이어, 제동장치, 오일류) 이상 여부를 점검하였는가?"},
            {"id": "veh_02", "text": "리프트 유압 호스 및 연결부위 누유·균열 여부를 점검하였는가?"},
            {"id": "veh_03", "text": "리프트 비상정지 스위치 정상 작동 여부를 확인하였는가?"},
            {"id": "veh_04", "text": "리프트 승강 구간 내 이물질 및 장애물을 제거하였는가?"},
            {"id": "veh_05", "text": "리프트 체인·와이어로프의 마모·손상 여부를 점검하였는가?"},
            {"id": "veh_06", "text": "적재함 도어 잠금 장치 정상 작동 여부를 확인하였는가?"},
            {"id": "veh_07", "text": "차량 경보음 및 작업 표시등 정상 작동 여부를 확인하였는가?"},
            {"id": "veh_08", "text": "차량이 평탄한 지면에 고정되어 있는가?"},
        ],
    },
    "중량물상하차": {
        "label": "중량물 상하차", "icon": "📦",
        "items": [
            {"id": "load_01", "text": "수거통 바퀴(캐스터) 상태 및 잠금장치를 점검하였는가?"},
            {"id": "load_02", "text": "수거통 리프트 걸이 체결 시 후크·고리 정위치를 확인하였는가?"},
            {"id": "load_03", "text": "리프트 작동 중 수거통 하부에 신체가 위치하지 않도록 조치하였는가?"},
            {"id": "load_04", "text": "리프트 작동은 수거통이 완전히 고정된 후 실시하였는가?"},
            {"id": "load_05", "text": "중량물 이동 시 올바른 자세로 작업하였는가?"},
            {"id": "load_06", "text": "미끄러운 바닥 조건에서는 안전 조치를 취하였는가?"},
            {"id": "load_07", "text": "수거통 적재 후 적재함 내부 고정 이상 여부를 확인하였는가?"},
        ],
    },
}


class DriverState(AuthState):
    """기사 대시보드 상태"""

    # ── 날씨 ──
    weather_available: bool = False
    weather_icon: str = "🌐"
    weather_summary: str = ""
    weather_alerts: list[str] = []
    weather_level: str = "normal"   # normal / caution / warning
    weather_source: str = ""

    # ── 안전점검 ──
    safety_done_today: bool = False
    safety_saved_time: str = ""
    safety_panel_collapsed: bool = False   # 완료 후 자동 접기
    checked_items: dict[str, bool] = {}
    fail_memo: str = ""
    safety_save_msg: str = ""

    # ── 수거일정 ──
    schedule_date: str = ""          # 선택된 날짜 (YYYY-MM-DD)
    schedule_schools: list[dict] = []  # 배정 학교 목록
    schedule_loading: bool = False

    # ── 수거 ──
    assigned_schools: list[str] = []
    selected_school: str = ""
    collection_weight: str = ""
    collection_item_type: str = "음식물"
    today_collections: list[dict] = []
    collection_rows: list[dict] = []   # 다중행: [{"date":"YYYY-MM-DD","item":"음식물","weight":""}]
    collection_unit_price: str = ""
    collection_time: str = ""
    collection_memo: str = ""
    collection_save_msg: str = ""

    # ── GPS ──
    gps_msg: str = ""

    # ── 거래처 아이콘 맵 ──
    school_icon_map: dict[str, str] = {}

    # ── 음성입력 ──
    voice_active: bool = False
    voice_result: str = ""

    # ── 스쿨존 ──
    schoolzone_enabled: bool = False

    # ── 사진 ──
    photo_upload_msg: str = ""
    today_photos: list[dict] = []

    # ── 계근표(처리확인) ──
    proc_weight: str = ""
    proc_location: str = ""
    proc_memo: str = ""
    proc_save_msg: str = ""
    today_processing: list[dict] = []

    # ── 퇴근 ──
    is_checked_out: bool = False
    checkout_time: str = ""

    @rx.var
    def today_str(self) -> str:
        return date.today().strftime("%Y-%m-%d")

    @rx.var
    def today_display(self) -> str:
        now = datetime.now()
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        wd = weekdays[now.weekday()]
        return now.strftime(f"%Y.%m.%d ({wd})")

    @rx.var
    def total_items(self) -> int:
        return sum(len(c["items"]) for c in SAFETY_CHECKLIST.values())

    @rx.var
    def checked_count(self) -> int:
        return sum(1 for v in self.checked_items.values() if v)

    @rx.var
    def safety_progress(self) -> int:
        """0~100 정수 퍼센트"""
        total = self.total_items
        if total == 0:
            return 0
        return int(self.checked_count * 100 / total)

    @rx.var
    def all_checked(self) -> bool:
        return self.checked_count == self.total_items and self.total_items > 0

    def on_driver_load(self):
        """기사 페이지 로드 시"""
        if not self.is_authenticated:
            return rx.redirect("/")
        self._load_weather()
        self._load_safety_status()
        self._load_schools()
        self._load_today_collections()
        self._load_today_photos()
        self._load_today_processing()
        self._load_checkout_status()
        # 수거일정 초기 로드 (오늘 날짜)
        if not self.schedule_date:
            self.schedule_date = self.today_str
        self._load_schedule()

    def _load_weather(self):
        """기상청 API로 오늘 날씨 로드"""
        try:
            result = fetch_today_weather_alert()
            self.weather_available = result.get("available", False)
            self.weather_icon = result.get("icon", "🌐")
            self.weather_summary = result.get("summary", "")
            self.weather_alerts = result.get("alerts", [])
            self.weather_level = result.get("level", "normal")
            self.weather_source = result.get("source", "")
        except Exception as e:
            logger.warning(f"날씨 로드 실패: {e}")
            self.weather_available = False

    def _load_safety_status(self):
        """오늘 안전점검 완료 여부 확인"""
        checks = get_daily_safety_checks(
            vendor=self.user_vendor,
            driver=self.user_name,
            check_date=self.today_str,
        )
        saved_cats = {r.get("category", "") for r in checks}
        required_cats = set(SAFETY_CHECKLIST.keys())
        self.safety_done_today = required_cats <= saved_cats
        if self.safety_done_today and checks:
            ct = str(checks[0].get("created_at", ""))
            self.safety_saved_time = ct[11:16] if len(ct) >= 16 else ""
            self.safety_panel_collapsed = True   # 오늘 이미 완료 → 자동 접기

    # ── 수거일정 핸들러 ──

    def _load_schedule(self):
        """선택 날짜의 수거일정 로드"""
        self.schedule_schools = get_driver_schedule_schools(
            vendor=self.user_vendor,
            driver=self.user_name,
            sel_date=self.schedule_date,
        )

    def set_schedule_date(self, value: str):
        """일정 날짜 변경"""
        self.schedule_date = value
        self._load_schedule()

    def set_schedule_today(self):
        """오늘 날짜로 리셋"""
        self.schedule_date = self.today_str
        self._load_schedule()

    @rx.var
    def schedule_date_display(self) -> str:
        """선택 날짜 표시용 (예: 2026-04-06 (월)요일)"""
        try:
            d = date.fromisoformat(self.schedule_date)
            wds = ["월", "화", "수", "목", "금", "토", "일"]
            return f"{self.schedule_date} ({wds[d.weekday()]}요일)"
        except Exception:
            return self.schedule_date

    @rx.var
    def schedule_total(self) -> int:
        """일정 학교 수"""
        return len(self.schedule_schools)

    @rx.var
    def schedule_done_schools(self) -> list[str]:
        """일정 중 수거 완료된 학교"""
        done = set(self.collected_schools)
        return [s["school_name"] for s in self.schedule_schools if s["school_name"] in done]

    @rx.var
    def schedule_remaining_schools(self) -> list[str]:
        """일정 중 미수거 학교"""
        done = set(self.collected_schools)
        return [s["school_name"] for s in self.schedule_schools if s["school_name"] not in done]

    def _load_schools(self):
        """배정된 학교 목록 + 아이콘 맵 로드"""
        self.assigned_schools = get_schools_by_vendor(self.user_vendor)
        self.school_icon_map = get_school_icons(self.user_vendor)
        if self.assigned_schools and not self.selected_school:
            self.selected_school = self.assigned_schools[0]

    def _load_today_collections(self):
        """오늘 수거 기록 로드"""
        self.today_collections = get_today_collections(
            vendor=self.user_vendor,
            driver=self.user_name,
            collect_date=self.today_str,
        )

    def _load_checkout_status(self):
        """퇴근 상태 로드"""
        logs = get_driver_checkout_log(
            vendor=self.user_vendor,
            driver=self.user_name,
            checkout_date=self.today_str,
        )
        if logs:
            self.is_checked_out = True
            self.checkout_time = logs[0].get("checkout_time", "")

    def toggle_check(self, item_id: str):
        """체크박스 토글"""
        current = self.checked_items.get(item_id, False)
        self.checked_items[item_id] = not current

    def check_all(self):
        """전체 양호"""
        for cat in SAFETY_CHECKLIST.values():
            for item in cat["items"]:
                self.checked_items[item["id"]] = True

    def uncheck_all(self):
        """전체 해제"""
        self.checked_items = {}

    def check_category(self, cat_key: str):
        """카테고리 전체 체크"""
        cat = SAFETY_CHECKLIST.get(cat_key)
        if cat:
            for item in cat["items"]:
                self.checked_items[item["id"]] = True

    def set_fail_memo(self, value: str):
        """불량 메모 입력"""
        self.fail_memo = value

    def save_safety_check(self):
        """안전점검 결과 저장 (4개 카테고리를 트랜잭션으로 처리)"""
        categories_data = []

        # 4개 카테고리 데이터 준비
        for cat_key, cat_info in SAFETY_CHECKLIST.items():
            items_dict = {}
            for item in cat_info["items"]:
                items_dict[item["id"]] = "양호" if self.checked_items.get(item["id"]) else "미점검"
            categories_data.append({
                "category": cat_key,
                "check_items": items_dict,
            })

        # 트랜잭션으로 한 번에 저장 (중간 실패 시 ROLLBACK)
        ok = save_daily_safety_checks_transaction(
            vendor=self.user_vendor,
            driver=self.user_name,
            check_date=self.today_str,
            categories_data=categories_data,
            fail_memo=self.fail_memo,
        )

        if ok:
            self.safety_done_today = True
            self.safety_saved_time = datetime.now().strftime("%H:%M")
            self.safety_panel_collapsed = True   # 저장 직후 자동 접기
            self.safety_save_msg = "저장 완료"
        else:
            self.safety_save_msg = "저장 중 오류가 발생했습니다."

    def toggle_safety_panel(self):
        """안전점검 패널 접기/펼치기"""
        self.safety_panel_collapsed = not self.safety_panel_collapsed

    # ── 수거입력 핸들러 ──

    def set_selected_school(self, value: str):
        """거래처 선택 → 다중행 초기화"""
        self.selected_school = value
        self.collection_rows = [
            {"date": self.today_str, "item": self.collection_item_type, "weight": ""}
        ]

    def set_collection_weight(self, value: str):
        """수거량 입력 (단일행 호환)"""
        self.collection_weight = value

    # ── 다중행 핸들러 ──

    def add_collection_row(self):
        """행 추가"""
        from datetime import timedelta
        existing_dates = {r["date"] for r in self.collection_rows}
        new_date = self.today_str
        for d in range(1, 31):
            candidate = (date.today() - timedelta(days=d)).strftime("%Y-%m-%d")
            if candidate not in existing_dates:
                new_date = candidate
                break
        self.collection_rows = self.collection_rows + [
            {"date": new_date, "item": "음식물", "weight": ""}
        ]

    def remove_collection_row(self, idx: int):
        """행 삭제"""
        if len(self.collection_rows) > 1:
            rows = list(self.collection_rows)
            rows.pop(idx)
            self.collection_rows = rows

    def set_row_date(self, idx_val: list):
        """행 날짜 변경 [idx, value]"""
        idx, val = int(idx_val[0]), str(idx_val[1])
        rows = list(self.collection_rows)
        if 0 <= idx < len(rows):
            rows[idx] = {**rows[idx], "date": val}
            self.collection_rows = rows

    def set_row_item(self, idx_val: list):
        """행 품목 변경 [idx, value]"""
        idx, val = int(idx_val[0]), str(idx_val[1])
        rows = list(self.collection_rows)
        if 0 <= idx < len(rows):
            rows[idx] = {**rows[idx], "item": val}
            self.collection_rows = rows

    def set_row_weight(self, idx_val: list):
        """행 수거량 변경 [idx, value]"""
        idx, val = int(idx_val[0]), str(idx_val[1])
        rows = list(self.collection_rows)
        if 0 <= idx < len(rows):
            rows[idx] = {**rows[idx], "weight": val}
            self.collection_rows = rows

    def set_collection_item_type(self, value: str):
        """품목 선택"""
        self.collection_item_type = value

    def set_collection_unit_price(self, value: str):
        """단가 입력"""
        self.collection_unit_price = value

    def set_collection_time(self, value: str):
        """수거시간 입력"""
        self.collection_time = value

    def set_collection_memo(self, value: str):
        """메모 입력"""
        self.collection_memo = value

    @rx.var
    def estimated_amount(self) -> str:
        """예상금액 자동계산"""
        try:
            w = float(self.collection_weight)
            p = float(self.collection_unit_price)
            return f"{int(w * p):,}원"
        except (ValueError, TypeError):
            return "-"

    @rx.var
    def today_total_weight(self) -> float:
        """오늘 총 수거량"""
        total = 0.0
        for c in self.today_collections:
            try:
                total += float(c.get("weight", 0))
            except (ValueError, TypeError):
                pass
        return round(total, 1)

    @rx.var
    def today_collection_count(self) -> int:
        """오늘 수거 건수"""
        return len(self.today_collections)

    def _validate_collection(self) -> float:
        """수거 입력 공통 검증. 유효하면 weight 반환, 실패 시 -1"""
        if not self.selected_school:
            self.collection_save_msg = "거래처를 선택하세요."
            return -1
        try:
            w = float(self.collection_weight)
        except (ValueError, TypeError):
            self.collection_save_msg = "수거량을 올바르게 입력하세요."
            return -1
        if w <= 0:
            self.collection_save_msg = "수거량은 0보다 커야 합니다."
            return -1
        if w > 9999:
            self.collection_save_msg = "수거량이 너무 큽니다. (최대 9,999kg)"
            return -1
        return w

    def _do_save_collection(self, status: str):
        """수거 데이터 저장 (draft / submitted) — 다중행 지원"""
        self.collection_save_msg = ""
        if not self.selected_school:
            self.collection_save_msg = "거래처를 선택하세요."
            return
        # 단가 파싱
        try:
            up = float(self.collection_unit_price) if self.collection_unit_price else 0
        except (ValueError, TypeError):
            up = 0
        ct = self.collection_time if self.collection_time else datetime.now().strftime("%H:%M")
        label = "임시저장" if status == "draft" else "본사전송"

        # 다중행이 있으면 다중행 저장, 없으면 단일행
        rows_to_save = self.collection_rows if self.collection_rows else []
        if not rows_to_save:
            # 단일행 폴백
            w = self._validate_collection()
            if w < 0:
                return
            rows_to_save = [{"date": self.today_str, "item": self.collection_item_type, "weight": str(w)}]

        # ── 학교 타입 확인 (토요일→금요일 변환용) ──
        cust_rows = db_get("customer_info", {"vendor": self.user_vendor})
        cust_type_map = {}
        for cr in cust_rows:
            cust_type_map[cr.get("name", "")] = cr.get("cust_type", cr.get("\uad6c\ubd84", ""))

        sat_converted = False
        saved = 0
        for row in rows_to_save:
            try:
                w = float(row.get("weight", 0))
            except (ValueError, TypeError):
                continue
            if w <= 0:
                continue
            rd = str(row.get("date", self.today_str))
            ri = str(row.get("item", "음식물"))

            # ── 토요일→금요일 자동 변환 (학교만) ──
            try:
                from datetime import timedelta as _td
                rd_date = date.fromisoformat(rd)
                ct = cust_type_map.get(self.selected_school, "")
                if rd_date.weekday() == 5 and ct in ("학교", "school", ""):
                    rd_date = rd_date - _td(days=1)
                    rd = rd_date.strftime("%Y-%m-%d")
                    sat_converted = True
            except Exception:
                pass
            ok = save_collection(
                vendor=self.user_vendor,
                driver=self.user_name,
                school_name=self.selected_school,
                collect_date=rd,
                item_type=ri,
                weight=w,
                status=status,
                unit_price=up,
                memo=self.collection_memo,
                collect_time=ct,
            )
            if ok:
                saved += 1

        if saved > 0:
            msg = f"✅ {self.selected_school} {saved}건 {label} 완료"
            if sat_converted:
                msg += " (토요일→금요일 자동변환)"
            self.collection_save_msg = msg
            self.collection_weight = ""
            self.collection_unit_price = ""
            self.collection_memo = ""
            self.collection_rows = [
                {"date": self.today_str, "item": self.collection_item_type, "weight": ""}
            ]
            self._load_today_collections()
        else:
            self.collection_save_msg = "저장 중 오류가 발생했습니다."

    def save_collection_entry(self):
        """수거완료·본사전송 (submitted)"""
        self._do_save_collection("submitted")

    def save_collection_draft(self):
        """임시저장 (draft)"""
        self._do_save_collection("draft")

    # ── 수거 완료/미완료 거래처 추적 ──

    @rx.var
    def collected_schools(self) -> list[str]:
        """오늘 수거 완료된 거래처 목록 (중복 제거)"""
        return list({c.get("school_name", "") for c in self.today_collections})

    @rx.var
    def remaining_schools(self) -> list[str]:
        """아직 수거하지 않은 거래처 목록"""
        done = set(self.collected_schools)
        return [s for s in self.assigned_schools if s not in done]

    @rx.var
    def collection_progress_text(self) -> str:
        """수거 진행률 텍스트 (예: 3/5 거래처 완료)"""
        done = len(self.collected_schools)
        total = len(self.assigned_schools)
        return f"{done}/{total} 거래처 완료"

    @rx.var
    def collection_progress_pct(self) -> int:
        """수거 진행률 (0~100)"""
        total = len(self.assigned_schools)
        if total == 0:
            return 0
        done = len(self.collected_schools)
        return int(done * 100 / total)

    @rx.var
    def selected_school_icon(self) -> str:
        """선택된 거래처의 아이콘 (cust_type 기반, 기본값 🏫)"""
        return self.school_icon_map.get(self.selected_school, "🏫")

    @rx.var
    def all_collected(self) -> bool:
        """모든 거래처 수거 완료 여부"""
        return (
            len(self.assigned_schools) > 0
            and len(self.remaining_schools) == 0
        )

    # ── 수거기록 삭제 ──

    def delete_collection_entry(self, rowid: int):
        """수거 기록 삭제"""
        self.collection_save_msg = ""
        ok = delete_collection(rowid)
        if ok:
            self.collection_save_msg = "삭제 완료"
            self._load_today_collections()
        else:
            self.collection_save_msg = "삭제 실패"

    # ── 음성입력 핸들러 ──

    def handle_voice_result(self, text: str):
        """음성인식 결과 처리 — 숫자 추출 + 거래처명 매칭"""
        import re
        import difflib

        self.voice_active = False
        if not text:
            self.voice_result = "음성을 인식하지 못했습니다."
            return

        # ── 1. 숫자(kg) 추출 ──
        nums = re.findall(r"\d+\.?\d*", text)
        matched_kg = nums[0] if nums else ""

        if matched_kg:
            if self.collection_rows:
                rows = list(self.collection_rows)
                placed = False
                for i, row in enumerate(rows):
                    if not row.get("weight"):
                        rows[i] = {**rows[i], "weight": matched_kg}
                        self.collection_rows = rows
                        placed = True
                        break
                if not placed:
                    self.collection_weight = matched_kg
            else:
                self.collection_weight = matched_kg

        # ── 2. 거래처명 매칭 (사용자가 이미 선택한 경우 덮지 않음) ──
        matched_school = ""
        if not self.selected_school and self.assigned_schools:

            def _norm(s: str) -> str:
                """약칭 정규화: 초→초등학교, 중→중학교, 고→고등학교"""
                s = re.sub(r"초(?!등)", "초등학교", s)
                s = re.sub(r"중(?!학)", "중학교", s)
                s = re.sub(r"고(?!등)", "고등학교", s)
                return s

            norm_text = _norm(text)
            best_score = 0.0
            best_school = ""

            for school in self.assigned_schools:
                # 직접 포함 확인 (최우선)
                if school in text or school in norm_text:
                    best_school = school
                    best_score = 1.0
                    break
                # difflib 유사도 (threshold 0.6)
                score = difflib.SequenceMatcher(
                    None, norm_text, _norm(school)
                ).ratio()
                if score > best_score:
                    best_score = score
                    best_school = school

            if best_school and best_score >= 0.6:
                matched_school = best_school
                self.selected_school = best_school
                # 거래처 변경 → 다중행 초기화 (weight는 방금 추출한 값 유지)
                self.collection_rows = [
                    {
                        "date": self.today_str,
                        "item": self.collection_item_type,
                        "weight": matched_kg,
                    }
                ]

        # ── 결과 토스트 ──
        parts = []
        if matched_school:
            parts.append(matched_school)
        if matched_kg:
            parts.append(f"{matched_kg}kg")
        if parts:
            self.voice_result = "🎤 음성 인식: " + " ".join(parts)
        else:
            self.voice_result = f"🎤 인식: {text}"

    # ── GPS 핸들러 ──

    def save_gps_location(self, coords: str):
        """GPS 좌표 저장 (JS에서 'lat,lng' 문자열로 전달)"""
        self.gps_msg = ""
        if not self.selected_school:
            self.gps_msg = "거래처를 선택하세요."
            return
        try:
            parts = coords.split(",")
            lat = float(parts[0])
            lng = float(parts[1])
        except (ValueError, IndexError):
            self.gps_msg = "위치 정보를 가져올 수 없습니다."
            return
        ok = save_customer_gps(
            vendor=self.user_vendor,
            name=self.selected_school,
            lat=lat, lng=lng,
        )
        if ok:
            self.gps_msg = f"📍 위치 저장: {self.selected_school} ({lat:.5f}, {lng:.5f})"
        else:
            self.gps_msg = "위치 저장 실패"

    def auto_match_school_by_gps(self, coords: str):
        """GPS 기반 거래처 자동 선택 — 200m 이내 가장 가까운 거래처 선택"""
        self.gps_msg = ""
        try:
            parts = coords.split(",")
            cur_lat = float(parts[0])
            cur_lng = float(parts[1])
        except (ValueError, IndexError):
            self.gps_msg = "위치 정보를 가져올 수 없습니다."
            return

        if cur_lat == 0 and cur_lng == 0:
            self.gps_msg = "위치 권한을 허용해주세요."
            return

        candidates = get_customers_with_gps(self.user_vendor)
        if not candidates:
            self.gps_msg = "GPS 좌표가 등록된 거래처가 없습니다."
            return

        best_dist = float("inf")
        best_name = ""
        for c in candidates:
            dist = haversine(cur_lat, cur_lng, c["lat"], c["lng"])
            if dist < best_dist:
                best_dist = dist
                best_name = c["name"]

        if best_dist <= 200:
            self.selected_school = best_name
            self.collection_rows = [
                {
                    "date": self.today_str,
                    "item": self.collection_item_type,
                    "weight": "",
                }
            ]
            self.gps_msg = f"📍 자동 선택: {best_name} ({int(best_dist)}m)"
        else:
            near_info = f"{best_name} {int(best_dist)}m" if best_name else "-"
            self.gps_msg = f"근처 거래처 없음 (최근: {near_info})"

    # ── 스쿨존 핸들러 ──

    def toggle_schoolzone(self, value: bool):
        """스쿨존 알림 토글"""
        self.schoolzone_enabled = value

    # ── 사진 핸들러 ──

    def _load_today_photos(self):
        """오늘 사진 기록 로드"""
        self.today_photos = get_photo_records_today(
            vendor=self.user_vendor,
            driver=self.user_name,
            collect_date=self.today_str,
        )

    @rx.var
    def today_photo_count(self) -> int:
        return len(self.today_photos)

    async def handle_photo_upload(self, files: list[rx.UploadFile]):
        """수거 사진 업로드 (최대 3장)"""
        self.photo_upload_msg = ""
        if not self.selected_school:
            self.photo_upload_msg = "거래처를 먼저 선택하세요."
            return

        upload_dir = os.path.join("uploaded_files", "photos", self.today_str)
        os.makedirs(upload_dir, exist_ok=True)

        saved = 0
        for file in files[:3]:
            upload_data = await file.read()
            fname = f"{self.user_vendor}_{self.selected_school}_{datetime.now().strftime('%H%M%S')}_{saved}.jpg"
            fpath = os.path.join(upload_dir, fname)
            with open(fpath, "wb") as f:
                f.write(upload_data)
            save_photo_record(
                vendor=self.user_vendor,
                driver=self.user_name,
                school_name=self.selected_school,
                photo_type="collection",
                photo_url=fpath,
                collect_date=self.today_str,
            )
            saved += 1

        if saved > 0:
            self.photo_upload_msg = f"📸 사진 {saved}장 저장 완료"
            self._load_today_photos()
        else:
            self.photo_upload_msg = "사진 업로드 실패"

    # ── 계근표(처리확인) 핸들러 ──

    def _load_today_processing(self):
        """오늘 처리확인 기록 로드"""
        self.today_processing = get_today_processing(
            vendor=self.user_vendor,
            driver=self.user_name,
            confirm_date=self.today_str,
        )

    def set_proc_weight(self, value: str):
        self.proc_weight = value

    def set_proc_location(self, value: str):
        self.proc_location = value

    def set_proc_memo(self, value: str):
        self.proc_memo = value

    @rx.var
    def today_proc_count(self) -> int:
        return len(self.today_processing)

    def save_processing(self):
        """처리확인 저장"""
        self.proc_save_msg = ""
        try:
            w = float(self.proc_weight)
        except (ValueError, TypeError):
            self.proc_save_msg = "처리량을 입력하세요."
            return
        if w <= 0:
            self.proc_save_msg = "처리량은 0보다 커야 합니다."
            return
        if not self.proc_location.strip():
            self.proc_save_msg = "처리장명을 입력하세요."
            return

        ok = save_processing_confirm(
            vendor=self.user_vendor,
            driver=self.user_name,
            total_weight=w,
            location_name=self.proc_location.strip(),
            memo=self.proc_memo,
        )
        if ok:
            self.proc_save_msg = f"✅ 처리확인 완료 ({w}kg @ {self.proc_location})"
            self.proc_weight = ""
            self.proc_location = ""
            self.proc_memo = ""
            self._load_today_processing()
        else:
            self.proc_save_msg = "저장 실패. 다시 시도해주세요."

    # ── 퇴근 핸들러 ──

    def do_checkout(self):
        """퇴근 처리"""
        ok = save_driver_checkout(
            vendor=self.user_vendor,
            driver=self.user_name,
            checkout_date=self.today_str,
        )
        if ok:
            self.is_checked_out = True
            self.checkout_time = datetime.now().strftime("%H:%M:%S")
