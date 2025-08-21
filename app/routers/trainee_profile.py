
# from typing import Annotated
# from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
# from sqlalchemy.orm import Session
# import json
# import os
# from ..database import SessionMoriz
# from ..models import TraineeProfile, User
# from ..services.ai_service import process_profile_in_background, _build_user_prompt
# from ..schemas import CreateTraineeProfileRequest
# from ..routers.auth import get_current_user, db_dependecy
# from redis.asyncio import Redis

# REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# r: Redis = Redis.from_url(REDIS_URL, decode_responses=True)  # מחזיר str ולא bytes
# CACHE_TTL_SECONDS = 3600  # 60 דקות – שנה לפי הצורך שלך






# router = APIRouter(prefix="/trainee_profile", tags=["trainee_profile"])



# # @router.post("/create_trainee_profile", status_code=status.HTTP_201_CREATED)
# # async def create_trainee_profile(
# #     background_tasks: BackgroundTasks,
# #     db: db_dependecy,
# #     profile: CreateTraineeProfileRequest,
# #     user: Annotated[dict, Depends(get_current_user)],
# # ):
# #     if user['role'] == 'trainer':
# #         raise HTTPException(status_code=403, detail="User role not allowed to create trainee profile")

# #     trainee_profile = TraineeProfile(
# #         age=profile.Age,
# #         gender=profile.Gender,
# #         height_cm=profile.Height,
# #         weight_kg=profile.Weight,
# #         level=profile.Level,
# #         number_of_week_training=profile.Number_Of_Week_Training,
# #         limitations=profile.Limitation,
# #         user_id=user['id'],
# #         ai_status="queued",
# #     )
# #     db.add(trainee_profile)
# #     db.commit()
# #     db.refresh(trainee_profile)
# #     background_tasks.add_task(process_profile_in_background, trainee_profile.id)

# #     return {"message": "Trainee profile created successfully", "profile_id": trainee_profile.id}


# from functools import wraps
# import inspect

# def my_decorator(fn):
#     @wraps(fn)   # ← משמר שם/דוק/חתימה
#     async def wrapper(*args, **kwargs):
#         return await fn(*args, **kwargs)
#     wrapper.__signature__ = inspect.signature(fn)  # ← מפילס את OpenAPI
#     return wrapper

# @router.delete("/delete_trainee_profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
# @my_decorator
# async def delete_trainee_profile(profile_id: int, db: db_dependecy, user: Annotated[dict, Depends(get_current_user)]):
#     if user['role'] == 'trainer':
#         raise HTTPException(status_code=403, detail="User role not allowed to delete trainee profile")
    
#     profile = db.query(TraineeProfile).filter(TraineeProfile.id == profile_id).first()
#     if not profile:
#         raise HTTPException(status_code=404, detail="Trainee profile not found")

#     db.delete(profile)
#     db.commit()
#     return {"message": "Trainee profile deleted successfully"}

# @router.post("/create_trainee_profile", status_code=status.HTTP_201_CREATED)
# @my_decorator
# async def create_trainee_profile(
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(db_dependecy),
#     profile: CreateTraineeProfileRequest = None,
#     user: dict = Depends(get_current_user),
# ):
#     if user['role'] == 'trainer':
#         raise HTTPException(status_code=403, detail="User role not allowed to create trainee profile")

#     trainee_profile = TraineeProfile(
#         age=profile.Age,
#         gender=profile.Gender,
#         height_cm=profile.Height,
#         weight_kg=profile.Weight,
#         level=profile.Level,
#         number_of_week_training=profile.Number_Of_Week_Training,
#         limitations=profile.Limitation,
#         user_id=user['id'],
#         ai_status="queued",
#     )
#     db.add(trainee_profile)
#     db.commit()
#     db.refresh(trainee_profile)

