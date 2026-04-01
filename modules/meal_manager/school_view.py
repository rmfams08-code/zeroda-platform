# modules/meal_manager/school_view.py
# 급식담당 모드 — 학교 수거현황·정산·ESG 래퍼
# school/dashboard.py의 기존 함수를 재사용 (안전관리 제외)
import streamlit as st
from modules.school.dashboard import (
    _render_monthly,
    _render_detail,
    _render_settlement,
    _render_esg,
)


def _get_school(user: dict) -> str:
    """user 객체에서 담당 학교명 추출"""
    schools_str = user.get('schools', '')
    school_list = [s.strip() for s in schools_str.split(',') if s.strip()] if schools_str else []
    if not school_list:
        return ''
    if len(school_list) > 1:
        return st.selectbox("학교 선택", school_list, key="meal_school_sel")
    return school_list[0]


def render_school_collection(user: dict):
    """수거 현황 (월별 현황 + 수거 내역)"""
    st.title("📊 수거 현황")
    school = _get_school(user)
    if not school:
        st.warning("담당 학교가 배정되지 않았습니다.")
        return

    st.caption(f"📍 {school}")
    tab1, tab2 = st.tabs(["📊 월별 현황", "📋 수거 내역"])
    with tab1:
        _render_monthly(school)
    with tab2:
        _render_detail(school)


def render_school_settlement(user: dict):
    """정산 확인"""
    st.title("💰 정산 확인")
    school = _get_school(user)
    if not school:
        st.warning("담당 학교가 배정되지 않았습니다.")
        return

    st.caption(f"📍 {school}")
    _render_settlement(school)


def render_school_esg(user: dict):
    """ESG 보고서"""
    st.title("🌿 ESG 보고서")
    school = _get_school(user)
    if not school:
        st.warning("담당 학교가 배정되지 않았습니다.")
        return

    st.caption(f"📍 {school}")
    _render_esg(school)
