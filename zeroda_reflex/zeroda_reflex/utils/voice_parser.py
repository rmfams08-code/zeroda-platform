# zeroda_reflex/zeroda_reflex/utils/voice_parser.py
"""음성 인식 전처리 유틸리티 (섹션 1+2)

- normalize_korean_number : STT 원문의 숫자 표현을 아라비아 숫자로 정규화
- jamo_decompose          : 한글 음절을 초성+중성+종성 자모로 분해
- generate_auto_aliases   : 거래처명에서 자동 약칭 후보 생성 (접미사 제거 등)
- build_match_pool        : 자동약칭+수동별칭 통합 매칭풀 구축 ({alias → canonical})
- match_school_by_jamo    : 자모+원문 유사도 기반 거래처명 매칭
"""

import re
from difflib import SequenceMatcher
from typing import Optional

# ── 혼동 맵 (STT 오인식 패턴 — 안전한 2음절 이상만) ──
_CONFUSION_MAP: dict[str, str] = {
    "샘백": "삼백",
    "샘천": "삼천",
    "유백": "육백",
    "유천": "육천",
    "치빽": "칠백",
    "칠빽": "칠백",
    "쳔이": "천이",
    "쳔삼": "천삼",
    "쳔사": "천사",
    "쳔오": "천오",
    "쳔육": "천육",
    "쳔칠": "천칠",
    "쳔팔": "천팔",
    "쳔구": "천구",
}

# ── 한글 숫자 사전 ──
_KTOR: dict[str, int] = {
    "공": 0, "영": 0,
    "일": 1, "이": 2, "삼": 3, "사": 4, "오": 5,
    "육": 6, "칠": 7, "팔": 8, "구": 9,
    "십": 10, "백": 100, "천": 1000, "만": 10000,
}

# ── 자모 분해 상수 (유니코드 0xAC00 기반, 외부 라이브러리 불필요) ──
_CHOSUNG  = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"   # 19자
_JUNGSUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"  # 21자
_JONGSUNG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"  # 28자(첫자=없음)
_HANGUL_START = 0xAC00
_HANGUL_END   = 0xD7A3


# ══════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════

def _apply_confusion_map(text: str) -> str:
    """혼동 맵 치환 + 단독 '쳔' → '천' 변환.
    '배' → '백' 은 한글 숫자 뒤에 한글 숫자·공백·숫자 가 이어질 때만 치환(오탐 방지).
    """
    for src, dst in _CONFUSION_MAP.items():
        text = text.replace(src, dst)
    # 단독 '쳔' 처리 (이미 '쳔이' 등이 위에서 처리됐으므로 나머지 잔여분만)
    text = text.replace("쳔", "천")
    # '배' → '백': 앞에 한글 숫자가 있을 때만
    text = re.sub(
        r"([일이삼사오육칠팔구])\s*배(?=[일이삼사오육칠팔구십백천만\s\d]|$)",
        r"\1백",
        text,
    )
    return text


def _parse_mixed_number(s: str) -> Optional[int]:
    """아라비아+한글 혼용 숫자 문자열 → int.
    예: '2백4' → 204, '3천5백' → 3500, '1만2천' → 12000
    순서: 만 → 천 → 백 → 십 → 일
    """
    result = 0
    remaining = s.strip()

    def _grab(unit_word: str, unit_val: int) -> int:
        nonlocal remaining
        m = re.match(r"^(\d+|[일이삼사오육칠팔구]?)\s*" + unit_word, remaining)
        if m:
            prefix = m.group(1)
            if not prefix:
                n = 1
            elif prefix.isdigit():
                n = int(prefix)
            else:
                n = _KTOR.get(prefix, 1)
            remaining = remaining[m.end():]
            return n * unit_val
        return 0

    result += _grab("만", 10000)
    result += _grab("천", 1000)
    result += _grab("백", 100)
    result += _grab("십", 10)

    # 나머지 일 단위
    m_rest = re.match(r"^(\d+|[일이삼사오육칠팔구])", remaining)
    if m_rest:
        v = m_rest.group(1)
        result += int(v) if v.isdigit() else _KTOR.get(v, 0)

    return result if result > 0 else None


def _korean_number_to_int(text: str) -> Optional[int]:
    """순수 한글 숫자 → int.
    예: '이백사' → 204, '삼백' → 300, '천오백' → 1500
    """
    result = 0
    current = 0
    for ch in text:
        if ch not in _KTOR:
            return None
        n = _KTOR[ch]
        if n >= 10:
            if current == 0:
                current = 1
            result += current * n
            current = 0
        else:
            current = n
    result += current
    return result if result > 0 else None


# ══════════════════════════════════════════
#  공개 API
# ══════════════════════════════════════════

