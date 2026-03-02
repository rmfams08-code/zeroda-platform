# zeroda_platform/database/db_init.py
import sqlite3
import os
from config.settings import DB_PATH


def init_db():
    """SQLite DB 초기화 - 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        pw_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        name TEXT,
        vendor TEXT DEFAULT '',
        schools TEXT DEFAULT '',
        edu_office TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS school_master (
        school_name TEXT PRIMARY KEY,
        vendor TEXT DEFAULT '',
        edu_office TEXT DEFAULT '',
        student_count INTEGER DEFAULT 0,
        address TEXT DEFAULT '',
        contact TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS vendor_info (
        vendor TEXT PRIMARY KEY,
        biz_name TEXT DEFAULT '',
        rep TEXT DEFAULT '',
        biz_no TEXT DEFAULT '',
        address TEXT DEFAULT '',
        contact TEXT DEFAULT '',
        email TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS contract_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        school_name TEXT,
        contract_type TEXT,
        unit_price REAL DEFAULT 0,
        start_date TEXT,
        end_date TEXT
    );

    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        month TEXT,
        weekdays TEXT,
        schools TEXT,
        items TEXT,
        driver TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS real_collection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        날짜 TEXT,
        학교명 TEXT,
        "음식물(kg)" REAL DEFAULT 0,
        "단가(원)" REAL DEFAULT 0,
        공급가 REAL DEFAULT 0,
        재활용방법 TEXT DEFAULT '',
        재활용업체 TEXT DEFAULT '',
        월 INTEGER,
        년도 INTEGER,
        월별파일 TEXT DEFAULT '',
        vendor TEXT DEFAULT '',
        collect_date TEXT,
        item_type TEXT,
        weight REAL DEFAULT 0,
        driver TEXT DEFAULT '',
        memo TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS sim_collection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        school_name TEXT,
        collect_date TEXT,
        item_type TEXT,
        weight REAL DEFAULT 0,
        driver TEXT DEFAULT '',
        memo TEXT DEFAULT '',
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS customer_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        name TEXT,
        biz_no TEXT DEFAULT '',
        rep TEXT DEFAULT '',
        addr TEXT DEFAULT '',
        biz_type TEXT DEFAULT '',
        biz_item TEXT DEFAULT '',
        email TEXT DEFAULT '',
        cust_type TEXT DEFAULT '학교'
    );

    CREATE TABLE IF NOT EXISTS biz_customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        name TEXT,
        biz_no TEXT DEFAULT '',
        contact TEXT DEFAULT '',
        address TEXT DEFAULT '',
        memo TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS price_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        school_name TEXT,
        item_type TEXT,
        unit_price REAL DEFAULT 0,
        year INTEGER,
        month INTEGER
    );

    CREATE TABLE IF NOT EXISTS schedule_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        school_name TEXT,
        weekday TEXT,
        item_type TEXT
    );

    CREATE TABLE IF NOT EXISTS today_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vendor TEXT,
        driver TEXT,
        school_name TEXT,
        schedule_date TEXT,
        item_type TEXT,
        status TEXT DEFAULT '예정'
    );
    """)

    # 기본 admin 계정 생성
    import hashlib
    admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, pw_hash, role, name, is_active, created_at)
        VALUES (?, ?, 'admin', '관리자', 1, datetime('now'))
    """, ('admin', admin_pw))

    conn.commit()
    conn.close()


def migrate_csv_to_db():
    """CSV 마이그레이션 - 필요 시 구현"""
    pass
