# zeroda_platform/database/db_manager.py
# ==========================================
# Supabase 연동 DB 매니저
# ==========================================

import json
import streamlit as st
from datetime import datetime

# ──────────────────────────────────────────
# Supabase 클라이언트 초기화
# ──────────────────────────────────────────

@st.cache_resource
def get_supabase():
    try:
        from supabase import create_client
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase 연결 실패: {e}")
        return None


# ──────────────────────────────────────────
# 기본 CRUD (SQLite API와 동일한 인터페이스 유지)
# ──────────────────────────────────────────

def db_get(table, where_dict=None):
    """SELECT"""
    sb = get_supabase()
    if not sb:
        return []
    try:
        query = sb.table(table).select("*")
        if where_dict:
            for k, v in where_dict.items():
                query = query.eq(k, v)
        res = query.execute()
        return res.data or []
    except Exception:
        return []


def db_upsert(table, data):
    """INSERT OR UPDATE"""
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table(table).upsert(data).execute()
        return True
    except Exception:
        return False


def db_delete(table, where_dict):
    """DELETE"""
    sb = get_supabase()
    if not sb:
        return False
    try:
        query = sb.table(table).delete()
        for k, v in where_dict.items():
            query = query.eq(k, v)
        query.execute()
        return True
    except Exception:
        return False


def db_execute(sql, params=None):
    """직접 SQL (Supabase RPC 사용)"""
    sb = get_supabase()
    if not sb:
        return []
    try:
        res = sb.rpc('execute_sql',
                     {'query': sql, 'params': params or []}).execute()
        return res.data or []
    except Exception:
        return []


# ──────────────────────────────────────────
# 학교 마스터
# ──────────────────────────────────────────

def get_all_schools():
    rows = db_get('school_master')
    return sorted([r['school_name'] for r in rows])


def get_school_student_count(school_name):
    rows = db_get('school_master', {'school_name': school_name})
    return rows[0]['student_count'] if rows else 0


def get_schools_by_vendor(vendor):
    rows = db_get('school_master', {'vendor': vendor})
    return [r['school_name'] for r in rows]


def get_schools_by_edu_office(edu_office):
    rows = db_get('school_master', {'edu_office': edu_office})
    return [r['school_name'] for r in rows]


def assign_school_to_vendor(school_name, vendor):
    return db_upsert('school_master', {
        'school_name': school_name,
        'vendor': vendor
    })


# ──────────────────────────────────────────
# 외주업체
# ──────────────────────────────────────────

def get_all_vendors():
    rows = db_get('vendor_info')
    return [r.get('biz_name') or r['vendor'] for r in rows]


def get_vendor_display_name(vendor_id):
    rows = db_get('vendor_info', {'vendor': vendor_id})
    if rows:
        return rows[0].get('biz_name') or vendor_id
    return vendor_id


def update_vendor_name(old_vendor_id, new_biz_name):
    """업체명 변경 CASCADE"""
    sb = get_supabase()
    if not sb:
        return False
    try:
        sb.table('vendor_info').update(
            {'biz_name': new_biz_name}
        ).eq('vendor', old_vendor_id).execute()

        cascade_tables = [
            ('users',         'vendor'),
            ('contract_info', 'vendor'),
            ('schedule_data', 'vendor'),
            ('schedules',     'vendor'),
            ('customer_info', 'vendor'),
            ('biz_customers', 'vendor'),
            ('school_master', 'vendor'),
        ]
        for tbl, col in cascade_tables:
            try:
                sb.table(tbl).update(
                    {col: new_biz_name}
                ).eq(col, old_vendor_id).execute()
            except Exception:
                pass
        return True
    except Exception:
        return False


# ──────────────────────────────────────────
# 거래처
# ──────────────────────────────────────────

def load_customers_from_db(vendor):
    rows = db_get('customer_info', {'vendor': vendor})
    if not rows:
        return {}
    return {
        r['name']: {
            '사업자번호': r.get('biz_no', ''),
            '상호':      r['name'],
            '대표자':    r.get('rep', ''),
            '주소':      r.get('addr', ''),
            '업태':      r.get('biz_type', ''),
            '종목':      r.get('biz_item', ''),
            '이메일':    r.get('email', ''),
            '구분':      r.get('cust_type', '학교'),
        }
        for r in rows
    }


def save_customer_to_db(vendor, name, info):
    return db_upsert('customer_info', {
        'vendor':    vendor,
        'name':      name,
        'biz_no':    info.get('사업자번호', ''),
        'rep':       info.get('대표자', ''),
        'addr':      info.get('주소', ''),
        'biz_type':  info.get('업태', ''),
        'biz_item':  info.get('종목', ''),
        'email':     info.get('이메일', ''),
        'cust_type': info.get('구분', '학교'),
    })


def delete_customer_from_db(vendor, name):
    return db_delete('customer_info', {'vendor': vendor, 'name': name})


# ──────────────────────────────────────────
# 수거일정
# ──────────────────────────────────────────

def save_schedule(vendor, month, weekdays, schools, items, driver=''):
    return db_upsert('schedules', {
        'vendor':     vendor,
        'month':      month,
        'weekdays':   json.dumps(weekdays, ensure_ascii=False),
        'schools':    json.dumps(schools,  ensure_ascii=False),
        'items':      json.dumps(items,    ensure_ascii=False),
        'driver':     driver,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    })


def load_schedule(vendor, month):
    rows = db_get('schedules', {'vendor': vendor, 'month': month})
    if not rows:
        return None
    r = rows[0]
    return {
        '요일': json.loads(r['weekdays']) if r.get('weekdays') else [],
        '학교': json.loads(r['schools'])  if r.get('schools')  else [],
        '품목': json.loads(r['items'])    if r.get('items')    else [],
        '기사': r.get('driver', ''),
    }


def load_all_schedules(vendor):
    sb = get_supabase()
    if not sb:
        return {}
    try:
        res = sb.table('schedules').select("*").eq('vendor', vendor).execute()
        rows = res.data or []
    except Exception:
        return {}
    result = {}
    for r in rows:
        result[r['month']] = {
            '요일': json.loads(r['weekdays']) if r.get('weekdays') else [],
            '학교': json.loads(r['schools'])  if r.get('schools')  else [],
            '품목': json.loads(r['items'])    if r.get('items')    else [],
            '기사': r.get('driver', ''),
        }
    return result


def delete_schedule(vendor, month):
    return db_delete('schedules', {'vendor': vendor, 'month': month})