def normalize_korean_number(text: str) -> str:
    """STT 원문의 다양한 숫자 표현을 아라비아 숫자로 정규화.

    처리 순서:
      1) 혼동 맵 치환 (샘백→삼백, 쳔→천 등)
      2) 아라비아+한글 혼용 패턴 → 정수 변환 (예: '2백4' → '204')
      3) 순수 한글 숫자 패턴 2자 이상 → 정수 변환 (예: '이백사' → '204')

    반환: 숫자 표현 부분만 아라비아 숫자로 치환된 새 텍스트
    """
    text = _apply_confusion_map(text)

    # ── 아라비아+한글 혼용: 아라비아 숫자로 시작하는 단위 표현 ──
    def _replace_mixed(m: re.Match) -> str:
        val = _parse_mixed_number(m.group(0))
        return str(val) if val is not None else m.group(0)

    text = re.sub(
        r"\d+\s*(?:만|천|백|십)(?:\s*\d*\s*(?:만|천|백|십))*(?:\s*\d+)?",
        _replace_mixed,
        text,
    )

    # ── 순수 한글 숫자 2자 이상 ──
    def _replace_korean(m: re.Match) -> str:
        val = _korean_number_to_int(m.group(0))
        return str(val) if val is not None else m.group(0)

    text = re.sub(
        r"[일이삼사오육칠팔구십백천만]{2,}",
        _replace_korean,
        text,
    )

    return text


def jamo_decompose(text: str) -> str:
    """한글 음절을 초성+중성+(종성) 자모로 분해. 비한글 문자는 그대로.
    예: '송호' → 'ㅅㅗㅇㅎㅗ', '서초고' → 'ㅅㅓㅊㅗㄱㅗ'
    (외부 라이브러리 없이 유니코드 계산)
    """
    result: list[str] = []
    for ch in text:
        code = ord(ch)
        if _HANGUL_START <= code <= _HANGUL_END:
            offset   = code - _HANGUL_START
            jong_idx = offset % 28
            offset //= 28
            jung_idx = offset % 21
            cho_idx  = offset // 21
            result.append(_CHOSUNG[cho_idx])
            result.append(_JUNGSUNG[jung_idx])
            if jong_idx > 0:
                result.append(_JONGSUNG[jong_idx])
        else:
            result.append(ch)
    return "".join(result)


# ── 자동 약칭 생성 규칙: (제거할_접미사, [단축형_추가]) ──
# 학교류: "고등학교" 제거 후 코어 + "고" 단축형도 후보로 포함
#   예) 송호고등학교 → ["송호고", "송호"]
# 일반류: 접미사 제거만
#   예) 정가네식당 → ["정가네"]
_AUTO_SUFFIX_RULES: list[tuple[str, list[str]]] = [
    ("고등학교", ["고"]),
    ("중학교",   ["중"]),
    ("초등학교", ["초"]),
    ("유치원",   []),
    ("어린이집", []),
    ("복지관",   []),
    ("병원",     []),
    ("교회",     []),
    ("식당",     []),
    ("회사",     []),
]

# (주) / 주식회사 제거용 정규식
_CORP_RE = re.compile(r"^\(주\)\s*|\s*\(주\)$|^주식회사\s*|\s*주식회사$")

# ── 접미사 목록 (핵심어 추출 시 사용) ──
_MATCH_SUFFIXES: tuple = (
    "고등학교", "초등학교", "중학교", "식당", "고", "초", "중",
)


def generate_auto_aliases(name: str) -> list[str]:
    """거래처명에서 자동 약칭 후보를 생성 (원본 제외).

    규칙:
      1) (주)/주식회사 접두·접미 제거
      2) 접미사 제거 + 학교류 단축형 추가
         예) 정가네식당    → ["정가네"]
             송호고등학교  → ["송호고", "송호"]
             서초초등학교  → ["서초초", "서초"]
             서초중학교    → ["서초중", "서초"]
             (주)삼성      → ["삼성"]

    반환: 약칭 문자열 리스트 (원본은 포함하지 않음)
    """
    name = name.strip()
    if not name:
        return []

    aliases: list[str] = []
    seen: set[str] = {name}

    def _add(s: str) -> None:
        s = s.strip()
        if s and s not in seen:
            aliases.append(s)
            seen.add(s)

    # 1) (주)/주식회사 제거
    clean = _CORP_RE.sub("", name).strip()
    if clean != name:
        _add(clean)
    else:
        clean = name

    # 2) 접미사 규칙 (첫 번째 매칭만 적용)
    for suffix, short_alts in _AUTO_SUFFIX_RULES:
        if clean.endswith(suffix):
            core = clean[: -len(suffix)]
            if core:
                for alt in short_alts:
                    _add(core + alt)        # 단축형 먼저  (예: 송호고)
                _add(core)                  # 코어         (예: 송호, 정가네)
            break

    return aliases


