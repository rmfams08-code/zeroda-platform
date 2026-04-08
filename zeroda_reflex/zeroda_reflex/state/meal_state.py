# zeroda_reflex/state/meal_state.py
# 급식담당자 상태 관리 — 6메뉴
import reflex as rx
import logging
from datetime import datetime
from zeroda_reflex.state.auth_state import AuthState
from zeroda_reflex.utils.filters import safe_int

logger = logging.getLogger(__name__)
from zeroda_reflex.utils.database import (
    meal_get_menus, meal_save_menu, meal_delete_menu,
    meal_analyze_waste, meal_get_analysis_summary,
    meal_get_menu_ranking, meal_get_weekday_pattern,
    meal_get_cost_savings, meal_get_settlement,
    meal_get_esg, school_filter_collections,
    get_school_standard, WASTE_GRADE_TABLE,
    meal_get_menus_by_month, meal_get_collected_dates,
    meal_get_school_student_count,
    meal_get_monthly_trend, meal_get_seasonal_compare,
    save_meal_schedule_drafts,
)


# ── 메뉴 목록 ──
MEAL_TABS = ["식단등록", "스마트잔반분석", "AI잔반분석", "정산확인", "ESG보고서"]


class MealState(AuthState):
    """급식담당자 전체 상태"""

    # ══════════════════════════════
    #  공통
    # ══════════════════════════════
    active_tab: str = "식단등록"
    selected_year: str = str(datetime.now().year)
    selected_month: str = str(datetime.now().month).zfill(2)
    site_name: str = ""  # 담당 급식소 (= user_schools의 첫번째)
    msg: str = ""
    msg_ok: bool = False

    # ══════════════════════════════
    #  탭1: 식단등록
    # ══════════════════════════════
    menu_rows: list[dict] = []
    # 입력 폼
    mf_date: str = ""
    mf_menu: str = ""
    mf_calories: str = "0"
    mf_servings: str = "0"
    # 수정1: 영양정보 9항목
    mf_nutrition: dict = {}

    # ══════════════════════════════
    #  탭2: 스마트잔반분석
    # ══════════════════════════════
    analysis_rows: list[dict] = []
    analysis_summary: dict = {}
    best_menus: list[dict] = []
    worst_menus: list[dict] = []
    weekday_pattern: list[dict] = []

    # ══════════════════════════════
    #  탭3: AI잔반분석
    # ══════════════════════════════
    cost_data: dict = {}
    # AI 분석 결과 상태
    ai_api_key: str = ""              # 사용자 입력 API 키
    ai_comprehensive_result: str = "" # 종합분석 결과 (마크다운)
    ai_recommend_result: list[dict] = []  # 추천식단 결과
    ai_loading: bool = False          # 분석 진행중 플래그
    ai_error: str = ""                # 에러 메시지
    # 수정5: AI 잔반 원인 분석
    ai_cause_result: str = ""
    ai_cause_loading: bool = False
    # 수정10: AI 일별 특이사항
    ai_daily_remarks: dict = {}
    ai_daily_loading: bool = False

    # ══════════════════════════════
    #  탭5: 정산확인
    # ══════════════════════════════
    settle_data: dict = {}
    settle_items: list[dict] = []

    # ══════════════════════════════
    #  탭6: ESG보고서
    # ══════════════════════════════
    esg_data: dict = {}

    # ══════════════════════════════
    #  수정4: 학교급식법 공식기준
    # ══════════════════════════════
    school_standard: dict = {}
    waste_grade_table: list[dict] = []

    # ══════════════════════════════
    #  수정1: 달력형 식단 보기
    # ══════════════════════════════
    calendar_month: str = ""
    # 평탄화 달력: 각 셀 dict에 row_end="1" 이면 주(週) 마지막 셀
    calendar_cells: list[dict] = []
    calendar_open: bool = True   # 달력 섹션 접기/펴기
    expanded_date: str = ""  # 일별 식단 펼침 (한 번에 한 날짜만)
    collection_rows: list[dict] = []  # 달력 수거 상세 표시용

    # ══════════════════════════════
    #  수정3: 잔반 트렌드
    # ══════════════════════════════
    trend_subtab: str = "weekday"
    monthly_trend: list[dict] = []
    seasonal_compare: list[dict] = []

    # ══════════════════════════════
    #  Computed vars
    # ══════════════════════════════

    @rx.var
    def has_msg(self) -> bool:
        return len(self.msg) > 0

    @rx.var
    def year_month(self) -> str:
        return f"{self.selected_year}-{self.selected_month.zfill(2)}"

    @rx.var
    def has_menus(self) -> bool:
        return len(self.menu_rows) > 0

    @rx.var
    def menu_count(self) -> int:
        return len(self.menu_rows)

    @rx.var
    def has_analysis(self) -> bool:
        return len(self.analysis_rows) > 0

    @rx.var
    def has_best(self) -> bool:
        return len(self.best_menus) > 0

    @rx.var
    def has_worst(self) -> bool:
        return len(self.worst_menus) > 0

    @rx.var
    def has_weekday(self) -> bool:
        return len(self.weekday_pattern) > 0

    @rx.var
    def has_cost(self) -> bool:
        return bool(self.cost_data)

    @rx.var
    def has_ai_result(self) -> bool:
        return len(self.ai_comprehensive_result) > 0

    @rx.var
    def has_ai_recommend(self) -> bool:
        return len(self.ai_recommend_result) > 0

    @rx.var
    def has_ai_error(self) -> bool:
        return len(self.ai_error) > 0

    @rx.var
    def has_api_key(self) -> bool:
        """API 키 존재 여부 (사용자 입력 또는 환경변수)"""
        if self.ai_api_key:
            return True
        import os
        return bool(os.environ.get("ANTHROPIC_API_KEY", ""))

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
    def standard_compliance(self) -> str:
        """1인당 평균 잔반량 / 245g × 100 — 기준 대비 비율(%)"""
        avg_pp = float(self.analysis_summary.get("avg_waste_pp", "0") or "0")
        if avg_pp <= 0:
            return "0"
        return str(round(avg_pp / 245 * 100, 1))

    @rx.var
    def has_standard(self) -> bool:
        return bool(self.school_standard)

    @rx.var
    def has_calendar(self) -> bool:
        return len(self.calendar_cells) > 0

    # ── 선택된 날짜 상세 (달력 펼침 패널용) ──

    @rx.var
    def has_selected_menu(self) -> bool:
        return any(r.get("meal_date") == self.expanded_date for r in self.menu_rows)

    @rx.var
    def selected_menu_items(self) -> str:
        for r in self.menu_rows:
            if r.get("meal_date") == self.expanded_date:
                return str(r.get("menu_items", ""))
        return ""

    @rx.var
    def selected_calories(self) -> str:
        for r in self.menu_rows:
            if r.get("meal_date") == self.expanded_date:
                return str(r.get("calories", "0"))
        return "0"

    @rx.var
    def selected_servings(self) -> str:
        for r in self.menu_rows:
            if r.get("meal_date") == self.expanded_date:
                return str(r.get("servings", "0"))
        return "0"

    @rx.var
    def selected_collection_items(self) -> list[dict]:
        return [r for r in self.collection_rows if r.get("collect_date") == self.expanded_date]

    @rx.var
    def has_selected_collections(self) -> bool:
        return any(r.get("collect_date") == self.expanded_date for r in self.collection_rows)

    @rx.var
    def has_monthly_trend(self) -> bool:
        return len(self.monthly_trend) > 0

    @rx.var
    def has_seasonal(self) -> bool:
        return len(self.seasonal_compare) > 0

    # ══════════════════════════════
    #  수정3: 등급 분포 파이차트
    # ══════════════════════════════
    @rx.var
    def grade_distribution(self) -> list[dict]:
        """등급 분포 — 파이차트용"""
        counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for r in self.analysis_rows:
            g = str(r.get("grade", "-"))
            if g in counts:
                counts[g] += 1
        colors = {"A": "#22c55e", "B": "#3b82f6", "C": "#f97316", "D": "#ef4444"}
        result = []
        for g, cnt in counts.items():
            if cnt > 0:
                result.append({"name": f"{g}등급", "value": cnt, "fill": colors[g]})
        return result

    @rx.var
    def has_grade_distribution(self) -> bool:
        return len(self.grade_distribution) > 0

    # ══════════════════════════════
    #  수정4: 일별 1인당 잔반 라인차트
    # ══════════════════════════════
    @rx.var
    def daily_waste_chart(self) -> list[dict]:
        """일별 1인당 잔반 추이 (라인차트용)"""
        result = []
        for r in self.analysis_rows:
            date_str = str(r.get("meal_date", ""))
            date_short = date_str[5:10] if len(date_str) >= 10 else date_str
            wpp = float(r.get("waste_per_person", 0) or 0)
            if wpp > 0:
                result.append({"date": date_short, "waste_per_person": wpp})
        return result

    @rx.var
    def has_daily_chart(self) -> bool:
        return len(self.daily_waste_chart) > 0

    # ══════════════════════════════
    #  수정5: AI 원인 분석
    # ══════════════════════════════
    @rx.var
    def has_ai_cause_result(self) -> bool:
        return len(self.ai_cause_result) > 0

    # ══════════════════════════════
    #  수정6: 메뉴 조합 효과 분석
    # ══════════════════════════════
    @rx.var
    def menu_combo_analysis(self) -> list[dict]:
        """메뉴 2개 조합 효과 분석 — 잔반 적은 상위 10 조합"""
        import json as _j
        from collections import defaultdict
        import itertools
        combo_map: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
        for r in self.analysis_rows:
            wpp = float(r.get("waste_per_person", 0) or 0)
            if wpp <= 0:
                continue
            menus_raw = r.get("menu_items", "[]")
            try:
                menus = _j.loads(menus_raw) if isinstance(menus_raw, str) else menus_raw
            except Exception:
                continue
            if not isinstance(menus, list) or len(menus) < 2:
                continue
            for a, b in itertools.combinations([str(m).strip() for m in menus if str(m).strip()], 2):
                key = tuple(sorted([a, b]))
                combo_map[key]["total"] += wpp
                combo_map[key]["count"] += 1
        result = []
        for key, v in combo_map.items():
            if v["count"] >= 2:
                avg = round(v["total"] / v["count"], 1)
                result.append({
                    "combo": f"{key[0]} + {key[1]}",
                    "avg_waste_pp": str(avg),
                    "count": str(v["count"]),
                    "avg_num": avg,
                })
        result.sort(key=lambda x: x["avg_num"])
        return result[:10]

    @rx.var
    def has_combo_analysis(self) -> bool:
        return len(self.menu_combo_analysis) > 0

    # ══════════════════════════════
    #  수정7: 이상치 탐지 Z-Score
    # ══════════════════════════════
    @rx.var
    def anomaly_dates(self) -> list[dict]:
        """Z-Score |z|>2 이상치 날짜"""
        import math as _math
        vals = [float(r.get("waste_per_person", 0) or 0) for r in self.analysis_rows
                if float(r.get("waste_per_person", 0) or 0) > 0]
        if len(vals) < 3:
            return []
        avg = sum(vals) / len(vals)
        variance = sum((v - avg) ** 2 for v in vals) / len(vals)
        std = _math.sqrt(variance) if variance > 0 else 0
        if std == 0:
            return []
        result = []
        for r in self.analysis_rows:
            wpp = float(r.get("waste_per_person", 0) or 0)
            if wpp <= 0:
                continue
            z = (wpp - avg) / std
            if abs(z) > 2:
                anomaly_type = "급증" if z > 0 else "급감"
                result.append({
                    "date": str(r.get("meal_date", "")),
                    "waste_per_person": str(r.get("waste_per_person", "")),
                    "type": anomaly_type,
                    "z_score": str(round(z, 2)),
                })
        return result

    @rx.var
    def has_anomaly(self) -> bool:
        return len(self.anomaly_dates) > 0

    # ══════════════════════════════
    #  수정10: AI 일별 특이사항
    # ══════════════════════════════
    @rx.var
    def has_ai_daily_remarks(self) -> bool:
        return bool(self.ai_daily_remarks)

    @rx.var
    def daily_remarks_list(self) -> list[dict]:
        """ai_daily_remarks dict → foreach 가능한 list[dict]"""
        return [
            {"date": k, "remark": v}
            for k, v in self.ai_daily_remarks.items()
        ]

    # ══════════════════════════════
    #  수정13: 전체 메뉴 통계
    # ══════════════════════════════
    @rx.var
    def all_menu_stats(self) -> list[dict]:
        """전체 메뉴별 통계 — count desc"""
        import json as _j
        from collections import defaultdict
        menu_map: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
        for r in self.analysis_rows:
            wpp = float(r.get("waste_per_person", 0) or 0)
            menus_raw = r.get("menu_items", "[]")
            try:
                menus = _j.loads(menus_raw) if isinstance(menus_raw, str) else menus_raw
            except Exception:
                continue
            if not isinstance(menus, list):
                continue
            for m in menus:
                name = str(m).strip()
                if not name:
                    continue
                menu_map[name]["total"] += wpp if wpp > 0 else 0
                menu_map[name]["count"] += 1
        result = []
        for name, v in menu_map.items():
            avg = round(v["total"] / v["count"], 1) if v["count"] > 0 else 0.0
            result.append({
                "menu": name,
                "count": str(v["count"]),
                "avg_waste_pp": str(avg),
                "count_num": v["count"],
            })
        result.sort(key=lambda x: x["count_num"], reverse=True)
        return result

    @rx.var
    def has_all_menu_stats(self) -> bool:
        return len(self.all_menu_stats) > 0

    # ══════════════════════════════
    #  수정14: 배식인원 효율 분석
    # ══════════════════════════════
    @rx.var
    def servings_analysis(self) -> list[dict]:
        """배식인원 구간별 평균 1인당 잔반"""
        buckets = [
            ("~100명", 0, 100),
            ("100~200명", 100, 200),
            ("200~300명", 200, 300),
            ("300~400명", 300, 400),
            ("400명+", 400, 999999),
        ]
        data: dict = {b[0]: {"total": 0.0, "count": 0} for b in buckets}
        for r in self.analysis_rows:
            srv = int(r.get("servings", 0) or 0)
            wpp = float(r.get("waste_per_person", 0) or 0)
            if srv <= 0 or wpp <= 0:
                continue
            for label, lo, hi in buckets:
                if lo < srv <= hi:
                    data[label]["total"] += wpp
                    data[label]["count"] += 1
                    break
        result = []
        for label, lo, hi in buckets:
            d = data[label]
            if d["count"] > 0:
                avg = round(d["total"] / d["count"], 1)
                result.append({"range": label, "avg_waste_pp": avg, "count": d["count"]})
        return result

    @rx.var
    def has_servings_analysis(self) -> bool:
        return len(self.servings_analysis) > 0

    # ══════════════════════════════
    #  초기화
    # ══════════════════════════════

    def on_meal_load(self):
        if not self.is_authenticated:
            return rx.redirect("/")
        if self.user_role not in ("meal_manager", "school_nutrition"):
            return rx.redirect("/")
        # site_name = 첫 번째 학교
        schools = [s.strip() for s in self.user_schools.split(",") if s.strip()]
        if schools:
            self.site_name = schools[0]
        self.load_school_standard()
        self.load_tab_data()

    # ══════════════════════════════
    #  탭 전환 / 필터
    # ══════════════════════════════

    def refresh_meal_dates(self):
        """급식식단 갱신 — 현재 탭 데이터 새로고침."""
        self.msg = "급식 데이터 갱신 중..."
        self.msg_ok = True
        self.load_tab_data()
        self.msg = "갱신 완료"

    def toggle_calendar_open(self):
        """달력 섹션 접기/펴기."""
        self.calendar_open = not self.calendar_open

    def toggle_day(self, date: str):
        """일별 식단 펼치기/접기 — 같은 날짜 클릭 시 접힘, 다른 날짜 클릭 시 교체."""
        if self.expanded_date == date:
            self.expanded_date = ""
        else:
            self.expanded_date = date

    def clear_expanded_date(self):
        """달력 상세 패널 닫기."""
        self.expanded_date = ""

    def delete_selected_menu(self):
        """expanded_date 식단 삭제."""
        if not self.expanded_date:
            return
        ok = meal_delete_menu(self.site_name, self.expanded_date)
        if ok:
            self.msg = f"{self.expanded_date} 식단 삭제"
            self.msg_ok = True
            self.expanded_date = ""
            self.load_menus()
            self.load_meal_calendar()
        else:
            self.msg = "삭제 실패"
            self.msg_ok = False

    def set_active_tab(self, tab: str):
        self.active_tab = tab
        self.msg = ""
        self.load_tab_data()

    def set_selected_year(self, y: str):
        self.selected_year = y
        self.load_tab_data()

    def set_selected_month(self, m: str):
        self.selected_month = m.zfill(2)
        self.load_tab_data()

    def load_tab_data(self):
        if not self.site_name:
            return
        tab = self.active_tab
        if tab == "식단등록":
            self.load_menus()
            self.load_meal_calendar()
            self.load_collections()
        elif tab == "스마트잔반분석":
            self.load_analysis()
        elif tab == "AI잔반분석":
            self.load_ai_analysis()
        elif tab == "정산확인":
            self.load_settlement()
        elif tab == "ESG보고서":
            self.load_esg()

    # ══════════════════════════════
    #  탭1: 식단등록
    # ══════════════════════════════

    def load_default_servings(self):
        """customer_info.student_count → mf_servings 기본값 (수정11)"""
        cnt = meal_get_school_student_count(self.site_name)
        if cnt > 0 and (self.mf_servings == "0" or not self.mf_servings):
            self.mf_servings = str(cnt)

    def load_menus(self):
        ym = f"{self.selected_year}-{self.selected_month.zfill(2)}"
        self.menu_rows = meal_get_menus(self.site_name, ym)
        self.load_default_servings()

    def set_mf_date(self, v: str):
        self.mf_date = v

    def set_mf_menu(self, v: str):
        self.mf_menu = v

    def set_mf_calories(self, v: str):
        self.mf_calories = v

    def set_mf_servings(self, v: str):
        self.mf_servings = v

    def set_mf_nut(self, key: str, value: str = ""):
        """영양정보 항목 업데이트 (수정1)"""
        self.mf_nutrition = {**self.mf_nutrition, key: value}

    def save_menu(self):
        if not self.mf_date or not self.mf_menu:
            self.msg = "날짜와 메뉴를 입력하세요."
            self.msg_ok = False
            return
        import json
        menu_list = [m.strip() for m in self.mf_menu.split(",") if m.strip()]
        menu_json = json.dumps(menu_list, ensure_ascii=False)
        try:
            cal = int(self.mf_calories)
        except (ValueError, TypeError):
            cal = 0
        try:
            srv = int(self.mf_servings)
        except (ValueError, TypeError):
            srv = 0

        # ── 칼로리 범위 검증 (0~5000kcal) ──
        if cal < 0 or cal > 5000:
            self.msg = "칼로리는 0~5000 범위여야 합니다."
            self.msg_ok = False
            return

        # ── 인원수 범위 검증 (0~10000명) ──
        if srv < 0 or srv > 10000:
            self.msg = "인원수는 0~10,000 범위여야 합니다."
            self.msg_ok = False
            return

        import json as _json_sn
        nutrition_json = _json_sn.dumps(self.mf_nutrition, ensure_ascii=False)
        ok = meal_save_menu(
            self.site_name, self.mf_date, "중식",
            menu_json, cal, srv, nutrition_json,
        )
        if ok:
            draft_n = save_meal_schedule_drafts(self.site_name, [self.mf_date])
            draft_msg = f" (수거일정 초안 {draft_n}건 생성)" if draft_n > 0 else ""
            self.msg = f"{self.mf_date} 식단 저장 완료{draft_msg}"
            self.msg_ok = True
            self.mf_date = ""
            self.mf_menu = ""
            self.mf_calories = "0"
            self.mf_servings = "0"
            self.mf_nutrition = {}
            self.load_menus()
        else:
            self.msg = "저장 실패"
            self.msg_ok = False

    def delete_menu(self, meal_date: str):
        ok = meal_delete_menu(self.site_name, meal_date)
        if ok:
            self.msg = f"{meal_date} 식단 삭제"
            self.msg_ok = True
            self.load_menus()
        else:
            self.msg = "삭제 실패"
            self.msg_ok = False

    # ══════════════════════════════
    #  NEIS 엑셀 파서 헬퍼
    # ══════════════════════════════

    NUTRITION_KEYS = ["에너지(kcal)", "탄수화물(g)", "단백질(g)", "지방(g)",
                       "비타민A(μg RE)", "티아민(mg)", "리보플라빈(mg)", "비타민C(mg)", "칼슘(mg)"]

    @staticmethod
    def _parse_menu_items(raw: str) -> list:
        """NEIS 요리명 파싱: <br/>/\n 분리 + 알러지 코드 제거"""
        import re as _re
        if not raw:
            return []
        items = _re.split(r"<br\s*/?>\s*|\n", str(raw))
        result = []
        for item in items:
            item = item.strip()
            if not item:
                continue
            # 알러지 코드 제거 (예: "김치찌개 (5.9.)" → "김치찌개")
            item = _re.sub(r"\s*[\(\[]\s*[\d\s\.]+[\)\]]", "", item).strip()
            if item:
                result.append(item)
        return result

    @staticmethod
    def _parse_nutrition(raw: str) -> dict:
        """NEIS 영양소 문자열 → 9항목 dict"""
        import re as _re
        result: dict = {}
        if not raw:
            return result
        # "에너지(kcal) : 650" 형태 또는 숫자만 있는 경우 처리
        parts = _re.split(r"[,\n]", str(raw))
        for part in parts:
            part = part.strip()
            if ":" in part:
                k, _, v = part.partition(":")
                result[k.strip()] = v.strip()
        return result

    @staticmethod
    def _parse_calories(raw: str) -> int:
        """문자열에서 숫자(칼로리) 추출"""
        import re as _re
        m = _re.search(r"[\d]+\.?[\d]*", str(raw or ""))
        if m:
            try:
                return int(float(m.group()))
            except (ValueError, TypeError):
                return 0
        return 0

    # ══════════════════════════════
    #  탭2: 스마트잔반분석
    # ══════════════════════════════

    def load_analysis(self):
        ym = f"{self.selected_year}-{self.selected_month.zfill(2)}"
        self.analysis_rows = meal_analyze_waste(self.site_name, ym)
        # 차트용 숫자 필드 추가 (Phase 9)
        for r in self.analysis_rows:
            r["waste_num"] = float(r.get("waste_kg", 0) or 0)
            r["pp_num"] = float(r.get("waste_per_person", 0) or 0)
        self.analysis_summary = meal_get_analysis_summary(self.analysis_rows)
        best, worst = meal_get_menu_ranking(self.analysis_rows)
        self.best_menus = best
        self.worst_menus = worst
        wd = meal_get_weekday_pattern(self.analysis_rows)
        for r in wd:
            r["avg_num"] = float(r.get("avg_kg", 0) or 0)
            r["pp_num"] = float(r.get("avg_pp", 0) or 0)
        self.weekday_pattern = wd
        # 수정3: 트렌드 로드
        self.load_trends()

    # ══════════════════════════════
    #  수정4: 학교급식법 공식기준 로드
    # ══════════════════════════════

    def load_school_standard(self):
        from zeroda_reflex.utils.database import _detect_school_level
        school_type = _detect_school_level(self.site_name)
        self.school_standard = get_school_standard(school_type)
        self.waste_grade_table = list(WASTE_GRADE_TABLE)

    # ══════════════════════════════
    #  수정1: 달력형 식단 보기
    # ══════════════════════════════

    def load_meal_calendar(self):
        import calendar as _cal
        ym = f"{self.selected_year}-{self.selected_month.zfill(2)}"
        self.calendar_month = ym
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        # 식단 날짜 맵
        menu_list = meal_get_menus_by_month(self.site_name, ym)
        menu_map = {item["date"]: item["summary"] for item in menu_list}
        # 수거 날짜 집합
        collected = set(meal_get_collected_dates(self.site_name, ym))
        # 달력 셀 평탄화 (각 셀에 col 0~6, row_end="1"이면 행 마지막)
        first_wd, num_days = _cal.monthrange(y, m)
        cells: list = []
        col = 0
        # 앞쪽 빈 셀
        for _ in range(first_wd):
            cells.append({"day": "", "date": "", "has_menu": "0",
                          "has_collect": "0", "menu_summary": "",
                          "row_end": "1" if col == 6 else "0"})
            col += 1
        for day in range(1, num_days + 1):
            date_str = f"{y}-{str(m).zfill(2)}-{str(day).zfill(2)}"
            is_row_end = "1" if col == 6 else "0"
            cells.append({
                "day": str(day),
                "date": date_str,
                "has_menu": "1" if date_str in menu_map else "0",
                "has_collect": "1" if date_str in collected else "0",
                "menu_summary": menu_map.get(date_str, ""),
                "row_end": is_row_end,
            })
            col = (col + 1) % 7
        # 뒤쪽 빈 셀 패딩
        while col != 0:
            is_row_end = "1" if col == 6 else "0"
            cells.append({"day": "", "date": "", "has_menu": "0",
                          "has_collect": "0", "menu_summary": "", "row_end": is_row_end})
            col = (col + 1) % 7
        self.calendar_cells = cells

    # ══════════════════════════════
    #  수정3: 잔반 트렌드 로드
    # ══════════════════════════════

    def set_trend_subtab(self, tab: str):
        self.trend_subtab = tab

    def load_trends(self):
        if not self.site_name:
            return
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return
        self.monthly_trend = meal_get_monthly_trend(self.site_name, y)
        self.seasonal_compare = meal_get_seasonal_compare(self.site_name, y)

    # ══════════════════════════════
    #  탭3: AI잔반분석
    # ══════════════════════════════

    def load_ai_analysis(self):
        # 분석 데이터 + 비용
        if not self.analysis_rows:
            ym = f"{self.selected_year}-{self.selected_month.zfill(2)}"
            self.analysis_rows = meal_analyze_waste(self.site_name, ym)
            self.analysis_summary = meal_get_analysis_summary(self.analysis_rows)
            best, worst = meal_get_menu_ranking(self.analysis_rows)
            self.best_menus = best
            self.worst_menus = worst
            self.weekday_pattern = meal_get_weekday_pattern(self.analysis_rows)
        self.cost_data = meal_get_cost_savings(self.site_name, self.analysis_rows)

    def set_ai_api_key(self, key: str):
        """사용자 입력 API 키 저장"""
        self.ai_api_key = key.strip()
        self.ai_error = ""

    async def run_ai_comprehensive(self):
        """AI 종합 잔반분석 실행 (비동기)"""
        from zeroda_reflex.utils.ai_service import (
            _build_comprehensive_prompt as _build_prompt, call_claude_api,
        )
        if not self.analysis_rows:
            self.ai_error = "분석할 데이터가 없습니다. 먼저 잔반 데이터를 로드하세요."
            return

        self.ai_loading = True
        self.ai_error = ""
        self.ai_comprehensive_result = ""
        yield  # UI 업데이트 (로딩 표시)

        # 수정9: 강화된 프롬프트 (이상치+조합 포함)
        prompt = _build_prompt(
            self.site_name, self.analysis_rows, self.cost_data,
            anomaly_dates=list(self.anomaly_dates),
            combo_analysis=list(self.menu_combo_analysis),
        )
        result = call_claude_api(prompt, self.ai_api_key)

        self.ai_loading = False
        if result.startswith("[ERROR]"):
            self.ai_error = result.replace("[ERROR] ", "")
        else:
            self.ai_comprehensive_result = result

    async def run_ai_recommend(self):
        """AI 추천식단 생성 (비동기)"""
        from zeroda_reflex.utils.ai_service import (
            build_recommend_prompt, call_claude_api, parse_recommend_json,
        )
        if not self.analysis_rows:
            self.ai_error = "분석할 데이터가 없습니다."
            return

        self.ai_loading = True
        self.ai_error = ""
        self.ai_recommend_result = []
        yield  # UI 업데이트

        prompt = build_recommend_prompt(self.site_name, self.analysis_rows)
        result = call_claude_api(prompt, self.ai_api_key)

        self.ai_loading = False
        if result.startswith("[ERROR]"):
            self.ai_error = result.replace("[ERROR] ", "")
        else:
            parsed = parse_recommend_json(result)
            if parsed:
                # dict의 모든 값을 str로 변환 (Reflex 직렬화)
                self.ai_recommend_result = [
                    {
                        "day": str(r.get("day", "")),
                        "menu": ", ".join(r["menu"]) if isinstance(r.get("menu"), list) else str(r.get("menu", "")),
                        "expected_waste": str(r.get("expected_waste", "")),
                        "reason": str(r.get("reason", "")),
                    }
                    for r in parsed
                ]
            else:
                # JSON 파싱 실패 시 원문 텍스트를 종합분석 결과에 표시
                self.ai_comprehensive_result = result

    async def run_ai_cause_analysis(self):
        """AI 잔반 원인 분석 (수정5)"""
        from zeroda_reflex.utils.ai_service import call_claude_api
        if not self.analysis_rows:
            self.ai_error = "분석할 데이터가 없습니다."
            return
        self.ai_cause_loading = True
        self.ai_error = ""
        self.ai_cause_result = ""
        yield

        bad_menus = "\n".join(
            f"- {r['menu']} ({r['avg_waste_pp']}g/인, {r['count']}회)"
            for r in self.worst_menus[:10]
        ) or "- 데이터 없음"
        wd_text = "\n".join(
            f"- {r['weekday']}: {r['avg_pp']}g/인"
            for r in self.weekday_pattern
        ) or "- 데이터 없음"
        avg_wpp = self.analysis_summary.get("avg_waste_pp", "0")
        prompt = f"""당신은 단체급식 잔반 원인 분석 전문가입니다.
아래 데이터를 기반으로 잔반 발생 원인을 심층 분석하세요.

## 기관: {self.site_name}
## 평균 1인당 잔반: {avg_wpp}g

## 잔반 많은 메뉴 TOP10
{bad_menus}

## 요일별 패턴
{wd_text}

## 분석 항목
1. **주요 원인 분석**: 메뉴/계절/요일/조리법 등 측면별 원인
2. **메뉴별 기피 원인**: 잔반 많은 메뉴의 학생 기피 이유
3. **패턴 분석**: 잔반 증가 패턴과 상관관계
4. **즉시 개선 방안**: 3가지 구체적 실행 방안

마크다운 형식으로 한국어로 작성하세요."""

        result = call_claude_api(prompt, self.ai_api_key)
        self.ai_cause_loading = False
        if result.startswith("[ERROR]"):
            self.ai_error = result.replace("[ERROR] ", "")
        else:
            self.ai_cause_result = result

    def save_ai_recommendations(self):
        """AI 추천식단 일괄등록 (수정8)"""
        import json as _j
        from datetime import datetime as _dt, timedelta as _td
        if not self.ai_recommend_result:
            self.msg = "저장할 추천식단이 없습니다."
            self.msg_ok = False
            return
        # 다음 월요일부터 시작
        today = _dt.now()
        days_to_mon = (7 - today.weekday()) % 7
        if days_to_mon == 0:
            days_to_mon = 7
        start = today + _td(days=days_to_mon)

        ok_count = 0
        saved_dates = []
        for idx, r in enumerate(self.ai_recommend_result):
            date_str = (start + _td(days=idx)).strftime("%Y-%m-%d")
            menu_val = r.get("menu", "")
            if isinstance(menu_val, list):
                menu_json = _j.dumps(menu_val, ensure_ascii=False)
            else:
                menu_list = [m.strip() for m in str(menu_val).split(",") if m.strip()]
                menu_json = _j.dumps(menu_list, ensure_ascii=False)

            ok = meal_save_menu(
                self.site_name, date_str, "중식",
                menu_json, 0, 0,
            )
            if ok:
                ok_count += 1
                saved_dates.append(date_str)

        draft_n = save_meal_schedule_drafts(self.site_name, saved_dates)
        self.msg = f"AI 추천식단 {ok_count}건 등록 완료 (수거일정 초안 {draft_n}건 생성)"
        self.msg_ok = ok_count > 0
        self.load_meal_calendar()

    async def generate_daily_remarks(self):
        """AI 일별 특이사항 생성 (수정10)"""
        from zeroda_reflex.utils.ai_service import call_claude_api
        import json as _j
        if not self.analysis_rows:
            self.ai_error = "분석할 데이터가 없습니다."
            return
        self.ai_daily_loading = True
        self.ai_error = ""
        yield

        data_json = _j.dumps([
            {"date": r.get("meal_date", ""),
             "waste_pp": r.get("waste_per_person", ""),
             "grade": r.get("grade", ""),
             "menu": r.get("menu_items", "")}
            for r in self.analysis_rows
        ], ensure_ascii=False)

        prompt = f"""아래 급식 잔반 데이터의 각 날짜별 특이사항을 한 문장으로 코멘트하세요.
기관: {self.site_name}
데이터: {data_json}

반드시 아래 JSON 형식으로만 답변하세요:
{{"YYYY-MM-DD": "코멘트", "YYYY-MM-DD": "코멘트"}}

한국어로 답변하세요."""

        result = call_claude_api(prompt, self.ai_api_key)
        self.ai_daily_loading = False
        if result.startswith("[ERROR]"):
            self.ai_error = result.replace("[ERROR] ", "")
            return

        import re as _re
        m = _re.search(r'\{[^{}]*\}', result, _re.DOTALL)
        if m:
            try:
                parsed = _j.loads(m.group())
                if isinstance(parsed, dict):
                    self.ai_daily_remarks = {str(k): str(v) for k, v in parsed.items()}
            except Exception:
                self.ai_daily_remarks = {}

    def download_ai_pdf(self):
        """AI 월말명세서 PDF 다운로드"""
        from zeroda_reflex.utils.pdf_export import build_ai_meal_statement_pdf
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return None
        if not self.analysis_rows:
            return None
        best, worst = meal_get_menu_ranking(self.analysis_rows)
        pdf_bytes = build_ai_meal_statement_pdf(
            self.site_name, y, m, self.analysis_rows,
            menu_ranking={"best": best, "worst": worst},
            ai_comment=self.ai_comprehensive_result[:2000] if self.ai_comprehensive_result else "",
            cost_savings=self.cost_data,
            weekday_pattern=self.weekday_pattern,
            daily_remarks=self.ai_daily_remarks,
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"AI월말명세서_{self.site_name}_{y}-{str(m).zfill(2)}.pdf",
            )
        return None

    def load_collections(self):
        """달력 수거 상세용 — 현재 년/월 수거 기록 로드."""
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        self.collection_rows = school_filter_collections(self.site_name, y, m)

    # ══════════════════════════════
    #  탭5: 정산확인
    # ══════════════════════════════

    def load_settlement(self):
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return
        result = meal_get_settlement(self.site_name, y, m)
        self.settle_items = result.pop("items", [])
        self.settle_data = result

    # ══════════════════════════════
    #  탭6: ESG보고서
    # ══════════════════════════════

    def load_esg(self):
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return
        self.esg_data = meal_get_esg(self.site_name, y)

    # ══════════════════════════════
    #  PDF 다운로드 핸들러
    # ══════════════════════════════

    def download_smart_pdf(self):
        """스마트월말명세서 PDF 다운로드"""
        from zeroda_reflex.utils.pdf_export import build_meal_statement_pdf
        try:
            y = int(self.selected_year)
            m = int(self.selected_month)
        except (ValueError, TypeError):
            return None
        if not self.analysis_rows:
            return None
        best, worst = meal_get_menu_ranking(self.analysis_rows)
        ranking = {"best": best, "worst": worst}
        pdf_bytes = build_meal_statement_pdf(
            self.site_name, y, m, self.analysis_rows, ranking,
        )
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"스마트월말명세서_{self.site_name}_{y}-{str(m).zfill(2)}.pdf",
            )
        return None

    def download_esg_pdf(self):
        """급식 ESG 보고서 PDF 다운로드"""
        from zeroda_reflex.utils.pdf_export import build_school_esg_pdf
        from zeroda_reflex.utils.database import school_filter_collections
        try:
            y = int(self.selected_year)
        except (ValueError, TypeError):
            return None
        rows = school_filter_collections(self.site_name, y, 0)
        if not rows:
            return None
        month_label = f"{y}년 전체"
        # vendor 정보 조회 — PDF 헤더에 업체명 표기
        from zeroda_reflex.utils.database import school_get_vendors
        try:
            vendors = school_get_vendors(self.site_name)
            vendor = vendors[0] if vendors else ""
        except Exception:
            vendor = ""
        pdf_bytes = build_school_esg_pdf(self.site_name, y, month_label, rows, vendor)
        if pdf_bytes:
            return rx.download(
                data=pdf_bytes,
                filename=f"ESG보고서_{self.site_name}_{y}.pdf",
            )
        return None

    # ══════════════════════════════
    #  Excel 다운로드 핸들러
    # ══════════════════════════════

    def download_meal_excel(self):
        """식단 및 잔반 분석 데이터 Excel 다운로드 (급식담당자)"""
        # menu_rows + analysis_rows + cost_data 통합 다운로드
        from zeroda_reflex.utils.excel_export import export_meal_data
        meal_data = {
            "menus": self.menu_rows,
            "analysis": self.analysis_rows,
            "best_menus": self.best_menus,
            "worst_menus": self.worst_menus,
            "weekday_pattern": self.weekday_pattern,
            "cost_data": self.cost_data,
        }
        if not any(meal_data.values()):
            return None
        xlsx = export_meal_data(meal_data, self.site_name, self.selected_year, self.selected_month)
        if xlsx:
            return rx.download(
                data=xlsx,
                filename=f"식단분석_{self.site_name}_{self.selected_year}-{self.selected_month.zfill(2)}.xlsx"
            )
        return None
