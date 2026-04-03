# zeroda_platform/database/db_manager.py
import sqlite3
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from config.settings import DB_PATH
from services.github_storage import (
    github_get, github_insert, github_upsert, github_delete,
    is_github_available, SHARED_TABLES
)
from services.supabase_storage import (
    supabase_get, supabase_insert, supabase_upsert, supabase_delete,
    supabase_bulk_upsert, is_supabase_available
)


def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _use_github(table: str) -> bool:
    """해당 테이블을 GitHub으로 처리할지 여부"""
    return table in SHARED_TABLES and is_github_available()


def _use_supabase(table: str) -> bool:
    """해당 테이블을 Supabase로 처리할지 여부 (GitHub보다 우선)"""
    return table in SHARED_TABLES and is_supabase_available()


def db_get(table, where_dict=None):
    """SELECT - Supabase 우선, GitHub 폴백, SQLite 폴백"""
    if _use_supabase(table):
        return supabase_get(table, where_dict)
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
    """INSERT OR REPLACE - Supabase 우선, GitHub 폴백, SQLite 폴백"""
    if _use_supabase(table):
        return supabase_upsert(table, data)
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
    """순수 INSERT - Supabase 우선, GitHub 폴백, SQLite 폴백"""
    if _use_supabase(table):
        return supabase_insert(table, data)
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
    """DELETE - Supabase 우선, GitHub 폴백, SQLite 폴백"""
    if _use_supabase(table):
        return supabase_delete(table, where_dict)
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


def get_vendors_by_school(school_name):
    """
    학교 → 담당 수거업체 목록 역조회 (중복 제거)
    1. school_master 테이블
    2. customer_info 테이블
    3. schedules 테이블
    """
    import json
    vendors = set()

    # 1단계: school_master
    rows = db_get('school_master')
    for r in rows:
        if r.get('school_name') == school_name and r.get('vendor'):
            vendors.add(r['vendor'])

    # 2단계: customer_info (name = school_name)
    cust_rows = db_get('customer_info')
    for r in cust_rows:
        if r.get('name') == school_name and r.get('vendor'):
            vendors.add(r['vendor'])

    # 3단계: schedules
    sched_rows = db_get('schedules')
    for r in sched_rows:
        try:
            school_list = json.loads(r.get('schools', '[]'))
            if school_name in school_list and r.get('vendor'):
                vendors.add(r['vendor'])
        except Exception:
            pass

    return sorted(list(vendors))


def get_vendors_by_schools(school_list):
    """
    학교 목록 → 담당 수거업체 목록 (중복 제거)
    교육청 등에서 관할학교 전체의 담당업체를 한번에 조회할 때 사용
    """
    vendors = set()
    for school in school_list:
        vendors.update(get_vendors_by_school(school))
    return sorted(list(vendors))


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
        '이메일': r.get('email', ''), '전화번호': r.get('phone', ''),
        '구분': r.get('cust_type', '학교'),
        '재활용자': r.get('recycler', ''),
        'latitude':  float(r.get('latitude', 0) or 0),
        'longitude': float(r.get('longitude', 0) or 0),
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
        'phone':     info.get('전화번호', ''),
        'cust_type': info.get('구분', '학교'),
        'recycler':  info.get('재활용자', ''),
        'latitude':  float(info.get('latitude', 0) or 0),
        'longitude': float(info.get('longitude', 0) or 0),
        'price_food':    float(info.get('price_food', 0) or 0),
        'price_recycle': float(info.get('price_recycle', 0) or 0),
        'price_general': float(info.get('price_general', 0) or 0),
    })


