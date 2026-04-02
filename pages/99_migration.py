# pages/99_migration.py
# ⚠️ 데이터 이전 완료 후 이 파일을 GitHub에서 삭제하세요
# GitHub JSON → Supabase 일괄 이전 도구 (관리자 전용)

import streamlit as st
import json
import os
import urllib.request
import urllib.parse

st.set_page_config(page_title="데이터 이전 | ZERODA", page_icon="🔄", layout="wide")

# ── 설정 ───────────────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# 이전할 파일 목록 (순서 중요 - 참조 관계 고려)
MIGRATE_FILES = [
    ('vendor_info',     'vendor_info.json',     '업체 정보',   '(vendor)'),
    ('users',           'users.json',            '계정',       '(user_id)'),
    ('school_master',   'school_master.json',    '학교 마스터', '(school_name)'),
    ('customer_info',   'customer_info.json',    '거래처',     '(vendor, name)'),
    ('schedules',       'schedules.json',        '수거일정',    None),
    ('real_collection', 'real_collection.json',  '수거기록',    None),
    ('sim_collection',  'sim_collection.json',   '시뮬레이션',  None),
    ('safety_education','safety_education.json', '안전교육',    None),
    ('safety_checklist','safety_checklist.json', '안전점검',    None),
    ('accident_report', 'accident_report.json',  '사고신고',    None),
    ('carbon_reduction','carbon_reduction.json', '탄소감축',    None),
    ('processing_confirm','processing_confirm.json','처리확인', None),
    ('meal_menus',      'meal_menus.json',       '급식식단',    '(site_name, meal_date, meal_type)'),
    ('meal_analysis',   'meal_analysis.json',    '잔반분석',    '(site_name, meal_date)'),
]


# ── Supabase 연결 ───────────────────────────────────────────────────────────
def get_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "").rstrip('/')
        key = st.secrets.get("SUPABASE_KEY", "")
        return url, key
    except Exception:
        return "", ""


def supabase_headers(key, prefer=None):
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def migrate_table(url, key, table, rows, conflict_expr):
    """테이블 데이터를 Supabase에 일괄 삽입"""
    if not rows:
        return 0, 0, "데이터 없음 (건너뜀)"

    # id 제거 (Supabase BIGSERIAL 자동생성)
    clean_rows = [{k: v for k, v in row.items() if k != 'id'} for row in rows]

    endpoint = f"{url}/rest/v1/{table}"
    if conflict_expr:
        cols = urllib.parse.quote(conflict_expr.strip('()').replace(' ', ''))
        endpoint += f"?on_conflict={cols}"
        prefer = "resolution=merge-duplicates,return=minimal"
    else:
        prefer = "return=minimal"

    payload = json.dumps(clean_rows, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers=supabase_headers(key, prefer=prefer),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return len(rows), 0, f"✅ {len(rows)}행 이전 완료"
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        return 0, len(rows), f"❌ HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return 0, len(rows), f"❌ 오류: {type(e).__name__}: {e}"


# ── UI ─────────────────────────────────────────────────────────────────────
st.title("🔄 GitHub JSON → Supabase 데이터 이전")
st.caption("⚠️ 이전 완료 후 이 페이지(pages/99_migration.py)를 GitHub에서 삭제하세요.")

supabase_url, supabase_key = get_supabase()

# Supabase 연결 상태
col1, col2 = st.columns(2)
with col1:
    if supabase_url and supabase_key:
        st.success(f"✅ Supabase 연결됨: `{supabase_url}`")
    else:
        st.error("❌ Supabase 연결 안 됨 — Streamlit Secrets에 URL/KEY 확인 필요")
        st.stop()

with col2:
    data_dir_abs = os.path.abspath(DATA_DIR)
    st.info(f"📂 data 폴더: `{data_dir_abs}`")

st.divider()

# 이전 대상 파일 목록 미리보기
st.subheader("📋 이전 대상 데이터")
preview_rows = []
for table, filename, label, conflict in MIGRATE_FILES:
    filepath = os.path.join(DATA_DIR, filename)
    if os.path.exists(filepath):
        with open(filepath, encoding='utf-8') as f:
            try:
                data = json.load(f)
                count = len(data) if isinstance(data, list) else 0
            except Exception:
                count = 0
        status = f"{count}행" if count > 0 else "비어있음"
        preview_rows.append({"테이블": table, "설명": label, "행 수": status, "파일": filename})
    else:
        preview_rows.append({"테이블": table, "설명": label, "행 수": "파일 없음", "파일": filename})

import pandas as pd
st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)

st.divider()

# 이전 실행
st.subheader("🚀 이전 실행")
st.warning("이전 버튼을 클릭하면 위 데이터가 Supabase에 업로드됩니다. 기존 데이터는 ON CONFLICT DO NOTHING으로 보호됩니다.")

if st.button("▶ 데이터 이전 시작", type="primary", use_container_width=True):
    total_success = 0
    total_fail = 0

    progress_bar = st.progress(0)
    result_container = st.container()

    with result_container:
        for i, (table, filename, label, conflict) in enumerate(MIGRATE_FILES):
            filepath = os.path.join(DATA_DIR, filename)
            progress_bar.progress((i + 1) / len(MIGRATE_FILES))

            if not os.path.exists(filepath):
                st.info(f"⏭️ {table} — 파일 없음, 건너뜀")
                continue

            with open(filepath, encoding='utf-8') as f:
                try:
                    rows = json.load(f)
                except Exception as e:
                    st.error(f"❌ {table} — JSON 읽기 실패: {e}")
                    continue

            if not isinstance(rows, list) or len(rows) == 0:
                st.info(f"⏭️ {table} — 데이터 없음, 건너뜀")
                continue

            with st.spinner(f"{label} ({len(rows)}행) 이전 중..."):
                ok, fail, msg = migrate_table(supabase_url, supabase_key, table, rows, conflict)
                total_success += ok
                total_fail += fail

            st.write(f"**{label}** (`{table}`): {msg}")

    progress_bar.progress(1.0)
    st.divider()

    if total_fail == 0:
        st.success(f"🎉 이전 완료! 총 **{total_success}행** 성공")
        st.balloons()
    else:
        st.warning(f"⚠️ 부분 완료: 성공 {total_success}행 / 실패 {total_fail}행")

    st.info("👉 Supabase Table Editor에서 데이터를 확인하고, 이상 없으면 이 페이지를 GitHub에서 삭제하세요.")

st.divider()
st.caption("zeroda 플랫폼 | 데이터 이전 도구 | 사용 후 삭제 권장")
