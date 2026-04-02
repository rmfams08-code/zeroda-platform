# pages/99_migration.py
# ⚠️ 데이터 이전 완료 후 이 파일을 GitHub에서 삭제하세요
# GitHub JSON → Supabase 일괄 이전 도구

import streamlit as st
import json
import os
import urllib.request
import urllib.parse
import urllib.error

st.set_page_config(page_title="데이터 이전 | ZERODA", page_icon="🔄", layout="wide")

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


# ── Supabase 헬퍼 ───────────────────────────────────────────────────────────
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


def get_table_columns(url, key, table):
    """
    Supabase 테이블의 실제 컬럼 목록 조회.
    information_schema.columns를 RPC로 쿼리.
    실패 시 빈 set 반환 (컬럼 필터링 건너뜀).
    """
    # 방법: OPTIONS 요청 또는 빈 데이터 GET 으로 컬럼 추출
    endpoint = f"{url}/rest/v1/{table}?select=*&limit=0"
    req = urllib.request.Request(endpoint, headers=sb_headers(key))
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            # Content-Profile 헤더에서 컬럼 추출은 안 되지만,
            # OpenAPI 자동생성 spec 에서 가져올 수 있음
            pass
    except Exception:
        pass

    # OpenAPI spec 에서 테이블 컬럼 가져오기
    endpoint2 = f"{url}/rest/v1/?apikey={key}"
    req2 = urllib.request.Request(endpoint2, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/openapi+json",
    })
    try:
        with urllib.request.urlopen(req2, timeout=10) as resp:
            spec = json.loads(resp.read().decode('utf-8'))
            # OpenAPI spec → definitions → {table} → properties
            definitions = spec.get("definitions", {})
            table_def = definitions.get(table, {})
            props = table_def.get("properties", {})
            if props:
                return set(props.keys())
    except Exception:
        pass

    # 폴백: RPC로 information_schema 직접 조회
    rpc_url = f"{url}/rest/v1/rpc/get_columns"
    # RPC가 없으면 결국 빈 set → 필터링 없이 전체 전송
    return set()


def filter_to_existing_columns(rows, table_columns):
    """
    데이터에서 Supabase 테이블에 실제 존재하는 컬럼만 남기기.
    table_columns가 비어있으면 필터링 건너뜀 (전체 전송).
    """
    if not table_columns:
        return rows
    # id 는 항상 제외 (BIGSERIAL 자동생성)
    allowed = table_columns - {'id'}
    return [{k: v for k, v in row.items() if k in allowed} for row in rows]


def normalize_keys(rows):
    """모든 행의 키를 통일 (Supabase bulk POST 요구사항)."""
    if not rows:
        return rows
    # id 제거
    clean = [{k: v for k, v in row.items() if k != 'id'} for row in rows]
    all_keys = set()
    for row in clean:
        all_keys.update(row.keys())
    sorted_keys = sorted(all_keys)
    return [{k: row.get(k) for k in sorted_keys} for row in clean]


def deduplicate_rows(rows, conflict_expr):
    """
    conflict 키 기준 중복 제거 (마지막 행 유지).
    ON CONFLICT DO UPDATE cannot affect row a second time 오류 방지.
    """
    if not conflict_expr or not rows:
        return rows
    # "(vendor, name)" → ['vendor', 'name']
    key_cols = [c.strip() for c in conflict_expr.strip('()').split(',')]
    seen = {}
    for row in rows:
        key = tuple(str(row.get(c, '')) for c in key_cols)
        seen[key] = row  # 같은 키면 마지막 행으로 덮어씀
    return list(seen.values())


def migrate_table(url, key, table, rows, conflict_expr):
    """테이블 데이터를 Supabase에 일괄 삽입."""
    if not rows:
        return 0, 0, "⏭️ 데이터 없음"

    # ── (1) Supabase 테이블의 실제 컬럼 조회 ──
    real_cols = get_table_columns(url, key, table)

    # ── (2) 존재하지 않는 컬럼 필터링 ──
    if real_cols:
        filtered_rows = filter_to_existing_columns(rows, real_cols)
        skipped_cols = set()
        for row in rows:
            for k in row:
                if k != 'id' and k not in real_cols:
                    skipped_cols.add(k)
    else:
        filtered_rows = [{k: v for k, v in row.items() if k != 'id'} for row in rows]
        skipped_cols = set()

    # ── (3) 중복 제거 (같은 conflict key 행 → 마지막만 유지) ──
    deduped = deduplicate_rows(filtered_rows, conflict_expr)

    # ── (4) 키 통일 ──
    unified = normalize_keys(deduped)

    # ── (5) Supabase POST ──
    endpoint = f"{url}/rest/v1/{table}"
    if conflict_expr:
        cols_raw = conflict_expr.strip('()').replace(' ', '')
        endpoint += f"?on_conflict={urllib.parse.quote(cols_raw)}"
        prefer = "resolution=merge-duplicates,return=minimal"
    else:
        prefer = "return=minimal"

    payload = json.dumps(unified, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        endpoint, data=payload,
        headers=sb_headers(key, prefer=prefer),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            msg = f"✅ {len(rows)}행 이전 완료"
            if skipped_cols:
                msg += f" (제외된 컬럼: {', '.join(sorted(skipped_cols))})"
            return len(rows), 0, msg
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        try:
            err_msg = json.loads(body).get("message", body[:300])
        except Exception:
            err_msg = body[:300]
        return 0, len(rows), f"❌ HTTP {e.code}: {err_msg}"
    except Exception as e:
        return 0, len(rows), f"❌ {type(e).__name__}: {e}"


# ── UI ─────────────────────────────────────────────────────────────────────
st.title("🔄 GitHub JSON → Supabase 데이터 이전")
st.caption("⚠️ 이전 완료 후 이 파일(pages/99_migration.py)을 GitHub에서 삭제하세요.")

supabase_url, supabase_key = get_supabase()

if supabase_url and supabase_key:
    st.success(f"✅ Supabase 연결됨: `{supabase_url}`")
else:
    st.error("❌ Supabase 미연결 — Streamlit Secrets 확인 필요")
    st.stop()

st.divider()

# ── 미리보기 ──
st.subheader("📋 이전 대상 데이터")
import pandas as pd
preview = []
for table, filename, label, _ in MIGRATE_FILES:
    fp = os.path.join(DATA_DIR, filename)
    if os.path.exists(fp):
        try:
            cnt = len(json.load(open(fp, encoding='utf-8')))
        except Exception:
            cnt = 0
        preview.append({"테이블": table, "설명": label, "행 수": f"{cnt}행", "파일": "✅ 있음"})
    else:
        preview.append({"테이블": table, "설명": label, "행 수": "-", "파일": "⏭️ 없음"})
st.dataframe(pd.DataFrame(preview), use_container_width=True, hide_index=True)

st.divider()
st.subheader("🚀 이전 실행")
st.info("Supabase 테이블 컬럼을 자동 감지하여, 존재하는 컬럼의 데이터만 전송합니다.")

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
            st.error(f"❌ **{label}** — JSON 읽기 실패: {e}")
            continue

        if not isinstance(rows, list) or len(rows) == 0:
            st.info(f"⏭️ **{label}** — 데이터 없음, 건너뜀")
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
    else:
        st.warning(f"⚠️ 부분 완료: 성공 {total_ok}행 / 실패 {total_fail}행")

st.divider()
st.caption("zeroda 플랫폼 | 데이터 이전 도구 | 사용 후 삭제 권장")
