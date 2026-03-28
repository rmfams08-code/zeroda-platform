# services/settlement_helpers.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 정산 관련 공통 헬퍼 함수 (본사·외주업체 공용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from database.db_manager import load_customers_from_db


def get_customer_match(vendor, school, customers=None):
    """
    vendor의 customer_info에서 school에 매칭되는 거래처 정보를 반환.
    customers: load_customers_from_db(vendor) 결과를 미리 넘길 수 있음.
    """
    if customers is None:
        customers = load_customers_from_db(vendor)
    cust = customers.get(school, {})
    if not cust:
        for _ck, _cv in customers.items():
            if _cv.get('상호') == school:
                cust = _cv
                break
    return cust


def build_price_map(cust_info):
    """거래처 정보에서 품목별 단가 맵 생성"""
    if not cust_info:
        return {}
    return {
        '음식물':       float(cust_info.get('price_food', 0) or 0),
        '재활용':       float(cust_info.get('price_recycle', 0) or 0),
        '일반':         float(cust_info.get('price_general', 0) or 0),
        '사업장폐기물': float(cust_info.get('price_general', 0) or 0),
        '음식물쓰레기': float(cust_info.get('price_food', 0) or 0),
    }


def correct_row_prices(rows, price_map):
    """
    수거 데이터 행에 단가·금액을 보정하여 반환.
    원본 rows는 변경하지 않고 새 리스트 반환.
    """
    corrected = []
    for r in rows:
        row = dict(r)
        item = str(row.get('item_type', '') or row.get('품목', '')).strip()
        up = price_map.get(item, 0.0)
        if up == 0.0:
            up = float(row.get('unit_price', 0) or 0)
        w = float(row.get('weight', 0) or row.get('음식물(kg)', 0) or 0)
        row['unit_price'] = up
        row['amount'] = round(w * up, 0)
        corrected.append(row)
    return corrected


def build_biz_info(cust_info, school):
    """거래처 정보에서 biz_info dict 생성 (PDF 생성용)"""
    if not cust_info:
        return {}
    return {
        '상호':       cust_info.get('상호', school),
        '사업자번호': cust_info.get('사업자번호', ''),
        '대표자':     cust_info.get('대표자', ''),
        '주소':       cust_info.get('주소', ''),
        '업태':       cust_info.get('업태', ''),
        '종목':       cust_info.get('종목', ''),
        '이메일':     cust_info.get('이메일', ''),
        '전화번호':   cust_info.get('전화번호', ''),
        '구분':       cust_info.get('구분', '학교'),
    }
