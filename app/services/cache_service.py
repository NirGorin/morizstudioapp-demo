# app/services/cache_service.py
import os, json
from typing import Optional

try:
    import redis
    _REDIS = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
except Exception:
    _REDIS = None

_TTL = int(os.getenv("AI_SUMMARY_CACHE_TTL_SECONDS", "86400"))

def cache_key(user_id: int) -> str:
    return f"ai_summary:{user_id}"

def cache_set(user_id: int, data: dict) -> None:
    if _REDIS:
        _REDIS.setex(cache_key(user_id), _TTL, json.dumps(data))

def cache_get(user_id: int) -> Optional[dict]:
    if not _REDIS:
        return None
    raw = _REDIS.get(cache_key(user_id))
    return json.loads(raw) if raw else None
