# pages/99_migration.py
# ⚠️ 데이터 이전 완료 후 이 파일을 GitHub에서 삭제하세요
# GitHub JSON → Supabase 일괄 이전 도구 (관리자 전용)

import streamlit as st
import json
import os
import urllib.request
import urllib.parse
import urllib.error

st.set_page_config(page_title="데이터 이전 | ZERODA", page_icon="🔄", layout="wide")

# ── 설정 ───────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

MIGRATE_FILES = [
    ('vendor_info',      'vendor_info.json',      '업체 정보',   '(vendor)'),
    ('users',            'users.json',             '계정',        '(user_id)'),
    ('school_master',    'school_master.json',     '학교 마스터', '(school_name)'),
    ('customer_info',    'customer_info.json',     '거래처',      '(vendor, name)'),
    ('schedules',        'schedules.json',         '수거일정',    None),
    ('real_collection',  'real_collection.json',   '수거기록',    None),
    ('sim_collection',   'sim_collection.json',    '시뮬레이션',  None),
    ('safety_education', 'safety_education.json',  '안전교육',    None),
    ('safety_checklist', 'safety_checklist.json',  '안전점검',    None),
    ('accident_report',  'accident_report.json',   '사고신고',    None),
    ('carbon_reduction', 'carbon_reduction.json',  '탄소감축',    None),
    ('processing_confirm','processing_confirm.json','처리확인',   None),
    ('meal_menus',       'meal_menus.json',        '급식식단',    '(site_name, meal_date, meal_type)'),
    ('meal_analysis',    'meal_analysis.json',     '잔반분석',    '(site_name, meal_date)'),
]


# ── Supabase 연결 ───────────────────────────────────────────────────────────
def get_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "").rstrip('/')
        key = st.secrets.get("SUPABASE_KEY", "")
        return url, key
    except Exception:
        return "", ""


def sb_headers(key, prefer=None):
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def normalize_rows(rows):
    """
    모든 행의 키를 통일.
    Supabase bulk POST는 모든 행이 동일한 키 집합을 가져야 함.
    누락된 키는 None 으로 채움.
    """
    # id 제거 (Supabase BIGSERIAL 자동생성)
    clean = [{k: v for k, v in row.items() if k != 'id'} for row in rows]
    # 전체 키 집합
    all_keys = set()
    for row in clean:
        all_keys.update(row.keys())
    # 정렬된 키 순서로 통일
    sorted_keys = sorted(all_keys)
    return [{k: row.get(k) for k in sorted_keys} for row in clean]