def build_match_pool(
    canonical_names: list[str],
    manual_aliases_map: "dict[str, list[str]] | None" = None,
) -> "dict[str, str]":
    """매칭 풀 구축: {alias/약칭 → canonical_name}.

    - 각 거래처명에서 자동 약칭 생성 (generate_auto_aliases)
    - 수동 별칭 추가 (manual_aliases_map: {canonical → [alias, ...]})
    - 중복 약칭 (여러 거래처가 동일 약칭 생성) 은 모호하므로 제외

    반환: alias → 원본 거래처명 dict
    """
    pool: dict[str, str] = {}
    ambiguous: set[str] = set()

    def _register(alias: str, canonical: str) -> None:
        """alias를 pool에 등록. 충돌 시 ambiguous 처리."""
        if not alias or not canonical:
            return
        if alias in ambiguous:
            return
        if alias in pool:
            if pool[alias] != canonical:
                # 두 거래처에서 동일 약칭 → 모호, 제외
                del pool[alias]
                ambiguous.add(alias)
        else:
            pool[alias] = canonical

    # 1) 자동 약칭
    for name in canonical_names:
        if not name:
            continue
        for alias in generate_auto_aliases(name):
            _register(alias, name)

    # 2) 수동 별칭 (manual_aliases_map: {canonical → [alias, ...]})
    if manual_aliases_map:
        for name, aliases in manual_aliases_map.items():
            for a in (aliases or []):
                if a:
                    _register(a, name)

    return pool


def match_school_by_jamo(
    spoken: str,
    candidates: list,
    min_score: float = 0.50,
    alias_to_canonical: "dict[str, str] | None" = None,
) -> tuple:
    """발화된 거래처명과 후보 목록을 자모+원문 유사도로 매칭.

    개선 사항:
    1) 공백 정규화: 발화·후보 모두 공백 제거 후 비교
    2) 포함 보너스: 한쪽이 다른 쪽에 완전 포함되면 +0.15
    3) 짧은 이름 임계값: 후보가 5자 이하이면 min_score → 0.42
    4) 핵심어 매칭: 접미사(식당/고등학교 등) 제거 후 코어 유사도 산출,
       원 점수보다 높으면 0.95 배율로 반영
    5) 자동/수동 약칭 풀: alias_to_canonical 제공 시 alias 후보도 함께 검색,
       alias 매칭 시 canonical 이름 반환

    - 자모 유사도: jamo_decompose 후 SequenceMatcher
    - 원문 유사도: 직접 SequenceMatcher
    - 두 값 중 max 가 effective_threshold 이상이면 매칭 성공

    반환: (matched_canonical_name: str, score: float)
    매칭 실패 시: ("", 0.0)
    """
    if not spoken or not candidates:
        return ("", 0.0)

    # 1) 공백 정규화
    spoken_stripped = spoken.replace(" ", "")
    spoken_jamo     = jamo_decompose(spoken_stripped)

    # 5) 후보 목록 확장: 원본 candidates + alias_to_canonical 키 (중복 제외)
    all_candidates: list[str] = list(candidates)
    if alias_to_canonical:
        existing = {str(c) for c in candidates}
        for alias in alias_to_canonical:
            if alias and alias not in existing:
                all_candidates.append(alias)

    best_name  = ""
    best_score = 0.0

    for cand in all_candidates:
        if not cand:
            continue
        cand_str      = str(cand)
        cand_stripped = cand_str.replace(" ", "")
        cand_jamo     = jamo_decompose(cand_stripped)

        jamo_score = SequenceMatcher(None, spoken_jamo,     cand_jamo    ).ratio()
        raw_score  = SequenceMatcher(None, spoken_stripped, cand_stripped).ratio()
        score      = max(jamo_score, raw_score)

        # 2) 포함 보너스
        if cand_stripped in spoken_stripped or spoken_stripped in cand_stripped:
            score = min(1.0, score + 0.15)

        # 4) 핵심어(접미사 제거) 매칭 보너스
        spoken_core = spoken_stripped
        cand_core   = cand_stripped
        for sfx in _MATCH_SUFFIXES:
            if spoken_core.endswith(sfx):
                spoken_core = spoken_core[: -len(sfx)]
                break
        for sfx in _MATCH_SUFFIXES:
            if cand_core.endswith(sfx):
                cand_core = cand_core[: -len(sfx)]
                break
        # 접미사가 실제로 제거된 경우에만 보너스 적용
        if spoken_core and cand_core and spoken_core != spoken_stripped:
            core_jamo  = SequenceMatcher(
                None, jamo_decompose(spoken_core), jamo_decompose(cand_core)
            ).ratio()
            core_raw   = SequenceMatcher(None, spoken_core, cand_core).ratio()
            core_score = max(core_jamo, core_raw) * 0.95  # 약간 패널티
            if core_score > score:
                score = core_score

        if score > best_score:
            best_score = score
            best_name  = cand_str

    # 3) 짧은 이름(5자 이하) 임계값 완화
    effective_threshold = min_score
    if best_name and len(best_name.replace(" ", "")) <= 5:
        effective_threshold = min(min_score, 0.42)

    if best_score < effective_threshold:
        return ("", 0.0)

    # 5) alias 매칭이면 canonical 이름으로 교체
    if alias_to_canonical and best_name in alias_to_canonical:
        best_name = alias_to_canonical[best_name]

    return (best_name, best_score)