#     # === שמירה גם ל-Redis (צילום מצב של הפרופיל שנוצר) ===
#     cache_key = f"trainee:{trainee_profile.id}:profile"
#     cache_payload = {
#         "profile_id": trainee_profile.id,
#         "user_id": user["id"],
#         "age": profile.Age,
#         "gender": profile.Gender,
#         "height_cm": profile.Height,
#         "weight_kg": profile.Weight,
#         "level": profile.Level,
#         "number_of_week_training": profile.Number_Of_Week_Training,
#         "limitations": profile.Limitation,
#         "ai_status": "queued",
#     }
#     try:
#         # כתיבה אסינכרונית ל-Redis עם תפוגה
#         await r.set(cache_key, json.dumps(cache_payload), ex=CACHE_TTL_SECONDS)
#     except Exception as e:
#         # לא מפילים את הבקשה אם Redis נפל — פשוט ממשיכים (Fail-open)
#         # אפשר להוסיף כאן לוג/מטריקה
#         pass

#     # המשך תהליך ה-AI ברקע
#     background_tasks.add_task(process_profile_in_background, trainee_profile.id)

#     return {"message": "Trainee profile created successfully", "profile_id": trainee_profile.id}

# @router.get("/trainees/{profile_id}/profile_cache", status_code=status.HTTP_200_OK)
# @my_decorator
# async def get_trainee_profile_cache_only(profile_id: int):
#     """
#     מחזיר את צילום הפרופיל מתוך Redis בלבד.
#     מחזיר 404 אם אין מפתח בקאש (לא פונה ל-DB).
#     """
#     cache_key = f"trainee:{profile_id}:profile"

#     try:
#         raw = await r.get(cache_key)
#     except Exception:
#         # אם Redis לא זמין – עדיף להחזיר 503 במקום להפיל את השרת
#         raise HTTPException(status_code=503, detail="Cache unavailable")

#     if not raw:
#         raise HTTPException(status_code=404, detail="Cache miss for trainee profile")

#     try:
#         data = json.loads(raw)
#     except Exception:
#         # אם מסיבה כלשהי לא JSON תקין — נחזיר את הגולמי
#         data = {"raw": raw}

#     return {"profile_id": profile_id, "cache": "HIT", "data": data}


# # ===== B) קריאה עם נפילה ל-DB (ומילוי קאש) =====
# @router.get("/trainees/{profile_id}/profile", status_code=status.HTTP_200_OK)
# async def get_trainee_profile(profile_id: int, db: Annotated[Session, Depends(db_dependecy)]):
#     """
#     מנסה קודם מ-Redis; אם אין, שולף מה-DB, שומר לקאש עם TTL ומחזיר.
#     """
#     cache_key = f"trainee:{profile_id}:profile"

#     # 1) ניסיון לקרוא מהקאש
#     try:
#         raw = await r.get(cache_key)
#     except Exception:
#         raw = None  # אם קאש לא זמין – נמשיך ל-DB (fail-open)

#     if raw:
#         try:
#             data = json.loads(raw)
#         except Exception:
#             data = {"raw": raw}
#         return {"profile_id": profile_id, "cache": "HIT", "data": data}

#     # 2) אם אין בקאש – שליפה מה-DB
#     tp = db.query(TraineeProfile).filter(TraineeProfile.id == profile_id).first()
#     if not tp:
#         raise HTTPException(status_code=404, detail="Trainee profile not found")

#     payload = {
#         "profile_id": tp.id,
#         "user_id": tp.user_id,
#         "age": tp.age,
#         "gender": getattr(tp.gender, "name", tp.gender),
#         "height_cm": tp.height_cm,
#         "weight_kg": tp.weight_kg,
#         "level": getattr(tp.level, "name", tp.level),
#         "number_of_week_training": tp.number_of_week_training,
#         "limitations": tp.limitations,
#         "ai_status": tp.ai_status,
#     }

#     # 3) כתיבה לקאש עם TTL (לא קריטי אם נכשלת)
#     try:
#         await r.set(cache_key, json.dumps(payload), ex=CACHE_TTL_SECONDS)
#     except Exception:
#         pass

#     return {"profile_id": profile_id, "cache": "MISS", "data": payload}


from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
import json, os
from ..models import TraineeProfile, User
from ..services.ai_service import process_profile_in_background
from ..schemas import CreateTraineeProfileRequest
from ..routers.auth import get_current_user
from .auth import get_db                # ← השתמש ב־get_db ישירות
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r: Redis = Redis.from_url(REDIS_URL, decode_responses=True)
CACHE_TTL_SECONDS = 3600

