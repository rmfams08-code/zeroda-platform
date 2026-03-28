# config/dashboard_helpers.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 대시보드 공통 헬퍼 함수 (본사·외주업체 공용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import streamlit as st


def calc_weight_by_item(month_data):
    """
    수거 데이터에서 품목별 수거량(kg) 집계.
    Returns: (food_kg, recycle_kg, general_kg)
    """
    food_kg = sum(float(r.get('weight', 0)) for r in month_data
                  if '음식물' in str(r.get('item_type', '')))
    recycle_kg = sum(float(r.get('weight', 0)) for r in month_data
                     if '재활용' in str(r.get('item_type', '')))
    general_kg = sum(float(r.get('weight', 0)) for r in month_data
                     if '일반' in str(r.get('item_type', ''))
                     or ('음식물' not in str(r.get('item_type', ''))
                         and '재활용' not in str(r.get('item_type', ''))))
    return food_kg, recycle_kg, general_kg


def render_weight_metrics(month_data, show_carbon=True):
    """
    4-컬럼 메트릭 카드 (음식물, 재활용, 사업장, CO₂/총수거량) 렌더.
    show_carbon=True → CO₂ 감축, False → 총 수거량 표시
    """
    food_kg, recycle_kg, general_kg = calc_weight_by_item(month_data)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🍱 음식물 수거량", f"{food_kg:,.1f} kg")
    with c2:
        st.metric("♻️ 재활용 수거량", f"{recycle_kg:,.1f} kg")
    with c3:
        st.metric("🏭 사업장 수거량", f"{general_kg:,.1f} kg")
    with c4:
        if show_carbon:
            try:
                from services.carbon_calculator import calculate_carbon_reduction
                carbon, _ = calculate_carbon_reduction(food_kg, recycle_kg, general_kg)
            except Exception:
                carbon = 0.0
            st.metric("🌿 CO₂ 감축", f"{carbon:,.1f} kg")
        else:
            total_kg = sum(float(r.get('weight', 0)) for r in month_data)
            st.metric("📦 총 수거량", f"{total_kg:,.1f} kg")


def render_env_contribution(month_data):
    """환경 기여 현황 (총수거량, CO₂ 감축, 소나무 효과) 3-컬럼 렌더."""
    st.markdown("### 🌱 환경 기여 현황")
    total_weight = sum(float(r.get('weight', 0)) for r in month_data)
    try:
        from services.carbon_calculator import calculate_from_rows
        result = calculate_from_rows(month_data)
        carbon_total = result.get('carbon_reduced', 0)
        trees = result.get('tree_equivalent', 0)
    except Exception:
        carbon_total = 0.0
        trees = 0.0

    e1, e2, e3 = st.columns(3)
    with e1:
        st.metric("총 수거량", f"{total_weight:,.1f} kg")
    with e2:
        st.metric("CO₂ 감축량", f"{carbon_total:,.1f} kg")
    with e3:
        st.metric("🌲 소나무 동등 효과", f"{trees:,.1f} 그루")
