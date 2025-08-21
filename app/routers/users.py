# app/routers/users.py
import os
import redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth import get_db
from ..models import User  # מניח שיש מודל עם id, email

router = APIRouter(prefix="/users", tags=["users"])
# app/cache.py

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)


# הגדרת Redis (ElastiCache) — שים כאן את ה-endpoint שלך של ElastiCache
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# לדוגמה ב-Prod:
# REDIS_URL = "redis://moriz-cache.abc123.il1.cache.amazonaws.com:6379/0"
# אם הפעלת TLS ב-ElastiCache: השתמש ב-rediss:// וודא שהספרייה תומכת ב-SSL

r = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,   # לקבל מחרוזת ולא bytes
)

CACHE_TTL_SECONDS = 600  # 10 דקות — שנה לפי הצורך

@router.get("/{user_id}/email")
def get_user_email(user_id: int, db: Session = Depends(get_db)):
    key = f"user:{user_id}:email"

    # 1) ניסיון קריאה מה-Redis
    email = r.get(key)
    if email:
        return {"user_id": user_id, "email": email, "cache": "HIT"}

    # 2) אם אין ב-Redis → שליפה ממוקדת מה-DB (רק עמודת email)
    email = db.query(User.email).filter(User.id == user_id).scalar()
    if email is None:
        raise HTTPException(status_code=404, detail="User not found")

    # 3) כתיבה ל-Redis עם TTL
    r.setex(key, CACHE_TTL_SECONDS, email)

    # 4) החזרה ללקוח
    return {"user_id": user_id, "email": email, "cache": "MISS"}