def save_customer_gps(vendor, name, lat, lng):
    """거래처 GPS 좌표만 업데이트 (기사 현장 위치 저장용)"""
    return db_upsert('customer_info', {
        'vendor': vendor, 'name': name,
        'latitude': float(lat),
        'longitude': float(lng),
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
    """
    본사관리자 일정 저장 (병합 방식).
    같은 vendor + month + weekdays(정렬) 조합이 이미 있으면:
      → 거래처(schools) 합집합, 품목(items) 합집합으로 기존 행을 업데이트.
    없으면 → 신규 INSERT.
    """
    _weekdays_key = json.dumps(sorted(weekdays), ensure_ascii=False)
    # 기존 행 검색
    _existing = db_get('schedules', {'vendor': vendor, 'month': month})
    if not isinstance(_existing, list):
        _existing = []
    _matched_row = None
    for _er in _existing:
        try:
            _er_wd = json.dumps(
                sorted(json.loads(_er['weekdays'])) if _er.get('weekdays') else [],
                ensure_ascii=False
            )
        except Exception:
            _er_wd = '[]'
        if _er_wd == _weekdays_key:
            _matched_row = _er
            break
    if _matched_row:
        # 병합: 거래처·품목 합집합
        try:
            _old_schools = json.loads(_matched_row.get('schools', '[]'))
        except Exception:
            _old_schools = []
        try:
            _old_items = json.loads(_matched_row.get('items', '[]'))
        except Exception:
            _old_items = []
        _merged_schools = list(dict.fromkeys(_old_schools + schools))
        _merged_items   = list(dict.fromkeys(_old_items + items))
        _update_data = {
            'id':            _matched_row.get('id'),
            'vendor':        vendor,
            'month':         month,
            'weekdays':      json.dumps(weekdays, ensure_ascii=False),
            'schools':       json.dumps(_merged_schools, ensure_ascii=False),
            'items':         json.dumps(_merged_items,   ensure_ascii=False),
            'driver':        driver if driver else _matched_row.get('driver', ''),
            'registered_by': 'admin',
            'created_at':    datetime.now(
                                 ZoneInfo('Asia/Seoul')
                             ).strftime('%Y-%m-%d %H:%M:%S'),
        }
        return db_upsert('schedules', _update_data)
    else:
        # 신규 INSERT
        data = {
            'vendor':        vendor,
            'month':         month,
            'weekdays':      json.dumps(weekdays, ensure_ascii=False),
            'schools':       json.dumps(schools,  ensure_ascii=False),
            'items':         json.dumps(items,    ensure_ascii=False),
            'driver':        driver,
            'registered_by': 'admin',
            'created_at':    datetime.now(
                                 ZoneInfo('Asia/Seoul')
                             ).strftime('%Y-%m-%d %H:%M:%S'),
        }
        return db_insert('schedules', data)


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
    """
    업체별 전체 일정 로드.
    반환: { month_key: [entry, entry, ...], ... }
    ※ 품목별로 복수 행이 존재할 수 있으므로 값이 리스트(list)임.
      하위 호환: 기존 코드에서 dict value를 직접 접근하는 경우 첫 번째 항목 사용.
    """
    try:
        rows = db_get('schedules', {'vendor': vendor})
        if not isinstance(rows, list):
            rows = []
        result = {}
        for r in rows:
            if not isinstance(r, dict):
                continue
            month_key = str(r.get('month', ''))
            if not month_key or month_key == 'None':
                continue
            try:
                new_entry = {
                    '요일': json.loads(r['weekdays'])
                            if r.get('weekdays') else [],
                    '학교': json.loads(r['schools'])
                            if r.get('schools')  else [],
                    '품목': json.loads(r['items'])
                            if r.get('items')    else [],
                    '기사': r.get('driver', ''),
                    'registered_by': r.get(
                        'registered_by', 'admin'),
                    'created_at': r.get('created_at', ''),
                }
                if month_key not in result:
                    result[month_key] = []
                result[month_key].append(new_entry)
            except Exception:
                if month_key not in result:
                    result[month_key] = []
                result[month_key].append(
                    {'요일': [], '학교': [], '품목': [], '기사': ''}
                )
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
        'created_at':     datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'),
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
        'updated_at':       datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'),
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


# ─────────────────────────────────────────────────────────────────────────────
# 기사 오늘 수거학교 조회 + 외주업체 일정 등록 (추가 - 기존 코드 유지)
# ─────────────────────────────────────────────────────────────────────────────

def get_today_schools_for_driver(driver_name):
    """
    기사 이름 기준으로 오늘 수거 학교 목록 반환.
    본사(admin) 및 외주업체(vendor)가 등록한
    schedules 전체에서 오늘 요일 포함 일정 조회.
    """
    import json
    from zoneinfo import ZoneInfo
    from datetime import datetime
    now_kst       = datetime.now(ZoneInfo('Asia/Seoul'))
    today_month   = now_kst.strftime('%Y-%m')
    weekday_map   = {
        0:'월', 1:'화', 2:'수', 3:'목',
        4:'금', 5:'토', 6:'일'
    }
    today_weekday = weekday_map[now_kst.weekday()]

    try:
        all_schedules = db_get('schedules')
        if not all_schedules:
            return []

        result = []
        for r in all_schedules:
            if not isinstance(r, dict):
                continue
            if not str(r.get('month', '')).startswith(
                today_month):
                continue
            r_driver = str(r.get('driver', '')).strip()
            if r_driver and r_driver != driver_name:
                continue
            try:
                weekdays = json.loads(r['weekdays']) \
                    if isinstance(r.get('weekdays'), str) \
                    else (r.get('weekdays') or [])
            except Exception:
                weekdays = []
            if today_weekday not in weekdays:
                continue
            try:
                schools = json.loads(r['schools']) \
                    if isinstance(r.get('schools'), str) \
                    else (r.get('schools') or [])
            except Exception:
                schools = []
            try:
                items = json.loads(r['items']) \
                    if isinstance(r.get('items'), str) \
                    else (r.get('items') or [])
            except Exception:
                items = []

            for school in schools:
                result.append({
                    'school':        school,
                    'vendor':        r.get('vendor', ''),
                    'items':         items,
                    'weekday':       today_weekday,
                    'registered_by': r.get(
                        'registered_by', 'admin'),
                })
        return result
    except Exception as e:
        print(f"get_today_schools_for_driver 오류: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 단체급식 관리 함수 (meal_menus, meal_analysis)
# ─────────────────────────────────────────────────────────────────────────────

def save_meal_menu(site_name, meal_date, meal_type, menu_items,
                   calories=0, nutrition_info=None, servings=0, site_type='학교'):
    """일별 식단 저장 (UPSERT: site_name+meal_date+meal_type 기준)
    SQLite + GitHub 동시 저장 (meal_menus가 SHARED_TABLES에 포함되어 있으므로)
    """
    year_month = meal_date[:7] if len(meal_date) >= 7 else ''
    data = {
        'site_name':      site_name,
        'site_type':      site_type,
        'meal_date':      meal_date,
        'meal_type':      meal_type,
        'menu_items':     json.dumps(menu_items, ensure_ascii=False) if isinstance(menu_items, list) else menu_items,
        'calories':       float(calories or 0),
        'nutrition_info': json.dumps(nutrition_info or {}, ensure_ascii=False),
        'servings':       int(servings or 0),
        'year_month':     year_month,
        'created_at':     datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'),
    }

    # ── 1) SQLite 저장 ──
    row_id = None
    try:
        conn = _conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO meal_menus
                (site_name, site_type, meal_date, meal_type, menu_items,
                 calories, nutrition_info, servings, year_month, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(site_name, meal_date, meal_type) DO UPDATE SET
                menu_items=excluded.menu_items,
                calories=excluded.calories,
                nutrition_info=excluded.nutrition_info,
                servings=excluded.servings,
                site_type=excluded.site_type,
                created_at=excluded.created_at
        """, (data['site_name'], data['site_type'], data['meal_date'],
              data['meal_type'], data['menu_items'], data['calories'],
              data['nutrition_info'], data['servings'], data['year_month'],
              data['created_at']))
        conn.commit()
        # UPSERT 후 해당 행의 id를 조회
        c.execute(
            "SELECT id FROM meal_menus WHERE site_name=? AND meal_date=? AND meal_type=?",
            (site_name, meal_date, meal_type)
        )
        result = c.fetchone()
        if result:
            row_id = result[0]
        conn.close()
    except Exception as e:
        print(f"[save_meal_menu] SQLite 오류: {e}")
        return False

    # ── 2) Supabase 동기화 (Supabase 우선, GitHub 폴백) ──
    if _use_supabase('meal_menus'):
        try:
            supabase_upsert('meal_menus', data)
        except Exception as e:
            print(f"[save_meal_menu] Supabase 동기화 오류 (SQLite 저장은 완료): {e}")
    elif _use_github('meal_menus'):
        try:
            from services.github_storage import _put_file, _get_file
            existing, sha = _get_file('meal_menus')
            if existing is None:
                existing = []
            gh_data = dict(data)
            if row_id:
                gh_data['id'] = row_id
            # GitHub에서 기존 행 찾아 업데이트 (site_name+meal_date+meal_type 기준)
            updated = False
            for i, row in enumerate(existing):
                if (row.get('site_name') == site_name and
                    row.get('meal_date') == meal_date and
                    row.get('meal_type') == meal_type):
                    gh_data['id'] = row.get('id', row_id)
                    existing[i] = gh_data
                    updated = True
                    break
            if not updated:
                if 'id' not in gh_data or not gh_data['id']:
                    max_id = max((int(r.get('id', 0)) for r in existing), default=0)
                    gh_data['id'] = max_id + 1
                existing.append(gh_data)
            _put_file('meal_menus', existing, sha)
        except Exception as e:
            print(f"[save_meal_menu] GitHub 동기화 오류 (SQLite 저장은 완료): {e}")

    return True


def save_meal_menus_bulk(site_name, items, site_type='학교'):
    """
    다건 식단 일괄 저장 (엑셀 업로드용).
    SQLite 건별 UPSERT 후, GitHub에는 1회만 동기화하여 API 호출을 최소화한다.
    items: list of dict — 각 dict에 date, menus, calories, nutrition, servings 포함
    반환: (성공건수, 실패건수)
    """
    success = 0
    fail = 0
    now_str = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
    saved_rows = []  # GitHub 동기화용

    # ── 1) SQLite 건별 UPSERT ──
    for item in items:
        meal_date = item['date']
        year_month = meal_date[:7] if len(meal_date) >= 7 else ''
        menu_items = item.get('menus', [])
        data = {
            'site_name':      site_name,
            'site_type':      site_type,
            'meal_date':      meal_date,
            'meal_type':      '중식',
            'menu_items':     json.dumps(menu_items, ensure_ascii=False) if isinstance(menu_items, list) else menu_items,
            'calories':       float(item.get('calories', 0) or 0),
            'nutrition_info': json.dumps(item.get('nutrition', {}) or {}, ensure_ascii=False),
            'servings':       int(item.get('servings', 0) or 0),
            'year_month':     year_month,
            'created_at':     now_str,
        }
        try:
            conn = _conn()
            c = conn.cursor()
            c.execute("""
                INSERT INTO meal_menus
                    (site_name, site_type, meal_date, meal_type, menu_items,
                     calories, nutrition_info, servings, year_month, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(site_name, meal_date, meal_type) DO UPDATE SET
                    menu_items=excluded.menu_items,
                    calories=excluded.calories,
                    nutrition_info=excluded.nutrition_info,
                    servings=excluded.servings,
                    site_type=excluded.site_type,
                    created_at=excluded.created_at
            """, (data['site_name'], data['site_type'], data['meal_date'],
                  data['meal_type'], data['menu_items'], data['calories'],
                  data['nutrition_info'], data['servings'], data['year_month'],
                  data['created_at']))
            conn.commit()
            # UPSERT 후 id 조회
            c.execute(
                "SELECT id FROM meal_menus WHERE site_name=? AND meal_date=? AND meal_type=?",
                (site_name, meal_date, '중식')
            )
            result = c.fetchone()
            if result:
                data['id'] = result[0]
            conn.close()
            saved_rows.append(data)
            success += 1
        except Exception as e:
            print(f"[save_meal_menus_bulk] SQLite 오류 ({meal_date}): {e}")
            fail += 1

    # ── 2) Supabase 일괄 동기화 (Supabase 우선, GitHub 폴백) ──
    if saved_rows and _use_supabase('meal_menus'):
        try:
            supabase_bulk_upsert('meal_menus', saved_rows)
        except Exception as e:
            print(f"[save_meal_menus_bulk] Supabase 동기화 오류 (SQLite 저장은 완료): {e}")
    elif saved_rows and _use_github('meal_menus'):
        try:
            from services.github_storage import _put_file, _get_file
            existing, sha = _get_file('meal_menus')
            if existing is None:
                existing = []
            # 기존 데이터에서 site_name+meal_date+meal_type 키로 인덱싱
            idx_map = {}
            for i, row in enumerate(existing):
                key = (row.get('site_name'), row.get('meal_date'), row.get('meal_type'))
                idx_map[key] = i

            for data in saved_rows:
                key = (data['site_name'], data['meal_date'], data['meal_type'])
                if key in idx_map:
                    data['id'] = existing[idx_map[key]].get('id', data.get('id'))
                    existing[idx_map[key]] = data
                else:
                    if 'id' not in data or not data['id']:
                        max_id = max((int(r.get('id', 0)) for r in existing), default=0)
                        data['id'] = max_id + 1
                    existing.append(data)
                    idx_map[key] = len(existing) - 1

            _put_file('meal_menus', existing, sha)
        except Exception as e:
            print(f"[save_meal_menus_bulk] GitHub 동기화 오류 (SQLite 저장은 완료): {e}")

    return success, fail


def get_meal_menus(site_name, year_month=None):
    """식단 조회. year_month 지정 시 해당 월만."""
    where = {'site_name': site_name}
    if year_month:
        where['year_month'] = year_month
    return db_get('meal_menus', where)


def delete_meal_menu(site_name, meal_date, meal_type='중식'):
    """특정 날짜 식단 삭제 (SQLite + GitHub 동시 삭제)"""
    # ── 1) SQLite 삭제 ──
    try:
        conn = _conn()
        c = conn.cursor()
        c.execute("DELETE FROM meal_menus WHERE site_name=? AND meal_date=? AND meal_type=?",
                  (site_name, meal_date, meal_type))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[delete_meal_menu] SQLite 오류: {e}")
        return False

    # ── 2) Supabase/GitHub 동기화 ──
    if _use_supabase('meal_menus'):
        try:
            supabase_delete('meal_menus', {
                'site_name': site_name, 'meal_date': meal_date, 'meal_type': meal_type
            })
        except Exception as e:
            print(f"[delete_meal_menu] Supabase 동기화 오류 (SQLite 삭제는 완료): {e}")
    elif _use_github('meal_menus'):
        try:
            from services.github_storage import _put_file, _get_file
            existing, sha = _get_file('meal_menus')
            if existing is None:
                existing = []
            filtered = [
                r for r in existing
                if not (r.get('site_name') == site_name and
                        r.get('meal_date') == meal_date and
                        r.get('meal_type') == meal_type)
            ]
            if len(filtered) != len(existing):
                _put_file('meal_menus', filtered, sha)
        except Exception as e:
            print(f"[delete_meal_menu] GitHub 동기화 오류 (SQLite 삭제는 완료): {e}")

    return True


def _classify_waste_grade(waste_per_person):
    """
    WASTE_GRADE 기준으로 등급 분류 (학교급식법 시행규칙 [별표 3] 근거).
    A: 0~150g 미만 (우수)
    B: 150~245g 미만 (양호, 혼합평균 이하)
    C: 245~300g 미만 (주의, 현장기준 이하)
    D: 300g 이상 (고잔반 경보)
    """
    if waste_per_person <= 0:
        return '-'
    elif waste_per_person < 150:
        return 'A'
    elif waste_per_person < 245:
        return 'B'
    elif waste_per_person < 300:
        return 'C'
    else:
        return 'D'


def _generate_menu_remark(menu_items_json, grade, waste_per_person):
    """
    메뉴 키워드 기반 잔반 특이사항 자동 생성.
    급식담당이 일별 잔반 원인을 파악할 수 있도록 코멘트 제공.

    근거:
    [3] 한국식품영양과학회(2019) — 잔반 순위: 채소찬 > 국·찌개 > 생선
    [4] 한국식품영양학회지 KCI — 잔식 순위: 채소·나물 > 생선 > 국 > 밥
    [2] 경기도교육청(2023) — 폐기물 유형: 전처리/일반/순수잔반
    """
    try:
        menus = json.loads(menu_items_json) if isinstance(menu_items_json, str) else menu_items_json
    except (json.JSONDecodeError, TypeError):
        menus = []
    if not menus:
        return ''

    menu_text = ' '.join(str(m) for m in menus)
    remarks = []

    # ── 채소·나물류 감지 (잔반 발생 1위) [근거 3,4] ──
    veg_keywords = ['나물', '시금치', '콩나물', '무침', '숙주', '미나리', '도라지',
                    '고사리', '취나물', '샐러드', '양배추', '브로콜리', '비빔밥',
                    '깻잎', '호박', '가지', '열무', '부추', '오이']
    veg_found = [kw for kw in veg_keywords if kw in menu_text]
    if veg_found:
        remarks.append(f"채소·나물({','.join(veg_found[:2])}) → 잔반 발생 1위 항목, 편식 요인 주의")

    # ── 국·찌개류 감지 (잔반 발생 2위) [근거 3,4] ──
    soup_keywords = ['국', '찌개', '탕', '전골', '스프', '수프', '미역국', '된장국',
                     '육개장', '갈비탕', '곰탕', '설렁탕', '부대찌개', '김치찌개',
                     '순두부', '떡국', '만두국', '해장국', '감자탕', '삼계탕']
    soup_found = [kw for kw in soup_keywords if kw in menu_text]
    if soup_found:
        remarks.append(f"국·찌개({','.join(soup_found[:2])}) → 잔반 발생 2위 항목, 국물 잔반 주의")

    # ── 생선류 감지 (잔반 발생 3위 + 뼈·가시 전처리) [근거 3,4,2] ──
    fish_keywords = ['생선', '고등어', '삼치', '꽁치', '조기', '갈치', '임연수',
                     '가자미', '동태', '명태', '대구', '코다리', '조림']
    fish_found = [kw for kw in fish_keywords if kw in menu_text]
    if fish_found:
        remarks.append(f"생선({','.join(fish_found[:2])}) → 잔반 발생 3위 항목, 뼈·가시 전처리 발생")

    # ── 과일류 감지 (전처리 잔여물: 껍질·씨) [근거 2] ──
    fruit_keywords = ['과일', '사과', '배', '귤', '오렌지', '수박', '참외', '포도',
                      '딸기', '바나나', '키위', '감', '자두', '복숭아', '멜론',
                      '망고', '체리', '파인애플', '블루베리']
    fruit_found = [kw for kw in fruit_keywords if kw in menu_text]
    if fruit_found:
        remarks.append(f"과일({','.join(fruit_found[:2])}) → 껍질·씨 전처리 잔여물 발생")

    # ── 육류·뼈류 감지 (뼈 전처리) [근거 2,4] ──
    meat_bone_keywords = ['갈비', '닭', '치킨', '뼈', '등뼈', '족발', '닭볶음탕',
                          '찜닭', '닭갈비', '삼계탕', '양념치킨', '등갈비']
    bone_found = [kw for kw in meat_bone_keywords if kw in menu_text]
    if bone_found:
        remarks.append(f"뼈류({','.join(bone_found[:2])}) → 뼈 전처리 잔여물 발생, 일반쓰레기 분류")

    # ── 김치류 다종 감지 [근거 3] ──
    kimchi_keywords = ['김치', '깍두기', '총각김치', '백김치', '열무김치', '동치미',
                       '겉절이', '파김치', '오이소박이']
    kimchi_found = [kw for kw in kimchi_keywords if kw in menu_text]
    if len(kimchi_found) >= 2:
        remarks.append(f"김치 {len(kimchi_found)}종 → 채소류 잔반 가중 요인")

    # ── 튀김류 감지 (기름 잔여물) [근거 2] ──
    fry_keywords = ['튀김', '돈까스', '커틀릿', '탕수육', '고로케', '텐동',
                    '후라이', '가스', '까스', '너겟', '프라이', '깐풍기']
    fry_found = [kw for kw in fry_keywords if kw in menu_text]
    if fry_found:
        remarks.append(f"튀김류({','.join(fry_found[:2])}) → 기름 잔여물 주의, 폐유 분류 필요")

    # ── 면류 감지 (국물+면 잔반) [근거 3] ──
    noodle_keywords = ['라면', '잔치국수', '칼국수', '우동', '냉면', '쫄면',
                       '파스타', '스파게티', '짜장면', '짬뽕', '비빔면']
    noodle_found = [kw for kw in noodle_keywords if kw in menu_text]
    if noodle_found:
        remarks.append(f"면류({','.join(noodle_found[:2])}) → 국물+면 잔반 주의")

    # ── 조개·갑각류 감지 (일반쓰레기: 껍데기) [근거 2] ──
    shell_keywords = ['조개', '홍합', '바지락', '꽃게', '새우', '대하',
                      '가리비', '전복', '소라', '굴']
    shell_found = [kw for kw in shell_keywords if kw in menu_text]
    if shell_found:
        remarks.append(f"패류({','.join(shell_found[:2])}) → 껍데기 일반쓰레기 분류 필요")

    # ── 등급별 종합 코멘트 ──
    if grade == 'D':
        remarks.append("고잔반 경보 — 메뉴 구성 재검토 필요")
    elif grade == 'C':
        remarks.append("표준 초과 — 고잔반 메뉴 조정 권장")
    elif grade == 'A' and waste_per_person > 0:
        remarks.append("우수 — 잔반 최소화 달성")

    return ' | '.join(remarks) if remarks else '정상 범위'


def analyze_meal_waste(site_name, year_month):
    """
    식단↔수거량 매칭 분석.
    meal_menus(일별 메뉴) × real_collection(일별 음식물 수거량)을 날짜로 매칭.
    WASTE_GRADE 기준(150/245/300g)으로 등급 산정.
    메뉴 키워드 기반 특이사항(remark) 자동 생성.
    결과를 meal_analysis 테이블에 캐시 저장 후 반환.
    """
    menus = get_meal_menus(site_name, year_month)
    if not menus:
        return []

    # 해당 월 수거 데이터 (음식물만)
    all_collections = db_get('real_collection')
    collections_map = {}
    for r in all_collections:
        # school_name 또는 학교명 매칭
        r_school = r.get('school_name', '') or r.get('학교명', '')
        r_date = str(r.get('collect_date', '') or r.get('날짜', ''))
        r_item = str(r.get('item_type', '')).strip()
        if r_school == site_name and r_date.startswith(year_month):
            if r_item in ('음식물', '음식물쓰레기', 'food_waste', ''):
                w = float(r.get('weight', 0) or r.get('음식물(kg)', 0) or 0)
                collections_map[r_date] = collections_map.get(r_date, 0) + w

    results = []
    now_str = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')

    for m in menus:
        meal_date = m.get('meal_date', '')
        waste_kg = collections_map.get(meal_date, 0)
        servings = int(m.get('servings', 0) or 0)
        waste_per_person = round((waste_kg * 1000) / servings, 1) if servings > 0 else 0

        # WASTE_GRADE 기준 등급 산정 (학교급식법 시행규칙 [별표 3] 근거)
        if waste_per_person == 0 and waste_kg == 0:
            grade = '-'
            waste_rate = 0
        else:
            grade = _classify_waste_grade(waste_per_person)
            # 잔반율: 1인당 잔반량 / 혼합평균 제공량(715g) × 100
            waste_rate = round(waste_per_person / 715 * 100, 1)

        # 메뉴 키워드 기반 특이사항 자동 생성
        remark = _generate_menu_remark(m.get('menu_items', '[]'), grade, waste_per_person)

        row = {
            'site_name':        site_name,
            'year_month':       year_month,
            'meal_date':        meal_date,
            'menu_items':       m.get('menu_items', '[]'),
            'waste_kg':         waste_kg,
            'waste_per_person': waste_per_person,
            'waste_rate':       waste_rate,
            'grade':            grade,
            'remark':           remark,
            'created_at':       now_str,
        }
        results.append(row)

        # meal_analysis에 캐시 저장
        try:
            conn = _conn()
            c = conn.cursor()
            c.execute("""
                INSERT INTO meal_analysis
                    (site_name, year_month, meal_date, menu_items,
                     waste_kg, waste_per_person, waste_rate, grade, remark, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(site_name, meal_date) DO UPDATE SET
                    menu_items=excluded.menu_items,
                    waste_kg=excluded.waste_kg,
                    waste_per_person=excluded.waste_per_person,
                    waste_rate=excluded.waste_rate,
                    grade=excluded.grade,
                    remark=excluded.remark,
                    created_at=excluded.created_at
            """, (row['site_name'], row['year_month'], row['meal_date'],
                  row['menu_items'], row['waste_kg'], row['waste_per_person'],
                  row['waste_rate'], row['grade'], row['remark'], row['created_at']))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[analyze_meal_waste] cache save: {e}")

    return results


def get_meal_analysis(site_name, year_month=None):
    """잔반 분석 캐시 조회"""
    where = {'site_name': site_name}
    if year_month:
        where['year_month'] = year_month
    return db_get('meal_analysis', where)


def save_schedule_by_vendor(vendor, month, weekdays,
                            schools, items, driver=''):
    """
    외주업체 일정 저장 (병합 방식).
    같은 vendor + month + weekdays(정렬) 조합이 이미 있으면:
      → 거래처(schools) 합집합, 품목(items) 합집합으로 기존 행을 업데이트.
    없으면 → 신규 INSERT.
    registered_by='vendor' 로 저장.
    """
    _weekdays_key = json.dumps(sorted(weekdays), ensure_ascii=False)
    _existing = db_get('schedules', {'vendor': vendor, 'month': month})
    if not isinstance(_existing, list):
        _existing = []
    _matched_row = None
    for _er in _existing:
        try:
            _er_wd = json.dumps(
                sorted(json.loads(_er['weekdays'])) if _er.get('weekdays') else [],
                ensure_ascii=False
            )
        except Exception:
            _er_wd = '[]'
        if _er_wd == _weekdays_key:
            _matched_row = _er
            break
    if _matched_row:
        try:
            _old_schools = json.loads(_matched_row.get('schools', '[]'))
        except Exception:
            _old_schools = []
        try:
            _old_items = json.loads(_matched_row.get('items', '[]'))
        except Exception:
            _old_items = []
        _merged_schools = list(dict.fromkeys(_old_schools + schools))
        _merged_items   = list(dict.fromkeys(_old_items + items))
        _update_data = {
            'id':            _matched_row.get('id'),
            'vendor':        vendor,
            'month':         month,
            'weekdays':      json.dumps(weekdays, ensure_ascii=False),
            'schools':       json.dumps(_merged_schools, ensure_ascii=False),
            'items':         json.dumps(_merged_items,   ensure_ascii=False),
            'driver':        driver if driver else _matched_row.get('driver', ''),
            'registered_by': 'vendor',
            'created_at':    datetime.now(
                                 ZoneInfo('Asia/Seoul')
                             ).strftime('%Y-%m-%d %H:%M:%S'),
        }
        return db_upsert('schedules', _update_data)
    else:
        data = {
            'vendor':        vendor,
            'month':         month,
            'weekdays':      json.dumps(weekdays, ensure_ascii=False),
            'schools':       json.dumps(schools,  ensure_ascii=False),
            'items':         json.dumps(items,    ensure_ascii=False),
            'driver':        driver,
            'registered_by': 'vendor',
            'created_at':    datetime.now(
                                 ZoneInfo('Asia/Seoul')
                             ).strftime('%Y-%m-%d %H:%M:%S'),
        }
        return db_insert('schedules', data)
