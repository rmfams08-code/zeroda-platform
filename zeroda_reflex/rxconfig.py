# zeroda_reflex/rxconfig.py
# Reflex 앱 설정
import os
import reflex as rx

# -- DB 경로: 환경변수 -> 기본값 (로컬 개발용) --
_db_path = os.environ.get("ZERODA_DB_PATH", "zeroda.db")

# -- Redis URL (서버 환경에서만 설정, 로컬은 빈 값 -> 메모리 모드) --
_redis_url = os.environ.get("ZERODA_REDIS_URL", "")

_config_kwargs = dict(
    app_name="zeroda_reflex",
    db_url=f"sqlite:///{_db_path}",
    frontend_port=3000,
    backend_port=8000,
)

# Redis 설정 - ZERODA_REDIS_URL이 있을 때만 활성화
# Worker 간 세션 공유를 위해 필수 (Phase 2)
if _redis_url:
    _config_kwargs["state_manager_mode"] = "redis"
    _config_kwargs["redis_url"] = _redis_url

config = rx.Config(**_config_kwargs)
