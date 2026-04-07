# zeroda_reflex/utils/database.py
# 기존 zeroda Streamlit 앱의 DB를 공유하는 유틸리티
# GitHub JSON API + SQLite 이중 구조 유지

import json
import sqlite3
import os
import hashlib
import hmac
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── DB 경로 (서버 배포 시 환경변수로 오버라이드) ──
DB_PATH = os.environ.get("ZERODA_DB_PATH", "zeroda.db")

# ══════════════════════════════════════════
#  Phase 1-6: 매직넘버 상수화
#  - 하드코딩된 숫자를 상수로 관리하여 유지보수성 향상
# ══════════════════════════════════════════
VAT_RATE = 0.1                   # 부가가치세 세율 (10%)
CARBON_FOOD = 0.47               # 음식물 1kg당 탄소감축 계수 (kg CO₂)
CARBON_RECYCLE = 0.21            # 재활용 1kg당 탄소감축 계수 (kg CO₂)
CARBON_GENERAL = 0.09            # 일반폐기물 1kg당 탄소감축 계수 (kg CO₂)
WASTE_REDUCTION_RATE = 0.1       # 잔반감축 목표 비율 (10%)


def get_db():
    """SQLite 연결 반환"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def db_get(table: str, where: dict = None) -> list[dict]:
    """테이블에서 조건에 맞는 행 조회"""
    conn = get_db()
    try:
        if where:
            clauses = " AND ".join(f"{k} = ?" for k in where)
            values = list(where.values())
            rows = conn.execute(
                f"SELECT * FROM {table} WHERE {clauses}", values
            ).fetchall()
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
    """행 삽입 또는 업데이트"""
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


# ── 인증 관련 ──

def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 우선 검증, SHA256 폴백 (기존 계정 호환)"""
    if not plain or not hashed:
        return False
    if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
        import bcrypt
        try:
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        except Exception as e:
            print(f"[DB ERROR] verify_password: {e}")
            logger.warning(f'Exception in database operation: {str(e)}')
            return False
    if hashlib.sha256(plain.strip().encode()).hexdigest() == hashed.strip():
        return True
    if plain.strip() == hashed.strip():
        return True
    return False


def authenticate_user(user_id: str, password: str) -> Optional[dict]:
    """사용자 인증. 성공 시 user dict 반환, 실패 시 None"""
    rows = db_get("users", {"user_id": user_id})
    if not rows:
        return None
    user = rows[0]
    # 승인 상태 확인
    if user.get("approval_status") == "pending":
        return None
    if user.get("approval_status") == "rejected":
        return None
    if int(user.get("is_active", 1)) == 0:
        return None
    if not verify_password(password, user.get("pw_hash", "")):
        return None
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

            conn.execute(
                f"INSERT OR REPLACE INTO daily_safety_check ({cols}) VALUES ({placeholders})",
                values,
            )

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
            "SELECT rowid, * FROM real_collection WHERE vendor=? AND driver=? AND collect_date=? ORDER BY created_at DESC",
            (vendor, driver, collect_date),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[DB ERROR] get_today_collections: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return []
    finally:
        conn.close()


def ensure_real_collection_gps_columns() -> None:
    """real_collection 테이블에 lat/lng 컨럼 추가 (idempotent — 이미 있으면 무시)"""
    conn = get_db()
    for col in ("lat REAL", "lng REAL"):
        try:
            conn.execute(f"ALTER TABLE real_collection ADD COLUMN {col}")
            conn.commit()
        except Exception as e:
            # 이미 컨럼이 존재하면 무시
            print(f"[DB ERROR] ensure_real_collection_gps_columns ({col}): {e}")
            logger.warning(f"GPS 컨럼 추가 (idempotent): {e}")
    conn.close()


# GPS 컨럼 보장 (모듈 임포트 시 1회 실행)
try:
    ensure_real_collection_gps_columns()
