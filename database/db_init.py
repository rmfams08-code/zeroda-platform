# zeroda_platform/database/db_init.py
import sqlite3
import os
from config.settings import DB_PATH


def migrate_customer_price():
    """
    customer_info 테이블에 단가 컬럼이 없으면 추가 (기존 DB 마이그레이션)
    앱 시작 시 자동 실행
    """
    import sqlite3
    from config.settings import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cols = [row[1] for row in c.execute("PRAGMA table_info(customer_info)").fetchall()]
        added = 0
        for col, default in [('price_food', 0), ('price_recycle', 0), ('price_general', 0)]:
            if col not in cols:
                c.execute(f"ALTER TABLE customer_info ADD COLUMN {col} REAL DEFAULT {default}")
                added += 1
        if added:
            conn.commit()
            print(f"[migrate] customer_info 단가 컬럼 {added}개 추가")
        conn.close()
    except Exception as e:
        print(f"[migrate_customer_price] {e}")

def migrate_customer_recycler():
    """
    customer_info 테이블에 recycler(재활용자/처리자) 컬럼이 없으면 추가
    앱 시작 시 자동 실행
    """
    import sqlite3
    from config.settings import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cols = [row[1] for row in c.execute("PRAGMA table_info(customer_info)").fetchall()]
        if 'recycler' not in cols:
            c.execute("ALTER TABLE customer_info ADD COLUMN recycler TEXT DEFAULT ''")
            conn.commit()
            print("[migrate] customer_info recycler 컬럼 추가")
        conn.close()
    except Exception as e:
        print(f"[migrate_customer_recycler] {e}")


def migrate_customer_gps():
    """
    customer_info 테이블에 latitude/longitude 컬럼이 없으면 추가
    GPS 기반 근접 거래처 매칭용 — 앱 시작 시 자동 실행
    """
    import sqlite3
    from config.settings import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cols = [row[1] for row in c.execute("PRAGMA table_info(customer_info)").fetchall()]
        if 'latitude' not in cols:
            c.execute("ALTER TABLE customer_info ADD COLUMN latitude REAL DEFAULT 0")
            conn.commit()
            print("[migrate] customer_info latitude 컬럼 추가")
        if 'longitude' not in cols:
            c.execute("ALTER TABLE customer_info ADD COLUMN longitude REAL DEFAULT 0")
            conn.commit()
            print("[migrate] customer_info longitude 컬럼 추가")
        conn.close()
    except Exception as e:
        print(f"[migrate_customer_gps] {e}")


