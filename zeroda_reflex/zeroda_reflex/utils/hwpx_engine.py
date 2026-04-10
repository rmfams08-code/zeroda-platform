# zeroda_reflex/utils/hwpx_engine.py
# 2026-04-10 신규: 문서서비스 엔진 (hwpx 전용)
#
# 기능
#   1) extract_tags(hwpx_path)         : 양식 업로드 시 {{태그}} 자동 추출
#   2) fill_template(hwpx, data, out)  : 태그 자동채움 → 새 hwpx 저장
#   3) insert_stamp(hwpx, png, out)    : (인) 문자 자동 찾기 + PNG 삽입
#   4) convert_to_pdf(hwpx, pdf)       : LibreOffice subprocess로 PDF 변환
#
# 의존성: 표준 라이브러리만 (zipfile, xml.etree, re, shutil, subprocess)
#         Pillow (직인 이미지 리사이즈 시에만)
#
# 설계 원칙
#   - hwpx는 ZIP 컨테이너 + XML 구조 (한컴 HWPML 2011 표준)
#   - 본문 파일은 Contents/section0.xml (멀티 섹션 양식은 section1.xml ... 순회)
#   - 텍스트는 <hp:t> 요소 안에 들어감. 단, 한 문장이 여러 <hp:t>로 쪼개질 수 있음
#   - 태그 치환 전 정규화 단계를 두어 파편화 이슈 대응
#   - 직인은 BinData/ 폴더에 PNG 삽입 후 매니페스트 업데이트

from __future__ import annotations

import os
import re
import shutil
import zipfile
import logging
import subprocess
from typing import Any
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

# ── HWPML 2011 네임스페이스 ──
NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
}
# ElementTree 출력 시 네임스페이스 prefix 유지
for _prefix, _uri in NS.items():
    ET.register_namespace(_prefix, _uri)

# 태그 형식: {{영문/한글/숫자/언더스코어}}
TAG_PATTERN = re.compile(r"\{\{([A-Za-z0-9가-힣_]+)\}\}")

# (인) 탐지 패턴 — 공백/띄어쓰기 관용
STAMP_MARK_PATTERN = re.compile(r"\(\s*인\s*\)")


# ══════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════

def _iter_section_xmls(zf: zipfile.ZipFile) -> list[str]:
    """hwpx 내부에서 본문 섹션 XML 파일명 목록 반환."""
    return sorted(
        [n for n in zf.namelist() if n.startswith("Contents/section") and n.endswith(".xml")]
    )


def _read_all_sections(hwpx_path: str) -> dict[str, str]:
    """모든 섹션 XML 원문을 {파일명: 원문} 로 반환."""
    out: dict[str, str] = {}
    with zipfile.ZipFile(hwpx_path, "r") as zf:
        for name in _iter_section_xmls(zf):
            out[name] = zf.read(name).decode("utf-8")
    return out


