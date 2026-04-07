# zeroda_reflex/state/driver_state.py
# 기사 대시보드 상태 관리
import reflex as rx
import logging
from datetime import datetime, date, timedelta
from zeroda_reflex.state.auth_state import AuthState

logger = logging.getLogger(__name__)
from zeroda_reflex.utils.weather_service import fetch_today_weather_alert
from zeroda_reflex.utils.database import (
    get_daily_safety_checks, save_daily_safety_check,
    save_daily_safety_checks_transaction,
    get_schools_by_vendor, db_get, db_insert,
    get_today_collections, get_driver_collections_range, save_collection,
    get_driver_checkout_log, save_driver_checkout,
    delete_collection,
    get_driver_schedule_schools,
    get_today_processing, save_processing_confirm,
    save_photo_record, get_photo_records_today,
    save_customer_gps,
    get_customers_with_gps, haversine, get_school_icons,
)
import os

# ── 한글 숫자 변환 사전 ──
KOREAN_NUMS = {
    "영": 0, "일": 1, "이": 2, "삼": 3, "사": 4,
    "오": 5, "육": 6, "칠": 7, "팔": 8, "구": 9,
    "십": 10, "백": 100, "천": 1000,
}


def _korean_to_int(text: str):
    """한글 숫자 문자열 → 정수 변환. 실패 시 None.
    예: '이백사' → 204, '백오십' → 150, '삼백' → 300
    """
    result = 0
    current = 0
    for ch in text:
        if ch not in KOREAN_NUMS:
            return None
        n = KOREAN_NUMS[ch]
        if n >= 10:   # 십/백/천 단위
            if current == 0:
                current = 1
            result += current * n
            current = 0
        else:
            current = n
    result += current
    return result if result > 0 else None


def _normalize_school(name: str) -> str:
    """약칭 → 정식명 정규화: 초/중/고 접미사 처리.
    '서초고' → '서초고등학교', '서초중' → '서초중학교', '서초초' → '서초초등학교'
    """
    import re
    name = re.sub(r"초(?!등)", "초등학교", name)
    name = re.sub(r"중(?!학)", "중학교", name)
    name = re.sub(r"고(?!등)", "고등학교", name)
    return name


