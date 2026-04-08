# zeroda_reflex/utils/url_shortener.py
# URL 단축 — TinyURL 공개 API 사용 (키 없음, 인증 불필요)
# iOS SMS 자동링크 인식을 위해 zeroda.co.kr 원본 URL 대신 단축 URL 전송
import logging
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

_TINYURL_API = "https://tinyurl.com/api-create.php"
_TIMEOUT = 5  # 초


def shorten_url(long_url: str) -> str:
    """URL을 TinyURL로 단축. 실패 시 원본 URL 그대로 반환."""
    if not long_url:
        return long_url
    try:
        params = urllib.parse.urlencode({"url": long_url})
        req_url = f"{_TINYURL_API}?{params}"
        with urllib.request.urlopen(req_url, timeout=_TIMEOUT) as resp:
            short = resp.read().decode("utf-8").strip()
        if short.startswith("https://tinyurl.com/"):
            return short
        logger.warning(f"shorten_url: 예상치 못한 응답 '{short}' — 원본 URL 사용")
        return long_url
    except Exception as e:
        logger.warning(f"shorten_url 실패 (원본 URL 사용): {e}")
        return long_url
