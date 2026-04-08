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


def _build_comprehensive_prompt(
    site_name: str,
    analysis_rows: list,
    cost_data: dict | None = None,
    anomaly_dates: list | None = None,
    combo_analysis: list | None = None,
) -> str:
    """강화된 종합 잔반분석 프롬프트"""
    stats = _build_menu_stats(analysis_rows)
    monthly = _build_monthly_summary(analysis_rows)
    weekday = _build_weekday_text(analysis_rows)

    # 핵심 지표
    total_waste = sum(float(r.get("waste_kg", 0) or 0) for r in analysis_rows)
    avg_wpp = stats["overall_avg"]

    # TOP5 잔반 많은/적은 메뉴
    bad5 = "\n".join(
        f"- {m['menu']} ({m['avg_waste']:.1f}g/인, {m['count']}회)"
        for m in stats["bad"][:5]
    ) or "- 데이터 없음"
    good5 = "\n".join(
        f"- {m['menu']} ({m['avg_waste']:.1f}g/인, {m['count']}회)"
        for m in stats["good"][:5]
    ) or "- 데이터 없음"

    # 이상치
    anomaly_text = ""
    if anomaly_dates:
        lines = [
            f"- {a['date']}: {a['type']} ({a['waste_per_person']}g/인, Z={a['z_score']})"
            for a in anomaly_dates
        ]
        anomaly_text = "\n## 이상치 날짜\n" + "\n".join(lines)

    # 메뉴 조합
    combo_text = ""
    if combo_analysis:
        lines = [
            f"- {c['combo']}: 평균 {c['avg_waste_pp']}g/인 ({c['count']}회)"
            for c in combo_analysis[:5]
        ]
        combo_text = "\n## 잔반 적은 메뉴 조합 TOP5\n" + "\n".join(lines)

    # 비용
    cost_text = ""
    if cost_data and float(cost_data.get("unit_price", 0) or 0) > 0:
        cost_text = f"""
## 비용 정보
- 음식물 처리 단가: {cost_data.get('unit_price', 0)}원/kg
- 월 처리비용: {cost_data.get('current_cost', 0)}원
- 10% 절감 시: {cost_data.get('save_10pct', 0)}원/월"""

    return f"""당신은 단체급식 잔반 분석 전문가입니다.
아래 데이터를 기반으로 종합 분석 리포트를 작성하세요.

## 기관: {site_name}
## 분석 일수: {len(analysis_rows)}일
## 핵심 지표
- 전체 평균 1인당 잔반: {avg_wpp:.1f}g
- 총 잔반량: {total_waste:.1f}kg

## 잔반 등급 기준
- A등급: 150g 미만 (우수) | B등급: 150~245g (양호)
- C등급: 245~300g (주의) | D등급: 300g 이상 (경보)

## 월별 추이
{monthly}

## 잔반 많은 메뉴 TOP5
{bad5}

## 잔반 적은 메뉴 TOP5
{good5}

{weekday}
{anomaly_text}
{combo_text}
{cost_text}

## 작성 항목 (반드시 모두 포함)
1. **종합 평가**: 전체적인 잔반 관리 수준
2. **월별 트렌드 분석**: 증감 패턴 및 원인 추정
3. **요일별 패턴 분석**: 요일별 잔반 차이 원인과 대응
4. **메뉴 분석**: 잔반 많은 메뉴 원인과 개선 방안
5. **비용 절감 방안**: 구체적 절감 목표와 실행 방안
6. **개선 권고사항**: 5가지 즉시 실행 가능한 방안
7. **목표 설정**: 다음 분기 잔반 감소 목표

마크다운 형식으로 간결하게 작성하세요. 한국어로 답변하세요."""


def build_comprehensive_prompt(
    site_name: str,
    analysis_rows: list,
    cost_data: dict | None = None,
) -> str:
    """종합 잔반분석 프롬프트 구성"""
    return _build_comprehensive_prompt(site_name, analysis_rows, cost_data)


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