router = APIRouter(prefix="/trainee_profile", tags=["trainee_profile"])

@router.delete("/delete_trainee_profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trainee_profile(
    profile_id: int,
    db: Session = Depends(get_db),           # ← אין db_dependecy
    user: dict = Depends(get_current_user),
):
    if user['role'] == 'trainer':
        raise HTTPException(status_code=403, detail="User role not allowed to delete trainee profile")
    profile = db.query(TraineeProfile).filter(TraineeProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Trainee profile not found")
    db.delete(profile)
    db.commit()
    return {"message": "Trainee profile deleted successfully"}

@router.post("/create_trainee_profile", status_code=status.HTTP_201_CREATED)
async def create_trainee_profile(
    profile: CreateTraineeProfileRequest,    # ← בלי ברירת מחדל None
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),           # ← תלות תקינה
    user: dict = Depends(get_current_user),
):
    if user['role'] == 'trainer':
        raise HTTPException(status_code=403, detail="User role not allowed to create trainee profile")

    trainee_profile = TraineeProfile(
        age=profile.Age,
        gender=profile.Gender,
        height_cm=profile.Height,
        weight_kg=profile.Weight,
        level=profile.Level,
        number_of_week_training=profile.Number_Of_Week_Training,
        limitations=profile.Limitation,
        user_id=user['id'],
        ai_status="queued",
    )
    db.add(trainee_profile)
    db.commit()
    db.refresh(trainee_profile)

    cache_key = f"trainee:{trainee_profile.id}:profile"
    cache_payload = {
        "profile_id": trainee_profile.id,
        "user_id": user["id"],
        "age": profile.Age,
        "gender": profile.Gender,
        "height_cm": profile.Height,
        "weight_kg": profile.Weight,
        "level": profile.Level,
        "number_of_week_training": profile.Number_Of_Week_Training,
        "limitations": profile.Limitation,
        "ai_status": "queued",
    }
    try:
        await r.set(cache_key, json.dumps(cache_payload), ex=CACHE_TTL_SECONDS)
    except Exception:
        pass

    background_tasks.add_task(process_profile_in_background, trainee_profile.id)
    return {"message": "Trainee profile created successfully", "profile_id": trainee_profile.id}

@router.get("/trainees/{profile_id}/profile_cache", status_code=status.HTTP_200_OK)
async def get_trainee_profile_cache_only(profile_id: int):
    cache_key = f"trainee:{profile_id}:profile"
    try:
        raw = await r.get(cache_key)
    except Exception:
        raise HTTPException(status_code=503, detail="Cache unavailable")
    if not raw:
        raise HTTPException(status_code=404, detail="Cache miss for trainee profile")
    try:
        data = json.loads(raw)
    except Exception:
        data = {"raw": raw}
    return {"profile_id": profile_id, "cache": "HIT", "data": data}

@router.get("/trainees/{profile_id}/profile", status_code=status.HTTP_200_OK)
async def get_trainee_profile(
    profile_id: int,
    db: Session = Depends(get_db),           # ← גם כאן
):
    cache_key = f"trainee:{profile_id}:profile"
    try:
        raw = await r.get(cache_key)
    except Exception:
        raw = None
    if raw:
        try:
            data = json.loads(raw)
        except Exception:
            data = {"raw": raw}
        return {"profile_id": profile_id, "cache": "HIT", "data": data}

    tp = db.query(TraineeProfile).filter(TraineeProfile.id == profile_id).first()
    if not tp:
        raise HTTPException(status_code=404, detail="Trainee profile not found")

    payload = {
        "profile_id": tp.id,
        "user_id": tp.user_id,
        "age": tp.age,
        "gender": getattr(tp.gender, "name", tp.gender),
        "height_cm": tp.height_cm,
        "weight_kg": tp.weight_kg,
        "level": getattr(tp.level, "name", tp.level),
        "number_of_week_training": tp.number_of_week_training,
        "limitations": tp.limitations,
        "ai_status": tp.ai_status,
    }
    try:
        await r.set(cache_key, json.dumps(payload), ex=CACHE_TTL_SECONDS)
    except Exception:
        pass
    return {"profile_id": profile_id, "cache": "MISS", "data": payload}
