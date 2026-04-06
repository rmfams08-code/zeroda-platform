# zeroda_reflex/rxconfig.py
# Reflex 앱 설정
import os
import reflex as rx

# ── DB 경로: 환경변수 → 기본값 (로컬 개발용) ──
_db_path = os.environ.get("ZERODA_DB_PATH", "zeroda.db")

config = rx.Config(
    app_name="zeroda_reflex",

    # 기존 zeroda Streamlit 앱과 같은 DB 공유
    db_url=f"sqlite:///{_db_path}",

    # 서버 포트 (Streamlit 8501과 겹치지 않게)
    frontend_port=3000,
    backend_port=8000,
)