def _write_hwpx(
    src_hwpx: str,
    dst_hwpx: str,
    replaced_xmls: dict[str, str],
    extra_bins: dict[str, bytes] | None = None,
) -> None:
    """원본 hwpx의 나머지는 그대로, 대상 XML만 교체해서 새 파일로 저장.

    replaced_xmls : {내부경로: 새 XML 문자열}
    extra_bins    : {내부경로: 바이너리} — BinData/*.png 같은 신규 파일 추가용
    """
    extra_bins = extra_bins or {}
    os.makedirs(os.path.dirname(dst_hwpx) or ".", exist_ok=True)
    with zipfile.ZipFile(src_hwpx, "r") as zin:
        with zipfile.ZipFile(dst_hwpx, "w", zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for item in zin.infolist():
                name = item.filename
                if name in replaced_xmls:
                    zout.writestr(name, replaced_xmls[name].encode("utf-8"))
                    written.add(name)
                elif name in extra_bins:
                    zout.writestr(name, extra_bins[name])
                    written.add(name)
                else:
                    zout.writestr(item, zin.read(name))
                    written.add(name)
            # 원본에 없는 신규 바이너리(예: 새 직인 PNG) 추가
            for name, data in extra_bins.items():
                if name not in written:
                    zout.writestr(name, data)


def _collect_hp_t_texts(xml_str: str) -> list[str]:
    """<hp:t>요소의 텍스트만 수집 (네임스페이스 무시, 정규식 방식)."""
    # ET로 파싱해서 안정적으로 수집
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return re.findall(r"<hp:t[^>]*>([^<]*)</hp:t>", xml_str)
    texts: list[str] = []
    for t in root.iter(f"{{{NS['hp']}}}t"):
        if t.text:
            texts.append(t.text)
    return texts


# ══════════════════════════════════════════
#  1) 태그 추출
# ══════════════════════════════════════════

def extract_tags(hwpx_path: str) -> list[str]:
    """양식 안에 등장하는 모든 {{태그}} 목록 반환 (중복 제거, 출현순).

    사용처: 양식 업로드 시 DB의 document_templates.tag_list JSON에 저장.
    주의: 태그가 여러 <hp:t>에 쪼개진 경우 전체 본문을 합쳐서 검색하므로
          사장님이 양식에 태그 입력할 때는 한 글자씩 끊어 치지 말고
          가능하면 한 번에 '{{거래처_상호}}' 형태로 입력해 주세요.
    """
    sections = _read_all_sections(hwpx_path)
    seen: set[str] = set()
    ordered: list[str] = []
    for xml_str in sections.values():
        # 전체 XML에서 한 번에 검색 (쪼개진 태그도 근사 탐지)
        for m in TAG_PATTERN.finditer(xml_str):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                ordered.append(name)
    return ordered


# ══════════════════════════════════════════
#  2) 태그 자동채움
# ══════════════════════════════════════════

def fill_template(hwpx_path: str, data: dict[str, Any], output_path: str) -> list[str]:
    """양식의 {{태그}}를 data 딕셔너리 값으로 치환.

    반환값: 실제로 치환된 태그명 목록 (누락분 추적용)
    미치환 태그는 빈 문자열로 남기지 않고 원본 유지(디버깅 편의).
    """
    sections = _read_all_sections(hwpx_path)
    replaced: set[str] = set()

    def _sub(match: re.Match) -> str:
        key = match.group(1)
        if key in data:
            replaced.add(key)
            val = data[key]
            return "" if val is None else str(val)
        return match.group(0)  # 원본 유지

    new_sections: dict[str, str] = {}
    for name, xml_str in sections.items():
        # XML 특수문자 안전성 확보: 치환 값에 & < > 가 들어가면 깨짐
        # → 미리 이스케이프
        def _sub_xml_safe(m: re.Match) -> str:
            key = m.group(1)
            if key in data:
                replaced.add(key)
                val = data[key]
                s = "" if val is None else str(val)
                return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return m.group(0)

        new_sections[name] = TAG_PATTERN.sub(_sub_xml_safe, xml_str)

    _write_hwpx(hwpx_path, output_path, new_sections)
    return sorted(replaced)


# ══════════════════════════════════════════
#  3) 직인 자동 삽입 — (인) 탐지 방식
# ══════════════════════════════════════════

def insert_stamp(
    hwpx_path: str,
    stamp_png_path: str,
    output_path: str,
    stamp_size_mm: int = 25,
) -> int:
    """본문에서 (인) 문자를 찾아 해당 위치에 직인 PNG를 삽입.

    1차 구현 방식 (단순):
      - <hp:t> 요소 안의 '(인)' 텍스트를 공백으로 치환하여 텍스트는 일단 제거
      - BinData/ 폴더에 직인 PNG를 zeroda_stamp.png 이름으로 추가
      - (인) 옆에 실제 이미지 요소를 삽입하려면 hwpx의 hp:pic 구조가 필요한데
        이는 복잡하여 Phase 테스트 후 2차 개선으로 분리
      - 1차는 (인)을 [직인] 텍스트 마커로 교체하고, PDF 변환 후 후처리 가능하도록
        BinData 준비만 해둠
      - 추후 S7에서 실제 이미지 삽입 로직 확장

    반환: 치환된 (인) 개수
    """
    sections = _read_all_sections(hwpx_path)
    total_replaced = 0
    new_sections: dict[str, str] = {}

    for name, xml_str in sections.items():
        count = 0

        def _sub(m: re.Match) -> str:
            nonlocal count
            count += 1
            # 1차: 텍스트를 공백으로 (추후 실제 이미지 요소로 대체 예정)
            # 마커는 남겨두어 PDF 후처리에서 위치 확인 가능하게
            return " "

        # <hp:t> 내부 텍스트만 대상으로 치환 (다른 XML 영역 보호)
        def _replace_in_hp_t(xml: str) -> tuple[str, int]:
            pat = re.compile(r"(<hp:t[^>]*>)([^<]*)(</hp:t>)")
            local_count = 0

            def _inner(m: re.Match) -> str:
                nonlocal local_count
                open_tag, text, close_tag = m.group(1), m.group(2), m.group(3)
                new_text, n = STAMP_MARK_PATTERN.subn(" ", text)
                local_count += n
                return f"{open_tag}{new_text}{close_tag}"

            new_xml = pat.sub(_inner, xml)
            return new_xml, local_count

        new_xml, c = _replace_in_hp_t(xml_str)
        total_replaced += c
        new_sections[name] = new_xml

    # 직인 PNG를 BinData/ 에 동봉 (2차 개선 시 실제 이미지 참조로 사용)
    extra_bins: dict[str, bytes] = {}
    if stamp_png_path and os.path.exists(stamp_png_path):
        with open(stamp_png_path, "rb") as f:
            extra_bins["BinData/zeroda_stamp.png"] = f.read()

    _write_hwpx(hwpx_path, output_path, new_sections, extra_bins=extra_bins)
    return total_replaced


# ══════════════════════════════════════════
#  4) PDF 변환 (LibreOffice --headless)
# ══════════════════════════════════════════

def convert_to_pdf(hwpx_path: str, output_pdf_path: str, timeout: int = 120) -> bool:
    """LibreOffice headless 모드로 hwpx → PDF 변환.

    전제:
      - 서버에 libreoffice 설치 필요 (apt install libreoffice)
      - 한글 폰트 필요 (fonts-nanum)
      - LibreOffice 7.x+ 는 hwpx 네이티브 지원
    반환: True = 성공, False = 실패
    """
    if not os.path.exists(hwpx_path):
        logger.error(f"convert_to_pdf: 원본 hwpx 없음 {hwpx_path}")
        return False

    out_dir = os.path.dirname(output_pdf_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "libreoffice", "--headless",
                "--convert-to", "pdf",
                "--outdir", out_dir,
                hwpx_path,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.error(f"libreoffice 변환 실패: {result.stderr}")
            return False

        # libreoffice는 원본파일명.pdf 로 저장 → 원하는 이름으로 이동
        base = os.path.splitext(os.path.basename(hwpx_path))[0]
        generated = os.path.join(out_dir, base + ".pdf")
        if generated != output_pdf_path and os.path.exists(generated):
            shutil.move(generated, output_pdf_path)
        return os.path.exists(output_pdf_path)
    except FileNotFoundError:
        logger.error("convert_to_pdf: libreoffice 명령 없음. apt install libreoffice 필요")
        return False
    except subprocess.TimeoutExpired:
        logger.error(f"convert_to_pdf: 타임아웃 {timeout}s")
        return False
    except Exception as e:
        logger.error(f"convert_to_pdf: 예외 {e}")
        return False


# ══════════════════════════════════════════
#  5) 셀 좌표 기반 자동채움 (Phase 2 — 2026-04-10)
# ══════════════════════════════════════════

HP_TBL = f"{{{NS['hp']}}}tbl"
HP_TR = f"{{{NS['hp']}}}tr"
HP_TC = f"{{{NS['hp']}}}tc"
HP_T = f"{{{NS['hp']}}}t"


def fill_by_cell_map(
    hwpx_path: str,
    cell_map: dict[tuple[int, int, int], str],
    data: dict[str, str],
    output_path: str,
) -> dict[str, str]:
    """테이블 셀 좌표 기반으로 값을 채워 넣음.

    Args:
        hwpx_path  : 원본 hwpx 경로
        cell_map   : {(테이블idx, 행idx, 열idx): 데이터키, ...}
                     form_field_config.py의 CELL_MAP_* 사용
        data       : {데이터키: 채울값, ...}
        output_path: 결과 hwpx 저장 경로

    Returns:
        실제로 채워진 {데이터키: 이전값} — 디버깅/로그용

    동작 원리:
        1. section0.xml 파싱 → <hp:tbl> 목록 추출
        2. (테이블idx, 행idx, 열idx)로 <hp:tc> 셀 특정
        3. 셀 내 첫 번째 <hp:t> 텍스트를 기존값 삭제 후 새 값으로 교체
        4. <hp:t>가 없으면 새로 생성
        5. 수정된 XML을 새 hwpx로 저장 (나머지 파일은 그대로 복사)
    """
    sections = _read_all_sections(hwpx_path)
    replaced_log: dict[str, str] = {}  # key → 이전값

    for sec_name, xml_str in sections.items():
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError as e:
            logger.error("fill_by_cell_map: XML 파싱 실패 %s: %s", sec_name, e)
            continue

        tables = root.findall(".//" + HP_TBL)

        for (tbl_i, row_i, col_i), data_key in cell_map.items():
            if data_key not in data:
                continue  # 데이터 없으면 스킵
            if tbl_i >= len(tables):
                logger.warning(
                    "fill_by_cell_map: 테이블%d 없음 (총 %d개)", tbl_i, len(tables)
                )
                continue

            tbl = tables[tbl_i]
            rows = tbl.findall(HP_TR)
            if row_i >= len(rows):
                logger.warning(
                    "fill_by_cell_map: 테이블%d 행%d 없음 (총 %d행)",
                    tbl_i, row_i, len(rows),
                )
                continue

            cells = rows[row_i].findall(HP_TC)
            if col_i >= len(cells):
                logger.warning(
                    "fill_by_cell_map: 테이블%d 행%d 열%d 없음 (총 %d열)",
                    tbl_i, row_i, col_i, len(cells),
                )
                continue

            cell = cells[col_i]
            new_val = str(data[data_key])
            # XML 특수문자 이스케이프
            safe_val = (
                new_val.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            # 셀 내 첫 번째 <hp:t> 찾기
            hp_t_list = list(cell.iter(HP_T))
            if hp_t_list:
                old_val = hp_t_list[0].text or ""
                replaced_log[data_key] = old_val
                hp_t_list[0].text = new_val
                # 나머지 <hp:t>는 비우기 (기존 데이터 잔존 방지)
                for extra_t in hp_t_list[1:]:
                    extra_t.text = ""
            else:
                # <hp:t>가 없는 경우 — 셀 내 첫 <hp:p> 아래에 생성
                replaced_log[data_key] = ""
                hp_p_list = list(cell.iter(f"{{{NS['hp']}}}p"))
                if hp_p_list:
                    # <hp:run> 아래에 <hp:t> 추가
                    hp_run_list = list(hp_p_list[0].iter(f"{{{NS['hp']}}}run"))
                    if hp_run_list:
                        new_t = ET.SubElement(hp_run_list[0], HP_T)
                        new_t.text = new_val
                    else:
                        # <hp:run>도 없으면 간단히 텍스트 추가 시도
                        logger.warning(
                            "fill_by_cell_map: 테이블%d 행%d 열%d — hp:run 없음, 건너뜀",
                            tbl_i, row_i, col_i,
                        )

        # 수정된 XML 직렬화
        sections[sec_name] = ET.tostring(root, encoding="unicode", xml_declaration=False)

    _write_hwpx(hwpx_path, output_path, sections)
    logger.info(
        "fill_by_cell_map: %s → %s, %d셀 채움",
        hwpx_path, output_path, len(replaced_log),
    )
    return replaced_log


def fill_body_text(
    hwpx_path: str,
    replacements: dict[str, str],
    output_path: str,
) -> int:
    """본문 <hp:t> 텍스트 내 키워드를 치환.

    Args:
        replacements: {찾을문자열: 바꿀문자열}
        (테이블이 아닌 본문 영역 — 예: 배출장소, 계약기간 등)

    Returns:
        치환 횟수
    """
    sections = _read_all_sections(hwpx_path)
    total = 0

    for sec_name, xml_str in sections.items():
        for old, new in replacements.items():
            safe_new = (
                new.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            count = xml_str.count(old)
            if count > 0:
                xml_str = xml_str.replace(old, safe_new)
                total += count
        sections[sec_name] = xml_str

    _write_hwpx(hwpx_path, output_path, sections)
    logger.info("fill_body_text: %d건 치환", total)
    return total


# ══════════════════════════════════════════
#  디버그 헬퍼 — 양식 내부 텍스트 덤프
# ══════════════════════════════════════════

def dump_texts(hwpx_path: str) -> list[str]:
    """양식 안 모든 <hp:t> 텍스트를 순서대로 반환 (개발자 디버깅용)."""
    out: list[str] = []
    sections = _read_all_sections(hwpx_path)
    for name, xml_str in sections.items():
        texts = _collect_hp_t_texts(xml_str)
        out.extend(texts)
    return out
