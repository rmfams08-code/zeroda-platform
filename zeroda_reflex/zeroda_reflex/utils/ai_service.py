# zeroda_reflex/utils/ai_service.py
# Claude API 연동 — AI 잔반 분석 서비스
# Phase 5 AI: Anthropic API를 이용한 종합 잔반 분석 + 추천식단
import logging
import os
import json

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """Anthropic API 키 조회 (환경변수 → .env)"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    # .env 파일에서 읽기
    try:
        import pathlib
        env_path = pathlib.Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _build_menu_stats(analysis_rows: list) -> dict:
    """메뉴별 잔반 통계 계산"""
    menu_map: dict = {}
    total_waste_pp = []

    for r in analysis_rows:
        waste_pp = float(r.get("waste_per_person", 0) or 0)
        if waste_pp > 0:
            total_waste_pp.append(waste_pp)

        menus_raw = r.get("menu_items", "[]")
        try:
            menus = json.loads(menus_raw) if isinstance(menus_raw, str) else menus_raw
        except (json.JSONDecodeError, TypeError):
            menus = [menus_raw] if menus_raw else []

        for m in menus:
            name = str(m).strip()
            if not name:
                continue
            if name not in menu_map:
                menu_map[name] = {"menu": name, "total_waste": 0, "count": 0}
            menu_map[name]["total_waste"] += waste_pp
            menu_map[name]["count"] += 1

    # 평균 계산
    for v in menu_map.values():
        v["avg_waste"] = v["total_waste"] / v["count"] if v["count"] > 0 else 0

    sorted_menus = sorted(menu_map.values(), key=lambda x: x["avg_waste"])
    good = [m for m in sorted_menus if m["count"] >= 2][:10]
    bad = [m for m in reversed(sorted_menus) if m["count"] >= 2][:10]

    overall_avg = sum(total_waste_pp) / len(total_waste_pp) if total_waste_pp else 0

    return {"good": good, "bad": bad, "overall_avg": overall_avg}


def _build_monthly_summary(analysis_rows: list) -> str:
    """월별 잔반 요약 텍스트"""
    monthly: dict = {}
    for r in analysis_rows:
        ym = str(r.get("year_month", "") or r.get("meal_date", "")[:7])
        if not ym:
            continue
        if ym not in monthly:
            monthly[ym] = {"total_kg": 0, "count": 0, "grades": []}
        monthly[ym]["total_kg"] += float(r.get("waste_kg", 0) or 0)
        monthly[ym]["count"] += 1
        g = str(r.get("grade", "-"))
        if g != "-":
            monthly[ym]["grades"].append(g)

    lines = []
    for ym, d in sorted(monthly.items()):
        grade_dist = {}
        for g in d["grades"]:
            grade_dist[g] = grade_dist.get(g, 0) + 1
        lines.append(
            f"- {ym}: 총 {d['total_kg']:.1f}kg, {d['count']}일, 등급분포 {grade_dist}"
        )
    return "\n".join(lines) or "- 데이터 없음"


def _build_weekday_text(analysis_rows: list) -> str:
    """요일별 잔반 패턴 텍스트"""
    from collections import defaultdict
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    data: dict = defaultdict(lambda: {"total": 0, "count": 0})
    for r in analysis_rows:
        date_str = str(r.get("meal_date", ""))[:10]
        if len(date_str) < 10:
            continue
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            wd = day_names[dt.weekday()]
        except (ValueError, IndexError):
            continue
        waste_pp = float(r.get("waste_per_person", 0) or 0)
        data[wd]["total"] += waste_pp
        data[wd]["count"] += 1

    if not data:
        return ""
    lines = ["## 요일별 1인당 잔반"]
    for wd in day_names[:5]:  # 월~금만
        d = data.get(wd)
        if d and d["count"] > 0:
            avg = d["total"] / d["count"]
            lines.append(f"- {wd}요일: {avg:.1f}g/인 ({d['count']}회)")
    return "\n".join(lines)


def build_comprehensive_prompt(
    site_name: str,
    analysis_rows: list,
    cost_data: dict | None = None,
) -> str:
    """종합 잔반분석 프롬프트 구성"""
    stats = _build_menu_stats(analysis_rows)
    monthly = _build_monthly_summary(analysis_rows)
    weekday = _build_weekday_text(analysis_rows)

    good_list = "\n".join(
        f"- {m['menu']} ({m['avg_waste']:.1f}g/인, {m['count']}회)"
        for m in stats["good"]
    ) or "- 데이터 없음"

    bad_list = "\n".join(
        f"- {m['menu']} ({m['avg_waste']:.1f}g/인, {m['count']}회)"
        for m in stats["bad"]
    ) or "- 데이터 없음"

    # 비용 정보
    cost_text = ""
    if cost_data and float(cost_data.get("unit_price", 0) or 0) > 0:
        cost_text = f"""
