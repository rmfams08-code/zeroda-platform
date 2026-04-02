# modules/meal_manager/menu_register.py
# 단체급식 담당 — 월별 식단 등록/수정 UI (수정4: 엑셀 업로드 기능 추가)
import streamlit as st
import json
import re
import calendar
from datetime import datetime, date
from zoneinfo import ZoneInfo
from database.db_manager import (
    save_meal_menu, save_meal_menus_bulk, get_meal_menus, delete_meal_menu,
    get_school_student_count,
)
from config.settings import COMMON_CSS


def render_menu_register(user: dict):
    st.markdown(COMMON_CSS, unsafe_allow_html=True)
    st.title("📋 식단 등록")

    site_name = _get_site_name(user)
    if not site_name:
        st.warning("담당 거래처(학교/기업)가 설정되지 않았습니다. 관리자에게 문의하세요.")
        return

    site_type = user.get('site_type', '학교')
    st.caption(f"📍 {site_name} ({site_type})")

    # ── 월 선택 ──
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    month_options = []
    for delta in range(-2, 3):
        m = now.month + delta
        y = now.year
        if m < 1:
            m += 12
            y -= 1
        elif m > 12:
            m -= 12
            y += 1
        month_options.append(f"{y}-{m:02d}")

    default_idx = 2  # 현재 월
    sel_month = st.selectbox("월 선택", month_options, index=default_idx,
                             key="meal_reg_month")

    # ── 엑셀 파일 업로드 (일괄 등록) ──
    with st.expander("📤 급식식단 엑셀 파일 업로드 (일괄 등록)", expanded=False):
        _render_excel_upload(site_name, sel_month)

    st.divider()

    # ── 기본 배식인원 ──
    student_count = get_school_student_count(site_name)
    default_servings = student_count if student_count > 0 else 0
    servings = st.number_input("기본 배식인원 (명)", min_value=0,
                               value=default_servings, step=10,
                               key="meal_reg_servings")

    # ── 기존 등록 식단 로드 ──
    existing = get_meal_menus(site_name, sel_month)
    existing_map = {}
    for m in existing:
        existing_map[m['meal_date']] = m

    # ── 달력 형태로 일별 식단 입력 ──
    st.subheader(f"{sel_month} 식단표")

    year, month = int(sel_month[:4]), int(sel_month[5:7])
    _, days_in_month = calendar.monthrange(year, month)
    weekday_names = ['월', '화', '수', '목', '금', '토', '일']

    # 주차별 렌더링
    first_weekday = calendar.weekday(year, month, 1)

    # 요일 헤더
    cols = st.columns(7)
    for i, wd in enumerate(weekday_names):
        cols[i].markdown(f"**{wd}**")

    st.divider()

    # 식단 입력 세션키 관리
    _edit_key = f"_meal_edit_{sel_month}"
    if _edit_key not in st.session_state:
        st.session_state[_edit_key] = {}

    day = 1
    week_start = True
    while day <= days_in_month:
        cols = st.columns(7)
        for wd_idx in range(7):
            if week_start and wd_idx < first_weekday:
                cols[wd_idx].write("")
                continue
            if day > days_in_month:
                cols[wd_idx].write("")
                continue

            date_str = f"{year}-{month:02d}-{day:02d}"
            ex = existing_map.get(date_str, {})
            ex_menus = []
            if ex:
                try:
                    ex_menus = json.loads(ex.get('menu_items', '[]'))
                except (json.JSONDecodeError, TypeError):
                    ex_menus = []

            with cols[wd_idx]:
                # 날짜 표시 + 등록 상태
                status_icon = "✅" if ex_menus else ""
                st.markdown(f"**{day}** {status_icon}")

                if ex_menus:
                    # 기존 메뉴 간략 표시
                    short = ", ".join(ex_menus[:2])
                    if len(ex_menus) > 2:
                        short += f" 외 {len(ex_menus)-2}"
                    st.caption(short)

                # 편집 버튼
                if st.button("편집" if ex_menus else "등록",
                             key=f"meal_btn_{date_str}",
                             use_container_width=True):
                    st.session_state[_edit_key] = {
                        'date': date_str,
                        'menus': ex_menus,
                        'calories': float(ex.get('calories', 0) or 0),
                        'nutrition': ex.get('nutrition_info', '{}'),
                    }

            day += 1
        week_start = False

    st.divider()

    # ── 선택된 날짜 편집 패널 ──
    edit_data = st.session_state.get(_edit_key, {})
    if edit_data and edit_data.get('date'):
        _render_edit_panel(edit_data, site_name, site_type, servings, _edit_key)