except Exception as _gps_col_err:
    print(f"[DB ERROR] GPS 컨럼 초기화 실패: {_gps_col_err}")


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
    """수거 기록 삭제 (rowid 기반)"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM real_collection WHERE rowid = ?", (rowid,))
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
            "SELECT rowid, * FROM processing_confirm "
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
) -> bool:
    """계근표 처리확인 저장"""
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
    })


# ── GPS 위치 저장 ──

def save_customer_gps(vendor: str, name: str, lat: float, lng: float) -> bool:
    """거래처 GPS 좌표 업데이트"""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE customer_info SET latitude=?, longitude=? WHERE vendor=? AND name=?",
            (lat, lng, vendor, name),
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] save_customer_gps: {e}")
        logger.warning(f"save_customer_gps error: {e}")
        return False
    finally:
        conn.close()


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
                "SELECT * FROM customer_info WHERE vendor=? AND (구분=? OR cust_type=?) ORDER BY name",
                (vendor, cust_type, cust_type),
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
            result.append({
                "name":          str(d.get("name", "")),
                "cust_type":     str(d.get("구분", d.get("cust_type", "학교")) or "학교"),
                "biz_no":        str(d.get("사업자번호", "") or ""),
                "ceo":           str(d.get("대표자", "") or ""),
                "address":       str(d.get("주소", d.get("address", "")) or ""),
                "biz_type":      str(d.get("업태", "") or ""),
                "biz_item":      str(d.get("종목", "") or ""),
                "email":         str(d.get("이메일", d.get("email", "")) or ""),
                "phone":         str(d.get("전화번호", d.get("phone", "")) or ""),
                "recycler":      str(d.get("재활용자", "") or ""),
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

        cols = {
            "name":              name,
            "vendor":            vendor,
            "구분":              str(data.get("cust_type", "학교")),
            "사업자번호":        str(data.get("biz_no", "") or ""),
            "대표자":            str(data.get("ceo", "") or ""),
            "주소":              str(data.get("address", "") or ""),
            "업태":              str(data.get("biz_type", "") or ""),
            "종목":              str(data.get("biz_item", "") or ""),
            "이메일":            str(data.get("email", "") or ""),
            "전화번호":          str(data.get("phone", "") or ""),
            "재활용자":          str(data.get("recycler", "") or ""),
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
            set_clause = ", ".join(f"{k}=?" for k in cols if k not in ("name", "vendor"))
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
    """거래처 상세 정보 — customer_info 전 컬럼, 키 정규화"""
    rows = db_get("customer_info", {"vendor": vendor})
    result = []
    for r in rows:
        if not r.get("name"):
            continue
        pf = r.get("price_food", 0) or 0
        pr = r.get("price_recycle", 0) or 0
        pg = r.get("price_general", 0) or 0
        result.append({
            "name":         str(r.get("name", "")),
            "cust_type":    str(r.get("cust_type", r.get("type", "학교")) or "학교"),
            "phone":        str(r.get("phone", r.get("전화번호", "")) or ""),
            "address":      str(r.get("address", r.get("주소", "")) or ""),
            "email":        str(r.get("email", r.get("이메일", "")) or ""),
            "price_food":   str(int(float(pf))),
            "price_recycle": str(int(float(pr))),
            "price_general": str(int(float(pg))),
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
    """차량 안전점검 이력 조회"""
    rows = db_get("safety_checklist", {"vendor": vendor})
    result = []
    for r in rows:
        result.append({
            "check_date":  str(r.get("check_date", "") or ""),
            "driver":      str(r.get("driver", "") or ""),
            "vehicle_no":  str(r.get("vehicle_no", "") or ""),
            "total_ok":    str(r.get("total_ok", 0) or 0),
            "total_fail":  str(r.get("total_fail", 0) or 0),
            "inspector":   str(r.get("inspector", "") or ""),
            "memo":        str(r.get("memo", "") or ""),
        })
    return sorted(result, key=lambda x: x["check_date"], reverse=True)


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
    """업체 기본 정보 조회 (vendor_info 테이블)"""
    rows = db_get("vendor_info", {"vendor": vendor})
    if not rows:
        return {
            "biz_name": str(vendor),
            "rep": "", "biz_no": "", "address": "", "contact": "",
        }
    r = rows[0]
    return {
        "biz_name": str(r.get("biz_name", vendor) or vendor),
        "rep":      str(r.get("rep", "") or ""),
        "biz_no":   str(r.get("biz_no", "") or ""),
        "address":  str(r.get("address", "") or ""),
        "contact":  str(r.get("contact", "") or ""),
    }


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
    # 추가 필드 (컬럼 없으면 무시)
    conn = get_db()
    try:
        for col in ("email", "account"):
            val = str(data.get(col, "") or "")
            if val:
                conn.execute(
                    f"UPDATE vendor_info SET {col}=? WHERE vendor=?",
                    (val, str(data.get("vendor", ""))),
                )
        conn.commit()
    except Exception as e:
        print(f"[DB ERROR] save_vendor_info: {e}")
        logger.warning(f'Exception caught: {str(e)}')
        pass
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
                "check_date": str(d.get("check_date", "") or ""),
                "driver":     str(d.get("driver", "") or ""),
                "category":   str(d.get("category", "") or ""),
                "total_ok":   str(ok),
                "total_fail": str(fail),
                "fail_memo":  str(d.get("fail_memo", "") or ""),
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

        return {
            "vendors": vendors,
            "scores": scores,
            "violations": violations,
            "education": edu_rows,
        }
    except Exception as e:
        print(f"[DB ERROR] school_get_safety_report: {e}")
        logger.warning(f'Exception in database operation: {str(e)}')
        return {"vendors": [], "scores": [], "violations": [], "education": []}
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
