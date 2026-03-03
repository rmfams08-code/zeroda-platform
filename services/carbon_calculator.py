# services/carbon_calculator.py
# 환경부 기준 탄소배출계수 적용

CARBON_FACTOR = {
    '음식물': 0.271,   # kg CO2 / kg (매립 대비 감축)
    '재활용': 0.461,   # kg CO2 / kg
    '일반':   0.054,   # kg CO2 / kg
}
TREE_ABSORPTION = 6.6  # kg CO2 / 그루 / 년


def calculate_carbon_reduction(food_kg: float, recycle_kg: float, general_kg: float):
    """
    수거량 → 탄소감축량, 나무 환산
    Returns: (carbon_reduced_kg, tree_equivalent)
    """
    total = (food_kg   * CARBON_FACTOR['음식물']
           + recycle_kg * CARBON_FACTOR['재활용']
           + general_kg * CARBON_FACTOR['일반'])
    trees = total / TREE_ABSORPTION
    return round(total, 2), round(trees, 1)


def calculate_from_rows(rows: list):
    """
    real_collection rows → 탄소감축량 계산
    Returns: {'carbon_reduced': float, 'tree_equivalent': float, 'by_item': dict}
    """
    food_kg = recycle_kg = general_kg = 0.0
    for r in rows:
        w         = float(r.get('weight', 0) or 0)
        item_type = str(r.get('item_type', r.get('재활용방법', '음식물')))
        if '음식물' in item_type:
            food_kg    += w
        elif '재활용' in item_type:
            recycle_kg += w
        else:
            general_kg += w

    carbon, trees = calculate_carbon_reduction(food_kg, recycle_kg, general_kg)
    return {
        'carbon_reduced':   carbon,
        'tree_equivalent':  trees,
        'food_kg':          round(food_kg, 1),
        'recycle_kg':       round(recycle_kg, 1),
        'general_kg':       round(general_kg, 1),
        'by_item': {
            '음식물': round(food_kg   * CARBON_FACTOR['음식물'], 2),
            '재활용': round(recycle_kg * CARBON_FACTOR['재활용'], 2),
            '일반':   round(general_kg * CARBON_FACTOR['일반'],   2),
        }
    }