def _render_edit_panel(edit_data, site_name, site_type, servings, edit_key):
    """선택된 날짜의 식단 편집 패널"""
    d = edit_data['date']
    st.subheader(f"📝 {d} 식단 편집")

    # 메뉴 입력 (줄바꿈으로 구분)
    existing_text = "\n".join(edit_data.get('menus', []))
    menu_text = st.text_area("메뉴 (줄바꿈으로 구분)",
                             value=existing_text,
                             height=150,
                             key=f"meal_ta_{d}",
                             placeholder="김치찌개\n제육볶음\n시금치나물\n잡곡밥\n배추김치")

    c1, c2 = st.columns(2)
    with c1:
        calories = st.number_input("총 칼로리 (kcal)", min_value=0.0,
                                   value=edit_data.get('calories', 0.0),
                                   step=10.0, key=f"meal_cal_{d}")
    with c2:
        day_servings = st.number_input("배식인원 (명)", min_value=0,
                                       value=servings,
                                       step=10, key=f"meal_srv_{d}")

    # 영양정보 (9항목: 교육청 NEIS 급식식단정보 기준)
    with st.expander("영양정보 입력 (선택)", expanded=False):
        try:
            nut = json.loads(edit_data.get('nutrition', '{}'))
        except (json.JSONDecodeError, TypeError):
            nut = {}

        # 주요 3대 영양소
        st.caption("주요 영양소")
        nc1, nc2, nc3 = st.columns(3)
        with nc1:
            carb = st.number_input("탄수화물(g)", min_value=0.0,
                                   value=float(nut.get('탄수화물', 0)),
                                   key=f"meal_nut_c_{d}")
        with nc2:
            protein = st.number_input("단백질(g)", min_value=0.0,
                                      value=float(nut.get('단백질', 0)),
                                      key=f"meal_nut_p_{d}")
        with nc3:
            fat = st.number_input("지방(g)", min_value=0.0,
                                  value=float(nut.get('지방', 0)),
                                  key=f"meal_nut_f_{d}")

        # 비타민
        st.caption("비타민")
        nv1, nv2, nv3 = st.columns(3)
        with nv1:
            vitA = st.number_input("비타민A(R.E)", min_value=0.0,
                                   value=float(nut.get('비타민A', 0)),
                                   key=f"meal_nut_va_{d}")
        with nv2:
            thiamin = st.number_input("티아민(mg)", min_value=0.0,
                                      value=float(nut.get('티아민', 0)),
                                      step=0.1, format="%.1f",
                                      key=f"meal_nut_t_{d}")
        with nv3:
            ribo = st.number_input("리보플라빈(mg)", min_value=0.0,
                                   value=float(nut.get('리보플라빈', 0)),
                                   step=0.1, format="%.1f",
                                   key=f"meal_nut_r_{d}")

        # 미네랄 + 비타민C
        st.caption("미네랄 / 비타민C")
        nm1, nm2, nm3 = st.columns(3)
        with nm1:
            vitC = st.number_input("비타민C(mg)", min_value=0.0,
                                   value=float(nut.get('비타민C', 0)),
                                   key=f"meal_nut_vc_{d}")
        with nm2:
            calcium = st.number_input("칼슘(mg)", min_value=0.0,
                                      value=float(nut.get('칼슘', 0)),
                                      key=f"meal_nut_ca_{d}")
        with nm3:
            iron = st.number_input("철분(mg)", min_value=0.0,
                                   value=float(nut.get('철분', 0)),
                                   step=0.1, format="%.1f",
                                   key=f"meal_nut_fe_{d}")

    # 저장 / 삭제 버튼
    bc1, bc2, bc3 = st.columns([2, 1, 1])
    with bc1:
        if st.button("💾 저장", key=f"meal_save_{d}", type="primary",
                     use_container_width=True):
            menus = [m.strip() for m in menu_text.split("\n") if m.strip()]
            if not menus:
                st.error("메뉴를 1개 이상 입력하세요.")
            else:
                nutrition = {
                    '탄수화물': carb, '단백질': protein, '지방': fat,
                    '비타민A': vitA, '티아민': thiamin, '리보플라빈': ribo,
                    '비타민C': vitC, '칼슘': calcium, '철분': iron,
                }
                ok = save_meal_menu(
                    site_name=site_name,
                    meal_date=d,
                    meal_type='중식',
                    menu_items=menus,
                    calories=calories,
                    nutrition_info=nutrition,
                    servings=day_servings,
                    site_type=site_type,
                )
                if ok:
                    st.success(f"✅ {d} 식단 저장 완료 ({len(menus)}개 메뉴)")
                    st.session_state[edit_key] = {}
                    st.rerun()
                else:
                    st.error("저장 실패. 다시 시도하세요.")

    with bc2:
        if st.button("🗑️ 삭제", key=f"meal_del_{d}", use_container_width=True):
            delete_meal_menu(site_name, d)
            st.session_state[edit_key] = {}
            st.rerun()

    with bc3:
        if st.button("닫기", key=f"meal_close_{d}", use_container_width=True):
            st.session_state[edit_key] = {}
            st.rerun()