## 비용 정보
- 음식물 처리 단가: {cost_data.get('unit_price', 0)}원/kg
- 월 처리비용: {cost_data.get('current_cost', 0)}원
- 10% 절감 시: {cost_data.get('save_10pct', 0)}원/월"""

    prompt = f"""당신은 단체급식 잔반 분석 전문가입니다.
아래 데이터를 기반으로 종합 분석 리포트를 작성하세요.

## 기관: {site_name}
## 분석 일수: {len(analysis_rows)}일
## 전체 평균 1인당 잔반: {stats['overall_avg']:.1f}g

## 잔반 등급 기준
- A등급: 150g 미만 (우수) | B등급: 150~245g (양호)
- C등급: 245~300g (주의) | D등급: 300g 이상 (경보)

## 월별 추이
{monthly}

## 잔반 적은 메뉴 TOP
{good_list}

## 잔반 많은 메뉴 TOP
{bad_list}
{weekday}
{cost_text}

## 작성 항목 (반드시 모두 포함)
1. **종합 평가**: 전체적인 잔반 관리 수준 (A~D 등급 기준)
2. **월별 트렌드 분석**: 증감 패턴 및 원인 추정
3. **요일별 패턴 분석**: 요일별 잔반 차이 원인과 대응 방안
4. **메뉴 분석**: 잔반 많은 메뉴의 원인과 개선 방안
5. **비용 절감 방안**: 구체적인 절감 목표와 실행 방안
6. **개선 권고사항**: 5가지 즉시 실행 가능한 방안
7. **목표 설정**: 다음 분기 잔반 감소 목표

마크다운 형식으로 간결하게 작성하세요. 한국어로 답변하세요."""

    return prompt


def build_recommend_prompt(
    site_name: str,
    analysis_rows: list,
    target_days: int = 5,
) -> str:
    """AI 추천식단 프롬프트 구성"""
    stats = _build_menu_stats(analysis_rows)

    good_list = "\n".join(
        f"- {m['menu']} ({m['avg_waste']:.1f}g/인)" for m in stats["good"]
    ) or "- 데이터 없음"
    bad_list = "\n".join(
        f"- {m['menu']} ({m['avg_waste']:.1f}g/인)" for m in stats["bad"]
    ) or "- 데이터 없음"

    prompt = f"""당신은 학교 영양교사이며 잔반 줄이기 전문가입니다.
아래 데이터를 기반으로 {target_days}일치 추천 식단을 작성하세요.

## 기관: {site_name}
## 평균 1인당 잔반: {stats['overall_avg']:.1f}g

## 잔반 적은 인기 메뉴
{good_list}

## 잔반 많은 비인기 메뉴
{bad_list}

## 작성 규칙
1. 잔반 적은 인기 메뉴 위주로 조합
2. 잔반 많은 메뉴는 조리법 변경 제안 포함
3. 각 일자: 밥, 국/찌개, 주반찬, 부반찬, 김치, 후식 구성
4. 예상 잔반량(g/인)과 절감 근거 포함
5. 영양균형 고려 (탄수화물:단백질:지방 = 6:2:2)

JSON 형식으로 답변하세요:
```json
[
  {{
    "day": "1일차 (월)",
    "menu": ["잡곡밥", "된장찌개", "돈까스", "시금치나물", "배추김치", "사과"],
    "expected_waste": 130,
    "reason": "인기 메뉴 조합으로 잔반 최소화"
  }}
]
```
한국어로 답변하세요."""

    return prompt


def call_claude_api(prompt: str, api_key: str = "") -> str:
    """Claude API 호출. 성공 시 응답 텍스트, 실패 시 에러 메시지 반환."""
    key = api_key or _get_api_key()
    if not key:
        return "[ERROR] API 키가 설정되지 않았습니다. 환경변수 ANTHROPIC_API_KEY를 설정하세요."

    try:
        import anthropic
    except ImportError:
        return "[ERROR] anthropic 패키지가 설치되지 않았습니다. pip install anthropic 을 실행하세요."

    try:
        client = anthropic.Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Claude API 호출 실패: {e}")
        return f"[ERROR] API 호출 실패: {str(e)}"


def parse_recommend_json(response: str) -> list[dict]:
    """AI 추천식단 응답에서 JSON 파싱"""
    try:
        # ```json ... ``` 블록 추출
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response.strip()

        data = json.loads(json_str)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"AI 추천식단 JSON 파싱 실패: {e}")
        return []
