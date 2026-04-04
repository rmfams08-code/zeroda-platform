# services/photo_storage.py
# Supabase Storage를 이용한 사진 업로드/조회 서비스
import json
import urllib.request
import urllib.parse
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

BUCKET_NAME = "photos"


def _get_supabase():
    """Supabase 연결 정보"""
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
    except Exception:
        url, key = "", ""
    return url.rstrip('/'), key


def _ensure_bucket():
    """photos 버킷이 없으면 생성 (앱 시작 시 1회)"""
    if st.session_state.get('_bucket_checked'):
        return
    url, key = _get_supabase()
    if not url or not key:
        return
    try:
        endpoint = f"{url}/storage/v1/bucket/{BUCKET_NAME}"
        req = urllib.request.Request(endpoint, headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        })
        urllib.request.urlopen(req, timeout=5)
        st.session_state['_bucket_checked'] = True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 버킷 없으면 생성
            try:
                create_url = f"{url}/storage/v1/bucket"
                body = json.dumps({
                    "id": BUCKET_NAME,
                    "name": BUCKET_NAME,
                    "public": True
                }).encode('utf-8')
                req = urllib.request.Request(create_url, data=body, headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                }, method="POST")
                urllib.request.urlopen(req, timeout=10)
                st.session_state['_bucket_checked'] = True
            except Exception as ce:
                print(f"[photo_storage] bucket create error: {ce}")
        else:
            print(f"[photo_storage] bucket check error: {e}")
    except Exception as e:
        print(f"[photo_storage] bucket check error: {e}")


def upload_photo(file_obj, vendor: str, driver: str, school_name: str,
                 photo_type: str, collect_date: str = None) -> str:
    """
    사진을 Supabase Storage에 업로드하고 public URL을 반환.

    Args:
        file_obj: Streamlit UploadedFile 객체
        vendor: 업체명
        driver: 기사명
        school_name: 학교명
        photo_type: 'collection' | 'processing' | 'vehicle' | 'accident'
        collect_date: 수거일 (YYYY-MM-DD)

    Returns:
        public URL (str) 또는 실패 시 None
    """
    url, key = _get_supabase()
    if not url or not key:
        print("[photo_storage] Supabase 연결 정보 없음")
        return None

    _ensure_bucket()

    # 파일 경로 구성: vendor/YYYY-MM/type_school_timestamp.ext
    now = datetime.now(ZoneInfo('Asia/Seoul'))
    if not collect_date:
        collect_date = now.strftime('%Y-%m-%d')
    year_month = collect_date[:7]  # YYYY-MM

    # 파일 확장자
    file_name = file_obj.name if hasattr(file_obj, 'name') else 'photo.jpg'
    ext = file_name.rsplit('.', 1)[-1].lower() if '.' in file_name else 'jpg'

    # 고유 파일명 생성
    timestamp = now.strftime('%Y%m%d_%H%M%S_%f')[:19]
    safe_school = school_name.replace(' ', '_').replace('/', '_')[:20]
    storage_path = f"{vendor}/{year_month}/{photo_type}_{safe_school}_{timestamp}.{ext}"

    # 파일 바이트 읽기
    file_bytes = file_obj.read()
    file_obj.seek(0)  # 재사용 가능하도록 되감기

    # Content-Type 결정
    content_type = "image/jpeg"
    if ext == 'png':
        content_type = "image/png"

    # Supabase Storage에 업로드
    encoded_path = urllib.parse.quote(storage_path, safe='/')
    endpoint = f"{url}/storage/v1/object/{BUCKET_NAME}/{encoded_path}"

    req = urllib.request.Request(endpoint, data=file_bytes, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": content_type,
        "Cache-Control": "max-age=3600",
        "x-upsert": "true",
    }, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # public URL 생성
            public_url = f"{url}/storage/v1/object/public/{BUCKET_NAME}/{encoded_path}"
            return public_url
    except Exception as e:
        print(f"[photo_storage] upload error: {e}")
        return None


def save_photo_record(vendor: str, driver: str, school_name: str,
                      photo_type: str, photo_url: str,
                      collect_date: str, record_id: str = "",
                      memo: str = ""):
    """사진 메타데이터를 photo_records 테이블에 저장"""
    from database.db_manager import db_insert
    now = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')
    data = {
        'vendor': vendor,
        'driver': driver,
        'school_name': school_name,
        'photo_type': photo_type,
        'photo_url': photo_url,
        'collect_date': collect_date or '',
        'record_id': record_id or '',
        'memo': memo or '',
        'created_at': now,
    }
    return db_insert('photo_records', data)


def get_photo_records(vendor: str = None, photo_type: str = None,
                      collect_date: str = None, school_name: str = None):
    """사진 기록 조회 (필터 조건)"""
    from database.db_manager import db_get
    rows = db_get('photo_records')
    if vendor:
        rows = [r for r in rows if r.get('vendor') == vendor]
    if photo_type:
        rows = [r for r in rows if r.get('photo_type') == photo_type]
    if collect_date:
        rows = [r for r in rows if r.get('collect_date') == collect_date]
    if school_name:
        rows = [r for r in rows if r.get('school_name') == school_name]
    # 최신순 정렬
    rows.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return rows