def migrate_table(url, key, table, rows, conflict_expr):
    """테이블 데이터를 Supabase에 일괄 삽입"""
    if not rows:
        return 0, 0, "⏭️ 데이터 없음 (건너뜀)"

    # ── 키 통일 (All object keys must match 오류 방지) ──
    unified_rows = normalize_rows(rows)

    endpoint = f"{url}/rest/v1/{table}"
    if conflict_expr:
        # "(vendor, name)" → "vendor,name" 형식으로 변환
        cols_raw = conflict_expr.strip('()').replace(' ', '')
        endpoint += f"?on_conflict={urllib.parse.quote(cols_raw)}"
        prefer = "resolution=merge-duplicates,return=minimal"
    else:
        prefer = "return=minimal"

    payload = json.dumps(unified_rows, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers=sb_headers(key, prefer=prefer),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return len(rows), 0, f"✅ {len(rows)}행 이전 완료"
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        err_info = ""
        try:
            err_json = json.loads(body)
            err_info = err_json.get("message", body[:300])
        except Exception:
            err_info = body[:300]

        # 스키마 캐시 오류 (컬럼 없음) → 행별 재시도
        if "schema cache" in err_info or "All object keys" in err_info:
            return migrate_row_by_row(url, key, table, unified_rows, conflict_expr, err_info)

        return 0, len(rows), f"❌ HTTP {e.code}: {err_info}"
    except Exception as e:
        return 0, len(rows), f"❌ 오류: {type(e).__name__}: {e}"


def migrate_row_by_row(url, key, table, unified_rows, conflict_expr, original_err):
    """
    bulk insert 실패 시 행별로 시도.
    스키마에 없는 컬럼이 포함된 행만 건너뜀.
    """
    success = 0
    fail = 0
    last_err = original_err

    endpoint = f"{url}/rest/v1/{table}"
    if conflict_expr:
        cols_raw = conflict_expr.strip('()').replace(' ', '')
        endpoint += f"?on_conflict={urllib.parse.quote(cols_raw)}"
        prefer = "resolution=merge-duplicates,return=minimal"
    else:
        prefer = "return=minimal"

    for row in unified_rows:
        payload = json.dumps([row], ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers=sb_headers(key, prefer=prefer),
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                success += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')
            try:
                err_json = json.loads(body)
                last_err = err_json.get("message", body[:200])
            except Exception:
                last_err = body[:200]
            fail += 1
        except Exception as ex:
            last_err = str(ex)
            fail += 1

    if fail == 0:
        return success, 0, f"✅ {success}행 이전 완료 (행별 처리)"
    else:
        return success, fail, f"⚠️ {success}성공/{fail}실패 — 마지막 오류: {last_err}"


# ── UI ─────────────────────────────────────────────────────────────────────
st.title("🔄 GitHub JSON → Supabase 데이터 이전")
st.caption("⚠️ 이전 완료 후 이 페이지(pages/99_migration.py)를 GitHub에서 삭제하세요.")

supabase_url, supabase_key = get_supabase()

col1, col2 = st.columns(2)
with col1:
    if supabase_url and supabase_key:
        st.success(f"✅ Supabase 연결됨: `{supabase_url}`")
    else:
        st.error("❌ Supabase 미연결 — Streamlit Secrets 확인 필요")
        st.stop()
with col2:
    st.info(f"📂 data 폴더: `{os.path.abspath(DATA_DIR)}`")

# ── 누락 컬럼 추가 SQL 안내 ─────────────────────────────────────────────────
with st.expander("⚠️ 먼저 실행: Supabase에서 누락 컬럼 추가 SQL", expanded=True):
    st.warning("아래 SQL을 Supabase SQL Editor에서 먼저 실행하세요. 이미 실행했다면 건너뛰어도 됩니다.")
    st.code("""
-- vendor_info 누락 컬럼 추가
ALTER TABLE vendor_info ADD COLUMN IF NOT EXISTS address TEXT DEFAULT '';
ALTER TABLE vendor_info ADD COLUMN IF NOT EXISTS biz_name TEXT DEFAULT '';
ALTER TABLE vendor_info ADD COLUMN IF NOT EXISTS rep TEXT DEFAULT '';
ALTER TABLE vendor_info ADD COLUMN IF NOT EXISTS biz_no TEXT DEFAULT '';
ALTER TABLE vendor_info ADD COLUMN IF NOT EXISTS contact TEXT DEFAULT '';
ALTER TABLE vendor_info ADD COLUMN IF NOT EXISTS email TEXT DEFAULT '';

-- schedules 누락 컬럼 추가
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS registered_by TEXT DEFAULT 'admin';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS weekdays TEXT DEFAULT '[]';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS schools TEXT DEFAULT '[]';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS items TEXT DEFAULT '[]';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS driver TEXT DEFAULT '';

-- users 누락 컬럼 추가
ALTER TABLE users ADD COLUMN IF NOT EXISTS schools TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS edu_office TEXT DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TEXT;

-- customer_info 누락 컬럼 추가
ALTER TABLE customer_info ADD COLUMN IF NOT EXISTS phone TEXT DEFAULT '';
ALTER TABLE customer_info ADD COLUMN IF NOT EXISTS recycler TEXT DEFAULT '';
ALTER TABLE customer_info ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION DEFAULT 0;
ALTER TABLE customer_info ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION DEFAULT 0;

-- real_collection 누락 컬럼 추가
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS collect_time TEXT DEFAULT '';
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "날짜" TEXT;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "학교명" TEXT;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "음식물(kg)" DOUBLE PRECISION DEFAULT 0;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "단가(원)" DOUBLE PRECISION DEFAULT 0;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "공급가" DOUBLE PRECISION DEFAULT 0;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "재활용방법" TEXT DEFAULT '';
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "재활용업체" TEXT DEFAULT '';
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "월" INTEGER;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "년도" INTEGER;
ALTER TABLE real_collection ADD COLUMN IF NOT EXISTS "월별파일" TEXT DEFAULT '';

-- Supabase 스키마 캐시 새로고침
NOTIFY pgrst, 'reload schema';
""", language="sql")

st.divider()

# ── 이전 대상 미리보기 ─────────────────────────────────────────────────────
st.subheader("📋 이전 대상 데이터")
import pandas as pd

preview = []
for table, filename, label, conflict in MIGRATE_FILES:
    fp = os.path.join(DATA_DIR, filename)
    if os.path.exists(fp):
        try:
            data = json.load(open(fp, encoding='utf-8'))
            cnt = len(data) if isinstance(data, list) else 0
        except Exception:
            cnt = 0
        preview.append({"테이블": table, "설명": label, "행 수": f"{cnt}행", "상태": "✅ 파일 있음"})
    else:
        preview.append({"테이블": table, "설명": label, "행 수": "-", "상태": "⏭️ 파일 없음"})

st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

st.divider()

# ── 이전 실행 ──────────────────────────────────────────────────────────────
st.subheader("🚀 이전 실행")
st.warning("버튼 클릭 시 data/*.json → Supabase로 업로드됩니다. ON CONFLICT DO NOTHING으로 기존 데이터 보호됩니다.")

if st.button("▶ 데이터 이전 시작", type="primary", use_container_width=True):
    total_ok = 0
    total_fail = 0
    progress = st.progress(0)

    for i, (table, filename, label, conflict) in enumerate(MIGRATE_FILES):
        progress.progress((i + 1) / len(MIGRATE_FILES))
        fp = os.path.join(DATA_DIR, filename)

        if not os.path.exists(fp):
            st.info(f"⏭️ **{label}** (`{table}`) — 파일 없음, 건너뜀")
            continue

        try:
            rows = json.load(open(fp, encoding='utf-8'))
        except Exception as e:
            st.error(f"❌ **{label}** (`{table}`) — JSON 읽기 실패: {e}")
            continue

        if not isinstance(rows, list) or len(rows) == 0:
            st.info(f"⏭️ **{label}** (`{table}`) — 데이터 없음, 건너뜀")
            continue

        with st.spinner(f"{label} ({len(rows)}행) 이전 중..."):
            ok, fail, msg = migrate_table(supabase_url, supabase_key, table, rows, conflict)
            total_ok += ok
            total_fail += fail

        st.write(f"**{label}** (`{table}`): {msg}")

    progress.progress(1.0)
    st.divider()

    if total_fail == 0:
        st.success(f"🎉 이전 완료! 총 **{total_ok}행** 성공")
        st.balloons()
        st.info("👉 Supabase Table Editor에서 데이터 확인 후, 이 파일(pages/99_migration.py)을 GitHub에서 삭제하세요.")
    else:
        st.warning(f"⚠️ 부분 완료: 성공 {total_ok}행 / 실패 {total_fail}행")
        st.info("위 '누락 컬럼 추가 SQL'을 Supabase에서 실행한 뒤 다시 시도하세요.")

st.divider()
st.caption("zeroda 플랫폼 | 데이터 이전 도구 | 사용 후 삭제 권장")
