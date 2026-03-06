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


def match_school_name(target: str, candidate: str) -> bool:
    """
    학교명 별칭 매칭 헬퍼.
    target   : users.schools 또는 UI에서 선택된 학교명 (예: "서초고")
    candidate: real_collection 등 데이터에 저장된 학교명 (예: "서초고등학교")
    반환: 동일하거나 별칭 관계이면 True

    매칭 순서:
    1. 완전 일치
    2. school_master alias 컬럼에 target이 포함 (쉼표 구분)
    3. target이 candidate에 포함되거나 candidate가 target에 포함
    """
    if not target or not candidate:
        return False
    if target == candidate:
        return True
    # school_master alias 조회
    rows = db_get('school_master', {'school_name': candidate})
    if not rows:
        # candidate가 alias인 경우 역방향도 시도
        rows = db_get('school_master', {'school_name': target})
        if rows:
            alias_str = rows[0].get('alias', '') or ''
            aliases = [a.strip() for a in alias_str.split(',') if a.strip()]
            if candidate in aliases:
                return True
    else:
        alias_str = rows[0].get('alias', '') or ''
        aliases = [a.strip() for a in alias_str.split(',') if a.strip()]
        if target in aliases:
            return True
    # 포함 관계 (짧은 쪽이 긴 쪽에 포함되는지)
    if target in candidate or candidate in target:
        return True
    return False


def filter_rows_by_school(rows: list, school: str) -> list:
    """
    real_collection 등의 row 리스트를 학교명(별칭 포함)으로 필터링
    기존 r.get('school_name') == school 대체용
    """
    return [r for r in rows if match_school_name(school, r.get('school_name', ''))]




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
    return {r['name']: {'사업자번호': r.get('biz_no',''),'상호': r['name'],'대표자': r.get('rep',''),
            '주소': r.get('addr',''),'업태': r.get('biz_type',''),'종목': r.get('biz_item',''),
            '이메일': r.get('email',''),'구분': r.get('cust_type','학교')} for r in rows}


def save_customer_to_db(vendor, name, info):
    return db_upsert('customer_info', {'vendor': vendor,'name': name,'biz_no': info.get('사업자번호',''),
        'rep': info.get('대표자',''),'addr': info.get('주소',''),'biz_type': info.get('업태',''),
        'biz_item': info.get('종목',''),'email': info.get('이메일',''),'cust_type': info.get('구분','학교')})


def delete_customer_from_db(vendor, name):
    return db_delete('customer_info', {'vendor': vendor, 'name': name})


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
