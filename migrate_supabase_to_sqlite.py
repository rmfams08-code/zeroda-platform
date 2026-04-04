#!/usr/bin/env python3
"""
Supabase → SQLite 일회성 데이터 마이그레이션 스크립트
서버에서 실행: python3 migrate_supabase_to_sqlite.py
"""
import json
import sqlite3
import urllib.request
import os
import sys

DB_PATH = os.environ.get("ZERODA_DB_PATH", "zeroda.db")
SECRETS_PATH = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')

def _read_secrets():
    url, key = "", ""
    try:
        with open(SECRETS_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('SUPABASE_URL'):
                    url = line.split('=', 1)[1].strip().strip('"').strip("'")
                elif line.startswith('SUPABASE_KEY'):
                    key = line.split('=', 1)[1].strip().strip('"').strip("'")
    except Exception as e:
        print(f"[ERROR] secrets.toml 읽기 실패: {e}")
    return url.rstrip('/'), key

TABLES = [
    'real_collection', 'sim_collection', 'users', 'vendor_info',
    'customer_info', 'schedules', 'school_master', 'safety_education',
    'safety_checklist', 'accident_report', 'carbon_reduction',
    'processing_confirm', 'meal_menus', 'meal_analysis', 'meal_schedules',
    'photo_records', 'school_zone_violations', 'safety_scores',
]

def fetch_supabase(url, key, table):
    endpoint = f"{url}/rest/v1/{table}?select=*&limit=50000"
    req = urllib.request.Request(endpoint, headers={
        "apikey": key, "Authorization": f"Bearer {key}",
        "Content-Type": "application/json", "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data if isinstance(data, list) else []
    except urllib.error.HTTPError as e:
        if e.code == 404: return []
        print(f"  [HTTP ERROR] {table}: {e.code}")
        return []
    except Exception as e:
        print(f"  [ERROR] {table}: {e}")
        return []

def create_table_if_needed(conn, table, rows):
    if not rows: return
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if c.fetchone():
        existing = [r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
        for col in rows[0].keys():
            if col not in existing and col != 'id':
                try:
                    c.execute(f'ALTER TABLE {table} ADD COLUMN "{col}" TEXT')
                    print(f"    + 컬럼 추가: {col}")
                except Exception: pass
        return
    cols = [f'"{k}" TEXT' for k in rows[0].keys() if k != 'id']
    cols_sql = ', '.join(cols)
    c.execute(f'CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_sql})')
    print(f"  [CREATE] {table} 테이블 생성")

def insert_rows(conn, table, rows):
    if not rows: return 0
    c = conn.cursor()
    count = 0
    for row in rows:
        data = {k: v for k, v in row.items()}
        keys = ', '.join(f'"{k}"' for k in data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f'INSERT OR REPLACE INTO {table} ({keys}) VALUES ({placeholders})'
        try:
            c.execute(sql, list(data.values()))
            count += 1
        except Exception as e:
            print(f"    [SKIP] {e}")
    conn.commit()
    return count

def main():
    print("=" * 60)
    print("  Supabase → SQLite 데이터 마이그레이션")
    print("=" * 60)
    url, key = _read_secrets()
    if not url or not key:
        print("[ERROR] SUPABASE_URL 또는 SUPABASE_KEY가 없습니다.")
        print(f"  secrets.toml 경로: {SECRETS_PATH}")
        sys.exit(1)
    print(f"  Supabase URL: {url}")
    print(f"  SQLite DB: {os.path.abspath(DB_PATH)}")
    print()
    conn = sqlite3.connect(DB_PATH)
    total_tables = 0
    total_rows = 0
    for table in TABLES:
        print(f"[{table}]", end=" ")
        rows = fetch_supabase(url, key, table)
        if not rows:
            print("→ 데이터 없음 (스킵)")
            continue
        create_table_if_needed(conn, table, rows)
        inserted = insert_rows(conn, table, rows)
        total_tables += 1
        total_rows += inserted
        print(f"→ {inserted}건 저장 완료")
    conn.close()
    print()
    print("=" * 60)
    print(f"  완료! {total_tables}개 테이블, {total_rows}건 마이그레이션")
    print("=" * 60)

if __name__ == '__main__':
    main()
