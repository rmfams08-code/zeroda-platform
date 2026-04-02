# services/supabase_storage.py
# Supabase REST API 연동 (PostgreSQL 기반 클라우드 DB)
# GitHub JSON 저장소 대체 - GitHub API Rate Limit 문제 해결
import json
import urllib.request
import urllib.parse
import streamlit as st

# ── 테이블별 upsert 기준 컬럼 ───────────────────────────────────────────────
# ON CONFLICT(컬럼들) DO UPDATE 에 사용
# 여기 없는 테이블은 항상 INSERT (수거기록 등 중복 없는 테이블)
UPSERT_KEYS = {
    'users':         ['user_id'],
    'school_master': ['school_name'],
    'vendor_info':   ['vendor'],
    'customer_info': ['vendor', 'name'],
    'meal_menus':    ['site_name', 'meal_date', 'meal_type'],
    'meal_analysis': ['site_name', 'meal_date'],
}


def _get_supabase():
    """Supabase 연결 정보 (Streamlit Secrets에서 읽기)"""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
    except Exception:
        url, key = "", ""
    return url.rstrip('/'), key


def is_supabase_available():
    """Supabase 연결 가능 여부 확인"""
    url, key = _get_supabase()
    return bool(url and key)


def _headers(key, prefer=None):
    """Supabase REST API 공통 헤더"""
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


@st.cache_data(ttl=5)
def _supabase_get_cached(table: str):
    """Supabase에서 테이블 전체 데이터 읽기 (5초 캐시)"""
    url, key = _get_supabase()
    if not url or not key:
        return []
    # limit=10000: Supabase 기본 1000행 제한 우회
    endpoint = f"{url}/rest/v1/{table}?select=*&limit=10000"
    req = urllib.request.Request(endpoint, headers=_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[supabase_get] {table}: {type(e).__name__}: {e}")
        return []


def _clear_cache():
    """Supabase 캐시 전체 무효화"""
    try:
        _supabase_get_cached.clear()
    except Exception:
        pass


def supabase_get(table: str, where_dict: dict = None):
    """Supabase에서 테이블 데이터 읽기 (where 필터는 캐시 밖에서 처리)"""
    rows = list(_supabase_get_cached(table))  # 캐시 복사본 사용
    if where_dict and rows:
        for k, v in where_dict.items():
            rows = [r for r in rows if str(r.get(k, '')) == str(v)]
    return rows


def supabase_insert(table: str, data: dict):
    """Supabase에 새 행 추가 (id는 자동생성)"""
    url, key = _get_supabase()
    if not url or not key:
        return None
    # Supabase는 id를 자동생성 → 제거 후 전송
    data_copy = {k: v for k, v in data.items() if k != 'id'}
    endpoint = f"{url}/rest/v1/{table}"
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(data_copy, ensure_ascii=False).encode('utf-8'),
        headers=_headers(key, prefer="return=representation"),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            _clear_cache()
            if isinstance(result, list) and result:
                return result[0].get('id', True)
            return True
    except Exception as e:
        print(f"[supabase_insert] {table}: {e}")
        return None


def supabase_upsert(table: str, data: dict):
    """
    Supabase에서 행 업데이트 또는 삽입.
    - data에 'id'가 있으면 → PATCH (해당 행 직접 수정)
    - id 없으면 → POST with ON CONFLICT (비즈니스 키 기준 upsert)
    """
    url, key = _get_supabase()
    if not url or not key:
        return False

    row_id = data.get('id')
    data_copy = {k: v for k, v in data.items() if k != 'id'}

    if row_id:
        # id 기준 PATCH 업데이트
        endpoint = f"{url}/rest/v1/{table}?id=eq.{row_id}"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(data_copy, ensure_ascii=False).encode('utf-8'),
            headers=_headers(key, prefer="return=minimal"),
            method="PATCH"
        )
    else:
        # 비즈니스 키 기준 upsert
        conflict_cols = UPSERT_KEYS.get(table)
        endpoint = f"{url}/rest/v1/{table}"
        prefer = "resolution=merge-duplicates,return=minimal"
        if conflict_cols:
            cols_str = urllib.parse.quote(','.join(conflict_cols))
            endpoint += f"?on_conflict={cols_str}"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(data_copy, ensure_ascii=False).encode('utf-8'),
            headers=_headers(key, prefer=prefer),
            method="POST"
        )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _clear_cache()
            return True
    except Exception as e:
        print(f"[supabase_upsert] {table}: {e}")
        return False


def supabase_delete(table: str, where_dict: dict):
    """Supabase에서 조건에 맞는 행 삭제 (AND 조건)"""
    url, key = _get_supabase()
    if not url or not key:
        return False
    if not where_dict:
        return False

    params = "&".join(
        f"{urllib.parse.quote(str(k))}=eq.{urllib.parse.quote(str(v))}"
        for k, v in where_dict.items()
    )
    endpoint = f"{url}/rest/v1/{table}?{params}"
    req = urllib.request.Request(
        endpoint,
        headers=_headers(key, prefer="return=minimal"),
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _clear_cache()
            return True
    except Exception as e:
        print(f"[supabase_delete] {table}: {e}")
        return False


def supabase_bulk_upsert(table: str, rows: list):
    """
    다건 일괄 upsert (엑셀 업로드 등 배치 작업용).
    GitHub API처럼 N번 호출하지 않고 1번에 처리 → Rate Limit 문제 없음
    """
    url, key = _get_supabase()
    if not url or not key:
        return False
    if not rows:
        return True

    conflict_cols = UPSERT_KEYS.get(table)
    # id 제거 후 전송
    clean_rows = [{k: v for k, v in row.items() if k != 'id'} for row in rows]
    endpoint = f"{url}/rest/v1/{table}"
    prefer = "resolution=merge-duplicates,return=minimal"
    if conflict_cols:
        cols_str = urllib.parse.quote(','.join(conflict_cols))
        endpoint += f"?on_conflict={cols_str}"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(clean_rows, ensure_ascii=False).encode('utf-8'),
        headers=_headers(key, prefer=prefer),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _clear_cache()
            return True
    except Exception as e:
        print(f"[supabase_bulk_upsert] {table}: {e}")
        return False
