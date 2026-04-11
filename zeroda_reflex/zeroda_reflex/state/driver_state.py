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
    db_get,
    get_today_collections, get_driver_collections_range, save_collection,
    get_driver_checkout_log, save_driver_checkout,
    delete_collection,
    get_driver_schedule_schools,
    get_today_processing, save_processing_confirm,
    save_photo_record, get_photo_records_today,
    save_customer_gps,
    get_all_customer_aliases,
    get_nearest_customer,
    get_nearby_customers,
)
from zeroda_reflex.utils.voice_parser import (
    normalize_korean_number,
    match_school_by_jamo,
    jamo_decompose,
    build_match_pool,
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


def _parse_voice_entries(
    text: str,
    today,
    schedule_schools: list,
    aliases_map: dict = None,
    all_customers: list = None,
) -> tuple:
    """발화 텍스트 파싱 → (entries, failed_chunks).

    entries: [{"date":"YYYY-MM-DD","school":str,"weight":str,"gps_needed":bool}, ...]
    failed_chunks: 파싱 실패 청크 목록

    섹션 1: normalize_korean_number로 전처리 (혼동맵 + 혼용숫자 변환)
    섹션 2: match_school_by_jamo로 자모 유사도 매칭 + 별칭 포함 탐색
    섹션 6: 거래처명이 없는 청크에 gps_needed=True 플래그
    """
    import re
    from datetime import timedelta

    # ── 섹션 1: 숫자 정규화 전처리 ──
    normalized_text = normalize_korean_number(text)

    school_names = [s.get("school_name", "") for s in schedule_schools]

    # 별칭 → 정식명 역방향 맵 구성 (섹션 3)
    alias_to_name: dict = {}
    if aliases_map:
        for name, aliases in aliases_map.items():
            for a in aliases:
                alias_to_name[a] = name

    # 자동약칭 + 수동별칭 통합 매칭풀 (루프 전 한 번만 빌드)
    match_pool: dict = build_match_pool(school_names, aliases_map)
    all_customer_pool: dict = {}
    if all_customers:
        all_cust_names = [c.get("name", "") for c in all_customers if c.get("name")]
        all_customer_pool = build_match_pool(all_cust_names, None)

    # 청크 분리: 쉼표/마침표/한국어 접속사
    chunks = re.split(
        r"[,，、.。]|그리고|그다음|그 다음|그담|그 담|또한|그리고서",
        normalized_text,
    )

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
            m = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", remaining)
            if m:
                try:
                    from datetime import date as _date
                    d = _date(today.year, int(m.group(1)), int(m.group(2)))
                except ValueError:
                    pass
                remaining = (remaining[:m.start()] + remaining[m.end():]).strip()

        if d is None:
            m = re.search(r"(\d{1,2})/(\d{1,2})", remaining)
            if m:
                try:
                    from datetime import date as _date
                    d = _date(today.year, int(m.group(1)), int(m.group(2)))
                except ValueError:
                    pass
                remaining = (remaining[:m.start()] + remaining[m.end():]).strip()

        if d is None:
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

        m = re.search(r"(\d+(?:\.\d+)?)\s*(kg|킬로그램|킬로|키로|k)\b", remaining, re.IGNORECASE)
        if m:
            weight = m.group(1)
            remaining = (remaining[:m.start()] + remaining[m.end():]).strip()
        else:
            nums = list(re.finditer(r"\d+(?:\.\d+)?", remaining))
            if nums:
                last = nums[-1]
                weight = last.group(0)
                remaining = (remaining[:last.start()] + remaining[last.end():]).strip()
            else:
                m_kor = re.search(r"([일이삼사오육칠팔구십백천]{2,})", remaining)
                if m_kor:
                    w = _korean_to_int(m_kor.group(1))
                    if w is not None and w > 0:
                        weight = str(w)
                        remaining = (remaining[:m_kor.start()] + remaining[m_kor.end():]).strip()

        if not weight:
            failed.append(chunk)
            continue

        # ── 2.5: 위치 지칭어 감지 + 노이즈 단어 제거 ──
        # 긴 표현 먼저 제거(부분 치환 방지), gps_intent 플래그 세팅
        _GPS_KWS = [
            "여기서", "이곳에서", "이 학교", "이학교",
            "이 거래처", "이거래처", "이 업체", "이업체",
            "이 현장", "이현장", "이곳", "여기",
        ]
        _NOISE_WS = ["수거량", "수거", "킬로그램", "킬로", "키로"]
        gps_intent = False
        for _kw in _GPS_KWS:
            if _kw in remaining:
                remaining = remaining.replace(_kw, "", 1).strip()
                gps_intent = True
        for _nw in _NOISE_WS:
            remaining = remaining.replace(_nw, "").strip()

        # ── 3. 거래처명 매칭 (섹션 2+3) ──
        name_text = remaining.strip()

        # 섹션 6: 거래처명이 비어있거나 위치 지칭어 발화 → GPS fallback 플래그
        if not name_text or gps_intent:
            entries.append({
                "date": d.strftime("%Y-%m-%d"),
                "school": "",
                "weight": weight,
                "gps_needed": True,
            })
            continue

        norm_text = _normalize_school(name_text)

        # 별칭 역방향 직접 매칭 (섹션 3)
        if name_text in alias_to_name:
            matched_sn = alias_to_name[name_text]
            if matched_sn in school_names or not school_names:
                entries.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "school": matched_sn,
                    "weight": weight,
                    "gps_needed": False,
                    "schedule_matched": True,
                })
                continue

        # 직접 포함 여부 (최우선) — 일정 1순위
        matched = None
        best_score = 0.0
        is_sched_match = False
        for sn in school_names:
            norm_sn = _normalize_school(sn)
            if (sn in name_text or norm_sn in norm_text
                    or (name_text and name_text in sn)
                    or (norm_text and norm_text in norm_sn)):
                matched = sn
                best_score = 1.0
                is_sched_match = True
                break

        # 자모+약칭 통합 매칭 (섹션 2+3: 자동약칭·수동별칭 포함 단일 탐색) — 일정 1순위
        if not matched or best_score < 1.0:
            jamo_matched, jamo_score = match_school_by_jamo(
                norm_text, school_names, min_score=0.50,
                alias_to_canonical=match_pool,
            )
            if jamo_matched and jamo_score > best_score:
                matched = jamo_matched
                best_score = jamo_score
                is_sched_match = True

        # fallback: 전체 customer_info에서 탐색 (threshold 0.65, 자동약칭 포함)
        if (not matched or best_score < 0.50) and all_customers:
            all_names = [c.get("name", "") for c in all_customers if c.get("name")]
            fb_matched, fb_score = match_school_by_jamo(
                norm_text, all_names, min_score=0.65,
                alias_to_canonical=all_customer_pool,
            )
            if fb_matched and fb_score > best_score:
                matched = fb_matched
                best_score = fb_score
                is_sched_match = False

        if not matched or best_score < 0.50:
            failed.append(chunk)
            continue

        entries.append({
            "date": d.strftime("%Y-%m-%d"),
            "school": matched,
            "weight": weight,
            "gps_needed": False,
            "schedule_matched": is_sched_match,
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
    weather_gps_coords: str = ""    # GPS 위치 캐시 "lat,lon"
    weather_location: str = ""      # GPS 기반 현재 지역명

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
    today_collections: list[dict] = []
    recent_collections: list[dict] = []
    record_filter: str = "7days"

    # ── 음성입력 ──
    voice_active: bool = False
    voice_result: str = ""
    voice_confirm_open: bool = False
    voice_pending_entries: list[dict] = []
    voice_pending_failed: list[str] = []
    voice_pending_raw: str = ""
    voice_normalized_text: str = ""   # 섹션 1: 정규화된 텍스트 (디버깅용)
    voice_interim: str = ""           # 섹션 5: 실시간 중간 인식 텍스트
    voice_gps_coords: str = ""        # 섹션 6: GPS 좌표 (lat,lng)
    voice_match_failed: bool = False   # 섹션 2: 매칭 실패 여부 (항상 다이얼로그 표시용)
    # 복수 GPS 후보 선택 다이얼로그
    voice_pick_open: bool = False
    voice_pick_candidates: list[dict] = []  # [{"name": str, "distance_m": float}, ...]
    voice_pick_weight: str = ""
    voice_pick_date: str = ""

    # ── 웨이크워드 ──
    wake_enabled: bool = False
    wake_status_text: str = "꺼짐"
    wake_keywords_start: str = "수거,입력,기록,제로다"
    wake_keywords_stop: str = "완료,끝,종료"

    # ── 스쿨존 ──
    schoolzone_enabled: bool = False

    # ── 사진 ──
    photo_upload_msg: str = ""
    today_photos: list[dict] = []

    # ── 섹션 접기/펼치기 ──
    recent_expanded: bool = True
    weighslip_expanded: bool = True

    # ── 계근표(처리확인) ──
    proc_weight: str = ""
    proc_location: str = ""
    proc_memo: str = ""
    proc_save_msg: str = ""
    today_processing: list[dict] = []

    # ── 계근표 OCR ──
    weighslip_image_bytes: bytes = b""      # 원본 이미지 (OCR용)
    weighslip_preview_data_url: str = ""    # 리사이즈 썸네일 data URL
    weighslip_image_ready: bool = False     # 사진 등록 완료 플래그
    weighslip_ocr_loading: bool = False
    weighslip_ocr_error: str = ""
    weighslip_ocr_first_time: str = ""    # 1차 계근시간
    weighslip_ocr_second_time: str = ""   # 2차 계근시간
    weighslip_ocr_gross_weight: str = ""
    weighslip_ocr_net_weight: str = ""
    weighslip_ocr_vehicle_number: str = ""
    weighslip_ocr_company: str = ""
    weighslip_photo_path: str = ""
    weighslip_ocr_done: bool = False

    # ── 거래처별 수거 입력 (일정 카드 통합) ──
    # 입력값은 schedule_schools 각 아이템에 직접 포함:
    # {school_name, icon, address, items, weight, item_type, memo, save_msg, photo_msg}
    active_save_school: str = ""              # GPS/음성/사진 콜백용 현재 대상 거래처
    show_photo_for: str = ""                  # 사진 업로드 패널 열린 거래처 (한 번에 하나)

    # ── 퇴근 ──
    is_checked_out: bool = False
    checkout_time: str = ""

    # ── 퇴근 차량점검 다이얼로그 ──
    checkout_dialog_open: bool = False
    vehicle_check_items: list[dict] = [
        {"label": "브레이크 정상 작동", "checked": False},
        {"label": "사이드브레이크 정상 작동", "checked": False},
        {"label": "계기판 경고등 없음 (정상)", "checked": False},
        {"label": "전조등 양쪽 양호", "checked": False},
        {"label": "후미등 양쪽 양호", "checked": False},
        {"label": "타이어 공기압·마모 양호", "checked": False},
        {"label": "경적 정상 작동", "checked": False},
        {"label": "안전벨트 정상 작동", "checked": False},
        {"label": "적재함 잠금장치 정상", "checked": False},
        {"label": "누유·누수 없음", "checked": False},
    ]
    vehicle_check_remark: str = ""

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

    @rx.var
    def all_vehicle_items_checked(self) -> bool:
        """퇴근 차량점검 — 10개 항목 전체 체크 여부"""
        items = self.vehicle_check_items
        return len(items) > 0 and all(item.get("checked", False) for item in items)

    def on_driver_load(self):
        """기사 페이지 로드 시"""
        if not self.is_authenticated:
            yield rx.redirect("/")
            return
        if self.user_role != "driver":
            yield rx.redirect("/")
            return
        self._load_weather()  # 기본 격자(DEFAULT_GRID)로 즉시 로드
        self._load_safety_status()
        self._load_today_collections()
        self._load_recent_collections()
        self._load_today_photos()
        self._load_today_processing()
        self._load_checkout_status()
        # 수거일정 초기 로드 (오늘 날짜)
        if not self.schedule_date:
            self.schedule_date = self.today_str
        self._load_schedule()
        # GPS 취득 → 날씨 업데이트 (비동기, 실패 시 위 기본 날씨 유지)
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  if (!navigator.geolocation) { resolve(''); return; }"
            "  navigator.geolocation.getCurrentPosition("
            "    (pos) => resolve(pos.coords.latitude + ',' + pos.coords.longitude),"
            "    () => resolve(''),"
            "    {timeout: 5000, maximumAge: 300000}"
            "  );"
            "})",
            callback=DriverState.load_weather_with_gps,
        )

    def load_weather_with_gps(self, coords: str):
        """GPS 콜백 — 'lat,lon' 문자열 수신 후 날씨 업데이트"""
        if not coords:
            return
        try:
            parts = coords.split(",")
            if len(parts) != 2:
                return
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            self.weather_gps_coords = coords
            self._load_weather(lat=lat, lon=lon)
        except Exception as e:
            logger.warning(f"GPS 날씨 업데이트 실패: {e}")

    def _load_weather(self, lat: float | None = None, lon: float | None = None):
        """기상청 API로 오늘 날씨 로드. lat/lon 제공 시 GPS 격자 변환."""
        try:
            result = fetch_today_weather_alert(lat=lat, lon=lon)
            self.weather_available = result.get("available", False)
            self.weather_icon = result.get("icon", "🌐")
            self.weather_summary = result.get("summary", "")
            self.weather_alerts = result.get("alerts", [])
            self.weather_level = result.get("level", "normal")
            self.weather_source = result.get("source", "")
            self.weather_location = result.get("location", "")
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

    def _load_today_collections(self):
        """오늘 수거 기록 로드 — 토요일은 금요일로 변환 (학교 수거 토→금 저장과 동일)
        일반 거래처는 토요일 그대로 저장되므로 토요일에는 금+토 양일 조회 후 합산"""
        _d = date.today()
        if _d.weekday() == 5:  # 토요일
            friday_str = (_d - timedelta(days=1)).strftime("%Y-%m-%d")
            saturday_str = _d.strftime("%Y-%m-%d")
            friday_rows = get_today_collections(
                vendor=self.user_vendor,
                driver=self.user_name,
                collect_date=friday_str,
            )
            saturday_rows = get_today_collections(
                vendor=self.user_vendor,
                driver=self.user_name,
                collect_date=saturday_str,
            )
            # 중복 제거: id 기준
            seen_ids = set()
            merged = []
            for row in friday_rows + saturday_rows:
                rid = row.get("id")
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    merged.append(row)
            self.today_collections = merged
        else:
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
        """전역 음성 입력 시작 — 날짜+거래처+수거량 동시 인식.
        섹션 5: interimResults=true → DOM id='voice-interim-text'에 실시간 표시.
        섹션 6: GPS 좌표를 동시에 취득 → 결과를 'lat,lng|transcript' 형태로 반환.
        """
        self.voice_active = True
        self.voice_result = ""
        self.voice_interim = ""
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  function startVoice(gps) {"
            "    try {"
            "      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;"
            "      if (!SR) { resolve('|지원안됨'); return; }"
            "      const r = new SR();"
            "      r.lang = 'ko-KR';"
            "      r.maxAlternatives = 1;"
            "      r.interimResults = true;"
            "      r.onresult = (e) => {"
            "        for (let i = e.resultIndex; i < e.results.length; i++) {"
            "          if (e.results[i].isFinal) {"
            "            r.stop();"
            "            resolve(gps + '|' + e.results[i][0].transcript);"
            "            return;"
            "          }"
            "          const el = document.getElementById('voice-interim-text');"
            "          if (el) el.textContent = '🎤 ' + e.results[i][0].transcript;"
            "        }"
            "      };"
            "      r.onerror = () => { r.stop(); resolve(gps + '|'); };"
            "      r.onend = () => {"
            "        const el = document.getElementById('voice-interim-text');"
            "        if (el) el.textContent = '';"
            "      };"
            "      r.start();"
            "    } catch(ex) { resolve('|지원안됨'); }"
            "  }"
            "  if (navigator.geolocation) {"
            "    navigator.geolocation.getCurrentPosition("
            "      (p) => { startVoice(p.coords.latitude + ',' + p.coords.longitude); },"
            "      () => { startVoice(''); },"
            "      {timeout: 3000, maximumAge: 60000}"
            "    );"
            "  } else {"
            "    startVoice('');"
            "  }"
            "})",
            callback=DriverState.handle_global_voice_result,
        )

    async def handle_global_voice_result(self, combined: str):
        """전역 음성 인식 결과 → 파싱 → 확인 다이얼로그 표시.
        combined 형식: 'lat,lng|transcript' (섹션 6)
        """
        self.voice_active = False
        self.voice_interim = ""

        # GPS + 텍스트 분리
        if "|" in combined:
            gps_part, text = combined.split("|", 1)
        else:
            gps_part, text = "", combined

        self.voice_gps_coords = gps_part.strip()

        if not text or text in ("지원안됨", ""):
            self.voice_result = "음성 인식 실패"
            await self.log_wake_event("voice_failed", heard=text)
            yield rx.toast.warning("음성 인식에 실패했습니다. 다시 시도해 주세요.")
            return

        today = date.today()

        # 섹션 3: 별칭 맵 로드
        aliases_map = {}
        try:
            aliases_map = get_all_customer_aliases(self.user_vendor)
        except Exception:
            pass

        # 전체 거래처 목록 (fallback용, 섹션 2)
        all_customers = []
        try:
            all_customers = db_get("customer_info", {"vendor": self.user_vendor})
        except Exception:
            pass

        entries, failed_chunks = _parse_voice_entries(
            text, today, self.schedule_schools,
            aliases_map=aliases_map,
            all_customers=all_customers,
        )

        # 섹션 6: GPS fallback — school이 비어있는 엔트리 처리
        if self.voice_gps_coords:
            try:
                lat_s, lng_s = self.voice_gps_coords.split(",", 1)
                lat_f, lng_f = float(lat_s), float(lng_s)
                sched_names = [s.get("school_name", "") for s in self.schedule_schools]
                new_entries = []
                for e in entries:
                    if e.get("gps_needed") or not e.get("school"):
                        nearby = get_nearby_customers(
                            self.user_vendor, lat_f, lng_f,
                            max_distance_m=500,
                            schedule_names=sched_names,
                        )
                        if not nearby:
                            # 반경 내 거래처 없음 → 실패
                            failed_chunks.append(e.get("weight", ""))
                            continue
                        elif len(nearby) == 1:
                            # 단일 후보 → 자동 적용
                            e = {**e, "school": nearby[0]["name"], "gps_needed": False,
                                 "gps_matched": True, "gps_dist": nearby[0]["distance_m"]}
                            new_entries.append(e)
                        else:
                            # 복수 후보 → 선택 다이얼로그로 라우팅
                            self.voice_pick_candidates = nearby
                            self.voice_pick_weight = str(e.get("weight", ""))
                            self.voice_pick_date = str(e.get("date", ""))
                            self.voice_pick_open = True
                            # 이 엔트리는 확정하지 않고 pending (다이얼로그에서 처리)
                            continue
                    else:
                        new_entries.append(e)
                entries = new_entries
            except Exception:
                pass

        # GPS 불필요 플래그 제거 후 failed 처리
        clean_entries = []
        for e in entries:
            if e.get("gps_needed"):
                failed_chunks.append(e.get("weight", ""))
            else:
                clean_entries.append(e)
        entries = clean_entries

        # 섹션 1: 정규화 텍스트 저장 (다이얼로그에 표시)
        self.voice_normalized_text = normalize_korean_number(text)
        self.voice_pending_raw = text
        self.voice_pending_entries = entries
        self.voice_pending_failed = failed_chunks

        # 복수 GPS 후보 선택 다이얼로그가 열린 경우 confirm dialog 차단
        if self.voice_pick_open:
            return

        if not entries:
            # 섹션 2: 매칭 실패여도 항상 다이얼로그 표시
            self.voice_match_failed = True
            self.voice_confirm_open = True
            return

        self.voice_match_failed = False
        await self.log_wake_event("voice_success", heard=text)
        self.voice_confirm_open = True

    def confirm_voice_apply(self):
        """확인 다이얼로그 '확인' — pending 항목을 카드 rows에 적용 후 자동 제출"""
        applied = []
        failed_msg = []
        new_schedules = list(self.schedule_schools)
        applied_card_idxs: list[int] = []  # 자동 제출 대상 카드 인덱스

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
            if card_idx not in applied_card_idxs:
                applied_card_idxs.append(card_idx)

        self.schedule_schools = new_schedules
        self.voice_confirm_open = False
        self.voice_pending_entries = []
        self.voice_pending_failed = []
        self.voice_pending_raw = ""
        self.voice_match_failed = False

        parts = ["🎤 인식됨: " + ", ".join(applied)] if applied else []
        if failed_msg:
            parts.append("실패: " + ", ".join(failed_msg))
        msg = " / ".join(parts) if parts else "🎤 적용 완료"
        self.voice_result = msg

        if applied:
            yield rx.toast.success(msg)
            # 음성인식 시 캡처된 GPS 좌표로 자동 제출 (GPS 재취득 없이)
            gps = self.voice_gps_coords or ""
            for card_idx in applied_card_idxs:
                if 0 <= card_idx < len(self.schedule_schools):
                    self.active_save_school = self.schedule_schools[card_idx].get("school_name", "")
                    self._do_save_for_school(gps, "submitted")
        else:
            yield rx.toast.warning(msg)

    def cancel_voice_apply(self):
        """확인 다이얼로그 '취소' / 외부 클릭 — pending 비우기, 아무 것도 적용 안 함"""
        self.voice_confirm_open = False
        self.voice_pending_entries = []
        self.voice_pending_failed = []
        self.voice_pending_raw = ""
        self.voice_normalized_text = ""
        self.voice_match_failed = False

    def pick_voice_candidate(self, school_name: str):
        """GPS 복수 후보 선택 다이얼로그에서 거래처 선택 → 수거량 적용 + 자동 제출"""
        weight = self.voice_pick_weight
        date_str = self.voice_pick_date
        gps = self.voice_gps_coords or ""

        # 다이얼로그 닫기 + stash 초기화
        self.voice_pick_open = False
        self.voice_pick_candidates = []
        self.voice_pick_weight = ""
        self.voice_pick_date = ""

        if not school_name or not weight or not date_str:
            yield rx.toast.warning("선택 정보가 올바르지 않습니다.")
            return

        # schedule_schools에서 해당 거래처 카드 찾기
        card_idx = -1
        for i, s in enumerate(self.schedule_schools):
            if s.get("school_name") == school_name:
                card_idx = i
                break

        if card_idx < 0:
            # 일정에 없으면 active_save_school 직접 세팅 후 저장
            self.active_save_school = school_name
            # rows에 임시로 weight/date 추가
            new_schedules = list(self.schedule_schools)
            new_schedules.append({
                "school_name": school_name,
                "rows": [{"date": date_str, "item_type": "음식물", "weight": weight, "memo": ""}],
                "save_msg": "", "photo_msg": "", "photo_remark": "",
            })
            self.schedule_schools = new_schedules
            card_idx = len(self.schedule_schools) - 1

        # 해당 카드 rows에 weight/date 주입
        schools = list(self.schedule_schools)
        card = schools[card_idx]
        rows = list(card.get("rows", []))
        row_idx = next((j for j, r in enumerate(rows) if r.get("date") == date_str), -1)
        if row_idx >= 0:
            rows[row_idx] = {**rows[row_idx], "weight": weight}
        else:
            rows.append({"date": date_str, "item_type": "음식물", "weight": weight, "memo": ""})
        schools[card_idx] = {**card, "rows": rows}
        self.schedule_schools = schools

        # 자동 제출
        self.active_save_school = school_name
        self._do_save_for_school(gps, "submitted")
        yield rx.toast.success(f"✅ {school_name} 수거량 {weight}kg 전송 완료")

    def cancel_voice_pick(self):
        """GPS 복수 후보 선택 다이얼로그 취소 버튼"""
        self.voice_pick_open = False
        self.voice_pick_candidates = []
        self.voice_pick_weight = ""
        self.voice_pick_date = ""

    def on_voice_pick_open_change(self, open: bool):
        """dialog on_open_change — 외부 클릭으로 닫힐 때 stash 초기화"""
        if not open:
            self.voice_pick_open = False
            self.voice_pick_candidates = []
            self.voice_pick_weight = ""
            self.voice_pick_date = ""

    def retry_voice_recognition(self):
        """섹션 4: 확인 다이얼로그에서 '다시 말하기' — pending 초기화 후 즉시 재청취"""
        self.voice_pending_entries = []
        self.voice_pending_failed = []
        self.voice_pending_raw = ""
        self.voice_normalized_text = ""
        self.voice_confirm_open = False
        self.voice_active = True
        self.voice_interim = ""
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  function startVoice(gps) {"
            "    try {"
            "      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;"
            "      if (!SR) { resolve('|지원안됨'); return; }"
            "      const r = new SR();"
            "      r.lang = 'ko-KR';"
            "      r.maxAlternatives = 1;"
            "      r.interimResults = true;"
            "      r.onresult = (e) => {"
            "        for (let i = e.resultIndex; i < e.results.length; i++) {"
            "          if (e.results[i].isFinal) {"
            "            r.stop();"
            "            resolve(gps + '|' + e.results[i][0].transcript);"
            "            return;"
            "          }"
            "          const el = document.getElementById('voice-interim-text');"
            "          if (el) el.textContent = '🎤 ' + e.results[i][0].transcript;"
            "        }"
            "      };"
            "      r.onerror = () => { r.stop(); resolve(gps + '|'); };"
            "      r.onend = () => {"
            "        const el = document.getElementById('voice-interim-text');"
            "        if (el) el.textContent = '';"
            "      };"
            "      r.start();"
            "    } catch(ex) { resolve('|지원안됨'); }"
            "  }"
            "  if (navigator.geolocation) {"
            "    navigator.geolocation.getCurrentPosition("
            "      (p) => { startVoice(p.coords.latitude + ',' + p.coords.longitude); },"
            "      () => { startVoice(''); },"
            "      {timeout: 3000, maximumAge: 60000}"
            "    );"
            "  } else {"
            "    startVoice('');"
            "  }"
            "})",
            callback=DriverState.handle_global_voice_result,
        )

    def save_collection_for_school_with_gps(self, coords: str):
        """GPS 콜백 — active_save_school 수거량 submitted로 저장"""
        if not coords:
            yield rx.toast.warning("📍 GPS 위치를 가져오지 못했습니다. 위치 권한을 확인해주세요.")
        self._do_save_for_school(coords, "submitted")

    def save_collection_for_school_draft_with_gps(self, coords: str):
        """GPS 콜백 — active_save_school 수거량 draft로 저장"""
        if not coords:
            yield rx.toast.warning("📍 GPS 위치를 가져오지 못했습니다. 위치 권한을 확인해주세요.")
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
    def collection_progress_pct(self) -> int:
        """수거 진행률 (0~100) — 오늘 일정 기준"""
        total = len(self.schedule_schools)
        if total == 0:
            return 0
        done = len(self.collected_schools)
        return int(done * 100 / total)

    # ── 수거기록 삭제 ──

    def delete_collection_entry(self, rowid: int):
        """수거 기록 삭제"""
        ok = delete_collection(rowid)
        if ok:
            self._load_today_collections()
            self._load_recent_collections()
            yield rx.toast.success("삭제 완료")
        else:
            yield rx.toast.error("삭제 실패")

    # ── 거래처 위치설정 핸들러 ──

    def initiate_location_for_school(self, idx: int):
        """카드 위치설정 버튼 — GPS 취득 후 customer_info에 저장"""
        if 0 <= idx < len(self.schedule_schools):
            self.active_save_school = self.schedule_schools[idx].get("school_name", "")
        yield rx.call_script(
            "new Promise((resolve) => {"
            "  if (!navigator.geolocation) { resolve(''); return; }"
            "  navigator.geolocation.getCurrentPosition("
            "    (pos) => resolve(pos.coords.latitude + ',' + pos.coords.longitude),"
            "    () => resolve(''),"
            "    {timeout: 8000, maximumAge: 0}"
            "  );"
            "})",
            callback=DriverState.save_location_for_school_with_gps,
        )

    def save_location_for_school_with_gps(self, coords: str):
        """GPS 콜백 — active_save_school 위치를 customer_info에 저장"""
        school = self.active_save_school
        if not school:
            yield rx.toast.error("거래처 정보가 없습니다.")
            return
        if not coords or coords in ("0,0", ""):
            yield rx.toast.error("위치 권한을 허용해주세요.")
            return
        try:
            parts = coords.split(",")
            lat = float(parts[0])
            lng = float(parts[1])
        except (ValueError, IndexError):
            yield rx.toast.error("위치 정보를 가져올 수 없습니다.")
            return
        ok = save_customer_gps(
            vendor=self.user_vendor,
            name=school,
            lat=lat, lng=lng,
        )
        if ok:
            yield rx.toast.success(f"📍 위치 저장: {school} ({lat:.5f}, {lng:.5f})")
        else:
            yield rx.toast.error(f"{school} 위치 저장 실패")

    # ── 스쿨존 핸들러 ──

    def toggle_recent_expanded(self):
        """최근 수거 기록 섹션 접기/펼치기"""
        self.recent_expanded = not self.recent_expanded

    def toggle_weighslip_expanded(self):
        """계근표(처리확인) 섹션 접기/펼치기"""
        self.weighslip_expanded = not self.weighslip_expanded

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

    async def register_weighslip_image(self, files: list[rx.UploadFile]):
        """Step 1: 사진 등록 — 썸네일 표시 + 원본 바이트 stash"""
        import base64
        import io
        import os

        print(f"[WEIGHSLIP-REG] entered, files count={len(files) if files else 0}")

        MAX_SIZE = 10 * 1024 * 1024
        ALLOWED_EXT = {".jpg", ".jpeg", ".png"}

        self.weighslip_ocr_error = ""
        self.weighslip_image_ready = False
        self.weighslip_preview_data_url = ""
        yield

        try:
            if not files:
                self.weighslip_ocr_error = "선택된 파일이 없습니다. 사진 선택 후 다시 시도하세요."
                return

            f = files[0]
            raw = await f.read()
            print(f"[WEIGHSLIP-REG] file read OK, size={len(raw)}, name={f.filename}")

            if len(raw) > MAX_SIZE:
                self.weighslip_ocr_error = "파일 크기 10MB 초과."
                return

            ext = os.path.splitext(f.filename or "")[1].lower()
            if ext not in ALLOWED_EXT:
                self.weighslip_ocr_error = "JPG/PNG 파일만 가능합니다."
                return

            # 원본 바이트 stash (OCR에서 사용)
            self.weighslip_image_bytes = raw

            # PIL로 400px 썸네일 리사이즈 → base64 data URL
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(raw))
                img.thumbnail((400, 400))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=70)
                thumb = buf.getvalue()
            except Exception:
                # PIL 실패 시 원본 그대로 (크기 제한 있는 경우)
                thumb = raw

            encoded = base64.b64encode(thumb).decode()
            self.weighslip_preview_data_url = "data:image/jpeg;base64," + encoded
            self.weighslip_image_ready = True
            print(f"[WEIGHSLIP-REG] thumbnail ready, thumb_size={len(thumb)}")

        except Exception as e:
            logger.error(f"[WEIGHSLIP-REG] exception: {e}", exc_info=True)
            self.weighslip_ocr_error = "사진 등록 중 오류가 발생했습니다."

    async def run_weighslip_ocr(self):
        """Step 2: OCR 실행 — stash된 원본 바이트로 Claude Vision 호출"""
        import asyncio
        import os
        import uuid
        from zeroda_reflex.utils.ai_service import extract_weigh_ticket

        print("[WEIGHSLIP-OCR] triggered")

        if not self.weighslip_image_bytes:
            self.weighslip_ocr_error = "등록된 사진이 없습니다. 먼저 사진을 등록하세요."
            return

        STAMP_DIR = "/opt/zeroda-platform/storage/weighslips"

        self.weighslip_ocr_loading = True
        self.weighslip_ocr_error = ""
        self.weighslip_ocr_done = False
        yield

        try:
            raw = self.weighslip_image_bytes

            # 이미지 파일 저장
            os.makedirs(STAMP_DIR, exist_ok=True)
            fname = "weighslip_" + uuid.uuid4().hex[:12] + ".jpg"
            fpath = os.path.join(STAMP_DIR, fname)
            with open(fpath, "wb") as w:
                w.write(raw)
            self.weighslip_photo_path = fpath

            # OCR 호출 (동기 함수 → executor)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, extract_weigh_ticket, raw)
            print(f"[WEIGHSLIP-OCR] result={result}")

            if result.get("error"):
                self.weighslip_ocr_error = result["error"]
            else:
                self.weighslip_ocr_first_time = str(result.get("first_weigh_time") or "")
                self.weighslip_ocr_second_time = str(result.get("second_weigh_time") or "")
                gw = result.get("gross_weight")
                nw = result.get("net_weight")
                self.weighslip_ocr_gross_weight = str(int(gw)) if gw else ""
                self.weighslip_ocr_net_weight = str(int(nw)) if nw else ""
                self.weighslip_ocr_vehicle_number = str(result.get("vehicle_number") or "")
                self.weighslip_ocr_company = str(result.get("processor_company") or "")
                if nw and nw > 0:
                    self.proc_weight = str(int(nw))
                elif gw and gw > 0:
                    self.proc_weight = str(int(gw))
                if result.get("processor_company"):
                    self.proc_location = str(result["processor_company"])
                self.weighslip_ocr_done = True

        except Exception as e:
            logger.error(f"[WEIGHSLIP-OCR] exception: {e}", exc_info=True)
            self.weighslip_ocr_error = "OCR 처리 중 오류가 발생했습니다."
        finally:
            self.weighslip_ocr_loading = False

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

        try:
            gw = float(self.weighslip_ocr_gross_weight) if self.weighslip_ocr_gross_weight else 0.0
        except ValueError:
            gw = 0.0
        try:
            nw = float(self.weighslip_ocr_net_weight) if self.weighslip_ocr_net_weight else 0.0
        except ValueError:
            nw = 0.0

        ok = save_processing_confirm(
            vendor=self.user_vendor,
            driver=self.user_name,
            total_weight=w,
            location_name=self.proc_location.strip(),
            memo=self.proc_memo,
            first_weigh_time=self.weighslip_ocr_first_time,
            second_weigh_time=self.weighslip_ocr_second_time,
            gross_weight=gw,
            net_weight=nw,
            vehicle_number=self.weighslip_ocr_vehicle_number,
            processor_company=self.weighslip_ocr_company,
            weighslip_photo_path=self.weighslip_photo_path,
        )
        if ok:
            self.proc_save_msg = f"✅ 처리확인 완료 ({w}kg @ {self.proc_location})"
            self.proc_weight = ""
            self.proc_location = ""
            self.proc_memo = ""
            self.weighslip_ocr_first_time = ""
            self.weighslip_ocr_second_time = ""
            self.weighslip_ocr_gross_weight = ""
            self.weighslip_ocr_net_weight = ""
            self.weighslip_ocr_vehicle_number = ""
            self.weighslip_ocr_company = ""
            self.weighslip_photo_path = ""
            self.weighslip_image_bytes = b""
            self.weighslip_preview_data_url = ""
            self.weighslip_image_ready = False
            self.weighslip_ocr_done = False
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

    # ── 퇴근 차량점검 다이얼로그 핸들러 ──

    def open_checkout_dialog(self):
        """퇴근하기 버튼 클릭 → 차량점검 다이얼로그 열기 (항목 초기화)"""
        self.vehicle_check_items = [
            {"label": "브레이크 정상 작동", "checked": False},
            {"label": "사이드브레이크 정상 작동", "checked": False},
            {"label": "계기판 경고등 없음 (정상)", "checked": False},
            {"label": "전조등 양쪽 양호", "checked": False},
            {"label": "후미등 양쪽 양호", "checked": False},
            {"label": "타이어 공기압·마모 양호", "checked": False},
            {"label": "경적 정상 작동", "checked": False},
            {"label": "안전벨트 정상 작동", "checked": False},
            {"label": "적재함 잠금장치 정상", "checked": False},
            {"label": "누유·누수 없음", "checked": False},
        ]
        self.vehicle_check_remark = ""
        self.checkout_dialog_open = True

    def toggle_vehicle_check(self, idx: int):
        """차량점검 항목 체크 토글"""
        items = list(self.vehicle_check_items)
        item = dict(items[idx])
        item["checked"] = not item["checked"]
        items[idx] = item
        self.vehicle_check_items = items

    def set_vehicle_check_remark(self, value: str):
        """특이사항 입력"""
        self.vehicle_check_remark = value

    def cancel_checkout(self):
        """차량점검 다이얼로그 취소"""
        self.checkout_dialog_open = False

    def confirm_checkout(self):
        """차량점검 확인 후 퇴근 처리"""
        import json as _json

        # ── 미체크 항목 확인 ──
        unchecked = [
            item["label"]
            for item in self.vehicle_check_items
            if not item.get("checked", False)
        ]
        if unchecked:
            msg = "미체크 항목이 있습니다:\\n" + "\\n".join(f"· {u}" for u in unchecked)
            yield rx.call_script(f"alert('{msg}')")
            return

        # ── 차량점검 결과를 daily_safety_check 테이블에 저장 (category='vehicle_checkout') ──
        check_dict = {item["label"]: item["checked"] for item in self.vehicle_check_items}
        save_daily_safety_check(
            vendor=self.user_vendor,
            driver=self.user_name,
            check_date=self.today_str,
            category="vehicle_checkout",
            check_items=check_dict,
            fail_memo=self.vehicle_check_remark,
        )

        # ── 안전점검 미완료 카테고리 경고 (기존 do_checkout 로직 동일) ──
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

        # ── 퇴근 기록 저장 ──
        ok = save_driver_checkout(
            vendor=self.user_vendor,
            driver=self.user_name,
            checkout_date=self.today_str,
        )
        if ok:
            self.is_checked_out = True
            self.checkout_time = datetime.now().strftime("%H:%M:%S")

        self.checkout_dialog_open = False

    # ============================================================
    # 웨이크워드 P1 — 토글 ON/OFF + 이벤트 핸들러
    # ============================================================
    def toggle_wake_word(self):
        """기사가 토글 버튼을 누름 → JS startWakeWord/stopWakeWord 호출."""
        self.wake_enabled = not self.wake_enabled
        if self.wake_enabled:
            self.wake_status_text = "대기중"
            yield rx.call_script(
                "(function(){"
                "  if (window.zerodaWake) {"
                "    window.zerodaWake.start();"
                "    window.addEventListener('zeroda-wake', function(){"
                "      window.dispatchEvent(new CustomEvent('zeroda-wake-relay'));"
                "    }, {once: false});"
                "  } else { console.warn('wake_word.js 미로딩'); }"
                "})()"
            )
        else:
            self.wake_status_text = "꺼짐"
            yield rx.call_script(
                "if (window.zerodaWake) window.zerodaWake.stop();"
            )

    async def on_wake_triggered(self):
        """JS 'zeroda-wake' 이벤트가 감지되면 자동 호출 — 기존 음성입력 시작."""
        if not self.wake_enabled:
            return
        self.wake_status_text = "인식중"
        await self.log_wake_event("wake_fired")
        return DriverState.start_global_voice

    # ============================================================
    # 웨이크워드 P2-1 — 사용자 설정 로드/저장
    # ============================================================
    @staticmethod
    def _ensure_wake_tables(conn) -> None:
        """wake_settings / wake_stats 테이블 없으면 자동 생성 (idempotent).
        PostgreSQL은 AUTOINCREMENT 미지원 → SERIAL PRIMARY KEY 사용.
        """
        _auto = "SERIAL PRIMARY KEY"
        _now_fn = "NOW()"
        conn.execute(
            "CREATE TABLE IF NOT EXISTS wake_settings ("
            "  username TEXT PRIMARY KEY,"
            "  keywords_start TEXT NOT NULL DEFAULT '수거,입력,기록,제로다',"
            "  keywords_stop  TEXT NOT NULL DEFAULT '완료,끝,종료',"
            "  keywords_cancel TEXT NOT NULL DEFAULT '취소',"
            "  enabled_default INTEGER DEFAULT 0,"
            f"  updated_at TEXT DEFAULT ({_now_fn})"
            ")"
        )
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS wake_stats ("
            f"  id {_auto},"
            "  username TEXT NOT NULL,"
            "  event_type TEXT NOT NULL,"
            "  heard_text TEXT,"
            "  matched_keyword TEXT,"
            f"  occurred_at TEXT DEFAULT ({_now_fn})"
            ")"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wake_stats_user_date "
            "ON wake_stats(username, occurred_at DESC)"
        )
        conn.commit()

    async def load_wake_settings(self):
        """로그인 직후 또는 driver_page mount 시 호출 — 사용자 호출명령 로드."""
        try:
            from ..utils.database import get_db
            auth = await self.get_state(AuthState)
            username = (auth.user_id or "").strip()
            if not username:
                return
            conn = get_db()
            try:
                self._ensure_wake_tables(conn)
                row = conn.execute(
                    "SELECT keywords_start, keywords_stop, enabled_default "
                    "FROM wake_settings WHERE username=?", (username,),
                ).fetchone()
            finally:
                conn.close()
            if row:
                self.wake_keywords_start = row["keywords_start"] or self.wake_keywords_start
                self.wake_keywords_stop = row["keywords_stop"] or self.wake_keywords_stop
                if int(row["enabled_default"] or 0) == 1 and not self.wake_enabled:
                    self.wake_enabled = True
                    self.wake_status_text = "대기중"
        except Exception:
            pass  # 테이블 미생성 / auth 미초기화 등 — 기본값 유지

    async def save_wake_settings(self):
        """기사가 입력 폼에서 [저장] 누름 → DB upsert + JS 키워드 즉시 갱신."""
        import json as _json
        try:
            from ..utils.database import get_db
            auth = await self.get_state(AuthState)
            username = (auth.user_id or "").strip()
            if not username:
                yield rx.toast.error("로그인 정보가 없습니다")
                return

            starts = ",".join([s.strip() for s in (self.wake_keywords_start or "").split(",") if s.strip()])
            stops = ",".join([s.strip() for s in (self.wake_keywords_stop or "").split(",") if s.strip()])
            if not starts:
                starts = "수거,입력,기록,제로다"
            if not stops:
                stops = "완료,끝,종료"
            self.wake_keywords_start = starts
            self.wake_keywords_stop = stops

            conn = get_db()
            try:
                self._ensure_wake_tables(conn)
                conn.execute(
                    "INSERT INTO wake_settings (username, keywords_start, keywords_stop, updated_at) "
                    "VALUES (?, ?, ?, datetime('now','localtime')) "
                    "ON CONFLICT(username) DO UPDATE SET "
                    "keywords_start=excluded.keywords_start, "
                    "keywords_stop=excluded.keywords_stop, "
                    "updated_at=excluded.updated_at",
                    (username, starts, stops),
                )
                conn.commit()
            finally:
                conn.close()

            payload = _json.dumps(
                {"start": starts.split(","), "stop": stops.split(","), "cancel": ["취소"]},
                ensure_ascii=False,
            )
            yield rx.call_script(
                "if(window.zerodaWake && window.__zerodaWake){"
                "  Object.assign(window.__zerodaWake.keywords, " + payload + ");"
                "}"
            )
            yield rx.toast.success("호출명령이 저장되었습니다")
        except Exception as _e:
            yield rx.toast.error(f"저장 실패: {type(_e).__name__}: {_e}")

    async def log_wake_event(self, event_type: str, heard: str = "", matched: str = ""):
        """P2-3 — 인식 통계 저장 (wake_fired/voice_success/voice_failed/cancel)."""
        try:
            from ..utils.database import get_db
            auth = await self.get_state(AuthState)
            conn = get_db()
            try:
                self._ensure_wake_tables(conn)
                conn.execute(
                    "INSERT INTO wake_stats (username, event_type, heard_text, matched_keyword) "
                    "VALUES (?, ?, ?, ?)",
                    (auth.user_id or "", event_type, heard[:200], matched[:50]),
                )
                conn.commit()
            finally:
                conn.close()
        except Exception:
            pass  # 통계 실패는 무시

    # ============================================================
    # 웨이크워드 P2-3 — 취소 이벤트 핸들러
    # ============================================================
    async def on_wake_cancel(self):
        """JS 'zeroda-wake-cancel' 이벤트 → 통계 기록 + 토스트."""
        await self.log_wake_event("cancel")
        self.voice_active = False
        return rx.toast.info("음성 입력이 취소되었습니다")
