# services/upload_handler.py
# CSV / 엑셀 업로드 → DB 저장
import pandas as pd
from datetime import datetime
from database.db_manager import db_insert, db_get

# CSV 컬럼 → DB 컬럼 매핑
COLUMN_MAP = {
    '날짜':        'collect_date',
    '학교명':      'school_name',
    '음식물(kg)':  'weight',
    '단가(원)':    'unit_price',
    '공급가':      'amount',
    '재활용방법':   'item_type',
    '재활용업체':   'vendor',
    '월':          'month_num',
    '년도':        'year_num',
    '월별파일':     'monthly_file',
    # 영문 컬럼도 그대로 허용
    'collect_date':  'collect_date',
    'school_name':   'school_name',
    'weight':        'weight',
    'unit_price':    'unit_price',
    'amount':        'amount',
    'item_type':     'item_type',
    'vendor':        'vendor',
    'driver':        'driver',
    'memo':          'memo',
    'status':        'status',
}

# DB에 실제 저장할 컬럼 (real_collection 기준)
DB_COLUMNS = [
    'vendor', 'school_name', 'collect_date', 'item_type',
    'weight', 'unit_price', 'amount', 'driver', 'memo',
    'status', 'created_at',
    # 한글 원본 컬럼도 함께 저장
    '날짜', '학교명', '음식물(kg)', '단가(원)', '공급가',
    '재활용방법', '재활용업체', '월', '년도',
]


def read_file(uploaded_file) -> pd.DataFrame:
    """업로드 파일 읽기 (CSV / XLSX)"""
    fname = uploaded_file.name.lower()
    if fname.endswith('.csv'):
        # 인코딩 자동 감지
        for enc in ('utf-8-sig', 'cp949', 'utf-8', 'euc-kr'):
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding=enc)
                return df
            except Exception:
                continue
        raise ValueError("CSV 인코딩을 인식할 수 없습니다.")
    elif fname.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError("CSV 또는 XLSX 파일만 지원합니다.")


def map_columns(df: pd.DataFrame) -> pd.DataFrame:
    """컬럼명 매핑 - 한글/영문 모두 대응"""
    df = df.copy()
    rename = {}
    for col in df.columns:
        col_stripped = col.strip()
        if col_stripped in COLUMN_MAP:
            mapped = COLUMN_MAP[col_stripped]
            if mapped != col_stripped:
                rename[col] = mapped
    df = df.rename(columns=rename)
    return df


def get_column_mapping_info(df: pd.DataFrame) -> dict:
    """매핑 결과 정보 반환 {원본컬럼: 매핑결과}"""
    info = {}
    for col in df.columns:
        col_s = col.strip()
        if col_s in COLUMN_MAP:
            info[col] = f"→ {COLUMN_MAP[col_s]}"
        else:
            info[col] = "→ (매핑 없음, 원본 유지)"
    return info


def save_to_db(df: pd.DataFrame, table: str,
               duplicate_action: str = 'skip',
               default_vendor: str = '') -> dict:
    """
    DataFrame → DB 저장
    duplicate_action: 'skip' or 'overwrite'
    Returns: {'success': N, 'skip': N, 'fail': N, 'errors': [...]}
    """
    result = {'success': 0, 'skip': 0, 'fail': 0, 'errors': []}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 기존 데이터 (중복 체크용)
    existing = db_get(table)
    existing_keys = set()
    if duplicate_action == 'skip':
        for r in existing:
            key = (str(r.get('collect_date', '')),
                   str(r.get('school_name', '')),
                   str(r.get('vendor', '')))
            existing_keys.add(key)

    for _, row in df.iterrows():
        try:
            # 기본값 세팅
            collect_date = str(row.get('collect_date', row.get('날짜', ''))).strip()
            school_name  = str(row.get('school_name',  row.get('학교명', ''))).strip()
            vendor_val   = str(row.get('vendor', row.get('재활용업체', default_vendor))).strip()
            if not vendor_val or vendor_val == 'nan':
                vendor_val = default_vendor

            # 중복 체크
            key = (collect_date, school_name, vendor_val)
            if duplicate_action == 'skip' and key in existing_keys:
                result['skip'] += 1
                continue

            weight     = float(row.get('weight',     row.get('음식물(kg)', 0)) or 0)
            unit_price = float(row.get('unit_price', row.get('단가(원)',   0)) or 0)
            amount     = float(row.get('amount',     row.get('공급가',     weight * unit_price)) or 0)
            if amount == 0 and weight > 0 and unit_price > 0:
                amount = weight * unit_price

            data = {
                'vendor':       vendor_val,
                'school_name':  school_name,
                'collect_date': collect_date,
                'item_type':    str(row.get('item_type', row.get('재활용방법', '음식물'))).strip(),
                'weight':       weight,
                'unit_price':   unit_price,
                'amount':       amount,
                'driver':       str(row.get('driver', '')).strip(),
                'memo':         str(row.get('memo', '')).strip(),
                'status':       'confirmed',
                'created_at':   now,
                # 한글 원본 컬럼도 함께 저장
                '날짜':         collect_date,
                '학교명':       school_name,
                '음식물(kg)':   weight,
                '단가(원)':     unit_price,
                '공급가':       amount,
                '재활용방법':   str(row.get('item_type', row.get('재활용방법', ''))).strip(),
                '재활용업체':   vendor_val,
                '월':           int(row.get('month_num', row.get('월', 0)) or 0),
                '년도':         int(row.get('year_num',  row.get('년도', 0)) or 0),
            }

            row_id = db_insert(table, data)
            if row_id:
                result['success'] += 1
                existing_keys.add(key)
            else:
                result['fail'] += 1
                result['errors'].append(f"행 저장 실패: {collect_date} / {school_name}")

        except Exception as e:
            result['fail'] += 1
            result['errors'].append(f"오류: {str(e)[:80]}")

    return result
