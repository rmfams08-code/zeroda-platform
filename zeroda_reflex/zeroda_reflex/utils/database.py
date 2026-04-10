# zeroda_reflex/utils/database.py
# 기존 zeroda 앱의 DB 어댑터 (PostgreSQL 전용)

import json
import math
import os
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── PostgreSQL 연결 정보 ──
PG_HOST = os.environ.get("ZERODA_PG_HOST", "")
PG_PORT = int(os.environ.get("ZERODA_PG_PORT", "5432"))
PG_DB = os.environ.get("ZERODA_PG_DB", "zeroda")
PG_USER = os.environ.get("ZERODA_PG_USER", "zeroda")
PG_PASSWORD = os.environ.get("ZERODA_PG_PASSWORD", "")
PG_MIN_CONN = int(os.environ.get("ZERODA_PG_MIN_CONN", "2"))
PG_MAX_CONN = int(os.environ.get("ZERODA_PG_MAX_CONN", "20"))

# ══════════════════════════════════════════
#  Phase 1-6: 매직넘버 상수화
#  - 하드코딩된 숫자를 상수로 관리하여 유지보수성 향상
# ══════════════════════════════════════════
VAT_RATE = 0.1                   # 부가가치세 세율 (10%)
CARBON_FOOD = 0.47               # 음식물 1kg당 탄소감축 계수 (kg CO₂)
CARBON_RECYCLE = 0.21            # 재활용 1kg당 탄소감축 계수 (kg CO₂)
CARBON_GENERAL = 0.09            # 일반폐기물 1kg당 탄소감축 계수 (kg CO₂)
WASTE_REDUCTION_RATE = 0.1       # 잔반감축 목표 비율 (10%)


# ══════════════════════════════════════════
#  SQL 인젝션 방어 — 테이블/컬럼명 화이트리스트
# ══════════════════════════════════════════

_ALLOWED_TABLES = frozenset({
    "users", "customer_info", "biz_customers", "real_collection",
    "processing_confirm", "daily_safety_check", "safety_checklist",
    "safety_education", "driver_checkout", "photo_records",
    "schedules", "vendor_info", "school_master", "school_zone_violations",
    "safety_scores", "accident_report", "driver_auth_tokens",
    "meal_schedules", "doc_templates", "doc_issue_log",
})

_ALLOWED_COLUMNS = frozenset({
    # users
    "user_id", "pw_hash", "role", "name", "vendor", "schools",
    "edu_office", "is_active", "approval_status", "status",
    "pending_vendor", "pending_school_name",
    "neis_edu_pending", "neis_school_pending",
    # customer_info
    "cust_type", "price_food", "price_recycle", "price_general",
    "address", "phone", "biz_no", "ceo", "fixed_fee", "email",
    "neis_edu_code", "neis_school_code", "rep", "addr",
    "cust_phone", "cust_email", "tax_type",
    # real_collection
    "school_name", "collect_date", "item_type", "weight", "driver",
    "memo", "vehicle_no",
    "unit_price", "amount", "collect_time", "submitted_at", "lat", "lng",
    # daily_safety_check
    "check_date", "category", "check_items", "fail_memo",
    # driver_checkout
    "checkout_date", "checkout_time",
    # processing_confirm
    "confirm_date", "total_weight",
    "confirm_time", "location_name", "first_weigh_time", "second_weigh_time",
    "gross_weight", "net_weight", "vehicle_number", "processor_company", "weighslip_photo_path",
    # photo_records
    "photo_type", "photo_url",
    # school_zone_violations
    "violation_date", "violation_type", "location", "fine_amount",
    # schedules
    "month", "day_schedule",
    "weekdays", "items", "registered_by",
    # school_master
    "alias",
    # vendor_info
    "account", "biz_name", "contact",
    # 공통
    "id", "vendor", "created_at", "updated_at",
})


def _check_table(table: str) -> str:
    """테이블명 화이트리스트 검증. 실패 시 ValueError."""
    if table not in _ALLOWED_TABLES:
        raise ValueError(f"허용되지 않은 테이블명: {table}")
    return table


def _check_column(col: str) -> str:
    """컬럼명 화이트리스트 검증. 실패 시 ValueError."""
    if col not in _ALLOWED_COLUMNS:
        raise ValueError(f"허용되지 않은 컬럼명: {col}")
    return col


def _check_columns(cols: dict | list) -> None:
    """딕셔너리 키 또는 리스트의 모든 컬럼명 검증."""
    keys = cols.keys() if isinstance(cols, dict) else cols
    for k in keys:
        _check_column(k)


# ══════════════════════════════════════════
#  PostgreSQL 어댑터
#  - psycopg 커넥션 풀 + 호환 인터페이스
# ══════════════════════════════════════════

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except ImportError as e:
    logger.error("psycopg / psycopg_pool 미설치. pip install 'psycopg[binary]' psycopg_pool")
    raise

# 모듈 전역 커넥션 풀 (앱 전체에서 1개)
_PG_POOL: Optional["ConnectionPool"] = None

def _get_pool() -> "ConnectionPool":
    global _PG_POOL
    if _PG_POOL is None:
        conninfo = (
            f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} "
            f"user={PG_USER} password={PG_PASSWORD} "
            f"connect_timeout=5 application_name=zeroda_reflex"
        )
        _PG_POOL = ConnectionPool(
            conninfo=conninfo,
            min_size=PG_MIN_CONN,
            max_size=PG_MAX_CONN,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        logger.info(f"[PG POOL] created min={PG_MIN_CONN} max={PG_MAX_CONN}")
    return _PG_POOL


class _PgCursorResult:
    """sqlite3 cursor.fetchall() 호환 래퍼.
    dict_row 결과를 반환하므로 dict(r) 로 변환 가능."""
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class PgWrapper:
    """sqlite3.Connection 호환 어댑터.
    - .execute(sql, params) 시 ? → %s 자동 치환
    - 결과는 dict_row 형태 (sqlite3.Row 와 동일하게 dict() 가능)
    - .commit() / .close() / context manager 지원
    - row_factory 속성은 호환용 stub (실제 효과 없음)
    """
    def __init__(self):
        pool = _get_pool()
        self._conn = pool.getconn()
        self._closed = False
        self.row_factory = None  # 호환용 stub

    @staticmethod
    def _q(sql: str) -> str:
        """? placeholder → %s 변환.
        주의: 문자열 리터럴 안의 ? 는 거의 없지만, 만약 있으면
             자료 파일 05_syntax_fixes_diff.md 의 예외 목록 참조."""
        return sql.replace("?", "%s")

    def execute(self, sql: str, params=None):
        cur = self._conn.cursor()
        try:
            cur.execute(self._q(sql), params or ())
            # SELECT 면 결과 가져옴, 그 외엔 빈 리스트
            if cur.description:
                rows = cur.fetchall()
                return _PgCursorResult(rows)
            return _PgCursorResult([])
        finally:
            cur.close()

    def executemany(self, sql: str, seq_of_params):
        cur = self._conn.cursor()
        try:
            cur.executemany(self._q(sql), seq_of_params)
            return _PgCursorResult([])
        finally:
            cur.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        if self._closed:
            return
        try:
            pool = _get_pool()
            pool.putconn(self._conn)
        except Exception as e:
            logger.warning(f"[PG] putconn failed: {e}")
            try:
                self._conn.close()
            except Exception:
                pass
        finally:
            self._closed = True

    # context manager (with get_db() as conn:)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_db():
    """PostgreSQL 연결 반환"""
    return PgWrapper()


def db_get(table: str, where: dict = None) -> list[dict]:
    """테이블에서 조건에 맞는 행 조회"""
    _check_table(table)
    if where:
        _check_columns(where)
    conn = get_db()
    try:
        if where:
            clauses = " AND ".join(f"{k} = ?" for k in where)
            values = list(where.values())
            sql = f"SELECT * FROM {table} WHERE {clauses}"
            rows = conn.execute(sql, values).fetchall()
        else:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] db_get: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def db_insert(table: str, data: dict) -> bool:
    """행 삽입"""
    _check_table(table)
    _check_columns(data)
    conn = get_db()
    try:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            list(data.values()),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] db_insert: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def db_upsert(table: str, data: dict, key_col: str = "id") -> bool:
    """행 삽입 또는 업데이트.
    SQLite 와 PostgreSQL 모두 ON CONFLICT(...) DO UPDATE 지원하므로
    문법 동일하게 사용."""
    _check_table(table)
    _check_column(key_col)
    _check_columns(data)
    conn = get_db()
    try:
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        updates = ", ".join(f"{k} = ?" for k in data if k != key_col)
        sql = (
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
            f"ON CONFLICT({key_col}) DO UPDATE SET {updates}"
        )
        values = list(data.values()) + [v for k, v in data.items() if k != key_col]
        conn.execute(sql, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] db_upsert: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def db_delete(table: str, where: dict) -> bool:
    if not where:
        return False
    _check_table(table)
    _check_columns(where)
    conn = get_db()
    try:
        cols = " AND ".join([f"{k}=?" for k in where.keys()])
        sql = f"DELETE FROM {table} WHERE {cols}"
        conn.execute(sql, tuple(where.values()))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] db_delete({table}): {e}")
        logger.warning(f"Exception in db_delete: {str(e)}")
        return False
    finally:
        conn.close()

# ── 인증 관련 ──

def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 우선 검증, SHA256/평문 폴백 (기존 계정 호환 — 로그인 시 자동 마이그레이션 대상)"""
    if not plain or not hashed:
        return False
    # 1순위: bcrypt 검증
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        import bcrypt
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception as e:
            logger.error(f"[verify_password] bcrypt 검증 실패: {e}")
            return False
    # 2순위: SHA256 레거시 (마이그레이션 대상)
    if hashlib.sha256(plain.strip().encode()).hexdigest() == hashed.strip():
        logger.info(f"[verify_password] SHA256 레거시 비밀번호 감지 — bcrypt 마이그레이션 필요")
        return True
    # 3순위: 평문 레거시 (마이그레이션 대상)
    if plain.strip() == hashed.strip():
        logger.warning(f"[verify_password] 평문 비밀번호 감지 — bcrypt 마이그레이션 필요")
        return True
    return False


def authenticate_user(user_id: str, password: str) -> Optional[dict]:
    """사용자 인증. 성공 시 user dict 반환, 실패 시 None.
    레거시(SHA256/평문) 비밀번호는 로그인 성공 시 bcrypt로 자동 마이그레이션."""
    rows = db_get("users", {"user_id": user_id})
    if not rows:
        return None
    user = rows[0]
    # 승인 상태 확인
    if user.get("approval_status") == "pending":
        return None
    if user.get("approval_status") == "rejected":
        return None
    stored_pw = user.get("pw_hash", "")
    if not verify_password(password, stored_pw):
        return None
    # 레거시 비밀번호 → bcrypt 자동 마이그레이션
    if stored_pw and not (stored_pw.startswith("$2b$") or stored_pw.startswith("$2a$")):
        try:
            import bcrypt as _bc
            new_hash = _bc.hashpw(password.encode(), _bc.gensalt()).decode()
            conn = get_db()
            try:
                conn.execute(
                    "UPDATE users SET pw_hash = ? WHERE user_id = ?",
                    (new_hash, user_id),
                )
                conn.commit()
                logger.info(f"[authenticate_user] bcrypt 마이그레이션 완료: {user_id}")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"[authenticate_user] bcrypt 마이그레이션 실패: {e}")
    return user


def get_schools_by_vendor(vendor: str) -> list[str]:
    """업체에 배정된 학교 목록"""
    rows = db_get("customer_info", {"vendor": vendor})
    return [r.get("name", "") for r in rows if r.get("name")]


def get_daily_safety_checks(vendor: str, driver: str, check_date: str) -> list[dict]:
    """일일 안전점검 기록 조회"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_safety_check WHERE vendor=? AND driver=? AND check_date=?",
            (vendor, driver, check_date),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_daily_safety_checks: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def save_daily_safety_check(
    vendor: str, driver: str, check_date: str,
    category: str, check_items: dict, fail_memo: str = ""
) -> bool:
    """일일 안전점검 저장"""
    return db_insert("daily_safety_check", {
        "vendor": vendor,
        "driver": driver,
        "check_date": check_date,
        "category": category,
        "check_items": json.dumps(check_items, ensure_ascii=False),
        "fail_memo": fail_memo,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def save_daily_safety_checks_transaction(
    vendor: str, driver: str, check_date: str,
    categories_data: list[dict], fail_memo: str = ""
) -> bool:
    """다중 카테고리 안전점검을 트랜잭션으로 저장

    Args:
        vendor: 업체명
        driver: 기사명
        check_date: 점검 날짜 (YYYY-MM-DD)
        categories_data: 카테고리별 체크 데이터 리스트
                        [{"category": str, "check_items": dict}, ...]
        fail_memo: 불량 메모

    Returns:
        bool: 성공 여부
    """
    conn = get_db()
    try:
        # 모든 INSERT를 하나의 트랜잭션으로 처리
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for cat_data in categories_data:
            category = cat_data.get("category", "")
            check_items = cat_data.get("check_items", {})

            cols = "vendor, driver, check_date, category, check_items, fail_memo, created_at"
            placeholders = "?, ?, ?, ?, ?, ?, ?"
            values = (
                vendor,
                driver,
                check_date,
                category,
                json.dumps(check_items, ensure_ascii=False),
                fail_memo,
                created_at,
            )

            # PG 호환: ON CONFLICT 사용. UNIQUE 제약: (vendor, driver, check_date, category)
            upsert_sql = (
                f"INSERT INTO daily_safety_check ({cols}) VALUES ({placeholders}) "
                f"ON CONFLICT (vendor, driver, check_date, category) DO UPDATE SET "
                f"check_items = EXCLUDED.check_items, "
                f"fail_memo = EXCLUDED.fail_memo, "
                f"created_at = EXCLUDED.created_at"
            )
            conn.execute(upsert_sql, values)

        # 모든 INSERT가 성공한 후에만 COMMIT
        conn.commit()
        return True
    except Exception as e:
        # 에러 발생 시 ROLLBACK
        print(f"[DB ERROR] save_daily_safety_checks_transaction: {e}")
        conn.rollback()
        logger.warning(f'Transaction failed in save_daily_safety_checks_transaction: {str(e)}')
        return False
    finally:
        conn.close()


# ── 수거 데이터 관련 ──

def get_today_collections(vendor: str, driver: str, collect_date: str) -> list[dict]:
    """오늘 수거 기록 조회"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, * FROM real_collection WHERE vendor=? AND driver=? AND collect_date=? ORDER BY created_at DESC",
            (vendor, driver, collect_date),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_today_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_driver_collections_range(vendor: str, driver: str, date_from: str, date_to: str) -> list[dict]:
    """기간별 수거 기록 조회 (date_from ~ date_to, YYYY-MM-DD)"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, * FROM real_collection "
            "WHERE vendor=? AND driver=? AND collect_date BETWEEN ? AND ? "
            "ORDER BY collect_date DESC, id DESC",
            (vendor, driver, date_from, date_to),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_driver_collections_range: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def ensure_real_collection_gps_columns() -> None:
    """real_collection 테이블에 lat/lng 컨럼 추가 (idempotent — 이미 있으면 무시).

    ▶ ADD COLUMN IF NOT EXISTS 사용 → 중복 시 에러 없음.
      각 컬럼마다 별도 커넥션 사용 → 첫 번째 실패가 두 번째를 오염시키지 않음.
    """
    # DOUBLE PRECISION = REAL 호환. IF NOT EXISTS 로 중복 무시.
    for col_name, col_type in (("lat", "DOUBLE PRECISION"), ("lng", "DOUBLE PRECISION")):
        conn = get_db()  # 컬럼별 독립 커넥션 (트랜잭션 오염 방지)
        try:
            conn.execute(
                f"ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
            )
            conn.commit()
            logger.info(f"[GPS] {col_name} 컬럼 확인/추가 완료 (PG)")
        except Exception as e:
            conn.rollback()
            logger.warning(f"[GPS] {col_name} 컬럼 추가 실패 (PG): {e}")
        finally:
            conn.close()


# GPS 컨럼 보장 (모듈 임포트 시 1회 실행)
try:
    ensure_real_collection_gps_columns()
except Exception as _gps_col_err:
    print(f"[DB ERROR] GPS 컨럼 초기화 실패: {_gps_col_err}")


def ensure_missing_tables() -> None:
    """photo_records / driver_checkout 테이블이 없으면 생성 (idempotent).

    사례 5(2026-04-07) GitHub 폴더 업로드 사고 수습 과정에서 마이그레이션이
    누락되어 운영 DB에 두 테이블이 없는 상태로 운영되고 있었음.
    컬럼 구조는 save_photo_record / save_driver_checkout 의 INSERT payload 기준.
    PostgreSQL은 AUTOINCREMENT 미지원 → SERIAL PRIMARY KEY 사용.
    """
    _auto = "SERIAL PRIMARY KEY"
    conn = get_db()
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS driver_checkout (
                id            {_auto},
                vendor        TEXT,
                driver        TEXT,
                checkout_date TEXT,
                checkout_time TEXT,
                created_at    TEXT
            )
        """)
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS photo_records (
                id           {_auto},
                vendor       TEXT,
                driver       TEXT,
                school_name  TEXT,
                photo_type   TEXT,
                photo_url    TEXT,
                collect_date TEXT,
                memo         TEXT,
                created_at   TEXT
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] ensure_missing_tables: {e}")
        logger.warning(f"ensure_missing_tables 실패 (idempotent): {e}")
    finally:
        conn.close()


# 누락 테이블 자동 생성 (모듈 임포트 시 1회 실행)
try:
    ensure_missing_tables()
except Exception as _tbl_init_err:
    print(f"[DB ERROR] 누락 테이블 초기화 실패: {_tbl_init_err}")


def ensure_driver_auth_tokens_table() -> None:
    """driver_auth_tokens 테이블 + 인덱스 생성 (idempotent)."""
    conn = get_db()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS driver_auth_tokens ("
            "  token           VARCHAR(64) PRIMARY KEY,"
            "  user_id         VARCHAR(50) NOT NULL,"
            "  device_hint     VARCHAR(200) DEFAULT '',"
            "  created_at      TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Seoul'),"
            "  last_used_at    TIMESTAMP,"
            "  expires_at      TIMESTAMP NOT NULL,"
            "  revoked         SMALLINT NOT NULL DEFAULT 0,"
            "  revoked_at      TIMESTAMP,"
            "  revoked_reason  VARCHAR(50) DEFAULT ''"
            ")"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_driver_auth_tokens_user_id "
            "ON driver_auth_tokens(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_driver_auth_tokens_expires "
            "ON driver_auth_tokens(expires_at)"
        )
        conn.commit()
        logger.info("ensure_driver_auth_tokens_table: OK")
    except Exception as e:
        print(f"[DB ERROR] ensure_driver_auth_tokens_table: {e}")
        logger.warning(f"ensure_driver_auth_tokens_table 실패: {e}")
    finally:
        conn.close()


# driver_auth_tokens 테이블 자동 생성
try:
    ensure_driver_auth_tokens_table()
except Exception as _dat_init_err:
    print(f"[DB ERROR] driver_auth_tokens 초기화 실패: {_dat_init_err}")


# ── driver 자동로그인 토큰 CRUD (PG 전용) ──────────────────────────────────

def create_driver_token(user_id: str, device_hint: str = "") -> str:
    """토큰 생성 및 DB 저장. 반환값: 생성된 토큰 문자열.
    로그에 token 값 절대 기록 금지.
    """
    import secrets
    token = secrets.token_urlsafe(48)
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO driver_auth_tokens"
            " (token, user_id, device_hint, expires_at)"
            " VALUES (%s, %s, %s, NOW() + INTERVAL '90 days')",
            (token, user_id, device_hint[:200] if device_hint else ""),
        )
        conn.commit()
        logger.info("create_driver_token: user_id=%s device_hint=%.40s", user_id, device_hint)
        return token
    except Exception as e:
        logger.error("create_driver_token 실패: user_id=%s err=%s", user_id, e)
        return ""
    finally:
        conn.close()


def verify_driver_token(token: str) -> "str | None":
    """토큰 검증. 유효하면 user_id 반환 + last_used_at 갱신. 무효면 None.
    토큰 값 로그 금지.
    """
    if not token:
        return None
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT user_id FROM driver_auth_tokens"
            " WHERE token=%s AND revoked=0 AND expires_at > NOW()",
            (token,),
        ).fetchone()
        if not row:
            return None
        user_id = row["user_id"]
        conn.execute(
            "UPDATE driver_auth_tokens SET last_used_at=NOW() WHERE token=%s",
            (token,),
        )
        conn.commit()
        logger.info("verify_driver_token: OK user_id=%s", user_id)
        return user_id
    except Exception as e:
        logger.error("verify_driver_token 실패: %s", e)
        return None
    finally:
        conn.close()


def revoke_driver_token(token: str, reason: str = "logout") -> bool:
    """단일 토큰 무효화 (revoked=1). 반환값: 성공 여부.
    토큰 값 로그 금지.
    """
    if not token:
        return False
    conn = get_db()
    try:
        conn.execute(
            "UPDATE driver_auth_tokens"
            " SET revoked=1, revoked_at=NOW(), revoked_reason=%s"
            " WHERE token=%s AND revoked=0",
            (reason[:50], token),
        )
        conn.commit()
        logger.info("revoke_driver_token: reason=%s", reason)
        return True
    except Exception as e:
        logger.error("revoke_driver_token 실패: %s", e)
        return False
    finally:
        conn.close()


def revoke_user_all_tokens(user_id: str, reason: str = "admin_revoke") -> int:
    """해당 user_id의 모든 활성 토큰 무효화.
    reason='admin_revoke'    → revoked=2
    reason='password_change' → revoked=3
    반환값: 무효화된 토큰 개수.
    """
    revoked_code = 3 if reason == "password_change" else 2
    conn = get_db()
    try:
        conn.execute(
            "UPDATE driver_auth_tokens"
            " SET revoked=%s, revoked_at=NOW(), revoked_reason=%s"
            " WHERE user_id=%s AND revoked=0",
            (revoked_code, reason[:50], user_id),
        )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM driver_auth_tokens"
            " WHERE user_id=%s AND revoked=%s AND revoked_at >= NOW() - INTERVAL '5 seconds'",
            (user_id, revoked_code),
        ).fetchone()
        cnt = count["cnt"] if count else 0
        logger.info("revoke_user_all_tokens: user_id=%s reason=%s count=%s", user_id, reason, cnt)
        return cnt
    except Exception as e:
        logger.error("revoke_user_all_tokens 실패: user_id=%s err=%s", user_id, e)
        return 0
    finally:
        conn.close()


def cleanup_expired_tokens() -> int:
    """expires_at < NOW() - INTERVAL '30 days' 인 토큰 DELETE.
    반환값: 삭제 개수.
    """
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM driver_auth_tokens"
            " WHERE expires_at < NOW() - INTERVAL '30 days'"
        )
        conn.commit()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM driver_auth_tokens"
            " WHERE expires_at < NOW() - INTERVAL '30 days'"
        ).fetchone()
        # 실제 삭제 수는 rowcount로 확인 불가(PgWrapper 제한) → 0 반환 후 로그만
        logger.info("cleanup_expired_tokens: completed")
        return 0
    except Exception as e:
        logger.error("cleanup_expired_tokens 실패: %s", e)
        return 0
    finally:
        conn.close()


def ensure_academic_schedule_table() -> None:
    """school_academic_schedule 테이블 + 인덱스 생성 (idempotent).
    PostgreSQL은 AUTOINCREMENT 미지원 → SERIAL PRIMARY KEY 사용.
    """
    _auto = "SERIAL PRIMARY KEY"
    conn = get_db()
    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS school_academic_schedule (
                id          {_auto},
                school_name TEXT NOT NULL,
                sched_date  TEXT NOT NULL,
                event_name  TEXT,
                event_type  TEXT,
                content     TEXT,
                last_synced TEXT,
                UNIQUE(school_name, sched_date, event_name)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sas_school_date
                ON school_academic_schedule(school_name, sched_date)
        """)
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] ensure_academic_schedule_table: {e}")
        logger.warning(f"ensure_academic_schedule_table 실패: {e}")
    finally:
        conn.close()