def _get_site_name(user: dict) -> str:
    """사용자 정보에서 담당 거래처명 추출"""
    schools = user.get('schools', '')
    if schools:
        return schools.split(',')[0].strip()
    vendor = user.get('vendor', '')
    if vendor:
        return vendor
    return ''


# ══════════════════════════════════════════════════════════════
# 엑셀 업로드 관련 함수
# ══════════════════════════════════════════════════════════════

def _render_excel_upload(site_name: str, sel_month: str):
    """급식식단정보 엑셀 파일(.xls/.xlsx) 업로드 → 일괄 등록"""
    st.markdown("교육청 NEIS 급식식단정보 엑셀 파일을 업로드하면 자동으로 파싱하여 등록합니다.")
    st.caption("지원 컬럼: 급식일자, 요리명, 칼로리정보, 영양정보, 급식인원수")

    uploaded = st.file_uploader(
        "엑셀 파일 선택 (.xls / .xlsx)",
        type=["xls", "xlsx"],
        key="meal_excel_upload"
    )

    if not uploaded:
        return

    # 파싱 (.xls → xlrd, .xlsx → openpyxl, fallback 포함)
    try:
        import pandas as pd
        fname = uploaded.name.lower()
        if fname.endswith('.xls') and not fname.endswith('.xlsx'):
            try:
                df = pd.read_excel(uploaded, engine='xlrd')
            except ImportError:
                st.warning("xlrd 미설치 → .xlsx 모드로 재시도합니다.")
                uploaded.seek(0)
                df = pd.read_excel(uploaded, engine='openpyxl')
        else:
            df = pd.read_excel(uploaded, engine='openpyxl')
    except Exception as e:
        st.error(f"파일 읽기 실패: `{e}`")
        st.info("💡 `.xls` 파일인 경우 엑셀에서 `.xlsx`로 다시 저장한 뒤 업로드하면 해결됩니다.")
        return

    # 필수 컬럼 확인
    required = ['급식일자', '요리명']
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"필수 컬럼 누락: {missing}")
        st.info(f"파일 컬럼: {list(df.columns)}")
        return

    # 데이터 파싱
    parsed = _parse_meal_excel(df, sel_month)

    if not parsed:
        st.warning(f"{sel_month}에 해당하는 식단 데이터가 없습니다.")
        return

    # 미리보기
    st.success(f"✅ {len(parsed)}일치 식단 데이터 파싱 완료")

    preview_rows = []
    for p in parsed:
        menus_short = ", ".join(p['menus'][:3])
        if len(p['menus']) > 3:
            menus_short += f" 외 {len(p['menus'])-3}"
        nut = p.get('nutrition', {})
        nut_str = ""
        if nut:
            parts = []
            for k in ['탄수화물', '단백질', '지방']:
                if k in nut:
                    parts.append(f"{k}:{nut[k]}g")
            nut_str = " / ".join(parts)
        preview_rows.append({
            '날짜': p['date'],
            '메뉴': menus_short,
            '칼로리': f"{p['calories']:.0f} kcal",
            '배식인원': p['servings'],
            '영양정보': nut_str,
        })

    import pandas as _pd
    st.dataframe(_pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

    # 일괄 등록 버튼 (bulk 함수로 GitHub API 최소화)
    if st.button("📥 전체 일괄 등록", type="primary", key="meal_excel_apply",
                 use_container_width=True):
        with st.spinner(f"⏳ {len(parsed)}일치 식단 등록 중..."):
            success, fail = save_meal_menus_bulk(
                site_name=site_name,
                items=parsed,
                site_type='학교',
            )

        if success > 0:
            st.success(f"✅ {success}일치 식단 등록 완료!")
        if fail > 0:
            st.error(f"❌ {fail}건 등록 실패")
        st.rerun()


def _find_column(df_columns, candidates):
    """데이터프레임 컬럼 중 candidates에 포함된 첫 번째 컬럼명 반환
    1차: 정확 매칭 (strip 후 비교)
    2차: 공백·괄호·특수문자 제거 후 포함(contains) 매칭
    """
    import re
    # 1차: 정확 매칭
    for col in df_columns:
        col_clean = str(col).strip()
        if col_clean in candidates:
            return col
    # 2차: 정규화 후 포함 매칭 (공백·괄호·단위 제거)
    def _normalize(s):
        return re.sub(r'[\s()（）\[\]명수인]', '', str(s).strip())
    norm_candidates = {_normalize(c): c for c in candidates}
    for col in df_columns:
        col_norm = _normalize(col)
        for nc in norm_candidates:
            if nc and col_norm and (nc in col_norm or col_norm in nc):
                return col
    return None


def _parse_meal_excel(df, sel_month: str) -> list:
    """교육청 NEIS 급식식단정보 엑셀 → 구조화된 리스트 변환"""
    results = []

    # ── 컬럼명 유연 매칭 (NEIS 파일 버전에 따라 컬럼명이 다를 수 있음) ──
    col_date     = _find_column(df.columns, ['급식일자', '급식날짜', '일자', '날짜']) or '급식일자'
    col_menu     = _find_column(df.columns, ['요리명', '메뉴명', '식단명', '메뉴']) or '요리명'
    col_cal      = _find_column(df.columns, ['칼로리정보', '칼로리', '열량', '에너지(kcal)']) or '칼로리정보'
    col_servings = _find_column(df.columns, [
        '급식인원수', '급식인원', '배식인원수', '배식인원', '인원수', '인원',
        '급식인원 수', '배식인원 수', '급식인원(명)', '배식인원(명)',
    ]) or '급식인원수'
    col_nut      = _find_column(df.columns, ['영양정보', '영양량정보', '영양소']) or '영양정보'

    for _, row in df.iterrows():
        # 날짜 파싱 (YYYYMMDD 또는 YYYY-MM-DD)
        raw_date = str(row.get(col_date, ''))
        meal_date = _parse_date(raw_date)
        if not meal_date:
            continue

        # 선택 월 필터
        if meal_date[:7] != sel_month:
            continue

        # 메뉴 파싱 (<br/> 구분, 알레르기 코드 제거)
        raw_menu = str(row.get(col_menu, ''))
        menus = _parse_menus(raw_menu)
        if not menus:
            continue

        # 칼로리 파싱
        raw_cal = str(row.get(col_cal, '0'))
        calories = _parse_calories(raw_cal)

        # 급식인원/배식인원 (유연 매칭 + NaN 안전 처리)
        import math
        _raw_srv = row.get(col_servings, 0)
        if _raw_srv is None or (isinstance(_raw_srv, float) and math.isnan(_raw_srv)):
            _raw_srv = 0
        try:
            servings = int(float(_raw_srv))
        except (ValueError, TypeError):
            servings = 0

        # 영양정보 파싱
        raw_nut = str(row.get(col_nut, ''))
        nutrition = _parse_nutrition(raw_nut)

        results.append({
            'date': meal_date,
            'menus': menus,
            'calories': calories,
            'servings': servings,
            'nutrition': nutrition,
        })

    # 날짜 정렬
    results.sort(key=lambda x: x['date'])
    return results


def _parse_date(raw: str) -> str:
    """YYYYMMDD 또는 YYYY-MM-DD → YYYY-MM-DD"""
    raw = raw.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    if len(raw) == 10 and raw[4] == '-':
        return raw
    # float → int 변환 (20260401.0)
    try:
        num = int(float(raw))
        s = str(num)
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    except (ValueError, TypeError):
        pass
    return ''


def _parse_menus(raw: str) -> list:
    """
    요리명 파싱: <br/> 구분자로 분리, 알레르기 코드 제거
    예: "현미밥 <br/>팽이장국 (5.6)<br/>쫄면야채무침 (5.6.13)"
    → ["현미밥", "팽이장국", "쫄면야채무침"]
    """
    items = re.split(r'<br\s*/?>', raw)
    menus = []
    for item in items:
        # 알레르기 코드 제거: (1.2.5.6) 패턴
        cleaned = re.sub(r'\s*\([\d.]+\)\s*$', '', item.strip())
        cleaned = cleaned.strip()
        if cleaned:
            menus.append(cleaned)
    return menus


def _parse_calories(raw: str) -> float:
    """'870.6 Kcal' → 870.6"""
    m = re.search(r'([\d.]+)\s*[Kk]cal', raw)
    if m:
        return float(m.group(1))
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def _parse_nutrition(raw: str) -> dict:
    """
    영양정보 파싱:
    "탄수화물(g) : 135.0<br/>단백질(g) : 40.7<br/>지방(g) : 16.7<br/>비타민A(R.E) : 92.0
     <br/>티아민(mg) : 0.9<br/>리보플라빈(mg) : 0.4<br/>비타민C(mg) : 8.4
     <br/>칼슘(mg) : 144.4<br/>철분(mg) : 3.3"
    → {'탄수화물': 135.0, '단백질': 40.7, '지방': 16.7, '비타민A': 92.0, ...}
    """
    if not raw or raw == 'nan':
        return {}

    nutrition = {}
    items = re.split(r'<br\s*/?>', raw)
    for item in items:
        item = item.strip()
        if not item or ':' not in item:
            continue
        # "탄수화물(g) : 135.0" → key="탄수화물", value=135.0
        parts = item.split(':', 1)
        key_raw = parts[0].strip()
        val_raw = parts[1].strip()

        # 키에서 단위 제거: "탄수화물(g)" → "탄수화물"
        key = re.sub(r'\(.*?\)', '', key_raw).strip()

        try:
            val = float(val_raw)
        except (ValueError, TypeError):
            continue

        nutrition[key] = val

    return nutrition
