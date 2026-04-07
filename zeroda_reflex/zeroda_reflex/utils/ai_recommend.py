# zeroda_reflex/zeroda_reflex/utils/ai_recommend.py
"""
AI 잔반 감축 추천식단 생성 — 고도화 버전
조건:
  1. C/D 등급 메뉴만 타겟
  2. 예산 상한선 (기본 3,500원/인)
  3. NEIS 19가지 알레르기 검증
  4. A등급 예상 메뉴로 대체
출력: 300자 이내, [AI 총평] + [다음 달 잔반 감축 추천 식단] 섹션
"""
from __future__ import annotations

import json
import logging
import os
import pathlib

logger = logging.getLogger(__name__)

# ── NEIS 19가지 알레르기 유발 물질 (학교급식법 기준) ──
NEIS_ALLERGENS: list[str] = [
    "난류", "우유", "메밀", "땅콩", "대두", "밀", "고등어", "게", "새우",
    "돼지고기", "복숭아", "토마토", "아황산류", "호두", "닭고기", "쇠고기",
    "오징어", "조개류", "잣",
]


def _get_api_key() -> str:
    """환경변수 → .env 파일 순서로 ANTHROPIC_API_KEY 조회"""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        env_path = pathlib.Path(__file__).resolve().parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def _extract_menus(analysis_rows: list[dict]) -> tuple[list[str], list[str]]:
    """
    analysis_rows에서 메뉴 추출.
    반환: (cd_menus: C/D 등급 메뉴 목록, all_menus: 전체 메뉴 목록)
    """
    cd_menus: list[str] = []
    all_menus: list[str] = []

    for r in analysis_rows:
        menus_raw = r.get("menu_items", "[]")
        try:
            menus: list = json.loads(menus_raw) if isinstance(menus_raw, str) else (menus_raw or [])
        except (json.JSONDecodeError, TypeError):
            menus = []

        names = [str(m).strip() for m in menus if m]
        all_menus.extend(names)

        if r.get("grade", "-") in ("C", "D"):
            cd_menus.extend(names)

    # 중복 제거 (순서 유지)
    def dedup(lst: list[str]) -> list[str]:
        seen: set[str] = set()
        return [x for x in lst if x not in seen and not seen.add(x)]  # type: ignore[func-returns-value]

    return dedup(cd_menus), dedup(all_menus)


def generate_ai_recommendation(
    analysis_rows: list[dict],
    site_name: str,
    year_month: str,
    budget_per_person: int = 3500,
    price_food: int | None = None,
) -> str:
    """
    AI 잔반 감축 추천식단 생성.

    Parameters
    ----------
    analysis_rows   meal_analyze_waste() 결과 리스트
    site_name       급식소(학교) 이름
    year_month      분석 기간 (YYYY-MM)
    budget_per_person  1인당 식재료 예산 상한 (원, 기본 3,500원)
    price_food      DB에서 가져온 실제 단가 (있으면 budget_per_person 대신 사용)

    Returns
    -------
    str  [AI 총평] + [다음 달 잔반 감축 추천 식단] 섹션 텍스트 (300자 이내)
         실패 시 "[ERROR] ..." 형식
    """
    api_key = _get_api_key()
    if not api_key:
        return "[ERROR] API 키가 설정되지 않았습니다. 환경변수 ANTHROPIC_API_KEY를 설정하세요."

    try:
        import anthropic
    except ImportError:
        return "[ERROR] anthropic 패키지가 설치되지 않았습니다. pip install anthropic 을 실행하세요."

    # ── C/D 등급 메뉴 및 전체 메뉴 추출 ──
    cd_menus, all_menus = _extract_menus(analysis_rows)

    # ── 예산 결정 ──
    effective_budget = price_food if (price_food and price_food > 0) else budget_per_person

    # ── 통계 요약 ──
    cd_count = len([r for r in analysis_rows if r.get("grade", "-") in ("C", "D")])
    total_count = len(analysis_rows)
    valid_pp = [float(r["waste_per_person"]) for r in analysis_rows
                if float(r.get("waste_per_person", 0) or 0) > 0]
    avg_pp = sum(valid_pp) / len(valid_pp) if valid_pp else 0

    cd_menu_text = "、".join(cd_menus) if cd_menus else "(C/D 등급 메뉴 없음)"
    all_menu_sample = "、".join(all_menus[:20]) if all_menus else "(데이터 없음)"
    allergen_text = "、".join(NEIS_ALLERGENS)

    # ── 시스템 프롬프트 (4가지 조건 명시) ──
    system_prompt = f"""당신은 학교급식 영양 전문가입니다.
아래 잔반 데이터를 분석하여 다음 달 잔반 감축 추천식단을 제안하세요.

[분석 기관 및 기간]
기관: {site_name}
기간: {year_month}
전체 분석일수: {total_count}일 (C/D 등급: {cd_count}일)
1인당 평균 잔반: {avg_pp:.1f}g

[잔반 등급 기준]
A등급(우수): 150g 미만 | B등급(양호): 150~245g | C등급(주의): 245~300g | D등급(경보): 300g 이상

[제약 조건 — 반드시 준수]
1. 대상 메뉴: C/D 등급을 받은 아래 메뉴만 타겟으로 대체 식단 제안
   C/D 등급 문제 메뉴: {cd_menu_text}

2. 예산 상한: 1인당 식재료 예산 {effective_budget:,}원 이하 메뉴만 추천
   예산 초과 예상 메뉴는 절대 추천 불가. 반드시 "(예산 내)"로 검증 표시.

3. 알레르기 검증: NEIS 19가지 알레르기 유발 물질 기준 검증 필수
   NEIS 알레르기 목록: {allergen_text}
   기존 식단 샘플: {all_menu_sample}
   기존 식단에 이미 포함된 알레르기원과 동일/유사 알레르기원 중복 금지.
   추천 메뉴 옆에 "(알레르기 없음)"으로 검증 표시.

4. 목표 등급: 추천 메뉴는 A등급(1인당 잔반 150g 미만) 달성 가능한 메뉴로 제한
   잔반이 적게 나올 것으로 예상되는 선호 메뉴 기반 추천.

[출력 형식 — 정확히 아래 2개 섹션 제목 사용, 전체 300자 이내]
[AI 총평]
현재 {year_month} 잔반 현황 평가 (1~2문장)

[다음 달 잔반 감축 추천 식단 (예산/알레르기 검증 완료)]
C/D 등급 메뉴별 대체안 (메뉴당 1줄 형식):
기존 메뉴명 → 대체 메뉴명 (A등급 예상, 예산 내, 알레르기 없음)
"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": system_prompt}],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"AI 추천식단 생성 실패: {e}")
        return f"[ERROR] AI 호출 실패: {str(e)}"
