# modules/meal_manager/menu_register.py
# 단체급식 담당 — 월별 식단 등록/수정 UI
import streamlit as st
import json
import calendar
from datetime import datetime, date
from zoneinfo import ZoneInfo
from database.db_manager import (
    save_meal_menu, get_meal_menus, delete_meal_menu,
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

    # 영양정보 (선택)
    with st.expander("영양정보 입력 (선택)", expanded=False):
        try:
            nut = json.loads(edit_data.get('nutrition', '{}'))
        except (json.JSONDecodeError, TypeError):
            nut = {}
        nc1, nc2, nc3, nc4 = st.columns(4)
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
        with nc4:
            sodium = st.number_input("나트륨(mg)", min_value=0.0,
                                     value=float(nut.get('나트륨', 0)),
                                     key=f"meal_nut_s_{d}")

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
                    '탄수화물': carb, '단백질': protein,
                    '지방': fat, '나트륨': sodium,
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
    # schools 필드 (학교)
    schools = user.get('schools', '')
    if schools:
        return schools.split(',')[0].strip()
    # vendor 필드 (기업 구내식당 등)
    vendor = user.get('vendor', '')
    if vendor:
        return vendor
    return ''