def ensure_users_neis_columns() -> None:
    """users 테이블에 NEIS 가입 임시보관 컬럼 4개 추가 (idempotent)."""
    conn = get_db()
    for col_def in [
        "neis_edu_pending TEXT",
        "neis_school_pending TEXT",
        "pending_vendor TEXT",
        "pending_school_name TEXT",
    ]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass  # 이미 존재하면 무시
    conn.close()


try:
    ensure_academic_schedule_table()
except Exception as _sched_init_err:
    print(f"[DB ERROR] school_academic_schedule 초기화 실패: {_sched_init_err}")

try:
    ensure_users_neis_columns()
except Exception as _neis_col_err:
    print(f"[DB ERROR] users NEIS 컬럼 초기화 실패: {_neis_col_err}")


def save_collection(
    vendor: str, driver: str, school_name: str,
    collect_date: str, item_type: str, weight: float,
    status: str = "submitted",
    unit_price: float = 0, memo: str = "", collect_time: str = "",
    lat: float = None, lng: float = None,
) -> bool:
    """수거 데이터 저장 (status: draft / submitted). lat/lng 는 GPS 좌표 (없으면 None)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "vendor": vendor,
        "driver": driver,
        "school_name": school_name,
        "collect_date": collect_date,
        "item_type": item_type,
        "weight": weight,
        "unit_price": unit_price,
        "amount": round(weight * unit_price, 0),
        "collect_time": collect_time,
        "memo": memo,
        "status": status,
        "submitted_at": now if status == "submitted" else "",
        "created_at": now,
        "lat": lat,
        "lng": lng,
    }
    return db_insert("real_collection", data)


def delete_collection(rowid: int) -> bool:
    """수거 기록 삭제 (id 기반, 인자명은 호환성 위해 유지)"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM real_collection WHERE id = ?", (rowid,))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_collection: {e}")
        logger.warning(f"수거 삭제 실패: {e}")
        return False
    finally:
        conn.close()


def update_collection_row(
    row_id: int, weight: float, unit_price: float,
    item_type: str = "", memo: str = "",
) -> bool:
    """수거 기록 수정 (P1 복원 — HQ 편집용).

    weight/unit_price 변경 시 amount 자동 재계산.
    item_type/memo 는 빈 문자열이면 미변경.
    """
    conn = get_db()
    try:
        cur_row = conn.execute(
            "SELECT item_type, memo FROM real_collection WHERE id=?", (row_id,),
        ).fetchone()
        if not cur_row:
            return False
        cur_d = dict(cur_row)
        new_item = item_type if item_type else cur_d.get("item_type", "")
        new_memo = memo if memo else cur_d.get("memo", "")
        new_amount = round(float(weight or 0) * float(unit_price or 0), 0)
        conn.execute(
            "UPDATE real_collection SET weight=?, unit_price=?, amount=?, "
            "item_type=?, memo=? WHERE id=?",
            (float(weight or 0), float(unit_price or 0), new_amount,
             new_item, new_memo, row_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] update_collection_row: {e}")
        logger.warning(f"수거 수정 실패: {e}")
        return False
    finally:
        conn.close()


def bulk_insert_collections(rows: list[dict], uploader: str = "admin") -> tuple[int, int]:
    """CSV/Excel 업로드로 real_collection 일괄 등록 (P1 복원).

    각 row 는 다음 키 사용 (한글/영문 둘 다 지원하지 않으므로 매핑 후 호출):
        vendor, school_name, collect_date, item_type, weight, unit_price, driver, memo

    중복 체크: 동일 (vendor, school_name, collect_date, item_type, driver) 가
    이미 존재하면 건너뜀 → 'skipped' 카운트 (실패 카운트 별도).
    Returns: (등록건수, 실패+중복건수)
    """
    from datetime import datetime as _dt
    if not rows:
        return 0, 0
    conn = get_db()
    success = 0
    fail = 0
    try:
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        for r in rows:
            try:
                vendor = str(r.get("vendor", "") or "").strip()
                school = str(r.get("school_name", "") or "").strip()
                cdate  = str(r.get("collect_date", "") or "").strip()[:10]
                item   = str(r.get("item_type", "음식물") or "음식물").strip()
                drv    = str(r.get("driver", "") or "").strip()
                memo   = str(r.get("memo", "") or "").strip()
                try:
                    w = float(r.get("weight", 0) or 0)
                except (ValueError, TypeError):
                    w = 0.0
                try:
                    up = float(r.get("unit_price", 0) or 0)
                except (ValueError, TypeError):
                    up = 0.0

                if not vendor or not school or not cdate:
                    fail += 1
                    continue

                # 중복 체크
                dup = conn.execute(
                    "SELECT id FROM real_collection WHERE vendor=? AND school_name=? "
                    "AND collect_date=? AND item_type=? AND driver=? LIMIT 1",
                    (vendor, school, cdate, item, drv),
                ).fetchone()
                if dup:
                    fail += 1
                    continue

                conn.execute(
                    "INSERT INTO real_collection "
                    "(vendor, school_name, collect_date, item_type, weight, "
                    "unit_price, amount, driver, memo, status, submitted_at, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        vendor, school, cdate, item, w, up,
                        round(w * up, 0), drv, memo, "confirmed",
                        now, now,
                    ),
                )
                success += 1
            except Exception as e:
                print(f"[DB ERROR] bulk_insert_collections: {e}")
                logger.warning(f"bulk_insert_collections row 실패: {e}")
                fail += 1
        conn.commit()
    finally:
        conn.close()
    return success, fail


def get_driver_checkout_log(vendor: str, driver: str, checkout_date: str) -> list[dict]:
    """퇴근 기록 조회"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM driver_checkout WHERE vendor=? AND driver=? AND checkout_date=?",
            (vendor, driver, checkout_date),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_driver_checkout_log: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def save_driver_checkout(vendor: str, driver: str, checkout_date: str) -> bool:
    """퇴근 기록 저장"""
    return db_insert("driver_checkout", {
        "vendor": vendor,
        "driver": driver,
        "checkout_date": checkout_date,
        "checkout_time": datetime.now().strftime("%H:%M:%S"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


# ── 계근표(처리확인) ──

def get_today_processing(vendor: str, driver: str, confirm_date: str) -> list[dict]:
    """오늘 처리확인 기록 조회"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, * FROM processing_confirm "
            "WHERE vendor=? AND driver=? AND confirm_date=? "
            "ORDER BY created_at DESC",
            (vendor, driver, confirm_date),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_today_processing: {e}")
        logger.warning(f"get_today_processing error: {e}")
        return []
    finally:
        conn.close()