def migrate_school_alias():
    """
    school_master 테이블에 alias 컬럼이 없으면 추가 (기존 DB 마이그레이션)
    앱 시작 시 자동 실행
    """
    import sqlite3
    from config.settings import DB_PATH
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cols = [row[1] for row in c.execute("PRAGMA table_info(school_master)").fetchall()]
        if 'alias' not in cols:
            c.execute("ALTER TABLE school_master ADD COLUMN alias TEXT DEFAULT ''")
            conn.commit()
            print("[migrate] school_master alias 컬럼 추가")
        conn.close()
    except Exception as e:
        print(f"[migrate_school_alias] {e}")


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
        contact TEXT DEFAULT '',
        alias TEXT DEFAULT ''
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
        cust_type TEXT DEFAULT '학교',
        price_food REAL DEFAULT 0,
        price_recycle REAL DEFAULT 0,
        price_general REAL DEFAULT 0
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

    # 기본 admin 계정 생성 (SQLite)
    import hashlib
    admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, pw_hash, role, name, is_active, created_at)
        VALUES (?, ?, 'admin', '관리자', 1, datetime('now'))
    """, ('admin', admin_pw))

    conn.commit()
    conn.close()

    # 기본 admin 계정 생성 (GitHub)
    try:
        from services.github_storage import github_get, github_insert, is_github_available
        import hashlib
        if is_github_available():
            existing = github_get('users', {'user_id': 'admin'})
            if not existing:
                from datetime import datetime
                admin_pw = hashlib.sha256("admin123".encode()).hexdigest()
                github_insert('users', {
                    'user_id':    'admin',
                    'pw_hash':    admin_pw,
                    'role':       'admin',
                    'name':       '관리자',
                    'vendor':     '',
                    'is_active':  1,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                })
    except Exception as e:
        print(f"[init_db] GitHub admin 계정 생성 실패: {e}")


def migrate_schedules_unique():
    """schedules 테이블: 기존 vendor+month UNIQUE 제약 제거.
    품목별로 같은 월에 복수 행을 저장할 수 있도록 변경."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        c = conn.cursor()
        # 기존 UNIQUE 인덱스 삭제 (있으면)
        c.execute("""
            DROP INDEX IF EXISTS idx_schedules_vendor_month
        """)
        # 일반 인덱스 추가 (조회 성능용)
        c.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_schedules_vendor_month_items
            ON schedules(vendor, month)
        """)
        conn.commit()
        conn.close()
        print("[migrate_schedules_unique] UNIQUE 제약 제거 → 품목별 복수행 허용")
        return True
    except Exception as e:
        print(f"[migrate_schedules_unique] 오류: {e}")
        return False


def migrate_csv_to_db():
    """CSV 마이그레이션 - 필요 시 구현"""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# FEAT-02: 안전관리 평가 테이블 마이그레이션 (추가 - 기존 코드 유지)
# ─────────────────────────────────────────────────────────────────────────────

def migrate_biz_to_customer():
    """
    biz_customers 테이블의 데이터를 customer_info로 마이그레이션
    (거래처+일반업장 통합) — 구분: '일반업장' 으로 이전
    앱 시작 시 자동 실행, 이미 이전된 건은 건너뜀
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # biz_customers 테이블 존재 여부 확인
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='biz_customers'")
        if not c.fetchone():
            conn.close()
            return

        biz_rows = c.execute("SELECT * FROM biz_customers").fetchall()
        migrated = 0
        for row in biz_rows:
            vendor   = row['vendor'] if 'vendor' in row.keys() else ''
            biz_name = row['biz_name'] if 'biz_name' in row.keys() else (row['name'] if 'name' in row.keys() else '')
            if not biz_name:
                continue

            # 이미 customer_info에 같은 vendor+name 조합이 있으면 건너뜀
            exists = c.execute(
                "SELECT id FROM customer_info WHERE vendor=? AND name=?",
                (vendor, biz_name)
            ).fetchone()
            if exists:
                continue

            c.execute(
                """INSERT INTO customer_info
                   (vendor, name, biz_no, rep, addr, biz_type, biz_item, email, cust_type)
                   VALUES (?, ?, ?, '', '', '', '', '', '일반업장')""",
                (vendor, biz_name, row['biz_no'] if 'biz_no' in row.keys() else '')
            )
            migrated += 1

        if migrated > 0:
            conn.commit()
            print(f"[migrate_biz_to_customer] {migrated}건 일반업장 → customer_info 이전 완료")
        conn.close()
    except Exception as e:
        print(f"[migrate_biz_to_customer] {e}")


def migrate_safety_tables():
    """
    안전관리 평가용 테이블 2개 생성 (없는 경우에만)
    - school_zone_violations: 스쿨존 위반 기록
    - safety_scores: 안전관리 평가 결과 캐시
    앱 시작 시 자동 실행
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # 스쿨존 위반 기록 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS school_zone_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                driver TEXT DEFAULT '',
                violation_date TEXT NOT NULL,
                violation_type TEXT DEFAULT '기타',
                location TEXT DEFAULT '',
                fine_amount INTEGER DEFAULT 0,
                memo TEXT DEFAULT '',
                created_at TEXT
            )
        """)

        # 안전관리 평가 결과 캐시 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS safety_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                year_month TEXT NOT NULL,
                violation_score REAL DEFAULT 40.0,
                checklist_score REAL DEFAULT 0.0,
                education_score REAL DEFAULT 0.0,
                total_score REAL DEFAULT 0.0,
                grade TEXT DEFAULT 'D',
                updated_at TEXT,
                UNIQUE(vendor, year_month)
            )
        """)

        # 일일 안전보건 점검표 테이블 (산업안전보건법 제36조)
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_safety_check (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                driver TEXT NOT NULL,
                check_date TEXT NOT NULL,
                vehicle_no TEXT DEFAULT '',
                category TEXT NOT NULL,
                check_items TEXT DEFAULT '{}',
                total_ok INTEGER DEFAULT 0,
                total_fail INTEGER DEFAULT 0,
                fail_memo TEXT DEFAULT '',
                created_at TEXT,
                UNIQUE(vendor, driver, check_date, category)
            )
        """)

        # safety_scores 테이블에 daily_check_score 컬럼 추가 (기존 DB 호환)
        try:
            c.execute("ALTER TABLE safety_scores ADD COLUMN daily_check_score REAL DEFAULT 0.0")
        except Exception:
            pass  # 이미 존재하면 무시

        conn.commit()
        conn.close()
        print("[migrate_safety_tables] 안전관리 평가 테이블 준비 완료")
    except Exception as e:
        print(f"[migrate_safety_tables] {e}")


