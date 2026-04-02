# services/github_storage.py
# GitHub API를 공용 저장소로 사용 - 실시간 데이터 공유
import json
import base64
import streamlit as st
from datetime import datetime

# 공유할 테이블 목록 (GitHub CSV로 관리)
SHARED_TABLES = [
    'real_collection',   # 수거 데이터 (기사→본사 실시간)
    'sim_collection',    # 시뮬레이션
    'users',             # 계정
    'vendor_info',       # 업체 정보
    'customer_info',     # 거래처
    'schedules',         # 수거일정
    'school_master',     # 학교 마스터
    'safety_education',  # 안전교육
    'safety_checklist',  # 안전점검
    'accident_report',   # 사고신고
    'carbon_reduction',      # 탄소감축
    'processing_confirm',    # 처리확인(계근표)
]


def _get_github():
    """GitHub 연결 정보"""
    try:
        token = st.secrets.get("GITHUB_TOKEN", "")
        repo  = st.secrets.get("GITHUB_REPO", "")
    except Exception:
        token = ""
        repo  = ""
    return token, repo


def _file_path(table: str) -> str:
    return f"data/{table}.json"


def _get_file(table: str):
    """GitHub에서 JSON 파일 읽기 → (rows, sha)"""
    import urllib.request
    token, repo = _get_github()
    if not token or not repo:
        return [], None

    url = f"https://api.github.com/repos/{repo}/contents/{_file_path(table)}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "zeroda-platform"
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            # GitHub API는 content에 줄바꿈 포함 - 제거 필요
            raw = data['content'].replace('\n', '').replace(' ', '')
            content = base64.b64decode(raw).decode('utf-8')
            rows = json.loads(content)
            return rows, data['sha']
    except urllib.error.HTTPError as e:
        print(f"[github_storage] HTTP {e.code}: {e.reason} / url={url}")
        return [], None
    except Exception as e:
        print(f"[github_storage] _get_file error: {type(e).__name__}: {e}")
        return [], None


def _put_file(table: str, rows: list, sha=None):
    """GitHub에 JSON 파일 쓰기"""
    import urllib.request
    token, repo = _get_github()
    if not token or not repo:
        return False

    content = base64.b64encode(
        json.dumps(rows, ensure_ascii=False, indent=2).encode('utf-8')
    ).decode()

    payload = {
        "message": f"[zeroda] {table} updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    url = f"https://api.github.com/repos/{repo}/contents/{_file_path(table)}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "zeroda-platform"
        },
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        print(f"[github_storage] PUT error: {e}")
        return False


# ──────────────────────────────────────────────────
# 공개 API (db_manager에서 호출)
# ──────────────────────────────────────────────────

@st.cache_data(ttl=10)   # 30초 캐시 - 실시간성 유지
def _github_get_cached(table: str):
    """GitHub에서 테이블 전체 데이터 읽기 (캐시 적용)"""
    rows, _ = _get_file(table)
    return rows or []


def github_get(table: str, where_dict: dict = None):
    """GitHub에서 테이블 데이터 읽기 (where 필터는 캐시 밖에서 처리)"""
    rows = _github_get_cached(table)
    if where_dict and rows:
        for k, v in where_dict.items():
            rows = [r for r in rows if str(r.get(k, '')) == str(v)]
    return rows


def github_insert(table: str, data: dict):
    """GitHub에 새 행 추가"""
    rows, sha = _get_file(table)
    if rows is None:
        rows = []

    # auto increment id
    max_id = max((r.get('id', 0) for r in rows), default=0)
    data['id'] = max_id + 1
    rows.append(data)

    success = _put_file(table, rows, sha)
    if success:
        # 캐시 무효화
        _github_get_cached.clear()
        return data['id']
    return None


def github_upsert(table: str, data: dict):
    """GitHub에서 행 업데이트 (id 기준) 또는 삽입"""
    rows, sha = _get_file(table)
    if rows is None:
        rows = []

    row_id = data.get('id')
    if row_id:
        updated = False
        for i, r in enumerate(rows):
            if r.get('id') == row_id:
                rows[i] = data
                updated = True
                break
        if not updated:
            rows.append(data)
    else:
        max_id = max((r.get('id', 0) for r in rows), default=0)
        data['id'] = max_id + 1
        rows.append(data)

    success = _put_file(table, rows, sha)
    if success:
        _github_get_cached.clear()
        return True
    return False


def github_delete(table: str, where_dict: dict):
    """GitHub에서 조건에 맞는 행 삭제 (AND 조건: 모든 key-value 동시 일치하는 행만 삭제)"""
    rows, sha = _get_file(table)
    if not rows:
        return False

    # AND 조건: where_dict의 모든 조건을 동시에 만족하는 행만 삭제
    # 예) {'vendor': 'hy', 'month': '2026-03'} → vendor='hy' AND month='2026-03'인 행만 삭제
    new_rows = [
        r for r in rows
        if not all(str(r.get(k, '')) == str(v) for k, v in where_dict.items())
    ]

    if len(new_rows) == len(rows):
        return False  # 삭제 대상 없음

    success = _put_file(table, new_rows, sha)
    if success:
        _github_get_cached.clear()
        return True
    return False


def is_github_available():
    """GitHub 연결 가능 여부 확인"""
    token, repo = _get_github()
    return bool(token and repo)