def save_processing_confirm(
    vendor: str, driver: str,
    total_weight: float, location_name: str, memo: str = "",
    first_weigh_time: str = "",
    second_weigh_time: str = "",
    gross_weight: float = 0.0,
    net_weight: float = 0.0,
    vehicle_number: str = "",
    processor_company: str = "",
    weighslip_photo_path: str = "",
) -> bool:
    """계근표 처리확인 저장 (OCR 필드 포함)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return db_insert("processing_confirm", {
        "vendor": vendor,
        "driver": driver,
        "confirm_date": datetime.now().strftime("%Y-%m-%d"),
        "confirm_time": datetime.now().strftime("%H:%M:%S"),
        "total_weight": total_weight,
        "location_name": location_name,
        "memo": memo,
        "status": "submitted",
        "created_at": now,
        "first_weigh_time": first_weigh_time,
        "second_weigh_time": second_weigh_time,
        "gross_weight": gross_weight,
        "net_weight": net_weight,
        "vehicle_number": vehicle_number,
        "processor_company": processor_company,
        "weighslip_photo_path": weighslip_photo_path,
    })


# ── GPS 위치 저장 ──

def save_customer_gps(vendor: str, name: str, lat: float, lng: float) -> bool:
    """거래처 GPS 좌표 저장 (UPDATE).
    customer_info 행이 존재하면 latitude/longitude 갱신 후 True 반환.
    행이 없으면 False 반환 (부분 데이터 INSERT 금지 — 가격/연락처 등 누락 방지).
    """
    conn = get_db()
    try:
        # 행 존재 확인 (PgWrapper는 rowcount 미노출 → SELECT COUNT 선행)
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM customer_info WHERE vendor=? AND name=?",
            (vendor, name),
        ).fetchone()
        cnt = int((row or {}).get("cnt", 0)) if isinstance(row, dict) else int(row[0] if row else 0)
        if cnt == 0:
            logger.warning(f"[save_customer_gps] 거래처 없음 — vendor={vendor}, name={name}")
            return False
        conn.execute(
            "UPDATE customer_info SET latitude=?, longitude=? WHERE vendor=? AND name=?",
            (lat, lng, vendor, name),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"save_customer_gps error: {type(e).__name__}: {e}")
        return False
    finally:
        conn.close()


# ── GPS 유틸 ──

def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 거리 계산 (미터) — Haversine 공식, 외부 라이브러리 없음"""
    R = 6_371_000  # 지구 반경 (m)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_customers_with_gps(vendor: str) -> list[dict]:
    """GPS 좌표(latitude/longitude)가 등록된 거래처 목록 반환"""
    conn = get_db()
    try:
        # idempotent: 컬럼이 없으면 추가
        for col in ("latitude", "longitude"):
            try:
                conn.execute(f"ALTER TABLE customer_info ADD COLUMN {col} REAL")
                conn.commit()
            except Exception:
                pass  # 이미 존재하면 무시
        rows = conn.execute(
            "SELECT name, latitude, longitude FROM customer_info "
            "WHERE vendor=? AND latitude IS NOT NULL AND longitude IS NOT NULL "
            "AND latitude != 0 AND longitude != 0",
            (vendor,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                result.append({
                    "name": str(d.get("name", "")),
                    "lat": float(d.get("latitude", 0)),
                    "lng": float(d.get("longitude", 0)),
                })
            except (ValueError, TypeError):
                pass
        return result
    except Exception as e:
        print(f"[DB ERROR] get_customers_with_gps: {e}")
        logger.warning(f"get_customers_with_gps error: {e}")
        return []
    finally:
        conn.close()


def get_school_icons(vendor: str) -> dict:
    """거래처명 → 아이콘 매핑 반환 (cust_type 기반)"""
    rows = db_get("customer_info", {"vendor": vendor})
    icon_map = {"학교": "🏫", "기업": "🏢", "관공서": "🏛️", "일반업장": "🍽️"}
    result = {}
    for r in rows:
        name = r.get("name", "")
        if not name:
            continue
        ct = str(r.get("cust_type", r.get("구분", "학교")) or "학교")
        result[name] = icon_map.get(ct, "🏫")
    return result


# ── 사진 기록 ──

def save_photo_record(
    vendor: str, driver: str, school_name: str,
    photo_type: str, photo_url: str, collect_date: str,
    memo: str = "",
) -> bool:
    """사진 메타데이터를 photo_records 테이블에 저장"""
    return db_insert("photo_records", {
        "vendor": vendor,
        "driver": driver,
        "school_name": school_name,
        "photo_type": photo_type,
        "photo_url": photo_url,
        "collect_date": collect_date,
        "memo": memo,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


def get_photo_records_today(
    vendor: str, driver: str, collect_date: str
) -> list[dict]:
    """오늘 사진 기록 조회"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM photo_records "
            "WHERE vendor=? AND driver=? AND collect_date=? "
            "ORDER BY created_at DESC",
            (vendor, driver, collect_date),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_photo_records_today: {e}")
        logger.warning(f"get_photo_records_today error: {e}")
        return []
    finally:
        conn.close()


def get_photo_records_all(
    vendor: str = "",
    photo_type: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 200,
) -> list[dict]:
    """본사관리자용 현장사진 조회 (필터 + LIMIT)"""
    conn = get_db()
    try:
        sql = "SELECT * FROM photo_records WHERE 1=1"
        params: list = []
        if vendor:
            sql += " AND vendor=?"
            params.append(vendor)
        if photo_type:
            sql += " AND photo_type=?"
            params.append(photo_type)
        if date_from:
            sql += " AND collect_date>=?"
            params.append(date_from)
        if date_to:
            sql += " AND collect_date<=?"
            params.append(date_to)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(int(limit))
        rows = conn.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_photo_records_all: {e}")
        logger.warning(f"get_photo_records_all error: {e}")
        return []
    finally:
        conn.close()


# ── 업체관리자 대시보드 관련 ──

def get_monthly_collections(vendor: str, year: int, month: int) -> list[dict]:
    """월별 수거 데이터 조회 (vendor + YYYY-MM 필터)"""
    month_str = f"{year}-{str(month).zfill(2)}"
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM real_collection "
            "WHERE vendor=? AND collect_date LIKE ? ORDER BY collect_date",
            (vendor, f"{month_str}%"),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_monthly_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_collection_summary_by_school(vendor: str, year: int, month: int) -> list[dict]:
    """학교별 수거량 집계 — total_weight(kg) + collect_count(건수)"""
    month_str = f"{year}-{str(month).zfill(2)}"
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT school_name, "
            "ROUND(SUM(weight), 1) AS total_weight, "
            "COUNT(*) AS collect_count "
            "FROM real_collection "
            "WHERE vendor=? AND collect_date LIKE ? "
            "GROUP BY school_name "
            "ORDER BY total_weight DESC",
            (vendor, f"{month_str}%"),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_collection_summary_by_school: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_vendor_schools(vendor: str) -> list[dict]:
    """업체에 배정된 학교 목록 (customer_info 테이블)"""
    rows = db_get("customer_info", {"vendor": vendor})
    return [
        {"name": r.get("name", ""), "school_type": r.get("type", "")}
        for r in rows
        if r.get("name")
    ]


def get_customers_by_vendor(vendor: str, cust_type: str = None) -> list[dict]:
    """거래처 전체 정보 조회 — 폼 편집용 전 컬럼 포함"""
    conn = get_db()
    try:
        if cust_type:
            rows = conn.execute(
                "SELECT * FROM customer_info WHERE vendor=? AND cust_type=? ORDER BY name",
                (vendor, cust_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM customer_info WHERE vendor=? ORDER BY name",
                (vendor,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if not d.get("name"):
                continue
            pf = d.get("price_food", 0) or 0
            pr = d.get("price_recycle", 0) or 0
            pg = d.get("price_general", 0) or 0
            ff = d.get("fixed_monthly_fee", 0) or 0
            # ── 운영 DB는 영문 컬럼만 존재 (사례 5 후속 정정) ──
            result.append({
                "name":          str(d.get("name", "")),
                "cust_type":     str(d.get("cust_type", "학교") or "학교"),
                "biz_no":        str(d.get("biz_no", "") or ""),
                "ceo":           str(d.get("rep", "") or ""),       # UI: ceo ← DB: rep
                "address":       str(d.get("addr", "") or ""),      # UI: address ← DB: addr
                "biz_type":      str(d.get("biz_type", "") or ""),
                "biz_item":      str(d.get("biz_item", "") or ""),
                "email":         str(d.get("email", "") or ""),
                "phone":         str(d.get("phone", "") or ""),
                "recycler":      str(d.get("recycler", "") or ""),
                "price_food":    str(int(float(pf))),
                "price_recycle": str(int(float(pr))),
                "price_general": str(int(float(pg))),
                "fixed_fee":     str(int(float(ff))),
                "neis_edu":      str(d.get("neis_edu_code", "") or ""),
                "neis_school":   str(d.get("neis_school_code", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_customers_by_vendor: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def save_customer(data: dict) -> bool:
    """거래처 저장 — name+vendor 기준 upsert (UPDATE 우선, 없으면 INSERT)"""
    conn = get_db()
    try:
        vendor = str(data.get("vendor", ""))
        name = str(data.get("name", "")).strip()
        if not name or not vendor:
            return False

        # ── 실제 customer_info 스키마와 일치하는 영문 컬럼 사용 ──
        # (사례 5 후속 정정: 운영 DB는 영문 컬럼만 존재)
        cols = {
            "name":              name,
            "vendor":            vendor,
            "cust_type":         str(data.get("cust_type", "학교")),
            "biz_no":            str(data.get("biz_no", "") or ""),
            "rep":               str(data.get("ceo", "") or ""),       # UI: ceo → DB: rep
            "addr":              str(data.get("address", "") or ""),   # UI: address → DB: addr
            "biz_type":          str(data.get("biz_type", "") or ""),
            "biz_item":          str(data.get("biz_item", "") or ""),
            "email":             str(data.get("email", "") or ""),
            "phone":             str(data.get("phone", "") or ""),
            "recycler":          str(data.get("recycler", "") or ""),
            "price_food":        float(data.get("price_food", 0) or 0),
            "price_recycle":     float(data.get("price_recycle", 0) or 0),
            "price_general":     float(data.get("price_general", 0) or 0),
            "fixed_monthly_fee": float(data.get("fixed_fee", 0) or 0),
            "neis_edu_code":     str(data.get("neis_edu", "") or ""),
            "neis_school_code":  str(data.get("neis_school", "") or ""),
        }

        exists = conn.execute(
            "SELECT 1 FROM customer_info WHERE vendor=? AND name=?",
            (vendor, name),
        ).fetchone()

        if exists:
            # UPDATE 도 INSERT 와 동일하게 컬럼명 quoting 통일 (안전)
            set_clause = ", ".join(f'"{k}"=?' for k in cols if k not in ("name", "vendor"))
            vals = [v for k, v in cols.items() if k not in ("name", "vendor")]
            vals += [vendor, name]
            conn.execute(
                f"UPDATE customer_info SET {set_clause} WHERE vendor=? AND name=?",
                vals,
            )
        else:
            col_str = ", ".join(f'"{k}"' for k in cols)
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(
                f"INSERT INTO customer_info ({col_str}) VALUES ({placeholders})",
                list(cols.values()),
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_customer: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def delete_customer(vendor: str, name: str) -> bool:
    """거래처 삭제"""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM customer_info WHERE vendor=? AND name=?",
            (vendor, name),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] delete_customer: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_customer_details(vendor: str) -> list[dict]:
    """거래처 상세 정보 — customer_info 전 컬럼, 키 정규화

    호출자(거래명세서 PDF/이메일 발송 등)가 기대하는 키:
        biz_no, representative, address, cust_type, fixed_fee
    실제 DB 컬럼은 영문(rep, addr, fixed_monthly_fee 등)만 존재.
    """
    rows = db_get("customer_info", {"vendor": vendor})
    result = []
    for r in rows:
        if not r.get("name"):
            continue
        pf = r.get("price_food", 0) or 0
        pr = r.get("price_recycle", 0) or 0
        pg = r.get("price_general", 0) or 0
        ff = r.get("fixed_monthly_fee", 0) or 0
        result.append({
            "name":           str(r.get("name", "")),
            "cust_type":      str(r.get("cust_type", "학교") or "학교"),
            "biz_no":         str(r.get("biz_no", "") or ""),
            "representative": str(r.get("rep", "") or ""),    # 거래명세서 PDF용
            "ceo":            str(r.get("rep", "") or ""),    # 일반 호출용 별칭
            "address":        str(r.get("addr", "") or ""),   # DB: addr → 키: address
            "biz_type":       str(r.get("biz_type", "") or ""),
            "biz_item":       str(r.get("biz_item", "") or ""),
            "phone":          str(r.get("phone", "") or ""),
            "email":          str(r.get("email", "") or ""),
            "recycler":       str(r.get("recycler", "") or ""),
            "price_food":     str(int(float(pf))),
            "price_recycle":  str(int(float(pr))),
            "price_general":  str(int(float(pg))),
            "fixed_fee":      str(int(float(ff))),
            "neis_edu":       str(r.get("neis_edu_code", "") or ""),
            "neis_school":    str(r.get("neis_school_code", "") or ""),
        })
    return result


def get_vendor_schedules(vendor: str) -> list[dict]:
    """수거 일정 조회 — schedules 테이블, 키 정규화"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM schedules WHERE vendor=? ORDER BY month DESC LIMIT 200",
            (vendor,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "month_key":     str(d.get("month", "")),
                "weekdays":      str(d.get("weekdays", d.get("요일", "")) or ""),
                "schools":       str(d.get("schools", d.get("학교", "")) or ""),
                "items":         str(d.get("items", d.get("품목", "")) or ""),
                "driver":        str(d.get("driver", d.get("기사", "")) or ""),
                "registered_by": str(d.get("registered_by", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_vendor_schedules: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_safety_education(vendor: str) -> list[dict]:
    """안전교육 이력 조회"""
    rows = db_get("safety_education", {"vendor": vendor})
    result = []
    for r in rows:
        result.append({
            "edu_date":   str(r.get("edu_date", "") or ""),
            "driver":     str(r.get("driver", "") or ""),
            "edu_type":   str(r.get("edu_type", "") or ""),
            "edu_hours":  str(r.get("edu_hours", "") or ""),
            "instructor": str(r.get("instructor", "") or ""),
            "result":     str(r.get("result", "") or ""),
            "memo":       str(r.get("memo", "") or ""),
        })
    return sorted(result, key=lambda x: x["edu_date"], reverse=True)


def get_safety_checklist(vendor: str) -> list[dict]:
    """차량 안전점검 이력 조회 (id·승인상태 포함)"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM safety_checklist WHERE vendor=? ORDER BY check_date DESC, id DESC",
            (vendor,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":          str(d.get("id", "") or ""),
                "check_date":  str(d.get("check_date", "") or ""),
                "driver":      str(d.get("driver", "") or ""),
                "vehicle_no":  str(d.get("vehicle_no", "") or ""),
                "total_ok":    str(d.get("total_ok", 0) or 0),
                "total_fail":  str(d.get("total_fail", 0) or 0),
                "inspector":   str(d.get("inspector", "") or ""),
                "memo":        str(d.get("memo", "") or ""),
                "status":      str(d.get("status", "pending") or "pending"),
                "approved_by": str(d.get("approved_by", "") or ""),
                "approved_at": str(d.get("approved_at", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_safety_checklist: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def update_safety_checklist_status(chk_id: str, status: str, approved_by: str) -> bool:
    """차량점검 승인/반려 상태 업데이트"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE safety_checklist SET status=?, approved_by=?, approved_at=? WHERE id=?",
            (status, approved_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(chk_id)),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] update_safety_checklist_status: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_daily_checks_by_month(vendor: str, year_month: str) -> list[dict]:
    """일일안전보건 점검 이력 — vendor + YYYY-MM 필터"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM daily_safety_check "
            "WHERE vendor=? AND check_date LIKE ? "
            "ORDER BY check_date DESC",
            (vendor, f"{year_month}%"),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "check_date":  str(d.get("check_date", "") or ""),
                "driver":      str(d.get("driver", "") or ""),
                "category":    str(d.get("category", "") or ""),
                "total_ok":    str(d.get("total_ok", 0) or 0),
                "total_fail":  str(d.get("total_fail", 0) or 0),
                "fail_memo":   str(d.get("fail_memo", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_daily_checks_by_month: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_collections_filtered(
    vendor: str, year_month: str, school: str = None
) -> list[dict]:
    """수거 기록 조회 — vendor + YYYY-MM 필터, 학교 선택적 필터"""
    conn = get_db()
    try:
        if school:
            rows = conn.execute(
                "SELECT * FROM real_collection "
                "WHERE vendor=? AND collect_date LIKE ? AND school_name=? "
                "ORDER BY collect_date DESC, created_at DESC",
                (vendor, f"{year_month}%", school),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM real_collection "
                "WHERE vendor=? AND collect_date LIKE ? "
                "ORDER BY collect_date DESC, created_at DESC",
                (vendor, f"{year_month}%"),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":           str(d.get("id", "") or ""),
                "school_name":  str(d.get("school_name", "") or ""),
                "collect_date": str(d.get("collect_date", "") or ""),
                "item_type":    str(d.get("item_type", "") or ""),
                "weight":       float(d.get("weight", 0) or 0),
                "driver":       str(d.get("driver", "") or ""),
                "memo":         str(d.get("memo", "") or ""),
                "status":       str(d.get("status", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_collections_filtered: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def upsert_collection(data: dict) -> bool:
    """수거 데이터 저장 (신규 insert — id 없을 때)"""
    payload = {
        "vendor":       str(data.get("vendor", "")),
        "school_name":  str(data.get("school_name", "")),
        "collect_date": str(data.get("collect_date", "")),
        "item_type":    str(data.get("item_type", "")),
        "weight":       float(data.get("weight", 0) or 0),
        "driver":       str(data.get("driver", "")),
        "memo":         str(data.get("memo", "")),
        "status":       str(data.get("status", "confirmed")),
        "created_at":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return db_insert("real_collection", payload)


def get_processing_confirms(vendor: str, status: str = None) -> list[dict]:
    """처리확인(계근표) 조회 — vendor 기준, status 선택적 필터"""
    conn = get_db()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM processing_confirm "
                "WHERE vendor=? AND status=? "
                "ORDER BY confirm_date DESC, confirm_time DESC",
                (vendor, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM processing_confirm "
                "WHERE vendor=? "
                "ORDER BY confirm_date DESC, confirm_time DESC",
                (vendor,),
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":            str(d.get("id", "") or ""),
                "confirm_date":  str(d.get("confirm_date", "") or ""),
                "confirm_time":  str(d.get("confirm_time", "") or "")[:5],
                "driver":        str(d.get("driver", "") or ""),
                "total_weight":  float(d.get("total_weight", 0) or 0),
                "location_name": str(d.get("location_name", "") or ""),
                "status":        str(d.get("status", "") or ""),
                "memo":          str(d.get("memo", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_processing_confirms: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def update_processing_confirm_status(
    record_id: str, status: str, confirmed_by: str
) -> bool:
    """처리확인 상태 업데이트 (confirmed / rejected)"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE processing_confirm "
            "SET status=?, confirmed_by=?, confirmed_at=? WHERE id=?",
            (status, confirmed_by,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id),
        )
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        print(f"[DB ERROR] update_processing_confirm_status: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def update_user_password(user_id: str, new_pw_hash: str) -> bool:
    """비밀번호 해시 업데이트"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET pw_hash=? WHERE user_id=?",
            (new_pw_hash, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] update_user_password: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_schedules(vendor: str, month: str = None) -> list[dict]:
    """일정 조회 — id 포함, month 선택 필터 (YYYY-MM 또는 YYYY-MM-DD)"""
    conn = get_db()
    try:
        if month:
            rows = conn.execute(
                "SELECT * FROM schedules WHERE vendor=? AND month LIKE ? "
                "ORDER BY month DESC",
                (vendor, f"{month}%"),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM schedules WHERE vendor=? "
                "ORDER BY month DESC LIMIT 500",
                (vendor,),
            ).fetchall()

        def _parse(raw) -> str:
            if not raw:
                return ""
            s = str(raw)
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return ", ".join(str(x) for x in parsed)
                return str(parsed)
            except Exception as e:
                print(f"[DB ERROR] get_schedules: {e}")
                logger.warning(f'Exception in database operation: {str(e)}')
                return s

        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":            str(d.get("id", "") or ""),
                "month_key":     str(d.get("month", "") or ""),
                "weekdays":      _parse(d.get("weekdays", d.get("요일", ""))),
                "schools":       _parse(d.get("schools", d.get("학교", ""))),
                "items":         _parse(d.get("items", d.get("품목", ""))),
                "driver":        str(d.get("driver", d.get("기사", "")) or ""),
                "registered_by": str(d.get("registered_by", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_schedules: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_driver_schedule_schools(
    vendor: str, driver: str, sel_date: str
) -> list[dict]:
    """기사 수거일정: 선택 날짜에 배정된 학교 목록 반환.

    schedules 테이블(요일 기반) + meal_schedules 테이블(급식일정 필터)을
    조합하여, 해당 날짜에 실제 수거해야 할 학교 리스트를 돌려준다.

    Returns:
        [{"school_name": "...", "items": "음식물, 재활용", "vendor": "..."}]
    """
    import json as _json
    from datetime import date as _date

    conn = get_db()
    try:
        # ── 선택일 파싱 ──
        try:
            d = _date.fromisoformat(sel_date)
        except (ValueError, TypeError):
            return []
        weekday_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
        sel_wd = weekday_map[d.weekday()]
        sel_month = sel_date[:7]  # YYYY-MM

        # ── schedules 조회 (해당 월) ──
        rows = conn.execute(
            "SELECT * FROM schedules WHERE vendor=? AND month LIKE ?",
            (vendor, f"{sel_month}%"),
        ).fetchall()

        # ── meal_schedules 조회 (해당 월, 급식일정 필터용) ──
        # 이 쿼리가 실패해도 schedules 테이블 기반 결과는 정상 반환 (fallback)
        meal_managed: set = set()
        meal_approved_dates: dict[str, set] = {}
        try:
            ms_rows = conn.execute(
                "SELECT school_name, collect_date, status FROM meal_schedules "
                "WHERE school_name IN "
                "(SELECT name FROM customer_info WHERE vendor=?) "
                "AND meal_date LIKE ?",
                (vendor, f"{sel_month}%"),
            ).fetchall()
            for ms in ms_rows:
                ms_d = dict(ms)
                sn = ms_d.get("school_name", "")
                if sn:
                    meal_managed.add(sn)
                    if ms_d.get("status") == "approved":
                        cd = str(ms_d.get("collect_date", ""))
                        if cd:
                            meal_approved_dates.setdefault(sn, set()).add(cd)
        except Exception as me:
            print(f"[DB ERROR] get_driver_schedule_schools meal_schedules: {me}")
            logger.warning(f"meal_schedules 조회 실패 (fallback 적용): {me}")
            meal_managed = set()
            meal_approved_dates = {}

        # ── 거래처 정보 조회 (주소 + 유형) ──
        addr_rows = conn.execute(
            "SELECT name, addr, cust_type FROM customer_info WHERE vendor=?",
            (vendor,),
        ).fetchall()
        addr_map = {}
        type_map = {}
        for ar in addr_rows:
            ard = dict(ar)
            nm = ard.get("name", "")
            addr_map[nm] = str(ard.get("addr", ard.get("address", ard.get("\uc8fc\uc18c", ""))) or "")
            ct = str(ard.get("cust_type", ard.get("\uad6c\ubd84", "")) or "")
            type_map[nm] = ct

        # ── 학교 필터링 ──
        result: list[dict] = []
        seen: set[str] = set()

        for r in rows:
            rd = dict(r)
            # 기사 매칭
            rd_driver = str(rd.get("driver", "")).strip()
            if rd_driver and rd_driver != driver:
                continue
            # 요일 매칭
            try:
                wds = _json.loads(rd["weekdays"]) if isinstance(rd.get("weekdays"), str) else (rd.get("weekdays") or [])
            except Exception as e:
                print(f"[DB ERROR] get_driver_schedule_schools: {e}")
                wds = []
            if sel_wd not in wds:
                continue
            # 학교 파싱
            try:
                schools = _json.loads(rd["schools"]) if isinstance(rd.get("schools"), str) else (rd.get("schools") or [])
            except Exception as e:
                print(f"[DB ERROR] get_driver_schedule_schools: {e}")
                schools = []
            # 품목 파싱
            try:
                items = _json.loads(rd["items"]) if isinstance(rd.get("items"), str) else (rd.get("items") or [])
            except Exception as e:
                print(f"[DB ERROR] get_driver_schedule_schools: {e}")
                items = []

            for sch in schools:
                if sch in seen:
                    continue
                # 식단기반 필터
                if sch in meal_managed:
                    approved = meal_approved_dates.get(sch, set())
                    if sel_date not in approved:
                        continue
                seen.add(sch)
                ct = type_map.get(sch, "")
                # 아이콘 매핑
                icon_map = {"학교": "🏫", "기업": "🏢", "관공서": "🏛️", "일반업장": "🍽️"}
                icon = icon_map.get(ct, "🏫")
                result.append({
                    "school_name": sch,
                    "items": ", ".join(items) if items else "-",
                    "vendor": rd.get("vendor", ""),
                    "address": addr_map.get(sch, ""),
                    "cust_type": ct,
                    "icon": icon,
                })

        return result
    except Exception as e:
        print(f"[DB ERROR] get_driver_schedule_schools: {e}")
        logger.warning(f"get_driver_schedule_schools error: {e}")
        return []
    finally:
        conn.close()


def save_schedule(data: dict) -> bool:
    """일정 저장 — schedules 테이블 INSERT"""
    conn = get_db()
    try:
        vendor = str(data.get("vendor", ""))
        month = str(data.get("month", ""))
        if not vendor or not month:
            return False
        weekdays = data.get("weekdays", [])
        schools = data.get("schools", [])
        items = data.get("items", [])
        if isinstance(weekdays, list):
            weekdays = json.dumps(weekdays, ensure_ascii=False)
        if isinstance(schools, list):
            schools = json.dumps(schools, ensure_ascii=False)
        if isinstance(items, list):
            items = json.dumps(items, ensure_ascii=False)
        conn.execute(
            "INSERT INTO schedules "
            "(vendor, month, weekdays, schools, items, driver, registered_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (vendor, month, weekdays, schools, items,
             str(data.get("driver", "") or ""), "vendor"),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_schedule: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def delete_schedule(schedule_id: str) -> bool:
    """일정 삭제 — id 기준"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        print(f"[DB ERROR] delete_schedule: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_drivers_by_vendor(vendor: str) -> list[str]:
    """vendor 소속 기사 이름 목록"""
    rows = db_get("users", {"vendor": vendor})
    names = []
    for r in rows:
        if r.get("role") == "driver":
            name = r.get("name") or r.get("user_id", "")
            if name:
                names.append(str(name))
    return names


def get_settlement_summary(vendor: str, year: int, month: int) -> list[dict]:
    """거래처별 수거량·금액 집계 — 구분별 단가 로직 적용"""
    conn = get_db()
    try:
        month_str = str(month).zfill(2)
        ym = f"{year}-{month_str}"

        coll_rows = conn.execute(
            "SELECT school_name, item_type, weight FROM real_collection "
            "WHERE vendor=? AND collect_date LIKE ?",
            (vendor, f"{ym}%"),
        ).fetchall()

        cust_rows = conn.execute(
            "SELECT * FROM customer_info WHERE vendor=?",
            (vendor,),
        ).fetchall()

        cust_map = {}
        for r in cust_rows:
            d = dict(r)
            name = str(d.get("name", "") or "")
            if not name:
                continue
            ct = str(d.get("구분", d.get("cust_type", "학교")) or "학교")
            cust_map[name] = {
                "cust_type":         ct,
                "price_food":        float(d.get("price_food", 0) or 0),
                "price_recycle":     float(d.get("price_recycle", 0) or 0),
                "price_general":     float(d.get("price_general", 0) or 0),
                "fixed_monthly_fee": float(d.get("fixed_monthly_fee", 0) or 0),
            }

        agg = {}
        for r in coll_rows:
            d = dict(r)
            sn = str(d.get("school_name", "") or "")
            it = str(d.get("item_type", "") or "")
            w = float(d.get("weight", 0) or 0)
            if sn not in agg:
                agg[sn] = {"total_weight": 0.0, "count": 0, "by_item": {}}
            agg[sn]["total_weight"] += w
            agg[sn]["count"] += 1
            agg[sn]["by_item"][it] = agg[sn]["by_item"].get(it, 0.0) + w

        price_key_map = {
            "음식물": "price_food",
            "재활용": "price_recycle",
            "일반":   "price_general",
        }
        tax_free_types = ("학교", "기타1(면세사업장)")
        fixed_fee_types = ("기타", "기타2(부가세포함)")

        result = []
        added = set()

        for name, data in sorted(agg.items()):
            cinfo = cust_map.get(name, {
                "cust_type": "학교", "price_food": 0,
                "price_recycle": 0, "price_general": 0, "fixed_monthly_fee": 0,
            })
            ct = cinfo["cust_type"]
            w = data["total_weight"]
            cnt = data["count"]
            added.add(name)

            if ct in fixed_fee_types:
                ff = cinfo["fixed_monthly_fee"]
                supply = ff
                vat = round(ff * VAT_RATE) if ct == "기타2(부가세포함)" else 0.0
                total = supply + vat
            else:
                supply = 0.0
                for item_type, item_w in data["by_item"].items():
                    pk = price_key_map.get(item_type, "price_food")
                    supply += cinfo.get(pk, 0) * item_w
                supply = round(supply)
                vat = 0.0 if ct in tax_free_types else round(supply * VAT_RATE)
                total = supply + vat

            result.append({
                "name":      name,
                "cust_type": ct,
                "weight":    round(w, 1),
                "count":     cnt,
                "supply":    float(supply),
                "vat":       float(vat),
                "total":     float(total),
            })

        # 수거 실적 없는 고정비 거래처 추가
        for name, cinfo in sorted(cust_map.items()):
            if name in added:
                continue
            ct = cinfo["cust_type"]
            if ct not in fixed_fee_types:
                continue
            ff = cinfo["fixed_monthly_fee"]
            if ff <= 0:
                continue
            vat = round(ff * VAT_RATE) if ct == "기타2(부가세포함)" else 0.0
            result.append({
                "name":      name,
                "cust_type": ct,
                "weight":    0.0,
                "count":     0,
                "supply":    float(ff),
                "vat":       float(vat),
                "total":     float(ff + vat),
            })

        return sorted(result, key=lambda x: (x["cust_type"], x["name"]))
    except Exception as e:
        print(f"[DB ERROR] get_settlement_summary: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_expenses(vendor: str, year_month: str) -> list[dict]:
    """지출 내역 조회 — vendor + YYYY-MM 필터"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE vendor=? AND year_month=? "
            "ORDER BY pay_date, id",
            (vendor, year_month),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":       str(d.get("id", "") or ""),
                "item":     str(d.get("item", "") or ""),
                "amount":   float(d.get("amount", 0) or 0),
                "pay_date": str(d.get("pay_date", "") or ""),
                "memo":     str(d.get("memo", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_expenses: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def save_expense(data: dict) -> bool:
    """지출 항목 저장 — expenses 테이블 INSERT"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (vendor, year_month, item, amount, pay_date, memo) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(data.get("vendor", "")),
                str(data.get("year_month", "")),
                str(data.get("item", "")),
                float(data.get("amount", 0) or 0),
                str(data.get("pay_date", "")),
                str(data.get("memo", "")),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_expense: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def delete_expense(expense_id: str) -> bool:
    """지출 항목 삭제 — id 기준"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        print(f"[DB ERROR] delete_expense: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_vendor_info(vendor: str) -> dict:
    """업체 정보 + 직인 경로 조회.
    반환 dict keys: biz_name, rep, biz_no, address, contact,
                    stamp_path, stamp_uploaded_at, stamp_updated_by
    """
    if not vendor:
        return {}
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT biz_name, rep, biz_no, address, contact,
                   COALESCE(stamp_path, '') AS stamp_path,
                   COALESCE(stamp_uploaded_at, '') AS stamp_uploaded_at,
                   COALESCE(stamp_updated_by, '') AS stamp_updated_by
              FROM vendor_info
             WHERE vendor = ?
             LIMIT 1
            """,
            (vendor,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return {
                "biz_name": str(vendor), "rep": "", "biz_no": "",
                "address": "", "contact": "",
                "stamp_path": "", "stamp_uploaded_at": "", "stamp_updated_by": "",
            }
        return {
            "biz_name": row[0] or str(vendor),
            "rep":      row[1] or "",
            "biz_no":   row[2] or "",
            "address":  row[3] or "",
            "contact":  row[4] or "",
            "stamp_path":        row[5] or "",
            "stamp_uploaded_at": row[6] or "",
            "stamp_updated_by":  row[7] or "",
        }
    except Exception as e:
        logger.error(f"get_vendor_info 실패 ({vendor}): {e}")
        return {
            "biz_name": str(vendor), "rep": "", "biz_no": "",
            "address": "", "contact": "",
            "stamp_path": "", "stamp_uploaded_at": "", "stamp_updated_by": "",
        }


def set_vendor_stamp(vendor: str, stamp_path: str, updated_by: str) -> bool:
    """업체 직인 경로 저장.
    stamp_path: /opt/zeroda-platform/storage/stamps/ 하위 절대경로
    updated_by: 로그인 사용자명
    """
    if not vendor or not stamp_path:
        return False
    try:
        conn = get_db()
        # PostgreSQL 현재시각 표현
        _now_expr = "compat.datetime_now_localtime()"
        result = conn.execute(
            f"""
            UPDATE vendor_info
               SET stamp_path = ?,
                   stamp_uploaded_at = {_now_expr},
                   stamp_updated_by = ?
             WHERE vendor = ?
            """,
            (stamp_path, updated_by, vendor),
        )
        conn.commit()
        # PgWrapper.execute() 는 rowcount 없으므로 True로 간주
        ok = True
        conn.close()
        return ok
    except Exception as e:
        logger.error(f"set_vendor_stamp 실패 ({vendor}): {e}")
        return False


def get_biz_customers(vendor: str) -> list[str]:
    """일반업장 목록 조회 — 이름 리스트 반환"""
    rows = db_get("biz_customers", {"vendor": vendor})
    names = [str(r.get("biz_name", "") or "") for r in rows if r.get("biz_name")]
    return sorted(names)


def save_biz_customer(vendor: str, biz_name: str) -> bool:
    """일반업장 단건 등록 (중복 시 False 반환)"""
    existing = db_get("biz_customers", {"vendor": vendor, "biz_name": biz_name})
    if existing:
        return False
    return db_insert("biz_customers", {"vendor": vendor, "biz_name": biz_name})


def delete_biz_customer(vendor: str, biz_name: str) -> bool:
    """일반업장 삭제"""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM biz_customers WHERE vendor=? AND biz_name=?",
            (vendor, biz_name),
        )
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        print(f"[DB ERROR] delete_biz_customer: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def save_vendor_info(data: dict) -> bool:
    """업체 기본 정보 저장 (vendor_info upsert)"""
    ok = db_upsert(
        "vendor_info",
        {
            "vendor":   str(data.get("vendor", "")),
            "biz_name": str(data.get("biz_name", "")),
            "rep":      str(data.get("rep", "")),
            "biz_no":   str(data.get("biz_no", "")),
            "address":  str(data.get("address", "")),
            "contact":  str(data.get("contact", "")),
        },
        key_col="vendor",
    )
    if not ok:
        return False
    # 추가 필드 (컬럼 없으면 무시 — 빈 값도 저장하여 지우기 가능)
    conn = get_db()
    try:
        for col in ("email", "account"):
            _check_column(col)  # SQL 인젝션 방어
            val = str(data.get(col, "") or "")
            try:
                conn.execute(
                    f"UPDATE vendor_info SET {col}=? WHERE vendor=?",
                    (val, str(data.get("vendor", ""))),
                )
            except Exception as col_e:
                # 컬럼이 없는 구버전 DB는 조용히 무시
                logger.debug(f"save_vendor_info: 컬럼 {col} 미존재 — 무시: {col_e}")
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] save_vendor_info: {e}")
        logger.warning(f'Exception caught: {str(e)}')
    finally:
        conn.close()
    return True


def save_safety_education(data: dict) -> bool:
    """안전교육 이력 저장"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO safety_education "
            "(vendor, driver, edu_date, edu_type, edu_hours, instructor, result, memo, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(data.get("vendor", "")),
                str(data.get("driver", "")),
                str(data.get("edu_date", "")),
                str(data.get("edu_type", "정기교육")),
                int(data.get("edu_hours", 2) or 2),
                str(data.get("instructor", "")),
                str(data.get("result", "이수")),
                str(data.get("memo", "")),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_safety_education: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def save_safety_checklist(data: dict) -> bool:
    """차량 안전점검 결과 저장"""
    import json as _json
    conn = get_db()
    try:
        check_items = data.get("check_items", {})
        if not isinstance(check_items, str):
            check_items = _json.dumps(check_items, ensure_ascii=False)
        conn.execute(
            "INSERT INTO safety_checklist "
            "(vendor, driver, check_date, vehicle_no, check_items, "
            "total_ok, total_fail, inspector, memo, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(data.get("vendor", "")),
                str(data.get("driver", "")),
                str(data.get("check_date", "")),
                str(data.get("vehicle_no", "")),
                check_items,
                int(data.get("total_ok", 0) or 0),
                int(data.get("total_fail", 0) or 0),
                str(data.get("inspector", "")),
                str(data.get("memo", "")),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_safety_checklist: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_accident_reports(vendor: str) -> list[dict]:
    """사고 신고 이력 조회"""
    rows = db_get("accident_report", {"vendor": vendor})
    result = []
    for r in rows:
        result.append({
            "id":             str(r.get("id", "") or ""),
            "occur_date":     str(r.get("occur_date", "") or ""),
            "driver":         str(r.get("driver", "") or ""),
            "accident_type":  str(r.get("accident_type", "") or ""),
            "severity":       str(r.get("severity", "") or ""),
            "occur_location": str(r.get("occur_location", "") or ""),
            "status":         str(r.get("status", "신고완료") or "신고완료"),
            "description":    str(r.get("description", "") or ""),
        })
    return sorted(result, key=lambda x: x["occur_date"], reverse=True)


def save_accident_report(data: dict) -> bool:
    """사고 신고 저장"""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO accident_report "
            "(vendor, driver, occur_date, occur_location, accident_type, "
            "severity, description, action_taken, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(data.get("vendor", "")),
                str(data.get("driver", "")),
                str(data.get("occur_date", "")),
                str(data.get("occur_location", "")),
                str(data.get("accident_type", "교통사고")),
                str(data.get("severity", "재산피해")),
                str(data.get("description", "")),
                str(data.get("action_taken", "")),
                "신고완료",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_accident_report: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_daily_check_summary(vendor: str, year_month: str, category: str = None) -> dict:
    """일일안전보건 점검 요약 (기사별 집계 포함)"""
    conn = get_db()
    try:
        if category and category != "전체":
            rows = conn.execute(
                "SELECT * FROM daily_safety_check "
                "WHERE vendor=? AND check_date LIKE ? AND category=? "
                "ORDER BY check_date DESC",
                (vendor, f"{year_month}%", category),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM daily_safety_check "
                "WHERE vendor=? AND check_date LIKE ? "
                "ORDER BY check_date DESC",
                (vendor, f"{year_month}%"),
            ).fetchall()
        items = []
        total_ok = 0
        total_fail = 0
        for r in rows:
            d = dict(r)
            ok = int(d.get("total_ok", 0) or 0)
            fail = int(d.get("total_fail", 0) or 0)
            total_ok += ok
            total_fail += fail
            items.append({
                "id":         str(d.get("id", "") or ""),
                "check_date": str(d.get("check_date", "") or ""),
                "driver":     str(d.get("driver", "") or ""),
                "category":   str(d.get("category", "") or ""),
                "total_ok":   str(ok),
                "total_fail": str(fail),
                "fail_memo":  str(d.get("fail_memo", "") or ""),
                "status":     str(d.get("status", "pending") or "pending"),
            })
        all_count = total_ok + total_fail
        rate = round(total_ok / all_count * 100, 1) if all_count > 0 else 0.0
        return {
            "items":      items,
            "total_ok":   total_ok,
            "total_fail": total_fail,
            "count":      len(items),
            "rate_str":   f"{rate:.1f}",
        }
    except Exception as e:
        print(f"[DB ERROR] get_daily_check_summary: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {"items": [], "total_ok": 0, "total_fail": 0, "count": 0, "rate_str": "0.0"}
    finally:
        conn.close()


def approve_all_daily_checks_by_vendor(vendor: str, year_month: str, approved_by: str) -> int:
    """해당 월 일일점검 전체 승인 — 승인 건수 반환"""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE daily_safety_check SET status='approved', approved_by=?, approved_at=? "
            "WHERE vendor=? AND check_date LIKE ? AND (status IS NULL OR status='pending')",
            (approved_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), vendor, f"{year_month}%"),
        )
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print(f"[DB ERROR] approve_all_daily_checks_by_vendor: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return 0
    finally:
        conn.close()


# ══════════════════════════════════════════
#  본사관리자(HQ Admin) 전용 함수
# ══════════════════════════════════════════

def get_all_collections(year_month: str = "") -> list[dict]:
    """전체 수거 데이터 (업체 무관). year_month: 'YYYY-MM' 필터"""
    conn = get_db()
    try:
        if year_month:
            rows = conn.execute(
                "SELECT * FROM real_collection WHERE collect_date LIKE ?",
                (f"{year_month}%",),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM real_collection").fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_all_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_all_vendors_list() -> list[str]:
    """전체 업체명 목록"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT vendor FROM users WHERE vendor IS NOT NULL AND vendor != ''"
        ).fetchall()
        return [r["vendor"] for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_all_vendors_list: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_all_users() -> list[dict]:
    """전체 사용자 목록"""
    return db_get("users")


def is_school_in_customer_info(vendor: str, school_name: str) -> bool:
    """가입 승인 사전 검증용 — 거래처가 등록되어 있는지 확인"""
    if not vendor or not school_name:
        return False
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM customer_info WHERE vendor=? AND name=? LIMIT 1",
            (vendor, school_name),
        ).fetchone()
        return row is not None
    except Exception as e:
        logger.warning(f"[is_school_in_customer_info] 조회 오류: {e}")
        return False
    finally:
        conn.close()


def update_user_approval(user_id: str, status: str) -> bool:
    """사용자 승인 상태 변경"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET approval_status = ? WHERE user_id = ?",
            (status, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] update_user_approval: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def update_user_active(user_id: str, is_active: int) -> bool:
    """사용자 활성/비활성"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE user_id = ?",
            (is_active, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] update_user_active: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def reset_user_password(user_id: str, new_pw: str) -> bool:
    """비밀번호 초기화 (bcrypt 해시)"""
    import bcrypt
    pw_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET pw_hash = ? WHERE user_id = ?",
            (pw_hash, user_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] reset_user_password: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def update_user_fields(user_id: str, name=None, role=None, vendor=None,
                       schools=None, edu_office=None, is_active=None,
                       new_password=None) -> tuple[bool, str]:
    """None이 아닌 필드만 동적으로 UPDATE. new_password 있으면 bcrypt 해시."""
    import bcrypt
    from datetime import datetime
    fields = []
    values = []
    if name is not None:
        fields.append("name = ?"); values.append(name)
    if role is not None:
        fields.append("role = ?"); values.append(role)
    if vendor is not None:
        fields.append("vendor = ?"); values.append(vendor)
    if schools is not None:
        fields.append("schools = ?"); values.append(schools)
    if edu_office is not None:
        fields.append("edu_office = ?"); values.append(edu_office)
    if is_active is not None:
        fields.append("is_active = ?"); values.append(int(is_active))
    if new_password is not None:
        pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        fields.append("pw_hash = ?"); values.append(pw_hash)
    if not fields:
        return False, "변경할 항목이 없습니다."
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fields.append("updated_at = ?"); values.append(now)
    values.append(user_id)
    sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?"
    conn = get_db()
    try:
        conn.execute(sql, values)
        conn.commit()
        return True, f"'{user_id}' 수정 완료"
    except Exception as e:
        print(f"[DB ERROR] update_user_fields: {e}")
        logger.warning(f"Exception in update_user_fields: {str(e)}")
        return False, f"수정 중 오류: {e}"
    finally:
        conn.close()


def delete_user(user_id: str) -> tuple[bool, str]:
    """계정 삭제. admin 마지막 계정 보호."""
    rows = db_get("users", {"role": "admin"})
    target = db_get("users", {"user_id": user_id})
    if not target:
        return False, "존재하지 않는 계정입니다."
    if target[0].get("role") == "admin" and len(rows) <= 1:
        return False, "본사관리자 계정이 1개뿐입니다. 삭제할 수 없습니다."
    ok = db_delete("users", {"user_id": user_id})
    if ok:
        return True, f"'{user_id}' 계정이 삭제되었습니다."
    return False, "삭제 중 오류가 발생했습니다."


def get_user_by_id(user_id: str) -> dict | None:
    """users 테이블에서 user_id(PK)로 단일 행 조회. 없으면 None 반환."""
    rows = db_get("users", {"user_id": user_id})
    return rows[0] if rows else None


def get_active_vendor_names() -> list[str]:
    """회원가입 드롭다운용 업체명 목록 반환.
    customer_info + users(vendor_admin) UNION — 계정 is_active 무관, 업체 존재 여부만 판단."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT vendor FROM customer_info "
            "WHERE vendor IS NOT NULL AND vendor <> '' "
            "UNION "
            "SELECT DISTINCT vendor FROM users "
            "WHERE role='vendor_admin' AND vendor IS NOT NULL AND vendor <> '' "
            "ORDER BY vendor"
        ).fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        print(f"[DB ERROR] get_active_vendor_names: {e}")
        logger.warning(f"Exception in get_active_vendor_names: {str(e)}")
        return []
    finally:
        conn.close()


def upsert_customer_neis_codes(vendor: str, school_name: str,
                               neis_edu: str, neis_school: str) -> bool:
    """customer_info의 (vendor, name) 행에 NEIS 코드 2개 UPDATE.
    해당 거래처가 존재하지 않으면 False 반환."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT 1 FROM customer_info WHERE vendor=? AND name=?",
            (vendor, school_name),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE customer_info SET neis_edu_code=?, neis_school_code=? "
            "WHERE vendor=? AND name=?",
            (neis_edu, neis_school, vendor, school_name),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] upsert_customer_neis_codes: {e}")
        logger.warning(f"Exception in upsert_customer_neis_codes: {str(e)}")
        return False
    finally:
        conn.close()


def validate_password(pw: str) -> tuple[bool, str]:
    """비밀번호 정책 검증.

    규칙: 8자 이상, 대문자·소문자·숫자·특수문자 각 1자 이상 포함.
    Returns (ok, error_message). ok=True 이면 msg="OK".
    """
    import re
    if not pw or len(pw) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."
    if not re.search(r"[A-Z]", pw):
        return False, "비밀번호에 영문 대문자가 1자 이상 포함되어야 합니다."
    if not re.search(r"[a-z]", pw):
        return False, "비밀번호에 영문 소문자가 1자 이상 포함되어야 합니다."
    if not re.search(r"[0-9]", pw):
        return False, "비밀번호에 숫자가 1자 이상 포함되어야 합니다."
    if not re.search(r"[^A-Za-z0-9]", pw):
        return False, "비밀번호에 특수문자(!@#$%^&* 등)가 1자 이상 포함되어야 합니다."
    return True, "OK"


def create_user(user_id, password, role, name, vendor="", schools="",
                edu_office="", approval_status="approved", is_active=0,
                pending_vendor=None, pending_school_name=None,
                neis_edu_pending=None, neis_school_pending=None):
    import bcrypt
    existing = db_get("users", {"user_id": user_id})
    if existing:
        return False, "이미 존재하는 아이디입니다."
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users "
            "(user_id, pw_hash, role, name, vendor, schools, edu_office, "
            " is_active, approval_status, "
            " pending_vendor, pending_school_name, "
            " neis_edu_pending, neis_school_pending) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, pw_hash, role, name, vendor, schools, edu_office,
             int(is_active), approval_status,
             pending_vendor, pending_school_name,
             neis_edu_pending, neis_school_pending),
        )
        conn.commit()
        return True, f"계정 '{user_id}' 가입 신청 완료"
    except Exception as e:
        logger.error(f"[create_user] {e}", exc_info=True)
        return False, "가입 처리 중 오류가 발생했습니다."
    finally:
        conn.close()


# ══════════════════════════════════════════
#  본사관리자 — 섹션B: 수거데이터 관리
# ══════════════════════════════════════════

def get_pending_collections() -> list[dict]:
    """기사 전송 미확인 데이터 (status='submitted')"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM real_collection WHERE status = 'submitted' "
            "ORDER BY submitted_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_pending_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def confirm_all_pending() -> int:
    """미확인 전송 데이터 전체 확인 처리. 처리 건수 반환."""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE real_collection SET status = 'confirmed' WHERE status = 'submitted'"
        )
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print(f"[DB ERROR] confirm_all_pending: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return 0
    finally:
        conn.close()


def reject_collection_by_id(row_id: int) -> bool:
    """특정 수거 데이터 반려"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE real_collection SET status = 'rejected' WHERE id = ?",
            (row_id,),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] reject_collection_by_id: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_filtered_collections(
    table: str = "real_collection",
    vendor: str = "",
    year_month: str = "",
    school: str = "",
) -> list[dict]:
    """필터링된 수거 데이터 (업체·월·학교)"""
    _check_table(table)
    conn = get_db()
    try:
        clauses = []
        params: list = []
        if vendor:
            clauses.append("vendor = ?")
            params.append(vendor)
        if year_month:
            clauses.append("collect_date LIKE ?")
            params.append(f"{year_month}%")
        if school:
            clauses.append("school_name = ?")
            params.append(school)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM {table}{where} ORDER BY collect_date DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_filtered_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_all_schools_list() -> list[str]:
    """전체 학교명 목록 (school_master + real_collection 합집합)"""
    conn = get_db()
    try:
        names: set[str] = set()
        try:
            rows = conn.execute(
                "SELECT DISTINCT school_name FROM school_master "
                "WHERE school_name IS NOT NULL AND school_name != ''"
            ).fetchall()
            names.update(r["school_name"] for r in rows)
        except Exception as e:
            print(f"[DB ERROR] get_all_schools_list: {e}")
            logger.warning(f'Exception caught: {str(e)}')
            pass
        try:
            rows = conn.execute(
                "SELECT DISTINCT school_name FROM real_collection "
                "WHERE school_name IS NOT NULL AND school_name != ''"
            ).fetchall()
            names.update(r["school_name"] for r in rows)
        except Exception as e:
            print(f"[DB ERROR] get_all_schools_list: {e}")
            logger.warning(f'Exception caught: {str(e)}')
            pass
        return sorted(names)
    except Exception as e:
        print(f"[DB ERROR] get_all_schools_list: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_hq_processing_confirms(
    vendor: str = "",
    driver: str = "",
    status: str = "",
) -> list[dict]:
    """처리확인(계근표) 데이터 조회 — 본사관리자용 (업체 무관 가능)"""
    conn = get_db()
    try:
        clauses = []
        params: list = []
        if vendor:
            clauses.append("vendor = ?")
            params.append(vendor)
        if driver:
            clauses.append("driver = ?")
            params.append(driver)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM processing_confirm{where} ORDER BY confirm_date DESC",
            params,
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_hq_processing_confirms: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def confirm_processing_item(row_id: int) -> bool:
    """처리확인 건 확인 처리"""
    conn = get_db()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE processing_confirm SET status = 'confirmed', "
            "confirmed_by = 'admin', confirmed_at = ? WHERE id = ?",
            (now, row_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] confirm_processing_item: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def reject_processing_item(row_id: int) -> bool:
    """처리확인 건 반려 처리"""
    conn = get_db()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE processing_confirm SET status = 'rejected', "
            "confirmed_by = 'admin', confirmed_at = ? WHERE id = ?",
            (now, row_id),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] reject_processing_item: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_processing_vendors() -> list[str]:
    """처리확인 데이터에 존재하는 업체 목록"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT vendor FROM processing_confirm "
            "WHERE vendor IS NOT NULL AND vendor != '' ORDER BY vendor"
        ).fetchall()
        return [r["vendor"] for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_processing_vendors: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_processing_drivers() -> list[str]:
    """처리확인 데이터에 존재하는 기사 목록"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT driver FROM processing_confirm "
            "WHERE driver IS NOT NULL AND driver != '' ORDER BY driver"
        ).fetchall()
        return [r["driver"] for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_processing_drivers: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


# ══════════════════════════════════════════
#  본사관리자 — 섹션C: 외주업체 관리
# ══════════════════════════════════════════

def get_all_vendor_info() -> list[dict]:
    """전체 업체 정보 목록 (vendor_info 테이블)"""
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM vendor_info ORDER BY vendor").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "vendor":     str(d.get("vendor", "") or ""),
                "biz_name":   str(d.get("biz_name", "") or ""),
                "rep":        str(d.get("rep", "") or ""),
                "biz_no":     str(d.get("biz_no", "") or ""),
                "address":    str(d.get("address", "") or ""),
                "contact":    str(d.get("contact", "") or ""),
                "email":      str(d.get("email", "") or ""),
                "vehicle_no": str(d.get("vehicle_no", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_all_vendor_info: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def save_hq_vendor_info(data: dict) -> bool:
    """업체 정보 등록/수정 (본사관리자용)"""
    return db_upsert("vendor_info", data, key_col="vendor")


def get_school_master_all() -> list[dict]:
    """전체 학교 마스터 목록"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM school_master ORDER BY school_name"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "school_name": str(d.get("school_name", "") or ""),
                "alias":       str(d.get("alias", "") or ""),
                "vendor":      str(d.get("vendor", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_school_master_all: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def update_school_alias(school_name: str, alias: str) -> bool:
    """학교 별칭 저장"""
    return db_upsert("school_master", {
        "school_name": school_name,
        "alias": alias,
    }, key_col="school_name")


def hq_add_violation(
    vendor: str, driver: str, violation_date: str,
    violation_type: str, location: str = "",
    fine_amount: int = 0, memo: str = "",
) -> bool:
    """스쿨존 위반 기록 등록"""
    return db_insert("school_zone_violations", {
        "vendor": vendor,
        "driver": driver,
        "violation_date": violation_date,
        "violation_type": violation_type,
        "location": location,
        "fine_amount": fine_amount,
        "memo": memo,
    })


def hq_get_violations(vendor: str = "", year_month: str = "") -> list[dict]:
    """스쿨존 위반 이력 조회"""
    conn = get_db()
    try:
        clauses = []
        params: list = []
        if vendor:
            clauses.append("vendor = ?")
            params.append(vendor)
        if year_month:
            clauses.append("violation_date LIKE ?")
            params.append(f"{year_month}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM school_zone_violations{where} ORDER BY violation_date DESC",
            params,
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":              str(d.get("id", "") or ""),
                "vendor":          str(d.get("vendor", "") or ""),
                "driver":          str(d.get("driver", "") or ""),
                "violation_date":  str(d.get("violation_date", "") or ""),
                "violation_type":  str(d.get("violation_type", "") or ""),
                "location":        str(d.get("location", "") or ""),
                "fine_amount":     str(d.get("fine_amount", 0) or 0),
                "memo":            str(d.get("memo", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] hq_get_violations: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def hq_get_safety_scores(year_month: str = "") -> list[dict]:
    """안전관리 평가 점수 조회"""
    conn = get_db()
    try:
        if year_month:
            rows = conn.execute(
                "SELECT * FROM safety_scores WHERE year_month = ? ORDER BY total_score DESC",
                (year_month,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM safety_scores ORDER BY year_month DESC, total_score DESC"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "vendor":           str(d.get("vendor", "") or ""),
                "year_month":       str(d.get("year_month", "") or ""),
                "violation_score":  str(d.get("violation_score", 0) or 0),
                "checklist_score":  str(d.get("checklist_score", 0) or 0),
                "daily_check_score": str(d.get("daily_check_score", 0) or 0),
                "education_score":  str(d.get("education_score", 0) or 0),
                "total_score":      str(d.get("total_score", 0) or 0),
                "grade":            str(d.get("grade", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] hq_get_safety_scores: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def hq_calculate_safety_score(vendor: str, year_month: str) -> dict:
    """안전관리 평가 점수 계산 및 저장"""
    conn = get_db()
    try:
        # 1. 스쿨존 위반 점수 (40점 만점 - 감점)
        violations = conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(fine_amount),0) as total_fine "
            "FROM school_zone_violations WHERE vendor=? AND violation_date LIKE ?",
            (vendor, f"{year_month}%"),
        ).fetchone()
        v_cnt = int(violations["cnt"]) if violations else 0
        violation_score = max(0, 40 - (v_cnt * 10))

        # 2. 차량점검 점수 (15점)
        try:
            checks = conn.execute(
                "SELECT * FROM safety_checklist WHERE vendor=? AND check_date LIKE ?",
                (vendor, f"{year_month}%"),
            ).fetchall()
            if checks:
                total_items = 0
                passed = 0
                for c in checks:
                    d = dict(c)
                    total_items += 1
                    if str(d.get("result", "")).lower() in ("pass", "ok", "양호", "1"):
                        passed += 1
                checklist_score = round((passed / total_items) * 15, 1) if total_items > 0 else 15.0
            else:
                checklist_score = 15.0
        except Exception as e:
            print(f"[DB ERROR] hq_calculate_safety_score: {e}")
            logger.error(f'Exception in operation: {str(e)}')
            checklist_score = 15.0

        # 3. 일일안전점검 점수 (15점)
        try:
            daily = conn.execute(
                "SELECT total_ok, total_fail FROM daily_safety_check "
                "WHERE vendor=? AND check_date LIKE ?",
                (vendor, f"{year_month}%"),
            ).fetchall()
            d_ok = sum(int(r["total_ok"] or 0) for r in daily)
            d_fail = sum(int(r["total_fail"] or 0) for r in daily)
            d_total = d_ok + d_fail
            daily_check_score = round((d_ok / d_total) * 15, 1) if d_total > 0 else 15.0
        except Exception as e:
            print(f"[DB ERROR] hq_calculate_safety_score: {e}")
            logger.error(f'Exception in operation: {str(e)}')
            daily_check_score = 15.0

        # 4. 교육이수 점수 (30점)
        try:
            edu = conn.execute(
                "SELECT COUNT(*) as cnt FROM safety_education "
                "WHERE vendor=? AND edu_date LIKE ?",
                (vendor, f"{year_month}%"),
            ).fetchall()
            edu_cnt = int(edu[0]["cnt"]) if edu else 0
            education_score = min(30.0, edu_cnt * 10.0)
        except Exception as e:
            print(f"[DB ERROR] hq_calculate_safety_score: {e}")
            logger.error(f'Exception in operation: {str(e)}')
            education_score = 0.0

        total_score = round(violation_score + checklist_score + daily_check_score + education_score)

        # 등급 산정
        if total_score >= 90:
            grade = "S"
        elif total_score >= 75:
            grade = "A"
        elif total_score >= 60:
            grade = "B"
        elif total_score >= 40:
            grade = "C"
        else:
            grade = "D"

        # DB 저장
        try:
            conn.execute(
                "INSERT INTO safety_scores (vendor, year_month, violation_score, "
                "checklist_score, daily_check_score, education_score, total_score, grade) "
                "VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(vendor, year_month) DO UPDATE SET "
                "violation_score=?, checklist_score=?, daily_check_score=?, "
                "education_score=?, total_score=?, grade=?",
                (vendor, year_month, violation_score, checklist_score,
                 daily_check_score, education_score, total_score, grade,
                 violation_score, checklist_score, daily_check_score,
                 education_score, total_score, grade),
            )
            conn.commit()
        except Exception as e:
            print(f"[DB ERROR] hq_calculate_safety_score: {e}")
            logger.warning(f'Exception caught: {str(e)}')
            pass

        return {
            "vendor": vendor,
            "year_month": year_month,
            "violation_score": violation_score,
            "checklist_score": checklist_score,
            "daily_check_score": daily_check_score,
            "education_score": education_score,
            "total_score": total_score,
            "grade": grade,
        }
    except Exception as e:
        print(f"[DB ERROR] hq_calculate_safety_score: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "vendor": vendor, "year_month": year_month,
            "violation_score": 0, "checklist_score": 0,
            "daily_check_score": 0, "education_score": 0,
            "total_score": 0, "grade": "D",
        }
    finally:
        conn.close()


# ══════════════════════════════════════════
#  본사관리자 — 섹션D: 수거일정 + NEIS
# ══════════════════════════════════════════

def get_hq_schedules(vendor: str = "", year_month: str = "") -> list[dict]:
    """본사관리자용 일정 조회 (업체 무관 가능)"""
    conn = get_db()
    try:
        clauses = []
        params: list = []
        if vendor:
            clauses.append("vendor = ?")
            params.append(vendor)
        if year_month:
            clauses.append("month LIKE ?")
            params.append(f"{year_month}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM schedules{where} ORDER BY month DESC LIMIT 500",
            params,
        ).fetchall()

        def _parse(raw) -> str:
            if not raw:
                return ""
            s = str(raw)
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return ", ".join(str(x) for x in parsed)
                return str(parsed)
            except Exception as e:
                print(f"[DB ERROR] get_hq_schedules: {e}")
                logger.warning(f'Exception in database operation: {str(e)}')
                return s

        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":        str(d.get("id", "") or ""),
                "vendor":    str(d.get("vendor", "") or ""),
                "month_key": str(d.get("month", "") or ""),
                "weekdays":  _parse(d.get("weekdays", d.get("요일", ""))),
                "schools":   _parse(d.get("schools", d.get("학교", ""))),
                "items":     _parse(d.get("items", d.get("품목", ""))),
                "driver":    str(d.get("driver", d.get("기사", "")) or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_hq_schedules: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def hq_save_schedule(data: dict) -> bool:
    """본사관리자 일정 저장"""
    return save_schedule(data)


def hq_delete_schedule(schedule_id: str) -> bool:
    """본사관리자 일정 삭제"""
    return delete_schedule(schedule_id)


def get_neis_schools_by_vendor(vendor: str) -> list[dict]:
    """NEIS 학교코드가 등록된 거래처 목록"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM customer_info "
            "WHERE vendor=? AND neis_edu_code IS NOT NULL AND neis_edu_code != '' "
            "AND neis_school_code IS NOT NULL AND neis_school_code != '' "
            "AND cust_type = '학교' ORDER BY name",
            (vendor,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "name":             str(d.get("name", "") or ""),
                "neis_edu_code":    str(d.get("neis_edu_code", "") or ""),
                "neis_school_code": str(d.get("neis_school_code", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_neis_schools_by_vendor: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def save_neis_meal_schedule(
    school_name: str, vendor: str, meal_date: str,
    collect_date: str, item_type: str = "음식물", driver: str = "",
) -> bool:
    """NEIS 급식일 기반 수거일정 저장"""
    return db_insert("schedules", {
        "vendor": vendor,
        "month": collect_date,
        "weekdays": json.dumps(["급식"]),
        "schools": json.dumps([school_name]),
        "items": json.dumps([item_type]),
        "driver": driver,
        "registered_by": "neis_api",
    })


# ── 급식일정 승인 워크플로우 (P1 복원) ──

def get_meal_schedules(
    vendor: str = "", status: str = "", year_month: str = ""
) -> list[dict]:
    """meal_schedules 조회 (본사관리자 — 승인 워크플로우용)

    status 가 비어있으면 전체, 'draft'/'approved'/'cancelled' 필터 가능.
    year_month 는 meal_date 기준 YYYY-MM.
    """
    conn = get_db()
    try:
        clauses: list = []
        params: list = []
        if vendor:
            clauses.append("vendor = ?")
            params.append(vendor)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if year_month:
            clauses.append("meal_date LIKE ?")
            params.append(f"{year_month}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM meal_schedules{where} "
            f"ORDER BY meal_date ASC, school_name ASC LIMIT 1000",
            params,
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":           str(d.get("id", "") or ""),
                "vendor":       str(d.get("vendor", "") or ""),
                "school_name":  str(d.get("school_name", "") or ""),
                "meal_date":    str(d.get("meal_date", "") or ""),
                "collect_date": str(d.get("collect_date", "") or ""),
                "item_type":    str(d.get("item_type", "") or ""),
                "status":       str(d.get("status", "") or ""),
                "uploaded_by":  str(d.get("uploaded_by", "") or ""),
                "approved_by":  str(d.get("approved_by", "") or ""),
                "note":         str(d.get("note", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_meal_schedules: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def approve_meal_schedules(
    ids: list, approved_by: str = "admin",
    driver: str = "", collect_offset: int = 0,
) -> tuple[int, int]:
    """급식일정 승인 → meal_schedules.status='approved' + schedules 자동 생성

    Returns (성공건수, 실패건수)
    """
    from datetime import datetime as _dt, timedelta as _td
    if not ids:
        return 0, 0
    conn = get_db()
    success = 0
    fail = 0
    try:
        for raw_id in ids:
            try:
                row = conn.execute(
                    "SELECT * FROM meal_schedules WHERE id=?", (raw_id,),
                ).fetchone()
                if not row:
                    fail += 1
                    continue
                d = dict(row)
                meal_date = str(d.get("meal_date", ""))
                # collect_date 재계산 (offset 반영)
                try:
                    base = _dt.strptime(meal_date, "%Y-%m-%d")
                    new_collect = (base + _td(days=int(collect_offset))).strftime("%Y-%m-%d")
                except Exception as e:
                    print(f"[DB ERROR] approve_meal_schedules: {e}")
                    new_collect = str(d.get("collect_date", meal_date))

                now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE meal_schedules SET status='approved', "
                    "approved_by=?, collect_date=?, updated_at=? WHERE id=?",
                    (approved_by, new_collect, now, raw_id),
                )

                # schedules 테이블에 자동 반영 (driver 지정 시 덮어쓰기)
                drv = driver or ""
                conn.execute(
                    "INSERT INTO schedules "
                    "(vendor, month, weekdays, schools, items, driver, "
                    "created_at, registered_by) VALUES (?,?,?,?,?,?,?,?)",
                    (
                        str(d.get("vendor", "")),
                        new_collect,
                        json.dumps(["급식"]),
                        json.dumps([str(d.get("school_name", ""))]),
                        json.dumps([str(d.get("item_type", "음식물"))]),
                        drv,
                        now,
                        f"meal_approve:{approved_by}",
                    ),
                )
                success += 1
            except Exception as e:
                print(f"[DB ERROR] approve_meal_schedules: {e}")
                logger.warning(f"approve_meal_schedules row 실패: {e}")
                fail += 1
        conn.commit()
    finally:
        conn.close()
    return success, fail


def cancel_meal_schedules(ids: list, note: str = "") -> tuple[int, int]:
    """급식일정 반려 → status='cancelled'"""
    from datetime import datetime as _dt
    if not ids:
        return 0, 0
    conn = get_db()
    success = 0
    fail = 0
    try:
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        for raw_id in ids:
            try:
                conn.execute(
                    "UPDATE meal_schedules SET status='cancelled', "
                    "note=?, updated_at=? WHERE id=?",
                    (note, now, raw_id),
                )
                success += 1
            except Exception as e:
                print(f"[DB ERROR] cancel_meal_schedules: {e}")
                logger.warning(f"cancel_meal_schedules 실패: {e}")
                fail += 1
        conn.commit()
    finally:
        conn.close()
    return success, fail


def check_schedule_duplicate(vendor: str, month_key: str, schools_json: str) -> bool:
    """schedules 중복 체크 (vendor + month + schools 기준).

    True 반환 시 '이미 등록된 일정' 의미.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM schedules WHERE vendor=? AND month=? AND schools=? LIMIT 1",
            (vendor, month_key, schools_json),
        ).fetchone()
        return row is not None
    except Exception as e:
        print(f"[DB ERROR] check_schedule_duplicate: {e}")
        logger.warning(f'check_schedule_duplicate 실패: {str(e)}')
        return False
    finally:
        conn.close()


# ══════════════════════════════════════════
#  본사관리자 — 섹션E: 정산관리 + 탄소감축
# ══════════════════════════════════════════

CARBON_FACTOR = 0.587  # 음식물 1kg당 CO₂ 감축량 (kg)
TREE_FACTOR = 21.77    # 나무 1그루 연간 CO₂ 흡수량 (kg)


def get_settlement_data(year: int, month: int, vendor: str = "") -> list[dict]:
    """정산용 수거 데이터 집계"""
    conn = get_db()
    try:
        ym = f"{year}-{str(month).zfill(2)}"
        clauses = ["collect_date LIKE ?"]
        params: list = [f"{ym}%"]
        if vendor:
            clauses.append("vendor = ?")
            params.append(vendor)
        where = " WHERE " + " AND ".join(clauses)
        rows = conn.execute(
            f"SELECT * FROM real_collection{where}",
            params,
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                w = float(d.get("weight", 0) or 0)
            except (ValueError, TypeError):
                w = 0.0
            try:
                up = float(d.get("unit_price", 0) or 0)
            except (ValueError, TypeError):
                up = 0.0
            result.append({
                "collect_date": str(d.get("collect_date", "") or ""),
                "school_name":  str(d.get("school_name", "") or ""),
                "vendor":       str(d.get("vendor", "") or ""),
                "item_type":    str(d.get("item_type", "") or ""),
                "weight":       str(round(w, 1)),
                "unit_price":   str(round(up)),
                "amount":       str(round(w * up)),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_settlement_data: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_hq_settlement_summary(year: int, month: int, vendor: str = "") -> dict:
    """정산 요약 (총 수거량, 총 금액, VAT) — 본사관리자용"""
    rows = get_settlement_data(year, month, vendor)
    total_weight = 0.0
    total_amount = 0.0
    for r in rows:
        try:
            total_weight += float(r.get("weight", 0))
        except (ValueError, TypeError):
            pass
        try:
            total_amount += float(r.get("amount", 0))
        except (ValueError, TypeError):
            pass
    vat = total_amount * VAT_RATE
    return {
        "total_weight": str(round(total_weight, 1)),
        "total_amount": str(round(total_amount)),
        "vat": str(round(vat)),
        "grand_total": str(round(total_amount + vat)),
        "count": str(len(rows)),
    }


def get_carbon_data(year: int, month: int = 0) -> dict:
    """탄소감축 현황 데이터"""
    conn = get_db()
    try:
        if month:
            ym = f"{year}-{str(month).zfill(2)}"
            rows = conn.execute(
                "SELECT * FROM real_collection WHERE collect_date LIKE ?",
                (f"{ym}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM real_collection WHERE collect_date LIKE ?",
                (f"{year}%",),
            ).fetchall()

        food_kg = 0.0
        recycle_kg = 0.0
        general_kg = 0.0
        school_map: dict[str, float] = {}

        for r in rows:
            d = dict(r)
            try:
                w = float(d.get("weight", 0) or 0)
            except (ValueError, TypeError):
                w = 0.0
            item = str(d.get("item_type", "") or "").strip()
            if "음식물" in item:
                food_kg += w
            elif "재활용" in item:
                recycle_kg += w
            else:
                general_kg += w
            sn = str(d.get("school_name", "") or "")
            if sn:
                school_map[sn] = school_map.get(sn, 0.0) + w

        total_kg = food_kg + recycle_kg + general_kg
        carbon_reduced = round(food_kg * CARBON_FACTOR, 1)
        tree_equiv = round(carbon_reduced / TREE_FACTOR) if carbon_reduced > 0 else 0

        # 학교별 순위 top 10
        sorted_schools = sorted(school_map.items(), key=lambda x: -x[1])[:10]
        school_ranking = [
            {"school_name": k, "total_weight": str(round(v, 1)),
             "carbon": str(round(v * CARBON_FACTOR, 1))}
            for k, v in sorted_schools
        ]

        return {
            "food_kg": str(round(food_kg, 1)),
            "recycle_kg": str(round(recycle_kg, 1)),
            "general_kg": str(round(general_kg, 1)),
            "total_kg": str(round(total_kg, 1)),
            "carbon_reduced": str(carbon_reduced),
            "tree_equivalent": str(tree_equiv),
            "carbon_tons": str(round(carbon_reduced / 1000, 2)),
            "school_ranking": school_ranking,
        }
    except Exception as e:
        print(f"[DB ERROR] get_carbon_data: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "food_kg": "0", "recycle_kg": "0", "general_kg": "0",
            "total_kg": "0", "carbon_reduced": "0", "tree_equivalent": "0",
            "carbon_tons": "0", "school_ranking": [],
        }
    finally:
        conn.close()


# ══════════════════════════════════════════
#  본사관리자 — 섹션F: 안전관리 + 폐기물분석
# ══════════════════════════════════════════

def get_hq_safety_checklist(vendor: str = "") -> list[dict]:
    """안전점검 결과 조회 (HQ용 래퍼) — vendor 미지정 시 전체"""
    conn = get_db()
    try:
        if vendor:
            rows = conn.execute(
                "SELECT * FROM safety_checklist WHERE vendor=? "
                "ORDER BY check_date DESC LIMIT 300",
                (vendor,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM safety_checklist "
                "ORDER BY check_date DESC LIMIT 300"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "check_date": str(d.get("check_date", "") or ""),
                "vendor":     str(d.get("vendor", "") or ""),
                "driver":     str(d.get("driver", "") or ""),
                "vehicle_no": str(d.get("vehicle_no", "") or ""),
                "total_ok":   str(d.get("total_ok", 0) or 0),
                "total_fail": str(d.get("total_fail", 0) or 0),
                "inspector":  str(d.get("inspector", "") or ""),
                "memo":       str(d.get("memo", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_hq_safety_checklist: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_hq_daily_checks(vendor: str = "", year_month: str = "") -> list[dict]:
    """일일안전점검 이력 조회 (HQ용 래퍼) — vendor / year_month 모두 선택적"""
    conn = get_db()
    try:
        clauses = []
        params: list = []
        if vendor:
            clauses.append("vendor=?")
            params.append(vendor)
        if year_month:
            clauses.append("check_date LIKE ?")
            params.append(f"{year_month}%")
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM daily_safety_check{where} ORDER BY check_date DESC LIMIT 500",
            params,
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "check_date": str(d.get("check_date", "") or ""),
                "vendor":     str(d.get("vendor", "") or ""),
                "driver":     str(d.get("driver", "") or ""),
                "vehicle_no": str(d.get("vehicle_no", "") or ""),
                "category":   str(d.get("category", "") or ""),
                "total_ok":   str(d.get("total_ok", 0) or 0),
                "total_fail": str(d.get("total_fail", 0) or 0),
                "fail_memo":  str(d.get("fail_memo", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_hq_daily_checks: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def update_accident_status(accident_id: int, new_status: str) -> bool:
    """사고 보고 상태 변경 (처리중 / 완료)"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE accident_reports SET status=? WHERE id=?",
            (new_status, int(accident_id)),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] update_accident_status: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def get_hq_safety_education(vendor: str = "") -> list[dict]:
    """안전교육 이력 조회"""
    conn = get_db()
    try:
        if vendor:
            rows = conn.execute(
                "SELECT * FROM safety_education WHERE vendor=? ORDER BY edu_date DESC",
                (vendor,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM safety_education ORDER BY edu_date DESC LIMIT 200"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":       str(d.get("id", "") or ""),
                "vendor":   str(d.get("vendor", "") or ""),
                "edu_date": str(d.get("edu_date", "") or ""),
                "edu_type": str(d.get("edu_type", "") or ""),
                "topic":    str(d.get("topic", "") or ""),
                "attendees": str(d.get("attendees", "") or ""),
                "hours":    str(d.get("hours", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_hq_safety_education: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_hq_accident_reports(vendor: str = "") -> list[dict]:
    """사고/신고 이력 조회"""
    conn = get_db()
    try:
        if vendor:
            rows = conn.execute(
                "SELECT * FROM accident_reports WHERE vendor=? ORDER BY accident_date DESC",
                (vendor,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM accident_reports ORDER BY accident_date DESC LIMIT 200"
            ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "id":            str(d.get("id", "") or ""),
                "vendor":        str(d.get("vendor", "") or ""),
                "accident_date": str(d.get("accident_date", "") or ""),
                "accident_type": str(d.get("accident_type", "") or ""),
                "driver":        str(d.get("driver", "") or ""),
                "description":   str(d.get("description", "") or ""),
                "status":        str(d.get("status", "") or ""),
                "action_taken":  str(d.get("action_taken", "") or ""),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] get_hq_accident_reports: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def get_waste_analytics(year: int, month: int = 0) -> dict:
    """폐기물 발생 분석 데이터"""
    conn = get_db()
    try:
        if month:
            ym = f"{year}-{str(month).zfill(2)}"
            rows = conn.execute(
                "SELECT * FROM real_collection WHERE collect_date LIKE ?",
                (f"{ym}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM real_collection WHERE collect_date LIKE ?",
                (f"{year}%",),
            ).fetchall()

        total = 0.0
        by_item: dict[str, float] = {}
        by_school: dict[str, float] = {}
        by_vendor: dict[str, float] = {}
        by_month: dict[str, float] = {}

        for r in rows:
            d = dict(r)
            try:
                w = float(d.get("weight", 0) or 0)
            except (ValueError, TypeError):
                w = 0.0
            total += w
            item = str(d.get("item_type", "기타") or "기타").strip()
            by_item[item] = by_item.get(item, 0.0) + w
            sn = str(d.get("school_name", "") or "")
            if sn:
                by_school[sn] = by_school.get(sn, 0.0) + w
            vn = str(d.get("vendor", "") or "")
            if vn:
                by_vendor[vn] = by_vendor.get(vn, 0.0) + w
            cd = str(d.get("collect_date", "") or "")[:7]
            if cd:
                by_month[cd] = by_month.get(cd, 0.0) + w

        by_item_list = [
            {"item": k, "weight": str(round(v, 1))}
            for k, v in sorted(by_item.items(), key=lambda x: -x[1])
        ]
        by_school_list = [
            {"school_name": k, "weight": str(round(v, 1))}
            for k, v in sorted(by_school.items(), key=lambda x: -x[1])[:15]
        ]
        by_vendor_list = [
            {"vendor": k, "weight": str(round(v, 1))}
            for k, v in sorted(by_vendor.items(), key=lambda x: -x[1])
        ]
        by_month_list = [
            {"month": k, "weight": str(round(v, 1))}
            for k, v in sorted(by_month.items())
        ]

        return {
            "total_weight": str(round(total, 1)),
            "count": str(len(rows)),
            "by_item": by_item_list,
            "by_school": by_school_list,
            "by_vendor": by_vendor_list,
            "by_month": by_month_list,
        }
    except Exception as e:
        print(f"[DB ERROR] get_waste_analytics: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "total_weight": "0", "count": "0",
            "by_item": [], "by_school": [], "by_vendor": [], "by_month": [],
        }
    finally:
        conn.close()


# ══════════════════════════════════════════
#  학교모드 전용 함수
# ══════════════════════════════════════════

def _build_alias_map(school_master_rows: list) -> dict:
    """school_master → alias_map (양방향)"""
    alias_map = {}
    for r in school_master_rows:
        sn = r.get("school_name", "")
        if not sn:
            continue
        aliases = [a.strip() for a in (r.get("alias", "") or "").split(",") if a.strip()]
        alias_map[sn] = aliases
        for a in aliases:
            if a not in alias_map:
                alias_map[a] = [sn] + [x for x in aliases if x != a]
    return alias_map


def _match_with_alias(target: str, candidate: str, alias_map: dict) -> bool:
    """alias 기반 학교명 매칭 (양방향 + 포함관계)"""
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


def school_filter_collections(school: str, year: int, month: int) -> list[dict]:
    """학교 수거 데이터 조회 (별칭 매칭 + 연/월 필터)"""
    conn = get_db()
    try:
        sm_rows = conn.execute("SELECT school_name, alias FROM school_master").fetchall()
        sm_rows = [dict(r) for r in sm_rows]
        alias_map = _build_alias_map(sm_rows)

        prefix = f"{year}-{str(month).zfill(2)}"
        rows = conn.execute(
            "SELECT * FROM real_collection WHERE collect_date LIKE ?",
            (f"{prefix}%",)
        ).fetchall()
        rows = [dict(r) for r in rows]

        filtered = [r for r in rows if _match_with_alias(school, r.get("school_name", ""), alias_map)]

        result = []
        for r in filtered:
            result.append({
                "id": str(r.get("id", "")),
                "collect_date": str(r.get("collect_date", "")),
                "item_type": str(r.get("item_type", "")),
                "weight": str(r.get("weight", 0)),
                "driver": str(r.get("driver", "")),
                "vendor": str(r.get("vendor", "")),
                "status": str(r.get("status", "")),
                "unit_price": str(r.get("unit_price", 0)),
                "memo": str(r.get("memo", "")),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] school_filter_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def school_get_monthly_summary(school: str, year: int) -> list[dict]:
    """학교 월별 수거량 요약 (1~12월)"""
    conn = get_db()
    try:
        sm_rows = conn.execute("SELECT school_name, alias FROM school_master").fetchall()
        sm_rows = [dict(r) for r in sm_rows]
        alias_map = _build_alias_map(sm_rows)

        rows = conn.execute(
            "SELECT * FROM real_collection WHERE collect_date LIKE ?",
            (f"{year}-%",)
        ).fetchall()
        rows = [dict(r) for r in rows]
        filtered = [r for r in rows if _match_with_alias(school, r.get("school_name", ""), alias_map)]

        monthly = {}
        for r in filtered:
            try:
                m = str(r.get("collect_date", ""))[5:7]
                m_int = int(m)
            except (ValueError, IndexError):
                continue
            w = float(r.get("weight", 0) or 0)
            if m_int not in monthly:
                monthly[m_int] = {"weight": 0.0, "count": 0}
            monthly[m_int]["weight"] += w
            monthly[m_int]["count"] += 1

        result = []
        for m in range(1, 13):
            d = monthly.get(m, {"weight": 0.0, "count": 0})
            result.append({
                "month": str(m),
                "weight": str(round(d["weight"], 1)),
                "count": str(d["count"]),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] school_get_monthly_summary: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def school_get_settlement(school: str, year: int, month: int) -> dict:
    """학교 정산 요약 (품목별 집계 + 합계)"""
    rows = school_filter_collections(school, year, month)
    confirmed = [r for r in rows if r.get("status") in ("submitted", "confirmed")]

    by_item = {}
    total_weight = 0.0
    total_amount = 0.0
    for r in confirmed:
        it = r.get("item_type", "기타")
        w = float(r.get("weight", 0) or 0)
        up = float(r.get("unit_price", 0) or 0)
        amt = w * up
        total_weight += w
        total_amount += amt
        if it not in by_item:
            by_item[it] = {"weight": 0.0, "amount": 0.0, "count": 0}
        by_item[it]["weight"] += w
        by_item[it]["amount"] += amt
        by_item[it]["count"] += 1

    vat = total_amount * VAT_RATE
    items_list = [
        {
            "item_type": k,
            "weight": str(round(v["weight"], 1)),
            "amount": str(int(v["amount"])),
            "count": str(v["count"]),
        }
        for k, v in sorted(by_item.items())
    ]

    return {
        "total_weight": str(round(total_weight, 1)),
        "total_amount": str(int(total_amount)),
        "vat": str(int(vat)),
        "grand_total": str(int(total_amount + vat)),
        "items": items_list,
        "row_count": str(len(confirmed)),
    }


def school_get_esg(school: str, year: int, month: int = 0) -> dict:
    """학교 ESG 탄소감축 현황"""
    conn = get_db()
    try:
        sm_rows = conn.execute("SELECT school_name, alias FROM school_master").fetchall()
        sm_rows = [dict(r) for r in sm_rows]
        alias_map = _build_alias_map(sm_rows)

        if month > 0:
            prefix = f"{year}-{str(month).zfill(2)}"
        else:
            prefix = f"{year}-"
        rows = conn.execute(
            "SELECT * FROM real_collection WHERE collect_date LIKE ?",
            (f"{prefix}%",)
        ).fetchall()
        rows = [dict(r) for r in rows]
        filtered = [r for r in rows if _match_with_alias(school, r.get("school_name", ""), alias_map)]

        food_kg = 0.0
        recycle_kg = 0.0
        general_kg = 0.0
        for r in filtered:
            w = float(r.get("weight", 0) or 0)
            it = str(r.get("item_type", ""))
            if "음식물" in it:
                food_kg += w
            elif "재활용" in it:
                recycle_kg += w
            else:
                general_kg += w

        # 탄소계수: 음식물 0.47, 재활용 0.21, 일반 0.09
        carbon = food_kg * CARBON_FOOD + recycle_kg * CARBON_RECYCLE + general_kg * CARBON_GENERAL
        total_kg = food_kg + recycle_kg + general_kg

        return {
            "total_kg": str(round(total_kg, 1)),
            "food_kg": str(round(food_kg, 1)),
            "recycle_kg": str(round(recycle_kg, 1)),
            "general_kg": str(round(general_kg, 1)),
            "carbon_reduced": str(round(carbon, 1)),
            "tree_equivalent": str(round(carbon / 21.77, 1)) if carbon > 0 else "0",
            "carbon_tons": str(round(carbon / 1000, 3)),
            "count": str(len(filtered)),
        }
    except Exception as e:
        print(f"[DB ERROR] school_get_esg: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "total_kg": "0", "food_kg": "0", "recycle_kg": "0", "general_kg": "0",
            "carbon_reduced": "0", "tree_equivalent": "0", "carbon_tons": "0", "count": "0",
        }
    finally:
        conn.close()


def school_get_vendors(school_name: str) -> list[str]:
    """학교에 배정된 수거업체 목록 역조회"""
    import json as _json
    conn = get_db()
    try:
        vendors = set()
        # 1. school_master
        rows = conn.execute("SELECT vendor FROM school_master WHERE school_name = ?", (school_name,)).fetchall()
        for r in rows:
            v = r[0]
            if v:
                vendors.add(v)
        # 2. customer_info
        rows = conn.execute("SELECT vendor FROM customer_info WHERE name = ?", (school_name,)).fetchall()
        for r in rows:
            v = r[0]
            if v:
                vendors.add(v)
        # 3. schedules
        rows = conn.execute("SELECT vendor, schools FROM schedules").fetchall()
        for r in rows:
            try:
                school_list = _json.loads(r[1] or "[]")
                if school_name in school_list and r[0]:
                    vendors.add(r[0])
            except Exception as e:
                print(f"[DB ERROR] school_get_vendors: {e}")
                logger.warning(f'Exception caught: {str(e)}')
                pass
        return sorted(list(vendors))
    except Exception as e:
        print(f"[DB ERROR] school_get_vendors: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def school_get_safety_report(school_name: str, year_month: str) -> dict:
    """학교 안전관리 보고서 데이터"""
    vendors = school_get_vendors(school_name)
    conn = get_db()
    try:
        # 1. 안전등급
        scores = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM safety_scores WHERE vendor = ? AND year_month = ?",
                (v, year_month)
            ).fetchall()
            for r in rows:
                d = dict(r)
                scores.append({
                    "vendor": str(d.get("vendor", "")),
                    "total_score": str(d.get("total_score", 0)),
                    "grade": str(d.get("grade", "")),
                    "violation_score": str(d.get("violation_score", 0)),
                    "checklist_score": str(d.get("checklist_score", 0)),
                    "daily_check_score": str(d.get("daily_check_score", 0)),
                    "education_score": str(d.get("education_score", 0)),
                })

        # 2. 스쿨존 위반
        violations = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM school_zone_violations WHERE vendor = ?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                vd = str(d.get("violation_date", ""))
                if vd.startswith(year_month):
                    violations.append({
                        "vendor": str(d.get("vendor", "")),
                        "driver": str(d.get("driver", "")),
                        "violation_date": vd,
                        "violation_type": str(d.get("violation_type", "")),
                        "location": str(d.get("location", "")),
                        "fine_amount": str(d.get("fine_amount", 0)),
                    })

        # 3. 안전교육
        edu_rows = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM safety_education WHERE vendor = ?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                ed = str(d.get("edu_date", ""))
                if ed.startswith(year_month[:4]):
                    edu_rows.append({
                        "vendor": str(d.get("vendor", "")),
                        "driver": str(d.get("driver", "")),
                        "edu_name": str(d.get("edu_name", "")),
                        "edu_date": ed,
                        "completed": str(d.get("completed", "")),
                    })

        # 4. 차량점검(safety_checklist)
        checklist_rows = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM safety_checklist WHERE vendor=?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                cd = str(d.get("check_date", ""))
                if cd.startswith(year_month):
                    checklist_rows.append(d)

        # 5. 사고보고(accident_report)
        accident_rows = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM accident_report WHERE vendor=?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                od = str(d.get("occur_date", ""))
                if od.startswith(year_month):
                    accident_rows.append(d)

        # 6. 일일안전점검(daily_safety_check)
        daily_checks = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM daily_safety_check WHERE vendor=? AND check_date LIKE ?",
                (v, f"{year_month}%")
            ).fetchall()
            daily_checks.extend([dict(r) for r in rows])

        return {
            "vendors": vendors,
            "scores": scores,
            "violations": violations,
            "education": edu_rows,
            "checklist": checklist_rows,
            "accident": accident_rows,
            "daily_checks": daily_checks,
        }
    except Exception as e:
        print(f"[DB ERROR] school_get_safety_report: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {"vendors": [], "scores": [], "violations": [], "education": [],
                "checklist": [], "accident": [], "daily_checks": []}
    finally:
        conn.close()


# ══════════════════════════════════════════
#  교육청모드 전용 함수
# ══════════════════════════════════════════

def edu_get_managed_schools(user_schools: str) -> list[str]:
    """교육청 관할 학교 목록 (빈 값이면 전체 학교)"""
    if user_schools and user_schools.strip():
        return [s.strip() for s in user_schools.split(",") if s.strip()]
    conn = get_db()
    try:
        rows = conn.execute("SELECT school_name FROM school_master ORDER BY school_name").fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        print(f"[DB ERROR] edu_get_managed_schools: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def edu_get_vendors_for_schools(schools: list[str]) -> list[str]:
    """관할 학교들의 담당 수거업체 목록 (중복 제거)"""
    vendors = set()
    for s in schools:
        vs = school_get_vendors(s)
        vendors.update(vs)
    return sorted(list(vendors))


def edu_get_overview(schools: list[str], year: int, month: int = 0) -> dict:
    """교육청 전체 현황 (관할학교 기준 집계)"""
    conn = get_db()
    try:
        sm_rows = conn.execute("SELECT school_name, alias FROM school_master").fetchall()
        sm_rows = [dict(r) for r in sm_rows]
        alias_map = _build_alias_map(sm_rows)

        if month > 0:
            prefix = f"{year}-{str(month).zfill(2)}"
        else:
            prefix = f"{year}-"
        rows = conn.execute(
            "SELECT * FROM real_collection WHERE collect_date LIKE ?",
            (f"{prefix}%",)
        ).fetchall()
        rows = [dict(r) for r in rows]

        # 관할학교 필터
        school_data = {}
        total_weight = 0.0
        total_count = 0
        for r in rows:
            sn = r.get("school_name", "")
            matched_school = None
            for s in schools:
                if _match_with_alias(s, sn, alias_map):
                    matched_school = s
                    break
            if matched_school is None:
                continue
            w = float(r.get("weight", 0) or 0)
            total_weight += w
            total_count += 1
            if matched_school not in school_data:
                school_data[matched_school] = {"weight": 0.0, "count": 0}
            school_data[matched_school]["weight"] += w
            school_data[matched_school]["count"] += 1

        school_list = [
            {
                "school_name": k,
                "weight": str(round(v["weight"], 1)),
                "count": str(v["count"]),
            }
            for k, v in sorted(school_data.items(), key=lambda x: -x[1]["weight"])
        ]

        vendors = edu_get_vendors_for_schools(schools)

        return {
            "school_count": str(len(schools)),
            "total_weight": str(round(total_weight, 1)),
            "total_count": str(total_count),
            "vendor_count": str(len(vendors)),
            "school_list": school_list,
        }
    except Exception as e:
        print(f"[DB ERROR] edu_get_overview: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "school_count": "0", "total_weight": "0", "total_count": "0",
            "vendor_count": "0", "school_list": [],
        }
    finally:
        conn.close()


def edu_get_by_school(schools: list[str], school: str, year: int, month: int) -> list[dict]:
    """교육청: 학교별 수거 데이터 조회"""
    return school_filter_collections(school, year, month)


def edu_get_by_vendor(schools: list[str], vendor: str, year: int) -> dict:
    """교육청: 업체별 수거 현황"""
    conn = get_db()
    try:
        sm_rows = conn.execute("SELECT school_name, alias FROM school_master").fetchall()
        sm_rows = [dict(r) for r in sm_rows]
        alias_map = _build_alias_map(sm_rows)

        rows = conn.execute(
            "SELECT * FROM real_collection WHERE vendor = ? AND collect_date LIKE ?",
            (vendor, f"{year}-%")
        ).fetchall()
        rows = [dict(r) for r in rows]

        # 관할학교만 필터
        by_school = {}
        total = 0.0
        for r in rows:
            sn = r.get("school_name", "")
            matched = None
            for s in schools:
                if _match_with_alias(s, sn, alias_map):
                    matched = s
                    break
            if matched is None:
                continue
            w = float(r.get("weight", 0) or 0)
            total += w
            if matched not in by_school:
                by_school[matched] = 0.0
            by_school[matched] += w

        school_list = [
            {"school_name": k, "weight": str(round(v, 1))}
            for k, v in sorted(by_school.items(), key=lambda x: -x[1])
        ]

        return {
            "total_weight": str(round(total, 1)),
            "school_count": str(len(by_school)),
            "school_list": school_list,
        }
    except Exception as e:
        print(f"[DB ERROR] edu_get_by_vendor: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {"total_weight": "0", "school_count": "0", "school_list": []}
    finally:
        conn.close()


def edu_get_carbon(schools: list[str], year: int, month: int = 0) -> dict:
    """교육청 탄소감축 현황"""
    conn = get_db()
    try:
        sm_rows = conn.execute("SELECT school_name, alias FROM school_master").fetchall()
        sm_rows = [dict(r) for r in sm_rows]
        alias_map = _build_alias_map(sm_rows)

        if month > 0:
            prefix = f"{year}-{str(month).zfill(2)}"
        else:
            prefix = f"{year}-"
        rows = conn.execute(
            "SELECT * FROM real_collection WHERE collect_date LIKE ?",
            (f"{prefix}%",)
        ).fetchall()
        rows = [dict(r) for r in rows]

        food_kg = 0.0
        recycle_kg = 0.0
        general_kg = 0.0
        by_school = {}

        for r in rows:
            sn = r.get("school_name", "")
            matched = None
            for s in schools:
                if _match_with_alias(s, sn, alias_map):
                    matched = s
                    break
            if matched is None:
                continue
            w = float(r.get("weight", 0) or 0)
            it = str(r.get("item_type", ""))
            if "음식물" in it:
                food_kg += w
            elif "재활용" in it:
                recycle_kg += w
            else:
                general_kg += w
            if matched not in by_school:
                by_school[matched] = 0.0
            by_school[matched] += w

        total = food_kg + recycle_kg + general_kg
        carbon = food_kg * CARBON_FOOD + recycle_kg * CARBON_RECYCLE + general_kg * CARBON_GENERAL

        ranking = [
            {
                "school_name": k,
                "weight": str(round(v, 1)),
                "carbon": str(round(v * 0.587, 1)),
            }
            for k, v in sorted(by_school.items(), key=lambda x: -x[1])[:15]
        ]

        return {
            "total_kg": str(round(total, 1)),
            "food_kg": str(round(food_kg, 1)),
            "recycle_kg": str(round(recycle_kg, 1)),
            "general_kg": str(round(general_kg, 1)),
            "carbon_reduced": str(round(carbon, 1)),
            "tree_equivalent": str(round(carbon / 21.77, 1)) if carbon > 0 else "0",
            "carbon_tons": str(round(carbon / 1000, 3)),
            "school_ranking": ranking,
        }
    except Exception as e:
        print(f"[DB ERROR] edu_get_carbon: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "total_kg": "0", "food_kg": "0", "recycle_kg": "0", "general_kg": "0",
            "carbon_reduced": "0", "tree_equivalent": "0", "carbon_tons": "0",
            "school_ranking": [],
        }
    finally:
        conn.close()


def edu_get_safety(schools: list[str], year_month: str) -> dict:
    """교육청 안전관리 현황"""
    vendors = edu_get_vendors_for_schools(schools)
    conn = get_db()
    try:
        # 1. 안전등급
        scores = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM safety_scores WHERE vendor = ? AND year_month = ?",
                (v, year_month)
            ).fetchall()
            for r in rows:
                d = dict(r)
                scores.append({
                    "vendor": str(d.get("vendor", "")),
                    "total_score": str(d.get("total_score", 0)),
                    "grade": str(d.get("grade", "")),
                    "violation_score": str(d.get("violation_score", 0)),
                    "checklist_score": str(d.get("checklist_score", 0)),
                    "daily_check_score": str(d.get("daily_check_score", 0)),
                    "education_score": str(d.get("education_score", 0)),
                })

        # 2. 스쿨존 위반
        violations = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM school_zone_violations WHERE vendor = ?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                vd = str(d.get("violation_date", ""))
                if vd.startswith(year_month):
                    violations.append({
                        "vendor": str(d.get("vendor", "")),
                        "driver": str(d.get("driver", "")),
                        "violation_date": vd,
                        "violation_type": str(d.get("violation_type", "")),
                        "location": str(d.get("location", "")),
                        "fine_amount": str(d.get("fine_amount", 0)),
                    })

        # 3. 안전교육
        edu_rows = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM safety_education WHERE vendor = ?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                ed = str(d.get("edu_date", ""))
                if ed.startswith(year_month[:4]):
                    edu_rows.append({
                        "vendor": str(d.get("vendor", "")),
                        "driver": str(d.get("driver", "")),
                        "edu_name": str(d.get("edu_name", "")),
                        "edu_date": ed,
                        "completed": str(d.get("completed", "")),
                    })

        # 4. 사고 보고
        accidents = []
        for v in vendors:
            rows = conn.execute(
                "SELECT * FROM accident_report WHERE vendor = ?", (v,)
            ).fetchall()
            for r in rows:
                d = dict(r)
                ad = str(d.get("accident_date", ""))
                if ad.startswith(year_month[:4]):
                    accidents.append({
                        "vendor": str(d.get("vendor", "")),
                        "driver": str(d.get("driver", "")),
                        "accident_date": ad,
                        "accident_type": str(d.get("accident_type", "")),
                        "location": str(d.get("location", "")),
                        "damage": str(d.get("damage", "")),
                        "status": str(d.get("status", "")),
                    })

        return {
            "vendors": vendors,
            "scores": scores,
            "violations": violations,
            "education": edu_rows,
            "accidents": accidents,
        }
    except Exception as e:
        print(f"[DB ERROR] edu_get_safety: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {"vendors": [], "scores": [], "violations": [], "education": [], "accidents": []}
    finally:
        conn.close()


# ══════════════════════════════════════════
#  급식담당자모드 전용 함수
# ══════════════════════════════════════════

import json as _json_mod
import re as _re_mod


def _classify_waste_grade(waste_per_person: float) -> str:
    """1인당 잔반량(g) → A/B/C/D 등급"""
    if waste_per_person <= 0:
        return "-"
    if waste_per_person < 150:
        return "A"
    elif waste_per_person < 245:
        return "B"
    elif waste_per_person < 300:
        return "C"
    else:
        return "D"


def _detect_school_level(school_name: str) -> str:
    """학교명에서 학교급 자동 추출"""
    name = str(school_name or "")
    if _re_mod.search(r"고등|고교", name):
        return "고등"
    if _re_mod.search(r"중학|중교", name):
        return "중학"
    if _re_mod.search(r"초등|초교", name):
        return "초등"
    return "혼합평균"


# ── 학교급식법 공식기준 ──
WASTE_GRADE_TABLE = [
    {"grade": "A", "range": "150g 미만", "color": "green", "label": "우수"},
    {"grade": "B", "range": "150~244g", "color": "blue", "label": "양호"},
    {"grade": "C", "range": "245~299g", "color": "orange", "label": "주의"},
    {"grade": "D", "range": "300g 이상", "color": "red", "label": "경보"},
]

# 학교급별 1끼 표준 제공량(g) — 학교급식법 기준
_SCHOOL_STANDARD: dict = {
    "초등": {"밥": 130, "국": 150, "반찬": 60, "김치": 40, "우유": 200, "합계": 580},
    "중학": {"밥": 210, "국": 200, "반찬": 80, "김치": 50, "우유": 200, "합계": 740},
    "고등": {"밥": 260, "국": 200, "반찬": 80, "김치": 50, "우유": 200, "합계": 790},
    "혼합평균": {"밥": 200, "국": 185, "반찬": 73, "김치": 47, "우유": 200, "합계": 705},
}

# 잔반 월별/계절별 트렌드용 상수
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
SEASON_MAP = {
    "봄": [3, 4, 5],
    "여름": [6, 7, 8],
    "가을": [9, 10, 11],
    "겨울": [12, 1, 2],
}


def get_school_standard(school_type: str) -> dict:
    """학교급별 1끼 표준 제공량(g) 반환"""
    return dict(_SCHOOL_STANDARD.get(school_type, _SCHOOL_STANDARD["혼합평균"]))


def meal_get_menus(site_name: str, year_month: str) -> list[dict]:
    """식단 조회"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM meal_menus WHERE site_name = ? AND year_month = ? ORDER BY meal_date",
            (site_name, year_month)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            result.append({
                "meal_date": str(d.get("meal_date", "")),
                "meal_type": str(d.get("meal_type", "중식")),
                "menu_items": str(d.get("menu_items", "[]")),
                "calories": str(d.get("calories", 0)),
                "servings": str(d.get("servings", 0)),
                "nutrition_info": str(d.get("nutrition_info", "{}")),
            })
        return result
    except Exception as e:
        print(f"[DB ERROR] meal_get_menus: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def meal_get_menus_by_month(site_name: str, year_month: str) -> list:
    """달력 표시용 식단 조회 (날짜→메뉴요약 매핑 리스트)"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT meal_date, menu_items FROM meal_menus WHERE site_name = ? AND year_month = ?",
            (site_name, year_month)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            md = str(d.get("meal_date", ""))
            try:
                mi = _json_mod.loads(d.get("menu_items", "[]"))
                summary = ", ".join(str(x) for x in (mi[:3] if isinstance(mi, list) else [mi]))
            except Exception:
                summary = str(d.get("menu_items", ""))
            result.append({"date": md, "summary": summary})
        return result
    except Exception as e:
        logger.warning(f"meal_get_menus_by_month: {e}")
        return []
    finally:
        conn.close()


def meal_get_collected_dates(site_name: str, year_month: str) -> list:
    """해당 급식소의 수거 완료 날짜 목록"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT DISTINCT collect_date FROM real_collection "
            "WHERE school_name = ? AND collect_date LIKE ?",
            (site_name, f"{year_month}%")
        ).fetchall()
        return [str(r[0]) for r in rows]
    except Exception as e:
        logger.warning(f"meal_get_collected_dates: {e}")
        return []
    finally:
        conn.close()


def meal_get_school_student_count(site_name: str) -> int:
    """급식소 기본 학생수 조회 — customer_info.student_count 없으면 0 반환"""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM customer_info WHERE name = ? LIMIT 1", (site_name,)
        ).fetchone()
        if row is None:
            return 0
        d = dict(row)
        cnt = d.get("student_count", d.get("students", 0))
        return int(cnt or 0)
    except Exception as e:
        logger.warning(f"meal_get_school_student_count: {e}")
        return 0
    finally:
        conn.close()


def meal_get_monthly_trend(site_name: str, year: int) -> list:
    """월별 잔반 트렌드 — meal_analysis 테이블에서 집계"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT year_month, AVG(waste_per_person) as avg_pp, "
            "SUM(waste_kg) as total_kg, COUNT(*) as cnt "
            "FROM meal_analysis WHERE site_name = ? AND year_month LIKE ? "
            "GROUP BY year_month ORDER BY year_month",
            (site_name, f"{year}%")
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            ym = str(d.get("year_month", ""))
            month = ym[5:7] if len(ym) >= 7 else ym
            result.append({
                "month": month + "월",
                "avg": str(round(float(d.get("avg_pp", 0) or 0), 1)),
                "total": str(round(float(d.get("total_kg", 0) or 0), 1)),
                "count": str(int(d.get("cnt", 0) or 0)),
                "avg_num": round(float(d.get("avg_pp", 0) or 0), 1),
                "total_num": round(float(d.get("total_kg", 0) or 0), 1),
            })
        return result
    except Exception as e:
        logger.warning(f"meal_get_monthly_trend: {e}")
        return []
    finally:
        conn.close()


def meal_get_seasonal_compare(site_name: str, year: int) -> list:
    """계절별 잔반 비교"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT year_month, AVG(waste_per_person) as avg_pp, COUNT(*) as cnt "
            "FROM meal_analysis WHERE site_name = ? AND year_month LIKE ? "
            "GROUP BY year_month",
            (site_name, f"{year}%")
        ).fetchall()
        season_data: dict = {"봄": {"sum": 0.0, "cnt": 0}, "여름": {"sum": 0.0, "cnt": 0},
                              "가을": {"sum": 0.0, "cnt": 0}, "겨울": {"sum": 0.0, "cnt": 0}}
        for r in rows:
            d = dict(r)
            ym = str(d.get("year_month", ""))
            try:
                month_num = int(ym[5:7])
            except (ValueError, IndexError):
                continue
            avg_pp = float(d.get("avg_pp", 0) or 0)
            cnt = int(d.get("cnt", 0) or 0)
            for season, months in SEASON_MAP.items():
                if month_num in months:
                    season_data[season]["sum"] += avg_pp * cnt
                    season_data[season]["cnt"] += cnt
                    break
        result = []
        for season in ["봄", "여름", "가을", "겨울"]:
            s = season_data[season]
            n = s["cnt"]
            avg = round(s["sum"] / n, 1) if n > 0 else 0.0
            result.append({
                "season": season,
                "avg": str(avg),
                "count": str(n),
                "avg_num": avg,
            })
        return result
    except Exception as e:
        logger.warning(f"meal_get_seasonal_compare: {e}")
        return []
    finally:
        conn.close()


def meal_save_menu(site_name: str, meal_date: str, meal_type: str,
                   menu_items: str, calories: int, servings: int,
                   nutrition_info: str = "{}") -> bool:
    """일별 식단 저장 (UPSERT)"""
    conn = get_db()
    try:
        from datetime import datetime as _dt
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        ym = meal_date[:7] if len(meal_date) >= 7 else ""
        conn.execute("""
            INSERT INTO meal_menus
                (site_name, meal_date, meal_type, menu_items, calories,
                 nutrition_info, servings, year_month, created_at, site_type)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(site_name, meal_date, meal_type) DO UPDATE SET
                menu_items=excluded.menu_items,
                calories=excluded.calories,
                nutrition_info=excluded.nutrition_info,
                servings=excluded.servings,
                created_at=excluded.created_at
        """, (site_name, meal_date, meal_type, menu_items, calories,
              nutrition_info, servings, ym, now, "학교"))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] meal_save_menu: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def meal_delete_menu(site_name: str, meal_date: str) -> bool:
    """식단 삭제"""
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM meal_menus WHERE site_name = ? AND meal_date = ?",
            (site_name, meal_date)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] meal_delete_menu: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return False
    finally:
        conn.close()


def meal_analyze_waste(site_name: str, year_month: str) -> list[dict]:
    """식단 ↔ 수거량 매칭 분석"""
    conn = get_db()
    try:
        # 식단 로드
        menus = conn.execute(
            "SELECT * FROM meal_menus WHERE site_name = ? AND year_month = ? ORDER BY meal_date",
            (site_name, year_month)
        ).fetchall()
        if not menus:
            return []

        # 수거 데이터 (음식물만)
        collections = conn.execute(
            "SELECT collect_date, weight, item_type FROM real_collection WHERE school_name = ? AND collect_date LIKE ?",
            (site_name, f"{year_month}%")
        ).fetchall()
        col_map = {}
        for r in collections:
            d = dict(r)
            it = str(d.get("item_type", ""))
            if "음식물" in it or it in ("food_waste", ""):
                dt = str(d.get("collect_date", ""))
                w = float(d.get("weight", 0) or 0)
                col_map[dt] = col_map.get(dt, 0) + w

        results = []
        for m in menus:
            m = dict(m)
            md = str(m.get("meal_date", ""))
            waste_kg = col_map.get(md, 0)
            servings = int(m.get("servings", 0) or 0)
            waste_pp = round((waste_kg * 1000) / servings, 1) if servings > 0 else 0
            grade = _classify_waste_grade(waste_pp) if waste_kg > 0 else "-"
            waste_rate = round(waste_pp / 715 * 100, 1) if waste_pp > 0 else 0

            # 메뉴 파싱
            try:
                menu_list = _json_mod.loads(m.get("menu_items", "[]"))
                if isinstance(menu_list, list):
                    menu_str = ", ".join(str(x) for x in menu_list[:5])
                else:
                    menu_str = str(menu_list)
            except Exception as e:
                print(f"[DB ERROR] meal_analyze_waste: {e}")
                logger.error(f'Exception in operation: {str(e)}')
                menu_str = str(m.get("menu_items", ""))

            results.append({
                "meal_date": md,
                "menu_items": menu_str,
                "servings": str(servings),
                "calories": str(m.get("calories", 0)),
                "waste_kg": str(round(waste_kg, 2)),
                "waste_per_person": str(waste_pp),
                "waste_rate": str(waste_rate),
                "grade": grade,
            })

        # 캐시 저장
        from datetime import datetime as _dt
        now = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
        for r in results:
            try:
                conn.execute("""
                    INSERT INTO meal_analysis
                        (site_name, year_month, meal_date, menu_items,
                         waste_kg, waste_per_person, waste_rate, grade, remark, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(site_name, meal_date) DO UPDATE SET
                        waste_kg=excluded.waste_kg, waste_per_person=excluded.waste_per_person,
                        waste_rate=excluded.waste_rate, grade=excluded.grade, created_at=excluded.created_at
                """, (site_name, year_month, r["meal_date"], r["menu_items"],
                      float(r["waste_kg"]), float(r["waste_per_person"]),
                      float(r["waste_rate"]), r["grade"], "", now))
            except Exception as e:
                print(f"[DB ERROR] meal_analyze_waste: {e}")
                logger.warning(f'Exception caught: {str(e)}')
                pass
        conn.commit()
        return results
    except Exception as e:
        print(f"[DB ERROR] meal_analyze_waste: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def meal_get_analysis_summary(analysis: list[dict]) -> dict:
    """잔반 분석 결과 요약 통계"""
    if not analysis:
        return {
            "avg_servings": "0", "total_waste": "0", "avg_waste_pp": "0",
            "matched_days": "0", "total_days": "0",
            "grade_a": "0", "grade_b": "0", "grade_c": "0", "grade_d": "0",
            "school_level": "",
        }
    total_servings = 0
    total_waste = 0.0
    total_pp = 0.0
    matched = 0
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "-": 0}
    for r in analysis:
        s = int(r.get("servings", 0) or 0)
        w = float(r.get("waste_kg", 0) or 0)
        pp = float(r.get("waste_per_person", 0) or 0)
        g = r.get("grade", "-")
        total_servings += s
        total_waste += w
        total_pp += pp
        if g in grades:
            grades[g] += 1
        if w > 0:
            matched += 1

    n = len(analysis)
    return {
        "avg_servings": str(round(total_servings / n)) if n > 0 else "0",
        "total_waste": str(round(total_waste, 1)),
        "avg_waste_pp": str(round(total_pp / n, 1)) if n > 0 else "0",
        "matched_days": str(matched),
        "total_days": str(n),
        "grade_a": str(grades.get("A", 0)),
        "grade_b": str(grades.get("B", 0)),
        "grade_c": str(grades.get("C", 0)),
        "grade_d": str(grades.get("D", 0)),
    }


def meal_get_menu_ranking(analysis: list[dict]) -> tuple[list[dict], list[dict]]:
    """메뉴별 잔반량 랭킹 (추천/개선)"""
    from collections import defaultdict
    stats = defaultdict(lambda: {"total_pp": 0.0, "count": 0})
    for r in analysis:
        pp = float(r.get("waste_per_person", 0) or 0)
        if pp <= 0:
            continue
        menu = r.get("menu_items", "")
        stats[menu]["total_pp"] += pp
        stats[menu]["count"] += 1

    ranking = []
    for menu, v in stats.items():
        avg = round(v["total_pp"] / v["count"], 1) if v["count"] > 0 else 0
        ranking.append({
            "menu": menu[:60],
            "avg_waste_pp": str(avg),
            "count": str(v["count"]),
        })

    ranking.sort(key=lambda x: float(x["avg_waste_pp"]))
    best = ranking[:10]
    worst = list(reversed(ranking[-10:])) if len(ranking) > 10 else list(reversed(ranking))
    return best, worst


def meal_get_weekday_pattern(analysis: list[dict]) -> list[dict]:
    """요일별 잔반 패턴"""
    from datetime import datetime as _dt
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    buckets = {i: {"kg": 0.0, "pp": 0.0, "cnt": 0} for i in range(7)}

    for r in analysis:
        try:
            dt = _dt.strptime(r.get("meal_date", ""), "%Y-%m-%d")
            wd = dt.weekday()
        except Exception as e:
            print(f"[DB ERROR] meal_get_weekday_pattern: {e}")
            logger.warning(f'Exception in loop: {str(e)}')
            continue
        w = float(r.get("waste_kg", 0) or 0)
        pp = float(r.get("waste_per_person", 0) or 0)
        if w > 0:
            buckets[wd]["kg"] += w
            buckets[wd]["pp"] += pp
            buckets[wd]["cnt"] += 1

    result = []
    for i in range(7):
        b = buckets[i]
        n = b["cnt"]
        result.append({
            "weekday": weekday_names[i],
            "avg_kg": str(round(b["kg"] / n, 1)) if n > 0 else "0",
            "avg_pp": str(round(b["pp"] / n, 1)) if n > 0 else "0",
            "count": str(n),
        })
    return result


def meal_get_cost_savings(site_name: str, analysis: list[dict]) -> dict:
    """비용 절감 분석"""
    conn = get_db()
    try:
        # 단가 조회
        rows = conn.execute(
            "SELECT price_food FROM customer_info WHERE name = ?", (site_name,)
        ).fetchall()
        unit_price = float(rows[0][0]) if rows else 0
        if unit_price == 0:
            # fallback
            rows = conn.execute(
                "SELECT price_food FROM customer_info WHERE name LIKE ?", (f"%{site_name}%",)
            ).fetchall()
            unit_price = float(rows[0][0]) if rows else 50

        total_waste = sum(float(r.get("waste_kg", 0) or 0) for r in analysis)
        current_cost = int(total_waste * unit_price)
        save_10pct = int(total_waste * WASTE_REDUCTION_RATE * unit_price)

        return {
            "unit_price": str(int(unit_price)),
            "total_waste_kg": str(round(total_waste, 1)),
            "current_cost": str(current_cost),
            "save_10pct": str(save_10pct),
            "annual_save": str(save_10pct * 12),
        }
    except Exception as e:
        print(f"[DB ERROR] meal_get_cost_savings: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {
            "unit_price": "0", "total_waste_kg": "0",
            "current_cost": "0", "save_10pct": "0", "annual_save": "0",
        }
    finally:
        conn.close()


def meal_get_settlement(site_name: str, year: int, month: int) -> dict:
    """급식담당자 정산 확인 (school_get_settlement 래퍼)"""
    return school_get_settlement(site_name, year, month)


def meal_get_esg(site_name: str, year: int, month: int = 0) -> dict:
    """급식담당자 ESG 보고서 (school_get_esg 래퍼)"""
    return school_get_esg(site_name, year, month)


def save_meal_schedule_drafts(site_name: str, dates: list) -> int:
    """급식담당자 식단 저장 시 수거일정 초안 자동생성

    customer_info에서 vendor 조회 후 schedules 테이블에 draft INSERT.
    중복(vendor+month+schools 기준) 체크 후 삽입.
    Returns: 삽입된 건수
    """
    if not site_name or not dates:
        return 0
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT vendor FROM customer_info WHERE name = ? LIMIT 1", (site_name,)
        ).fetchone()
        if not row:
            return 0
        vendor = str(dict(row).get("vendor", "") or "")
        if not vendor:
            return 0
        schools_json = json.dumps([site_name], ensure_ascii=False)
        count = 0
        for date_str in dates:
            if not date_str:
                continue
            # 중복 체크
            existing = conn.execute(
                "SELECT id FROM schedules WHERE vendor=? AND month=? AND schools=? LIMIT 1",
                (vendor, date_str, schools_json),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                "INSERT INTO schedules (vendor, month, weekdays, schools, items, driver, registered_by) "
                "VALUES (?,?,?,?,?,?,?)",
                (vendor, date_str, json.dumps(["급식"]), schools_json,
                 json.dumps(["음식물"]), "", "meal_draft"),
            )
            count += 1
        conn.commit()
        return count
    except Exception as e:
        logger.warning(f"save_meal_schedule_drafts: {e}")
        return 0
    finally:
        conn.close()


# ══════════════════════════════════════════
#  섹션 3: 거래처 음성 별칭 관리
#  customer_info.voice_aliases TEXT (comma-separated) — idempotent ADD COLUMN
# ══════════════════════════════════════════

def _ensure_voice_aliases_col(conn) -> None:
    """customer_info 테이블에 voice_aliases 컬럼이 없으면 추가 (idempotent)"""
    try:
        conn.execute(
            "ALTER TABLE customer_info ADD COLUMN voice_aliases TEXT DEFAULT ''"
        )
        conn.commit()
    except Exception:
        pass  # 이미 존재하면 무시


def get_customer_aliases(vendor: str, customer_name: str) -> list:
    """거래처의 음성 별칭 목록 반환 (빈 문자열 제거)"""
    conn = get_db()
    try:
        _ensure_voice_aliases_col(conn)
        row = conn.execute(
            "SELECT voice_aliases FROM customer_info WHERE vendor=? AND name=?",
            (vendor, customer_name),
        ).fetchone()
        if not row:
            return []
        raw = str(dict(row).get("voice_aliases", "") or "")
        return [a.strip() for a in raw.split(",") if a.strip()]
    except Exception as e:
        logger.warning(f"get_customer_aliases: {e}")
        return []
    finally:
        conn.close()


def add_customer_alias(vendor: str, customer_name: str, alias: str) -> bool:
    """거래처 음성 별칭 추가 (중복 무시)"""
    alias = alias.strip()
    if not alias:
        return False
    conn = get_db()
    try:
        _ensure_voice_aliases_col(conn)
        row = conn.execute(
            "SELECT voice_aliases FROM customer_info WHERE vendor=? AND name=?",
            (vendor, customer_name),
        ).fetchone()
        if not row:
            return False
        raw = str(dict(row).get("voice_aliases", "") or "")
        existing = [a.strip() for a in raw.split(",") if a.strip()]
        if alias in existing:
            return True  # 이미 존재
        existing.append(alias)
        new_val = ",".join(existing)
        conn.execute(
            "UPDATE customer_info SET voice_aliases=? WHERE vendor=? AND name=?",
            (new_val, vendor, customer_name),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"add_customer_alias: {e}")
        return False
    finally:
        conn.close()


def remove_customer_alias(vendor: str, customer_name: str, alias: str) -> bool:
    """거래처 음성 별칭 제거"""
    alias = alias.strip()
    conn = get_db()
    try:
        _ensure_voice_aliases_col(conn)
        row = conn.execute(
            "SELECT voice_aliases FROM customer_info WHERE vendor=? AND name=?",
            (vendor, customer_name),
        ).fetchone()
        if not row:
            return False
        raw = str(dict(row).get("voice_aliases", "") or "")
        existing = [a.strip() for a in raw.split(",") if a.strip()]
        updated = [a for a in existing if a != alias]
        conn.execute(
            "UPDATE customer_info SET voice_aliases=? WHERE vendor=? AND name=?",
            (",".join(updated), vendor, customer_name),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.warning(f"remove_customer_alias: {e}")
        return False
    finally:
        conn.close()


def get_all_customer_aliases(vendor: str) -> dict:
    """vendor 거래처 전체의 음성 별칭 맵 반환.
    반환: {customer_name: [alias1, alias2, ...], ...}
    """
    conn = get_db()
    try:
        _ensure_voice_aliases_col(conn)
        rows = conn.execute(
            "SELECT name, voice_aliases FROM customer_info WHERE vendor=?",
            (vendor,),
        ).fetchall()
        result: dict = {}
        for r in rows:
            d = dict(r)
            name = str(d.get("name", "") or "")
            if not name:
                continue
            raw = str(d.get("voice_aliases", "") or "")
            aliases = [a.strip() for a in raw.split(",") if a.strip()]
            result[name] = aliases
        return result
    except Exception as e:
        logger.warning(f"get_all_customer_aliases: {e}")
        return {}
    finally:
        conn.close()


# ══════════════════════════════════════════
#  섹션 6: GPS 기반 가장 가까운 거래처 조회
# ══════════════════════════════════════════

def get_nearest_customer(
    vendor: str,
    lat: float,
    lng: float,
    max_distance_m: int = 200,
    schedule_names: list = None,
) -> dict:
    """현재 GPS 좌표에서 가장 가까운 거래처를 반환.

    - schedule_names 가 지정되면 해당 거래처 중에서만 탐색 (오늘 일정 우선)
    - max_distance_m 이내에 없으면 None 반환
    - 반환 dict: {"name": str, "distance_m": float}
    """
    customers = get_customers_with_gps(vendor)
    if not customers:
        return None

    # 오늘 일정 필터
    if schedule_names:
        sched_set = set(schedule_names)
        pool = [c for c in customers if c["name"] in sched_set]
        if not pool:
            pool = customers  # fallback: 전체
    else:
        pool = customers

    best = None
    best_dist = float("inf")

    for c in pool:
        try:
            dist = haversine(lat, lng, c["lat"], c["lng"])
        except Exception:
            continue
        if dist < best_dist:
            best_dist = dist
            best = c

    if best is None or best_dist > max_distance_m:
        return None

    return {"name": best["name"], "distance_m": round(best_dist, 1)}


def get_nearby_customers(
    vendor: str,
    lat: float,
    lng: float,
    max_distance_m: int = 500,
    schedule_names: list = None,
    limit: int = 10,
) -> list[dict]:
    """현재 GPS 좌표에서 반경 내 거래처를 거리 오름차순으로 반환.

    - schedule_names 지정 시 해당 거래처 중에서만 탐색, 없으면 전체로 fallback
    - max_distance_m 초과 항목 제외
    - 반환 리스트: [{"name": str, "distance_m": float}, ...]
    """
    customers = get_customers_with_gps(vendor)
    if not customers:
        return []

    if schedule_names:
        sched_set = set(schedule_names)
        pool = [c for c in customers if c["name"] in sched_set]
        if not pool:
            pool = customers
    else:
        pool = customers

    candidates = []
    for c in pool:
        try:
            dist = haversine(lat, lng, c["lat"], c["lng"])
        except Exception:
            continue
        if dist <= max_distance_m:
            candidates.append({"name": c["name"], "distance_m": round(dist, 1)})

    candidates.sort(key=lambda x: x["distance_m"])
    return candidates[:limit]
