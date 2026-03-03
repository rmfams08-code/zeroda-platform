# zeroda_platform/database/db_init.py
import sqlite3
import os
from config.settings import DB_PATH


def migrate_vendor_names():
    """
    기존 users 테이블의 vendor 필드가 업체명으로 저장된 경우 업체ID로 교정
    예: '하영자원' → 'hy'
    앱 시작 시 자동 실행
    """
    import sqlite3
    from config.settings import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # vendor_info에서 biz_name → vendor ID 매핑 구성
        vendors = c.execute("SELECT vendor, biz_name FROM vendor_info").fetchall()
        name_to_id = {v['biz_name']: v['vendor'] for v in vendors if v['biz_name']}

        if not name_to_id:
            conn.close()
            return

        # users 테이블에서 업체명으로 저장된 vendor 교정
        users = c.execute("SELECT user_id, vendor FROM users").fetchall()
        fixed = 0
        for u in users:
            vendor_val = u['vendor'] or ''
            if vendor_val in name_to_id:
                correct_id = name_to_id[vendor_val]
                c.execute("UPDATE users SET vendor=? WHERE user_id=?",
                          (correct_id, u['user_id']))
                fixed += 1

        if fixed > 0:
            conn.commit()
            print(f"[migrate] vendor 필드 교정: {fixed}개 계정")
        conn.close()
    except Exception as e:
        print(f"[migrate_vendor_names] {e}")


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
        vendor TEXT DEFAULT '',
        school_name TEXT DEFAULT '',
        collect_date TEXT,
        item_type TEXT DEFAULT '',
        weight REAL DEFAULT 0,
        unit_price REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        driver TEXT DEFAULT '',
        memo TEXT DEFAULT '',
        status TEXT DEFAULT 'draft',
        submitted_at TEXT,
        created_at TEXT,
        날짜 TEXT,
        학교명 TEXT,
        "음식물(kg)" REAL DEFAULT 0,
        "단가(원)" REAL DEFAULT 0,
        공급가 REAL DEFAULT 0,
        재활용방법 TEXT DEFAULT '',
        재활용업체 TEXT DEFAULT '',
        월 INTEGER,
        년도 INTEGER,
        월별파일 TEXT DEFAULT ''
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

    # 안전관리 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS safety_education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT, driver TEXT, edu_date TEXT,
            edu_type TEXT, edu_hours INTEGER DEFAULT 0,
            instructor TEXT DEFAULT '', result TEXT DEFAULT '이수',
            memo TEXT DEFAULT '', created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS safety_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT, driver TEXT, check_date TEXT,
            vehicle_no TEXT DEFAULT '', check_items TEXT DEFAULT '{}',
            total_ok INTEGER DEFAULT 0, total_fail INTEGER DEFAULT 0,
            inspector TEXT DEFAULT '', memo TEXT DEFAULT '', created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS accident_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT, driver TEXT, occur_date TEXT,
            occur_location TEXT DEFAULT '', accident_type TEXT DEFAULT '기타',
            severity TEXT DEFAULT '경상', description TEXT DEFAULT '',
            action_taken TEXT DEFAULT '', status TEXT DEFAULT '신고완료',
            created_at TEXT
        )
    """)

    # 탄소감축량 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS carbon_reduction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_name TEXT, vendor TEXT, year INTEGER, month INTEGER,
            food_waste_kg REAL DEFAULT 0, recycle_kg REAL DEFAULT 0,
            general_kg REAL DEFAULT 0, carbon_reduced REAL DEFAULT 0,
            tree_equivalent REAL DEFAULT 0, created_at TEXT
        )
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