def migrate_meal_tables():
    """
    단체급식 관리용 테이블 2개 생성 (없는 경우에만)
    - meal_menus: 일별 식단 등록 (메뉴명, 칼로리, 영양정보)
    - meal_analysis: 잔반 분석 결과 캐시 (메뉴↔수거량 매칭)
    앱 시작 시 자동 실행
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # 일별 식단 등록 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS meal_menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                site_type TEXT DEFAULT '학교',
                meal_date TEXT NOT NULL,
                meal_type TEXT DEFAULT '중식',
                menu_items TEXT DEFAULT '[]',
                calories REAL DEFAULT 0,
                nutrition_info TEXT DEFAULT '{}',
                servings INTEGER DEFAULT 0,
                year_month TEXT DEFAULT '',
                created_at TEXT,
                UNIQUE(site_name, meal_date, meal_type)
            )
        """)

        # 잔반 분석 결과 캐시 테이블
        c.execute("""
            CREATE TABLE IF NOT EXISTS meal_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                year_month TEXT NOT NULL,
                meal_date TEXT NOT NULL,
                menu_items TEXT DEFAULT '[]',
                waste_kg REAL DEFAULT 0,
                waste_per_person REAL DEFAULT 0,
                waste_rate REAL DEFAULT 0,
                grade TEXT DEFAULT '-',
                created_at TEXT,
                UNIQUE(site_name, meal_date)
            )
        """)

        conn.commit()
        conn.close()
        print("[migrate_meal_tables] 단체급식 관리 테이블 준비 완료")
    except Exception as e:
        print(f"[migrate_meal_tables] {e}")