def build_esg_ai_prompt(
    org_name: str,
    org_type: str,            # "학교" | "급식소" | "교육청"
    year: int,
    month_label: str,         # 예) "2026년 전체", "2026년 4월"
    esg_data: dict,           # school_get_esg / meal_get_esg 반환값
    rows: list,               # real_collection raw rows (선택)
    vendor: str = "",
) -> str:
    """ESG 보고서 AI 작성용 프롬프트.

    출력 지침: 마크다운, 한국어, 5개 섹션(요약/상세/시사점/개선안/외부공개문구).
    PDF 변환 시 헤더 레벨이 잘 보이도록 ## / ### 위주로 작성하도록 유도.
    """
    total_kg = esg_data.get("total_kg", "0")
    food_kg = esg_data.get("food_kg", "0")
    recycle_kg = esg_data.get("recycle_kg", "0")
    general_kg = esg_data.get("general_kg", "0")
    carbon = esg_data.get("carbon_reduced", "0")
    tree = esg_data.get("tree_equivalent", "0")
    carbon_t = esg_data.get("carbon_tons", "0")
    count = esg_data.get("count", "0")

    sample_lines = []
    for r in (rows or [])[:8]:
        sample_lines.append(
            f"- {r.get('collect_date','')} | {r.get('item_type','')} | "
            f"{r.get('weight','0')}kg | {r.get('vendor','')}"
        )
    sample_block = "\n".join(sample_lines) if sample_lines else "- (수거 원본 데이터 표본 없음)"

    vendor_line = f"- 협력 수거업체: {vendor}\n" if vendor else ""

    return f"""당신은 학교·공공기관 ESG 폐기물 감축 보고서를 작성하는 환경경영 컨설턴트입니다.
아래 실측 데이터를 토대로 외부 공개 가능한 ESG 보고서 본문을 작성하세요.

# 기관 정보
- 기관 유형: {org_type}
- 기관명: {org_name}
- 보고 기간: {month_label}
{vendor_line}- 보고 작성일 기준연도: {year}

# 실측 집계 (zeroda 수거 데이터 기반)
- 총 수거량: {total_kg} kg
- 음식물 폐기물: {food_kg} kg
- 재활용 폐기물: {recycle_kg} kg
- 일반 폐기물: {general_kg} kg
- 탄소 감축량: {carbon} kg CO₂ ({carbon_t} tCO₂)
- 나무 환산: {tree} 그루
- 수거 건수: {count} 건

# 수거 원본 표본 (최대 8건)
{sample_block}

# 작성 지침
1. **마크다운**으로 작성, 한국어, 5개 섹션 고정.
2. 모든 섹션 제목은 `## 1. 요약` 형태의 H2 사용. 본문은 일반 단락.
3. 숫자는 위에 제공된 값만 사용. 임의 추정 금지.
4. 비교/벤치마크 수치를 만들어내지 말 것 (없으면 "비교 데이터 미제공"으로 명시).
5. 톤: 공공기관·학부모 대상의 신뢰감 있는 어조.
6. 분량: 섹션당 3~6 문장.

# 필수 섹션
## 1. 요약
보고 기간 동안의 핵심 성과를 3~4문장으로 압축. 총 수거량, 탄소 감축 효과, 나무 환산 1건씩 포함.

## 2. 폐기물 분류별 상세
음식물/재활용/일반 각각의 배출량과 비중(%)을 계산해서 서술. 비중은 위 숫자로 직접 산출.

## 3. 환경 영향 시사점
탄소 감축량과 나무 환산 결과가 갖는 의미. 사회적·환경적 함의 1~2문단.

## 4. 개선 권고
이 데이터를 바탕으로 다음 분기에 시도해볼 만한 실행 과제 3개. 각 과제는 한 줄 제목 + 1~2문장 설명.

## 5. 외부 공개 문구 (그대로 인용 가능)
학부모 안내문·홈페이지 게시용으로 그대로 복사해서 쓸 수 있는 4~5문장 단락. 인용부호 없이 평문으로.

지금 작성 시작.
"""


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


