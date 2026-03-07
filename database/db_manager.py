# zeroda_platform/database/db_manager.py
import sqlite3
import json
from datetime import datetime
from config.settings import DB_PATH
from services.github_storage import (
    github_get, github_insert, github_upsert, github_delete,
    is_github_available, SHARED_TABLES
)


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _use_github(table: str) -> bool:
    """해당 테이블을 GitHub으로 처리할지 여부"""
    return table in SHARED_TABLES and is_github_available()


def db_get(table, where_dict=None):
    """SELECT - GitHub 우선, 폴백 SQLite"""
    if _use_github(table):
        return github_get(table, where_dict)
    # SQLite 폴백
    try:
        conn = _conn()
        c = conn.cursor()
        sql = f"SELECT * FROM {table}"
        params = []
        if where_dict:
            conditions = [f"{k} = ?" for k in where_dict]
            sql += " WHERE " + " AND ".join(conditions)
            params = list(where_dict.values())
        c.execute(sql, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def db_upsert(table, data):
    """INSERT OR REPLACE - GitHub 우선, 폴백 SQLite"""
    if _use_github(table):
        return github_upsert(table, data)
    try:
        conn = _conn()
        c = conn.cursor()
        keys = ', '.join(f'"{k}"' for k in data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f'INSERT OR REPLACE INTO {table} ({keys}) VALUES ({placeholders})'
        c.execute(sql, list(data.values()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        import traceback
        print(f"[db_upsert ERROR] table={table}, error={e}")
        traceback.print_exc()
        return False


def db_insert(table, data):
    """순수 INSERT - GitHub 우선, 폴백 SQLite"""
    if _use_github(table):
        return github_insert(table, data)
    try:
        conn = _conn()
        c = conn.cursor()
        keys = ', '.join(f'"{k}"' for k in data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f'INSERT INTO {table} ({keys}) VALUES ({placeholders})'
        c.execute(sql, list(data.values()))
        row_id = c.lastrowid
        conn.commit()
        conn.close()
        return row_id
    except Exception as e:
        import traceback
        print(f"[db_insert ERROR] table={table}, error={e}")
        traceback.print_exc()
        return None


def db_delete(table, where_dict):
    """DELETE - GitHub 우선, 폴백 SQLite"""
    if _use_github(table):
        return github_delete(table, where_dict)
    try:
        conn = _conn()
        c = conn.cursor()
        conditions = [f"{k} = ?" for k in where_dict]
        sql = f"DELETE FROM {table} WHERE " + " AND ".join(conditions)
        c.execute(sql, list(where_dict.values()))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def db_execute(sql, params=None):
    """직접 SQL 실행"""
    try:
        conn = _conn()
        c = conn.cursor()
        c.execute(sql, params or [])
        rows = [dict(r) for r in c.fetchall()]
        conn.commit()
        conn.close()
        return rows
    except Exception:
        return []


def get_all_schools():
    rows = db_get('school_master')
    return sorted([r['school_name'] for r in rows])


def _build_alias_map(school_master_rows: list) -> dict:
    """
    school_master rows → alias_map 생성
    {school_name: [alias1, alias2, ...], ...}
    역방향(alias → school_name) 도 포함해 양방향 매칭 가능하게 구성
    """
    alias_map = {}
    for r in school_master_rows:
        sn = r.get('school_name', '')
        if not sn:
            continue
        aliases = [a.strip() for a in (r.get('alias', '') or '').split(',') if a.strip()]
        alias_map[sn] = aliases
        for a in aliases:
            if a not in alias_map:
                alias_map[a] = [sn] + [x for x in aliases if x != a]
    return alias_map


def _match_with_alias(target: str, candidate: str, alias_map: dict) -> bool:
    """
    alias_map 기반 학교명 매칭.
    1. 완전 일치
    2. target의 별칭 목록에 candidate 포함
    3. candidate의 별칭 목록에 target 포함
    4. 포함 관계 (짧은 쪽이 긴 쪽에 포함)
    """
    if not target or not candidate:
        return False
    if target == candidate:
        return True
    for alias in alias_map.get(target, []):
        if alias == candidate:
            return True
    for alias in alias_map.get(candidate, []):
        if alias == target:
            return True
    if target in candidate or candidate in target:
        return True
    return False


def filter_rows_by_school(rows: list, school: str, school_master_rows: list = None) -> list:
    """
    real_collection 등의 row 리스트를 학교명(별칭 포함)으로 필터링.
    school_master_rows를 외부에서 전달하면 db_get 중복 호출 방지.
    기존 r.get('school_name') == school 대체용
    """
    if school_master_rows is None:
        school_master_rows = db_get('school_master')
    alias_map = _build_alias_map(school_master_rows)
    return [r for r in rows if _match_with_alias(school, r.get('school_name', ''), alias_map)]


def get_school_student_count(school_name):
    rows = db_get('school_master', {'school_name': school_name})
    return rows[0]['student_count'] if rows else 0


def get_schools_by_vendor(vendor):
    """
    업체 담당 학교 목록 조회 - 3단계 순서로 시도
    1. school_master 테이블 (정식 등록)
    2. schedules 테이블 (수거일정에 등록된 학교)
    3. customer_info 테이블 (거래처로 등록된 학교)
    """
    import json

    # 1단계: school_master
    rows = db_get('school_master', {'vendor': vendor})
    if rows:
        return [r['school_name'] for r in rows]

    # 업체명→ID 역조회 후 school_master 재시도
    vendor_rows = db_get('vendor_info')
    vendor_id = vendor
    for v in vendor_rows:
        if v.get('biz_name') == vendor:
            vendor_id = v['vendor']
            rows2 = db_get('school_master', {'vendor': vendor_id})
            if rows2:
                return [r['school_name'] for r in rows2]

    # 2단계: schedules 테이블에서 학교 추출
    schedule_rows = db_get('schedules', {'vendor': vendor_id})
    if not schedule_rows:
        schedule_rows = db_get('schedules', {'vendor': vendor})
    schools = set()
    for r in schedule_rows:
        try:
            school_list = json.loads(r.get('schools', '[]'))
            schools.update(school_list)
        except Exception:
            pass
    if schools:
        return sorted(list(schools))

    # 3단계: customer_info 테이블에서 학교 추출
    customer_rows = db_get('customer_info', {'vendor': vendor_id})
    if not customer_rows:
        customer_rows = db_get('customer_info', {'vendor': vendor})
    if customer_rows:
        return [r['school_name'] for r in customer_rows if r.get('school_name')]

    return []


def get_schools_by_edu_office(edu_office):
    rows = db_get('school_master', {'edu_office': edu_office})
    return [r['school_name'] for r in rows]


def assign_school_to_vendor(school_name, vendor):
    return db_upsert('school_master', {'school_name': school_name, 'vendor': vendor})


def get_all_vendors():
    """업체 ID 목록 반환 (DB 저장용)"""
    rows = db_get('vendor_info')
    return [r['vendor'] for r in rows]


def get_vendor_options():
    """업체 선택용 딕셔너리 {표시명: ID} 반환 (UI 선택용)"""
    rows = db_get('vendor_info')
    return {f"{r.get('biz_name') or r['vendor']} ({r['vendor']})": r['vendor'] for r in rows}


def get_vendor_name(vendor_id):
    """업체ID → 업체명 변환"""
    rows = db_get('vendor_info', {'vendor': vendor_id})
    if rows:
        return rows[0].get('biz_name') or vendor_id
    return vendor_id


def get_vendor_display_name(vendor_id):
    rows = db_get('vendor_info', {'vendor': vendor_id})
    if rows:
        return rows[0].get('biz_name') or vendor_id
    return vendor_id


def update_vendor_name(old_vendor_id, new_biz_name):
    try:
        conn = _conn()
        c = conn.cursor()
        c.execute("UPDATE vendor_info SET biz_name=? WHERE vendor=?", (new_biz_name, old_vendor_id))
        for tbl, col in [('users','vendor'),('contract_info','vendor'),('schedule_data','vendor'),
                         ('schedules','vendor'),('customer_info','vendor'),('biz_customers','vendor'),('school_master','vendor')]:
            try:
                c.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (new_biz_name, old_vendor_id))
            except:
                pass
        conn.commit()
        conn.close()
        return True
    except:
        return False


def load_customers_from_db(vendor):
    rows = db_get('customer_info', {'vendor': vendor})
    if not rows:
        return {}
    return {r['name']: {
        '사업자번호': r.get('biz_no', ''), '상호': r['name'], '대표자': r.get('rep', ''),
        '주소': r.get('addr', ''), '업태': r.get('biz_type', ''), '종목': r.get('biz_item', ''),
        '이메일': r.get('email', ''), '구분': r.get('cust_type', '학교'),
        'price_food':    float(r.get('price_food', 0) or 0),
        'price_recycle': float(r.get('price_recycle', 0) or 0),
        'price_general': float(r.get('price_general', 0) or 0),
    } for r in rows}


def save_customer_to_db(vendor, name, info):
    return db_upsert('customer_info', {
        'vendor': vendor, 'name': name,
        'biz_no':    info.get('사업자번호', ''),
        'rep':       info.get('대표자', ''),
        'addr':      info.get('주소', ''),
        'biz_type':  info.get('업태', ''),
        'biz_item':  info.get('종목', ''),
        'email':     info.get('이메일', ''),
        'cust_type': info.get('구분', '학교'),
        'price_food':    float(info.get('price_food', 0) or 0),
        'price_recycle': float(info.get('price_recycle', 0) or 0),
        'price_general': float(info.get('price_general', 0) or 0),
    })


def delete_customer_from_db(vendor, name):
    return db_delete('customer_info', {'vendor': vendor, 'name': name})


# 품목 코드 → customer_info 컬럼 매핑
_ITEM_PRICE_COL = {
    'food_waste':  'price_food',
    '음식물':      'price_food',
    '음식물쓰레기': 'price_food',
    'recycle':     'price_recycle',
    '재활용':      'price_recycle',
    'general':     'price_general',
    '사업장':      'price_general',
    '사업장폐기물': 'price_general',
}


def get_unit_price(vendor: str, school: str, item_type: str) -> float:
    """
    거래처(학교)의 품목별 단가 조회.
    item_type: 'food_waste' | 'recycle' | 'general' 또는 한글 품목명
    매칭 실패 시 0.0 반환
    """
    col = _ITEM_PRICE_COL.get(item_type, '')
    if not col:
        return 0.0
    rows = db_get('customer_info', {'vendor': vendor, 'name': school})
    if rows:
        return float(rows[0].get(col, 0) or 0)
    return 0.0




def save_schedule(vendor, month, weekdays, schools, items, driver=''):
    return db_upsert('schedules', {'vendor': vendor,'month': month,
        'weekdays': json.dumps(weekdays, ensure_ascii=False),
        'schools': json.dumps(schools, ensure_ascii=False),
        'items': json.dumps(items, ensure_ascii=False),
        'driver': driver,'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})


def load_schedule(vendor, month):
    rows = db_get('schedules', {'vendor': vendor, 'month': month})
    if not rows:
        return None
    r = rows[0]
    return {'요일': json.loads(r['weekdays']) if r.get('weekdays') else [],
            '학교': json.loads(r['schools']) if r.get('schools') else [],
            '품목': json.loads(r['items']) if r.get('items') else [],
            '기사': r.get('driver', '')}


def load_all_schedules(vendor):
    try:
        rows = db_get('schedules', {'vendor': vendor})
        if not isinstance(rows, list):
            rows = []
        result = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            month_key = str(r.get('month', ''))  # 정수/문자열 통일
            if not month_key or month_key == 'None':
                continue
            try:
                result[month_key] = {
                    '요일': json.loads(r['weekdays']) if r.get('weekdays') else [],
                    '학교': json.loads(r['schools'])  if r.get('schools')  else [],
                    '품목': json.loads(r['items'])    if r.get('items')    else [],
                    '기사': r.get('driver', ''),
                }
            except Exception:
                result[month_key] = {'요일': [], '학교': [], '품목': [], '기사': ''}
        return result
    except Exception:
        return {}


def delete_schedule(vendor, month):
    return db_delete('schedules', {'vendor': vendor, 'month': month})


# ─────────────────────────────────────────────────────────────────────────────
# FEAT-02: 안전관리 평가 함수 (추가 - 기존 코드 유지)
# ─────────────────────────────────────────────────────────────────────────────

def add_violation(vendor: str, driver: str, violation_date: str,
                  violation_type: str = '기타', location: str = '',
                  fine_amount: int = 0, memo: str = '') -> bool:
    """스쿨존 위반 기록 추가"""
    return db_insert('school_zone_violations', {
        'vendor':         vendor,
        'driver':         driver,
        'violation_date': violation_date,
        'violation_type': violation_type,
        'location':       location,
        'fine_amount':    fine_amount,
        'memo':           memo,
        'created_at':     datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }) is not None


def calculate_safety_score(vendor: str, year_month: str) -> dict:
    """
    업체의 월별 안전관리 점수 계산 후 safety_scores 테이블에 저장.

    평가 기준:
      - 스쿨존 위반: 40점 만점, 1건당 -8점
      - 차량점검 이행률: 30점 만점, 이행률(%) × 30
      - 교육이수율: 30점 만점, 이수율(%) × 30

    등급:
      S(90~100), A(75~89), B(60~74), C(40~59), D(0~39)

    반환: {'vendor', 'year_month', 'violation_score', 'checklist_score',
            'education_score', 'total_score', 'grade'}
    """
    year, month = year_month.split('-')
    month_prefix = f"{year}-{month}"

    # ── 1) 스쿨존 위반 점수 (40점 만점) ─────────────────────────────────
    violations = [r for r in db_get('school_zone_violations', {'vendor': vendor})
                  if str(r.get('violation_date', '')).startswith(month_prefix)]
    violation_count  = len(violations)
    violation_score  = max(0.0, 40.0 - violation_count * 8.0)

    # ── 2) 차량점검 이행률 점수 (30점 만점) ─────────────────────────────
    # 해당 월 드라이버 수 기준: users 테이블에서 role=driver, vendor=vendor
    driver_rows = [r for r in db_get('users')
                   if r.get('role') == 'driver' and r.get('vendor') == vendor]
    driver_count = max(len(driver_rows), 1)  # 0 나눔 방지

    checklist_rows = [r for r in db_get('safety_checklist', {'vendor': vendor})
                      if str(r.get('check_date', '')).startswith(month_prefix)]
    checked_drivers = len(set(r.get('driver', '') for r in checklist_rows if r.get('driver')))
    checklist_rate   = min(checked_drivers / driver_count, 1.0)
    checklist_score  = round(checklist_rate * 30.0, 1)

    # ── 3) 교육이수율 점수 (30점 만점) ──────────────────────────────────
    edu_rows = [r for r in db_get('safety_education', {'vendor': vendor})
                if str(r.get('edu_date', '')).startswith(month_prefix)]
    educated_drivers = len(set(r.get('driver', '') for r in edu_rows if r.get('driver')))
    edu_rate         = min(educated_drivers / driver_count, 1.0)
    education_score  = round(edu_rate * 30.0, 1)

    # ── 총점 & 등급 ──────────────────────────────────────────────────────
    total_score = round(violation_score + checklist_score + education_score, 1)
    if total_score >= 90:
        grade = 'S'
    elif total_score >= 75:
        grade = 'A'
    elif total_score >= 60:
        grade = 'B'
    elif total_score >= 40:
        grade = 'C'
    else:
        grade = 'D'

    result = {
        'vendor':           vendor,
        'year_month':       year_month,
        'violation_score':  violation_score,
        'checklist_score':  checklist_score,
        'education_score':  education_score,
        'total_score':      total_score,
        'grade':            grade,
        'updated_at':       datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    # safety_scores 테이블에 저장 (UNIQUE(vendor, year_month) → upsert)
    try:
        conn = _conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO safety_scores
                (vendor, year_month, violation_score, checklist_score,
                 education_score, total_score, grade, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(vendor, year_month) DO UPDATE SET
                violation_score=excluded.violation_score,
                checklist_score=excluded.checklist_score,
                education_score=excluded.education_score,
                total_score=excluded.total_score,
                grade=excluded.grade,
                updated_at=excluded.updated_at
        """, (vendor, year_month, violation_score, checklist_score,
              education_score, total_score, grade,
              result['updated_at']))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[calculate_safety_score] DB 저장 오류: {e}")

    return result


def get_safety_scores(vendor: str = None, year_month: str = None) -> list:
    """
    안전관리 평가 결과 조회.
    vendor/year_month 미입력 시 전체 반환.
    """
    where = {}
    if vendor:
        where['vendor'] = vendor
    if year_month:
        where['year_month'] = year_month
    return db_get('safety_scores', where if where else None)


def get_violations(vendor: str = None, year_month: str = None) -> list:
    """스쿨존 위반 기록 조회"""
    rows = db_get('school_zone_violations', {'vendor': vendor} if vendor else None)
    if year_month:
        rows = [r for r in rows if str(r.get('violation_date', '')).startswith(year_month)]
    return rows