def _parse_voice_entries(text: str, today, schedule_schools: list) -> tuple:
    """발화 텍스트 파싱 → (entries, failed_chunks).

    entries: [{"date": "YYYY-MM-DD", "school": str, "weight": str}, ...]
    failed_chunks: 파싱 실패 청크 목록

    예: '6일 서초고 204, 17일 서초고 200'
     → [{"date":"2026-04-06","school":"서초고등학교","weight":"204"},
        {"date":"2026-04-17","school":"서초고등학교","weight":"200"}]
    """
    import re
    import difflib
    from datetime import timedelta

    school_names = [s.get("school_name", "") for s in schedule_schools]

    # 청크 분리: 쉼표/마침표/한국어 접속사
    chunks = re.split(r"[,，、.。]|그리고|그다음|그 다음|그담|그 담|또한|그리고서", text)

    entries = []
    failed = []

    for raw in chunks:
        chunk = raw.strip()
        if not chunk:
            continue

        remaining = chunk
        d = None

        # ── 1. 날짜 추출 ──
        for kw, delta in [("오늘", 0), ("어제", -1), ("내일", 1), ("모레", 2), ("그제", -2)]:
            if kw in remaining:
                d = today + timedelta(days=delta)
                remaining = remaining.replace(kw, "", 1).strip()
                break

        if d is None:
            # "N월 N일"
            m = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", remaining)
            if m:
                try:
                    from datetime import date as _date
                    d = _date(today.year, int(m.group(1)), int(m.group(2)))
                except ValueError:
                    pass
                remaining = (remaining[:m.start()] + remaining[m.end():]).strip()

        if d is None:
            # "N/N"
            m = re.search(r"(\d{1,2})/(\d{1,2})", remaining)
            if m:
                try:
                    from datetime import date as _date
                    d = _date(today.year, int(m.group(1)), int(m.group(2)))
                except ValueError:
                    pass
                remaining = (remaining[:m.start()] + remaining[m.end():]).strip()

        if d is None:
            # "N일" (현재 월 사용)
            m = re.search(r"(\d{1,2})\s*일", remaining)
            if m:
                try:
                    from datetime import date as _date
                    d = _date(today.year, today.month, int(m.group(1)))
                except ValueError:
                    pass
                remaining = (remaining[:m.start()] + remaining[m.end():]).strip()

        if d is None:
            failed.append(chunk)
            continue

        # ── 2. 수거량(kg) 추출 ──
        weight = None

        # 명시적 단위 우선
        m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|킬로그램|킬로|키로|k)\b", remaining, re.IGNORECASE)
        if m:
            weight = m.group(1)
            remaining = (remaining[:m.start()] + remaining[m.end():]).strip()
        else:
            # 단위 없는 아라비아 숫자 (마지막 등장 기준)
            nums = list(re.finditer(r"\d+(?:\.\d+)?", remaining))
            if nums:
                last = nums[-1]
                weight = last.group(0)
                remaining = (remaining[:last.start()] + remaining[last.end():]).strip()
            else:
                # 한글 숫자 시도 (2자 이상)
                m_kor = re.search(r"([일이삼사오육칠팔구십백천]{2,})", remaining)
                if m_kor:
                    w = _korean_to_int(m_kor.group(1))
                    if w is not None and w > 0:
                        weight = str(w)
                        remaining = (remaining[:m_kor.start()] + remaining[m_kor.end():]).strip()

        if not weight:
            failed.append(chunk)
            continue

        # ── 3. 거래처명 매칭 ──
        name_text = remaining.strip()
        norm_text = _normalize_school(name_text)

        matched = None
        best_score = 0.0

        for sn in school_names:
            norm_sn = _normalize_school(sn)
            # 직접 포함 (최우선)
            if (sn in name_text or norm_sn in norm_text
                    or (name_text and name_text in sn)
                    or (norm_text and norm_text in norm_sn)):
                matched = sn
                best_score = 1.0
                break
            # difflib 유사도
            score = difflib.SequenceMatcher(None, norm_text, norm_sn).ratio()
            if score > best_score:
                best_score = score
                matched = sn

        if not matched or best_score < 0.55:
            failed.append(chunk)
            continue

        entries.append({
            "date": d.strftime("%Y-%m-%d"),
            "school": matched,
            "weight": weight,
        })

    return entries, failed


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
    recent_collections: list[dict] = []
    record_filter: str = "7days"
    collection_rows: list[dict] = []   # 다중행: [{"date":"YYYY-MM-DD","item":"음식물","weight":""}]
    collection_unit_price: str = ""
    collection_time: str = ""
    collection_memo: str = ""
    collection_save_msg: str = ""

    # ── GPS (거래첫 위치 저장용) ──
    gps_msg: str = ""

    # ── 수거 GPS (수거완료 시 자동 취득) ──
    collection_lat: float = 0.0
    collection_lng: float = 0.0

    # ── 거래처 아이콘 맵 ──
    school_icon_map: dict[str, str] = {}

    # ── 음성입력 ──
    voice_active: bool = False
    voice_result: str = ""
    voice_confirm_open: bool = False
    voice_pending_entries: list[dict] = []
    voice_pending_failed: list[str] = []
    voice_pending_raw: str = ""

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

    # ── 거래처별 수거 입력 (일정 카드 통합) ──
    # 입력값은 schedule_schools 각 아이템에 직접 포함:
    # {school_name, icon, address, items, weight, item_type, memo, save_msg, photo_msg}
    active_save_school: str = ""              # GPS/음성/사진 콜백용 현재 대상 거래처
    show_photo_for: str = ""                  # 사진 업로드 패널 열린 거래처 (한 번에 하나)

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
        self._load_recent_collections()
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
        schools = get_driver_schedule_schools(
            vendor=self.user_vendor,
            driver=self.user_name,
            sel_date=self.schedule_date,
        )
        # 기존 입력값 보존 (날짜 변경 시 이미 입력한 행 유지)
        existing = {s.get("school_name", ""): s for s in self.schedule_schools}
        result = []
        for s in schools:
            name = s.get("school_name", "")
            ex = existing.get(name, {})
            default_rows = [{"date": self.schedule_date, "item_type": "음식물", "weight": "", "memo": ""}]
            rows = ex.get("rows", default_rows)
            if not rows:
                rows = default_rows
            result.append({
                **s,
                "rows":         rows,
                "save_msg":     ex.get("save_msg", ""),
                "photo_msg":    ex.get("photo_msg", ""),
                "photo_remark": ex.get("photo_remark", ""),
            })
        self.schedule_schools = result

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

    def _load_recent_collections(self):
        """최근 수거 기록 로드 (record_filter 기준)"""
        today = date.today()
        f = self.record_filter
        if f == "today":
            date_from = today
        elif f == "30days":
            date_from = today - timedelta(days=29)
        elif f == "month":
            date_from = today.replace(day=1)
        else:  # "7days" 기본
            date_from = today - timedelta(days=6)
        self.recent_collections = get_driver_collections_range(
            vendor=self.user_vendor,
            driver=self.user_name,
            date_from=date_from.strftime("%Y-%m-%d"),
            date_to=today.strftime("%Y-%m-%d"),
        )

    def set_record_filter(self, value: str):
        """수거 기록 기간 필터 변경"""
        self.record_filter = value
        self._load_recent_collections()

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

    @rx.var
    def recent_collection_count(self) -> int:
        """최근 수거 기록 건수 (record_filter 기준)"""
        return len(self.recent_collections)

    @rx.var
    def record_filter_label(self) -> str:
        """현재 필터 레이블"""
        labels = {
            "today": "오늘",
            "7days": "최근 7일",
            "30days": "최근 30일",
            "month": "이번 달",
        }
        return labels.get(self.record_filter, "최근 7일")

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
                lat=self.collection_lat if self.collection_lat != 0.0 else None,
                lng=self.collection_lng if self.collection_lng != 0.0 else None,
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
            self._load_recent_collections()
        else:
            self.collection_save_msg = "저장 중 오류가 발생했습니다."

    def save_collection_entry(self):
        """수거완료·본사전송 (submitted) — GPS 없이 직접 저장"""
        self.collection_lat = 0.0
        self.collection_lng = 0.0
        self._do_save_collection("submitted")

    def save_collection_draft(self):
        """임시저장 (draft) — GPS 없이 직접 저장"""
        self.collection_lat = 0.0
        self.collection_lng = 0.0
        self._do_save_collection("draft")

    def save_collection_with_gps(self, coords: str):
        """GPS 좌표를 받아 수거완료·본사전송 (JS call_script 콜백)"""
        self.collection_lat = 0.0
        self.collection_lng = 0.0
        if coords and coords not in ("0,0", ""):
            try:
                parts = coords.split(",")
                self.collection_lat = float(parts[0])
                self.collection_lng = float(parts[1])
            except (ValueError, IndexError):
                pass
        self._do_save_collection("submitted")

    def save_draft_with_gps(self, coords: str):
        """GPS 좌표를 받아 임시저장 (JS call_script 콜백)"""
        self.collection_lat = 0.0
        self.collection_lng = 0.0
        if coords and coords not in ("0,0", ""):
            try:
                parts = coords.split(",")
                self.collection_lat = float(parts[0])
                self.collection_lng = float(parts[1])
            except (ValueError, IndexError):
                pass
        self._do_save_collection("draft")

    # ── 거래처별 수거 입력 핸들러 (일정 카드 통합 — idx 기반) ──

    def set_school_weight(self, pair: list):
        """특정 거래처 수거량 변경 [idx, value]"""
        idx, val = int(pair[0]), str(pair[1])
        schools = list(self.schedule_schools)
        if 0 <= idx < len(schools):
            schools[idx] = {**schools[idx], "weight": val}
            self.schedule_schools = schools

    def set_school_item_type(self, pair: list):
        """특정 거래처 품목 변경 [idx, value]"""
        idx, val = int(pair[0]), str(pair[1])
        schools = list(self.schedule_schools)
        if 0 <= idx < len(schools):
            schools[idx] = {**schools[idx], "item_type": val}
            self.schedule_schools = schools

    def set_school_memo(self, pair: list):
        """특정 거래처 메모 변경 [idx, value] — 레거시 단일행 호환"""
        idx, val = int(pair[0]), str(pair[1])
        schools = list(self.schedule_schools)
        if 0 <= idx < len(schools):
            schools[idx] = {**schools[idx], "memo": val}
            self.schedule_schools = schools

    # ── 거래처 카드 다일자 행 핸들러 ──

    def add_row_for_school(self, idx: int):
        """거래처 카드에 수거 행 추가 (오늘 날짜 빈 행)"""
        schools = list(self.schedule_schools)
        if 0 <= idx < len(schools):
            rows = list(schools[idx].get("rows", []))
            rows.append({"date": self.today_str, "item_type": "음식물", "weight": "", "memo": ""})
            schools[idx] = {**schools[idx], "rows": rows}
            self.schedule_schools = schools

    def remove_row_for_school(self, pair: list):
        """거래처 카드 행 삭제 [school_idx, row_idx] — 마지막 행은 삭제 불가"""
        school_idx, row_idx = int(pair[0]), int(pair[1])
        schools = list(self.schedule_schools)
        if 0 <= school_idx < len(schools):
            rows = list(schools[school_idx].get("rows", []))
            if len(rows) > 1 and 0 <= row_idx < len(rows):
                rows.pop(row_idx)
                schools[school_idx] = {**schools[school_idx], "rows": rows}
                self.schedule_schools = schools

    def set_school_row_date(self, triple: list):
        """행 날짜 변경 [school_idx, row_idx, value]"""
        school_idx, row_idx, val = int(triple[0]), int(triple[1]), str(triple[2])
        schools = list(self.schedule_schools)
        if 0 <= school_idx < len(schools):
            rows = list(schools[school_idx].get("rows", []))
            if 0 <= row_idx < len(rows):
                rows[row_idx] = {**rows[row_idx], "date": val}
                schools[school_idx] = {**schools[school_idx], "rows": rows}
                self.schedule_schools = schools

    def set_school_row_item_type(self, triple: list):
        """행 품목 변경 [school_idx, row_idx, value]"""
        school_idx, row_idx, val = int(triple[0]), int(triple[1]), str(triple[2])
        schools = list(self.schedule_schools)
        if 0 <= school_idx < len(schools):
            rows = list(schools[school_idx].get("rows", []))
            if 0 <= row_idx < len(rows):
                rows[row_idx] = {**rows[row_idx], "item_type": val}
                schools[school_idx] = {**schools[school_idx], "rows": rows}
                self.schedule_schools = schools

    def set_school_row_weight(self, triple: list):
        """행 수거량 변경 [school_idx, row_idx, value]"""
        school_idx, row_idx, val = int(triple[0]), int(triple[1]), str(triple[2])
        schools = list(self.schedule_schools)
        if 0 <= school_idx < len(schools):
            rows = list(schools[school_idx].get("rows", []))
            if 0 <= row_idx < len(rows):
                rows[row_idx] = {**rows[row_idx], "weight": val}
                schools[school_idx] = {**schools[school_idx], "rows": rows}
                self.schedule_schools = schools

    def set_school_row_memo(self, triple: list):
        """행 메모 변경 [school_idx, row_idx, value]"""
        school_idx, row_idx, val = int(triple[0]), int(triple[1]), str(triple[2])
        schools = list(self.schedule_schools)
        if 0 <= school_idx < len(schools):
            rows = list(schools[school_idx].get("rows", []))
            if 0 <= row_idx < len(rows):
                rows[row_idx] = {**rows[row_idx], "memo": val}
                schools[school_idx] = {**schools[school_idx], "rows": rows}
                self.schedule_schools = schools

    def initiate_save_for_school(self, idx: int):
        """카드 수거완료 버튼 — GPS 취득 후 저장 (submitted)"""
        if 0 <= idx < len(self.schedule_schools):
            self.active_save_school = self.schedule_schools[idx].get("school_name", "")
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  if (!navigator.geolocation) { resolve(''); return; }"
            "  navigator.geolocation.getCurrentPosition("
            "    (pos) => resolve(pos.coords.latitude + ',' + pos.coords.longitude),"
            "    () => resolve(''),"
            "    {timeout: 5000, maximumAge: 60000}"
            "  );"
            "})",
            callback=DriverState.save_collection_for_school_with_gps,
        )

    def initiate_draft_for_school(self, idx: int):
        """카드 임시저장 버튼 — GPS 취득 후 저장 (draft)"""
        if 0 <= idx < len(self.schedule_schools):
            self.active_save_school = self.schedule_schools[idx].get("school_name", "")
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  if (!navigator.geolocation) { resolve(''); return; }"
            "  navigator.geolocation.getCurrentPosition("
            "    (pos) => resolve(pos.coords.latitude + ',' + pos.coords.longitude),"
            "    () => resolve(''),"
            "    {timeout: 5000, maximumAge: 60000}"
            "  );"
            "})",
            callback=DriverState.save_collection_for_school_draft_with_gps,
        )

    def start_global_voice(self):
        """전역 음성 입력 시작 — 날짜+거래처+수거량 동시 인식"""
        self.voice_active = True
        self.voice_result = ""
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  try {"
            "    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;"
            "    if (!SR) { resolve('지원안됨'); return; }"
            "    const r = new SR();"
            "    r.lang = 'ko-KR'; r.maxAlternatives = 1;"
            "    r.onresult = (e) => resolve(e.results[0][0].transcript);"
            "    r.onerror = () => resolve('');"
            "    r.onend = () => {};"
            "    r.start();"
            "  } catch(e) { resolve('지원안됨'); }"
            "})",
            callback=DriverState.handle_global_voice_result,
        )

    def handle_global_voice_result(self, text: str):
        """전역 음성 인식 결과 → 파싱 → 확인 다이얼로그 표시 (적용은 confirm_voice_apply에서)"""
        self.voice_active = False

        if not text or text in ("지원안됨", ""):
            self.voice_result = "음성 인식 실패"
            yield rx.toast.warning("음성 인식에 실패했습니다. 다시 시도해 주세요.")
            return

        today = date.today()
        entries, failed_chunks = _parse_voice_entries(text, today, self.schedule_schools)

        if not entries:
            self.voice_result = f"🎤 인식: {text}"
            yield rx.toast.warning("음성에서 입력 항목을 찾지 못했습니다.")
            return

        # 파싱 결과 대기열에 저장 → 다이얼로그 오픈
        self.voice_pending_raw = text
        self.voice_pending_entries = entries
        self.voice_pending_failed = failed_chunks
        self.voice_confirm_open = True

    def confirm_voice_apply(self):
        """확인 다이얼로그 '확인' — pending 항목을 카드 rows에 실제 적용"""
        applied = []
        failed_msg = []
        new_schedules = list(self.schedule_schools)

        for entry in self.voice_pending_entries:
            sch = entry["school"]
            entry_date = entry["date"]
            entry_weight = entry["weight"]

            card_idx = -1
            for i, s in enumerate(new_schedules):
                if s.get("school_name") == sch:
                    card_idx = i
                    break

            if card_idx < 0:
                failed_msg.append(f"{sch}(일정 없음)")
                continue

            card = new_schedules[card_idx]
            rows = list(card.get("rows", []))
            row_idx = next(
                (j for j, r in enumerate(rows) if r.get("date") == entry_date), -1
            )
            if row_idx >= 0:
                rows[row_idx] = {**rows[row_idx], "weight": entry_weight}
            else:
                rows.append({
                    "date": entry_date,
                    "item_type": card.get("item_type", "음식물"),
                    "weight": entry_weight,
                    "memo": "",
                })
            new_schedules[card_idx] = {**card, "rows": rows}

            disp_date = entry_date[5:]
            applied.append(f"{sch} {disp_date} {entry_weight}kg")

        self.schedule_schools = new_schedules
        self.voice_confirm_open = False
        self.voice_pending_entries = []
        self.voice_pending_failed = []
        self.voice_pending_raw = ""

        parts = ["🎤 인식됨: " + ", ".join(applied)] if applied else []
        if failed_msg:
            parts.append("실패: " + ", ".join(failed_msg))
        msg = " / ".join(parts) if parts else "🎤 적용 완료"
        self.voice_result = msg

        if applied:
            yield rx.toast.success(msg)
        else:
            yield rx.toast.warning(msg)

    def cancel_voice_apply(self):
        """확인 다이얼로그 '취소' / 외부 클릭 — pending 비우기, 아무 것도 적용 안 함"""
        self.voice_confirm_open = False
        self.voice_pending_entries = []
        self.voice_pending_failed = []
        self.voice_pending_raw = ""

    def save_collection_for_school_with_gps(self, coords: str):
        """GPS 콜백 — active_save_school 수거량 submitted로 저장"""
        self._do_save_for_school(coords, "submitted")

    def save_collection_for_school_draft_with_gps(self, coords: str):
        """GPS 콜백 — active_save_school 수거량 draft로 저장"""
        self._do_save_for_school(coords, "draft")

    def _do_save_for_school(self, coords: str, status: str):
        """거래처별 수거 저장 — 카드의 모든 행(rows)을 순회하며 INSERT"""
        school = self.active_save_school
        if not school:
            return

        school_data = None
        school_idx = -1
        for i, s in enumerate(self.schedule_schools):
            if s.get("school_name") == school:
                school_data = s
                school_idx = i
                break

        if school_data is None:
            return

        # GPS 파싱
        lat, lng = None, None
        if coords and coords not in ("0,0", ""):
            try:
                parts = coords.split(",")
                lat = float(parts[0])
                lng = float(parts[1])
            except (ValueError, IndexError):
                pass

        # 토요일→금요일 변환용 거래처 타입 조회 (한 번만)
        try:
            cust_rows = db_get("customer_info", {"vendor": self.user_vendor})
            cust_type_map = {cr.get("name", ""): cr.get("cust_type", cr.get("\uad6c\ubd84", "")) for cr in cust_rows}
        except Exception:
            cust_type_map = {}

        label = "임시저장" if status == "draft" else "전송 완료"
        collect_time = datetime.now().strftime("%H:%M")

        rows = school_data.get("rows", [])
        if not rows:
            self._set_school_save_msg(school_idx, "입력된 행이 없습니다.")
            return

        saved = 0
        skipped = 0
        sat_converted = False

        for row in rows:
            weight_str = row.get("weight", "")
            try:
                w = float(weight_str)
            except (ValueError, TypeError):
                skipped += 1
                continue
            if w <= 0 or w > 9999:
                skipped += 1
                continue

            collect_date = str(row.get("date", self.today_str)) or self.today_str
            item_type = str(row.get("item_type", "음식물"))
            memo = str(row.get("memo", ""))

            # 토요일 → 금요일 자동 변환 (학교만)
            try:
                from datetime import timedelta as _td
                rd_date = date.fromisoformat(collect_date)
                ct_type = cust_type_map.get(school, "")
                if rd_date.weekday() == 5 and ct_type in ("학교", "school", ""):
                    rd_date = rd_date - _td(days=1)
                    collect_date = rd_date.strftime("%Y-%m-%d")
                    sat_converted = True
            except Exception:
                pass

            ok = save_collection(
                vendor=self.user_vendor,
                driver=self.user_name,
                school_name=school,
                collect_date=collect_date,
                item_type=item_type,
                weight=w,
                status=status,
                unit_price=0,
                memo=memo,
                collect_time=collect_time,
                lat=lat,
                lng=lng,
            )
            if ok:
                saved += 1

        if saved > 0:
            msg = f"✅ {saved}건 {label}"
            if skipped > 0:
                msg += f" ({skipped}행 건너뜀)"
            if sat_converted:
                msg += " (토→금 변환)"
            clear = (status == "submitted")
            self._set_school_save_msg(school_idx, msg, clear_rows=clear)
            self._load_today_collections()
            self._load_recent_collections()
        elif skipped > 0:
            self._set_school_save_msg(school_idx, "수거량을 입력하세요.")
        else:
            self._set_school_save_msg(school_idx, "저장 실패")

    def _set_school_save_msg(self, idx: int, msg: str, clear_weight: bool = False, clear_rows: bool = False):
        """schedule_schools[idx]의 save_msg 업데이트 헬퍼"""
        if 0 <= idx < len(self.schedule_schools):
            schools = list(self.schedule_schools)
            update = {"save_msg": msg}
            if clear_weight or clear_rows:
                # 전송 완료 후 행 초기화 (오늘 날짜 빈 행 1개)
                update["rows"] = [{"date": self.today_str, "item_type": "음식물", "weight": "", "memo": ""}]
            schools[idx] = {**schools[idx], **update}
            self.schedule_schools = schools

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
            self._load_recent_collections()
        else:
            self.collection_save_msg = "삭제 실패"

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

    def toggle_photo_panel(self, idx: int):
        """카드 사진 업로드 패널 토글 — 한 번에 하나의 카드만 열림 (idx 기반)"""
        if 0 <= idx < len(self.schedule_schools):
            school = self.schedule_schools[idx].get("school_name", "")
            if self.show_photo_for == school:
                self.show_photo_for = ""
            else:
                self.show_photo_for = school
                self.active_save_school = school

    def set_photo_remark(self, pair: list):
        """거래처별 특이사항 코멘트 입력 [school_idx, value]"""
        school_idx, val = int(pair[0]), str(pair[1])
        schools = list(self.schedule_schools)
        if 0 <= school_idx < len(schools):
            schools[school_idx] = {**schools[school_idx], "photo_remark": val}
            self.schedule_schools = schools

    async def handle_card_photo_upload(self, files: list[rx.UploadFile]):
        """카드 내 사진 업로드 (거래처당 1장) — active_save_school 사용"""
        school = self.active_save_school
        if not school or not files:
            return

        upload_dir = os.path.join("uploaded_files", "photos", self.today_str)
        os.makedirs(upload_dir, exist_ok=True)

        file = files[0]  # 거래처당 1장
        upload_data = await file.read()
        fname = f"{self.user_vendor}_{school}_{datetime.now().strftime('%H%M%S')}.jpg"
        fpath = os.path.join(upload_dir, fname)
        with open(fpath, "wb") as f:
            f.write(upload_data)

        # 해당 거래처의 특이사항 코멘트 조회
        remark = ""
        schools = list(self.schedule_schools)
        remark_idx = -1
        for i, s in enumerate(schools):
            if s.get("school_name") == school:
                remark = str(s.get("photo_remark", "") or "")
                remark_idx = i
                break

        save_photo_record(
            vendor=self.user_vendor,
            driver=self.user_name,
            school_name=school,
            photo_type="collection",
            photo_url=fpath,
            collect_date=self.today_str,
            memo=remark,
        )
        # photo_msg 업데이트 + photo_remark 초기화
        if remark_idx >= 0:
            schools[remark_idx] = {
                **schools[remark_idx],
                "photo_msg": "📸 저장 완료",
                "photo_remark": "",
            }
        else:
            for i, s in enumerate(schools):
                if s.get("school_name") == school:
                    schools[i] = {**schools[i], "photo_msg": "📸 저장 완료", "photo_remark": ""}
                    break
        self.schedule_schools = schools
        self.show_photo_for = ""
        self._load_today_photos()

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
        """퇴근 처리 — 안전점검 미완료 시 경고 후 퇴근 진행"""
        # ── 안전점검 미완료 카테고리 확인 ──
        checks = get_daily_safety_checks(
            vendor=self.user_vendor,
            driver=self.user_name,
            check_date=self.today_str,
        )
        saved_cats = {r.get("category", "") for r in checks}
        missing_labels = [
            SAFETY_CHECKLIST[k]["label"]
            for k in SAFETY_CHECKLIST
            if k not in saved_cats
        ]
        if missing_labels:
            warning_msg = (
                "\u26a0\ufe0f \uc548\uc804\uc810\uac80 \ubbf8\uc644\ub8cc \ud56d\ubaa9:\\n"
                + ", ".join(missing_labels)
                + "\\n\\n\ud1f4\uadfc \ucc98\ub9ac\ub97c \uc9c4\ud589\ud569\ub2c8\ub2e4."
            )
            yield rx.call_script(f"alert('{warning_msg}')")

        ok = save_driver_checkout(
            vendor=self.user_vendor,
            driver=self.user_name,
            checkout_date=self.today_str,
        )
        if ok:
            self.is_checked_out = True
            self.checkout_time = datetime.now().strftime("%H:%M:%S")