def extract_weigh_ticket(image_bytes: bytes, api_key: str = "") -> dict:
    """계량표(대금표) 이미지 → OCR → 5개 필드 dict 반환.

    반환 형식:
    {
        "first_weigh_time": "2026-04-08 14:05",  # 1차 계근시간 공차 (없으면 null)
        "second_weigh_time": "2026-04-08 14:23", # 2차 계근시간 실차 (없으면 null)
        "gross_weight": 7520.0,                   # 총중량 kg (없으면 null)
        "net_weight": 3240.0,                     # 실중량 kg (없으면 null)
        "vehicle_number": "12가3456",             # 차량번호 (없으면 null)
        "processor_company": "OO자원",            # 처분업체 상호 (없으면 null)
        "error": null                             # 오류 메시지 (성공 시 null)
    }
    """
    import base64

    key = api_key or _get_api_key()
    if not key:
        return {"error": "API 키가 설정되지 않았습니다. 서버 .env에 ANTHROPIC_API_KEY를 등록하세요.",
                "first_weigh_time": None, "second_weigh_time": None,
                "gross_weight": None, "net_weight": None,
                "vehicle_number": None, "processor_company": None}

    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic 패키지가 설치되지 않았습니다.",
                "first_weigh_time": None, "second_weigh_time": None,
                "gross_weight": None, "net_weight": None,
                "vehicle_number": None, "processor_company": None}

    _PROMPT = """이 이미지는 폐기물 수거 차량이 처리장에서 받은 계량표(대금표/계근표)입니다.
아래 6개 항목을 이미지에서 추출하여 JSON 형식으로만 응답하세요. 추가 설명 없이 JSON만 출력.

추출 항목:
- first_weigh_time: 1차 계근시간 (공차, 차량 진입 시각, 예: "2026-04-08 14:05", 없으면 null)
- second_weigh_time: 2차 계근시간 (실차, 반출 후 시각, 예: "2026-04-08 14:23", 없으면 null)
- gross_weight: 총중량 kg (숫자만, 톤 단위면 1000 곱해서 kg으로 환산, 없으면 null)
- net_weight: 실중량 kg (총중량 - 공차중량, 숫자만, 없으면 null)
- vehicle_number: 차량번호 (예: "12가3456", 없으면 null)
- processor_company: 처분업체 상호명 (없으면 null)

응답 형식 예시:
{"first_weigh_time": "2026-04-08 14:05", "second_weigh_time": "2026-04-08 14:23", "gross_weight": 7520.0, "net_weight": 3240.0, "vehicle_number": "12가3456", "processor_company": "OO자원"}"""

    try:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        # 이미지 타입 추론 (JPEG/PNG)
        media_type = "image/jpeg"
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            media_type = "image/png"

        client = anthropic.Anthropic(api_key=key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
        raw = message.content[0].text.strip()

        # JSON 블록 추출
        if "```json" in raw:
            raw = raw[raw.index("```json") + 7: raw.index("```", raw.index("```json") + 7)]
        elif "```" in raw:
            raw = raw[raw.index("```") + 3: raw.rindex("```")]

        parsed = json.loads(raw.strip())

        # 숫자 필드 float 변환
        for field in ("gross_weight", "net_weight"):
            v = parsed.get(field)
            if v is not None:
                try:
                    parsed[field] = float(v)
                except (ValueError, TypeError):
                    parsed[field] = None

        parsed.setdefault("first_weigh_time", None)
        parsed.setdefault("second_weigh_time", None)
        parsed.setdefault("gross_weight", None)
        parsed.setdefault("net_weight", None)
        parsed.setdefault("vehicle_number", None)
        parsed.setdefault("processor_company", None)
        parsed["error"] = None
        return parsed

    except json.JSONDecodeError as e:
        logger.warning(f"계량표 OCR JSON 파싱 실패: {e} / raw={raw!r}")
        return {"error": f"OCR 결과 파싱 실패: {e}",
                "first_weigh_time": None, "second_weigh_time": None,
                "gross_weight": None, "net_weight": None,
                "vehicle_number": None, "processor_company": None}
    except Exception as e:
        logger.error(f"계량표 OCR API 오류: {e}")
        return {"error": f"OCR 오류: {str(e)}",
                "first_weigh_time": None, "second_weigh_time": None,
                "gross_weight": None, "net_weight": None,
                "vehicle_number": None, "processor_company": None}


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
