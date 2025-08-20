# app/routers/ai.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import json
from ..database import SessionMoriz
from ..models import TraineeProfile, User
from ..services.cache_service import cache_get, cache_set
from ..services.storage_service import get_json_from_s3

router = APIRouter(prefix="/ai", tags=["ai"])

def get_db():
    db = SessionMoriz()
    try:
        yield db
    finally:
        db.close()

@router.get("/users/{user_id}/summary")
def get_user_ai_summary(user_id: int, db: Session = Depends(get_db)):
    # 1) Redis
    cached = cache_get(user_id)
    if cached:
        return cached

    # 2) שליפה דרך הפרופיל → מצביע ב-ai_json → S3
    profile = db.query(TraineeProfile).join(User, ( (User.trainee_id == TraineeProfile.id) | (User.id == TraineeProfile.user_id) )).filter(User.id == user_id).first()
    if not profile or not profile.ai_json:
        raise HTTPException(404, "no summary yet")

    try:
        ptr = json.loads(profile.ai_json)
    except Exception:
        raise HTTPException(500, "invalid pointer format")

    s3_key = ptr.get("s3_key")
    if not s3_key:
        raise HTTPException(404, "no s3_key pointer")

    data = get_json_from_s3(s3_key)
    if not data:
        raise HTTPException(404, "summary not found in S3")

    # כתוב לקאש
    cache_set(user_id, data)
    return data