def migrate_school_nutrition_to_meal():
    """
    기존 school_nutrition 역할 계정을 meal_manager로 자동 전환
    (school_nutrition은 더 이상 독립 화면이 없으며, meal_manager와 동일 메뉴 사용)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE role='school_nutrition'")
        cnt = c.fetchone()[0]
        if cnt > 0:
            c.execute("UPDATE users SET role='meal_manager' WHERE role='school_nutrition'")
            conn.commit()
            print(f"[migrate_school_nutrition_to_meal] {cnt}건 school_nutrition → meal_manager 전환 완료")
        conn.close()
    except Exception as e:
        print(f"[migrate_school_nutrition_to_meal] {e}")


def migrate_processing_confirm_table():
    """
    처리확인(계근표) 테이블 생성 (없는 경우에만)
    - 기사가 처리장에서 계근표 사진촬영 + 처리량 입력 + GPS 위치 보고
    - 본사/외주업체관리자에게 실시간 연동
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS processing_confirm (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                driver TEXT NOT NULL,
                confirm_date TEXT NOT NULL,
                confirm_time TEXT DEFAULT '',
                total_weight REAL DEFAULT 0,
                photo_attached INTEGER DEFAULT 0,
                latitude REAL DEFAULT 0,
                longitude REAL DEFAULT 0,
                location_name TEXT DEFAULT '',
                memo TEXT DEFAULT '',
                status TEXT DEFAULT 'submitted',
                confirmed_by TEXT DEFAULT '',
                confirmed_at TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        print("[migrate_processing_confirm_table] 처리확인 테이블 준비 완료")
    except Exception as e:
        print(f"[migrate_processing_confirm_table] {e}")


def migrate_expenses_table():
    """월말정산 지출내역 테이블 생성 (없는 경우에만)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL,
                year_month TEXT NOT NULL,
                item TEXT NOT NULL DEFAULT '',
                amount REAL DEFAULT 0,
                pay_date TEXT DEFAULT '',
                memo TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
        print("[migrate_expenses_table] 지출내역 테이블 준비 완료")
    except Exception as e:
        print(f"[migrate_expenses_table] {e}")


def migrate_meal_analysis_remark():
    """meal_analysis 테이블에 remark 컬럼 추가 (메뉴별 특이사항 자동생성용)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # 컬럼 존재 여부 확인 후 추가
        c.execute("PRAGMA table_info(meal_analysis)")
        cols = [row[1] for row in c.fetchall()]
        if 'remark' not in cols:
            c.execute("ALTER TABLE meal_analysis ADD COLUMN remark TEXT DEFAULT ''")
            conn.commit()
            print("[migrate_meal_analysis_remark] remark 컬럼 추가 완료")
        conn.close()
    except Exception as e:
        print(f"[migrate_meal_analysis_remark] {e}")


def migrate_neis_school_code():
    """
    customer_info 테이블에 NEIS 학교코드 컬럼 추가
    - neis_edu_code: 시도교육청코드 (예: J10 = 경기도)
    - neis_school_code: 학교표준코드 (예: 7530560)
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cols = [row[1] for row in c.execute("PRAGMA table_info(customer_info)").fetchall()]
        if 'neis_edu_code' not in cols:
            c.execute("ALTER TABLE customer_info ADD COLUMN neis_edu_code TEXT DEFAULT ''")
            conn.commit()
            print("[migrate_neis_school_code] neis_edu_code 컬럼 추가")
        if 'neis_school_code' not in cols:
            c.execute("ALTER TABLE customer_info ADD COLUMN neis_school_code TEXT DEFAULT ''")
            conn.commit()
            print("[migrate_neis_school_code] neis_school_code 컬럼 추가")
        conn.close()
    except Exception as e:
        print(f"[migrate_neis_school_code] {e}")


def migrate_meal_schedules_table():
    """
    식단기반 수거일정 테이블 생성 (없는 경우에만)
    - 급식담당자가 식단 업로드 → draft 상태로 자동 생성
    - 본사관리자 승인 → approved → schedules 테이블에 확정 반영
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS meal_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT NOT NULL DEFAULT '',
                school_name TEXT NOT NULL,
                meal_date TEXT NOT NULL,
                collect_date TEXT NOT NULL,
                item_type TEXT DEFAULT '음식물',
                status TEXT DEFAULT 'draft',
                uploaded_by TEXT DEFAULT '',
                approved_by TEXT DEFAULT '',
                note TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_meal_schedules_vendor_status
            ON meal_schedules(vendor, status)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_meal_schedules_school_date
            ON meal_schedules(school_name, meal_date)
        """)
        conn.commit()
        conn.close()
        print("[migrate_meal_schedules_table] 식단기반 수거일정 테이블 준비 완료")
    except Exception as e:
        print(f"[migrate_meal_schedules_table] {e}")


def migrate_customer_fixed_fee():
    """customer_info 테이블에 fixed_monthly_fee 컬럼 추가 (기타 구분 월 고정비용)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        cols = [row[1] for row in c.execute("PRAGMA table_info(customer_info)").fetchall()]
        if 'fixed_monthly_fee' not in cols:
            c.execute("ALTER TABLE customer_info ADD COLUMN fixed_monthly_fee REAL DEFAULT 0")
            conn.commit()
            print("[migrate_customer_fixed_fee] fixed_monthly_fee 컬럼 추가 완료")
        conn.close()
    except Exception as e:
        print(f"[migrate_customer_fixed_fee] {e}")


