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
)

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
    checked_items: dict[str, bool] = {}
    fail_memo: str = ""
    safety_save_msg: str = ""

    # ── 수거 ──
    assigned_schools: list[str] = []
    selected_school: str = ""
    collection_weight: str = ""
    collection_item_type: str = "음식물"
    today_collections: list[dict] = []
    collection_save_msg: str = ""

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
        self._load_checkout_status()

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

    def _load_schools(self):
        """배정된 학교 목록 로드"""
        self.assigned_schools = get_schools_by_vendor(self.user_vendor)
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
            self.safety_save_msg = "저장 완료"
        else:
            self.safety_save_msg = "저장 중 오류가 발생했습니다."

    # ── 수거입력 핸들러 ──

    def set_selected_school(self, value: str):
        """거래처 선택"""
        self.selected_school = value

    def set_collection_weight(self, value: str):
        """수거량 입력"""
        self.collection_weight = value

    def set_collection_item_type(self, value: str):
        """품목 선택"""
        self.collection_item_type = value

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

    def save_collection_entry(self):
        """수거 데이터 저장"""
        self.collection_save_msg = ""
        if not self.selected_school:
            self.collection_save_msg = "거래처를 선택하세요."
            return
        try:
            w = float(self.collection_weight)
        except (ValueError, TypeError):
            self.collection_save_msg = "수거량을 올바르게 입력하세요."
            return
        # ── 수거량 범위 검증 (0~9999kg) ──
        if w < 0:
            self.collection_save_msg = "수거량은 0 이상이어야 합니다."
            return
        if w > 9999:
            self.collection_save_msg = "수거량이 너무 큽니다. (최대 9,999kg)"
            return
        if w <= 0:
            self.collection_save_msg = "수거량은 0보다 커야 합니다."
            return

        ok = save_collection(
            vendor=self.user_vendor,
            driver=self.user_name,
            school_name=self.selected_school,
            collect_date=self.today_str,
            item_type=self.collection_item_type,
            weight=w,
        )
        if ok:
            self.collection_save_msg = f"✅ {self.selected_school} {w}kg 저장 완료"
            self.collection_weight = ""
            self._load_today_collections()
        else:
            self.collection_save_msg = "저장 중 오류가 발생했습니다."

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
