# zeroda_reflex/utils/neis_sync_service.py
# NEIS 학사일정 동기화 서비스
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def sync_school_schedule_for_school(
    school_name: str,
    neis_edu_code: str,
    neis_school_code: str,
    year: int | None = None,
) -> dict:
    """단일 학교의 학사일정을 NEIS에서 가져와 DB에 저장.

    Returns:
        {'success': bool, 'school_name': str, 'events': int, 'message': str}
    """
    from zeroda_reflex.utils.neis_api import fetch_school_schedule
    from zeroda_reflex.utils.database import get_db

    if not neis_edu_code or not neis_school_code:
        return {"success": False, "school_name": school_name, "events": 0,
                "message": "NEIS 코드 누락"}

    if year is None:
        year = datetime.now().year

    from_ymd = f"{year}0101"
    to_ymd = f"{year}1231"

    rows = fetch_school_schedule(neis_edu_code, neis_school_code, from_ymd, to_ymd)
    if not rows:
        return {"success": True, "school_name": school_name, "events": 0,
                "message": "학사일정 없음 (API 응답 0건)"}

    try:
        conn = get_db()
        cur = conn.cursor()
        # 해당 학교·연도 기존 데이터 삭제 후 재삽입
        cur.execute(
            "DELETE FROM school_academic_schedule WHERE school_name = ? AND strftime('%Y', sched_date) = ?",
            (school_name, str(year)),
        )
        inserted = 0
        for r in rows:
            cur.execute(
                """INSERT OR IGNORE INTO school_academic_schedule
                   (school_name, sched_date, event_name, event_type, content)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    school_name,
                    r["sched_date"],
                    r["event_name"],
                    r["event_type"],
                    r["content"],
                ),
            )
            inserted += cur.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "school_name": school_name, "events": inserted,
                "message": f"{inserted}건 저장"}
    except Exception as e:
        logger.error(f"[neis_sync] {school_name} DB 저장 실패: {e}", exc_info=True)
        return {"success": False, "school_name": school_name, "events": 0,
                "message": str(e)}


def sync_all_schools(vendor: str | None = None, year: int | None = None) -> dict:
    """모든 학교(또는 특정 업체 소속 학교)의 학사일정 일괄 동기화.

    Args:
        vendor: 업체명 필터 (None이면 전체)
        year: 동기화 연도 (None이면 현재 연도)

    Returns:
        {'total_schools': int, 'success': int, 'failed': int, 'events': int, 'details': list}
    """
    from zeroda_reflex.utils.database import get_db

    conn = get_db()
    cur = conn.cursor()
    if vendor:
        cur.execute(
            """SELECT DISTINCT name, neis_edu_code, neis_school_code
               FROM customer_info
               WHERE vendor = ? AND neis_edu_code IS NOT NULL AND neis_school_code IS NOT NULL""",
            (vendor,),
        )
    else:
        cur.execute(
            """SELECT DISTINCT name, neis_edu_code, neis_school_code
               FROM customer_info
               WHERE neis_edu_code IS NOT NULL AND neis_school_code IS NOT NULL"""
        )
    schools = cur.fetchall()
    conn.close()

    stats = {"total_schools": len(schools), "success": 0, "failed": 0, "events": 0, "details": []}
    for row in schools:
        school_name = row["name"] if "name" in row.keys() else row[0]
        neis_edu = row["neis_edu_code"] if "neis_edu_code" in row.keys() else row[1]
        neis_sch = row["neis_school_code"] if "neis_school_code" in row.keys() else row[2]
        result = sync_school_schedule_for_school(school_name, neis_edu, neis_sch, year)
        stats["details"].append(result)
        if result["success"]:
            stats["success"] += 1
            stats["events"] += result["events"]
        else:
            stats["failed"] += 1
    return stats


def get_school_schedule(school_name: str, year: int | None = None, month: int | None = None) -> list[dict]:
    """DB에서 학교 학사일정 조회.

    Args:
        school_name: 학교명
        year: 연도 필터 (None이면 전체)
        month: 월 필터 (None이면 전체)

    Returns:
        [{'sched_date': 'YYYY-MM-DD', 'event_name': str, 'event_type': str, 'content': str}, ...]
    """
    from zeroda_reflex.utils.database import get_db

    conn = get_db()
    cur = conn.cursor()
    if year and month:
        ym = f"{year}-{str(month).zfill(2)}"
        cur.execute(
            """SELECT sched_date, event_name, event_type, content
               FROM school_academic_schedule
               WHERE school_name = ? AND strftime('%Y-%m', sched_date) = ?
               ORDER BY sched_date""",
            (school_name, ym),
        )
    elif year:
        cur.execute(
            """SELECT sched_date, event_name, event_type, content
               FROM school_academic_schedule
               WHERE school_name = ? AND strftime('%Y', sched_date) = ?
               ORDER BY sched_date""",
            (school_name, str(year)),
        )
    else:
        cur.execute(
            """SELECT sched_date, event_name, event_type, content
               FROM school_academic_schedule
               WHERE school_name = ?
               ORDER BY sched_date""",
            (school_name,),
        )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "sched_date": r["sched_date"] or r[0],
            "event_name": r["event_name"] or r[1] or "",
            "event_type": r["event_type"] or r[2] or "",
            "content": r["content"] or r[3] or "",
        }
        for r in rows
    ]
