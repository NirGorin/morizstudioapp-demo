# # app/services/ai_service.py
# import os, json
# from openai import OpenAI
# from sqlalchemy.orm import Session
# from ..database import SessionMoriz
# from ..models import TraineeProfile

# MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
# print(f"[AI] Using model: {repr(MODEL)}", flush=True)

# SYSTEM_PROMPT = (
#     "You are a physiotherapy-aware fitness coach. "
#     "Given trainee details (age, gender, level, weekly frequency, and limitations in free text), "
#     "return STRICT JSON with keys: "
#     "`summary` (string, <= 5 lines plain English), "
#     "`avoid` (array of {exercise, reason}), "
#     "`caution` (array of {exercise, reason}), "
#     "`safe` (array of {exercise, reason}). "
#     "Do not include any extra keys or prose outside JSON."
# )

# def _build_user_prompt(profile: TraineeProfile) -> str:
#     gender = getattr(profile.gender, "name", None) or str(profile.gender)
#     level  = getattr(profile.level, "name", None) or str(profile.level)
#     freq   = getattr(profile.number_of_week_training, "name", None) or str(profile.number_of_week_training)
#     return (
#         f"age: {profile.age}\n"
#         f"gender: {gender}\n"
#         f"level: {level}\n"
#         f"weekly_training_frequency: {freq}\n"
#         f"medical_limitations_free_text: {profile.limitations or ''}\n"
#         "Return JSON only."
#     )

# def process_profile_in_background(profile_id: int) -> None:
#     db: Session = SessionMoriz()
#     try:
#         profile = db.query(TraineeProfile).get(profile_id)
#         if not profile:
#             return
#         profile.ai_status = "processing"
#         db.commit()

#         client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#         resp = client.chat.completions.create(
#             model=MODEL,
#             temperature=0.2,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": _build_user_prompt(profile)},
#             ],
#         )
#         content = resp.choices[0].message.content.strip()

#         # ננסה לפרסר JSON; אם לא מצליח—נשמור את הטקסט כמו שהוא
#         summary = ""
#         try:
#             parsed = json.loads(content)
#             summary = parsed.get("summary", "")[:2000]
#         except Exception:
#             parsed = None
#             summary = content[:2000]

#         profile.ai_model = MODEL
#         profile.ai_summary = summary
#         profile.ai_json = content
#         profile.ai_status = "done"
#         db.commit()

#     except Exception as e:
#         # ניסיון עדין לסמן שגיאה על הפרופיל
#         try:
#             profile = db.query(TraineeProfile).get(profile_id)
#             if profile:
#                 profile.ai_status = "error"
#                 prev = profile.ai_summary or ""
#                 profile.ai_summary = (prev + f"\nAI error: {e}")[:4000]
#                 db.commit()
#         finally:
#             pass
#     finally:
#         db.close()

# app/services/ai_service.py
# app/services/ai_service.py
import os, json, redis
from datetime import datetime, timezone
from openai import OpenAI
from sqlalchemy.orm import Session
from ..database import SessionMoriz
from ..models import TraineeProfile

MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL = int(os.getenv("REDIS_TTL_SECONDS", "3600"))
r: redis.Redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

SYSTEM_PROMPT = (
    "You are a physiotherapy-aware fitness coach. "
    "Given trainee details (age, gender, level, weekly frequency, and limitations in free text), "
    "return STRICT JSON with keys: "
    "`summary` (string, <= 5 lines plain English), "
    "`avoid` (array of {exercise, reason}), "
    "`caution` (array of {exercise, reason}), "
    "`safe` (array of {exercise, reason}). "
    "Do not include any extra keys or prose outside JSON."
)

def _build_user_prompt_from_snapshot(snap: dict) -> str:
    gender = str(snap.get("gender", "") or "")
    level  = str(snap.get("level", "") or "")
    freq   = str(snap.get("number_of_week_training", "") or "")
    age    = snap.get("age", "")
    limitations = snap.get("limitations") or ""
    return (
        f"age: {age}\n"
        f"gender: {gender}\n"
        f"level: {level}\n"
        f"weekly_training_frequency: {freq}\n"
        f"medical_limitations_free_text: {limitations}\n"
        "Return JSON only."
    )

# ⬇️ שינוי: מחזירים גם snap וגם source
def _load_profile_snapshot(profile_id: int, db: Session) -> tuple[dict | None, str | None]:
    key = f"trainee:{profile_id}:profile"

    # נסיון מ-Redis
    try:
        raw = r.get(key)
        if raw:
            try:
                snap = json.loads(raw)
                if {"age", "gender", "level", "number_of_week_training"}.issubset(snap.keys()):
                    return snap, "redis"
            except Exception:
                pass
    except Exception:
        pass

    # נפילה ל-DB
    profile = db.query(TraineeProfile).get(profile_id)
    if not profile:
        return None, None

    snap = {
        "profile_id": profile.id,
        "user_id": profile.user_id,
        "age": profile.age,
        "gender": getattr(profile.gender, "name", None) or str(profile.gender),
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "level": getattr(profile.level, "name", None) or str(profile.level),
        "number_of_week_training": profile.number_of_week_training,
        "limitations": profile.limitations,
        "ai_status": profile.ai_status or "queued",
    }
    # כתיבה ל-Redis כדי להאיץ ריצות עתידיות
    try:
        r.set(key, json.dumps(snap), ex=REDIS_TTL)
    except Exception:
        pass

    return snap, "db"

def process_profile_in_background(profile_id: int) -> None:
    db: Session = SessionMoriz()
    key = f"trainee:{profile_id}:profile"

    try:
        profile = db.query(TraineeProfile).get(profile_id)
        if not profile:
            return

        # סימון processing
        profile.ai_status = "processing"
        db.commit()

        # עדכון סטטוס גם בקאש
        try:
            raw = r.get(key)
            if raw:
                snap = json.loads(raw)
                snap["ai_status"] = "processing"
                r.set(key, json.dumps(snap), ex=REDIS_TTL)
        except Exception:
            pass

        # ⬇️ טוענים snapshot + מקור
        snap, source = _load_profile_snapshot(profile_id, db)
        if not snap:
            profile.ai_status = "error"
            profile.ai_summary = ((profile.ai_summary or "") + "\nAI error: profile not found")[:4000]
            db.commit()
            return

        # רשום מטה מיידית (כדי שתוכל לבדוק בזמן אמת)
        try:
            meta = {
                "ai_input_source": source,
                "ai_started_at": now_iso(),
                "ai_status": "processing",
            }
            # שמור גם בתוך ה-snapshot וגם כ-meta נפרד
            snap.update(meta)
            r.set(key, json.dumps(snap), ex=REDIS_TTL)
            r.set(f"{key}:ai_meta", json.dumps(meta), ex=REDIS_TTL)
        except Exception:
            pass

        print(f"[AI] profile={profile_id} input={source}", flush=True)

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt_from_snapshot(snap)},
            ],
        )
        content = (resp.choices[0].message.content or "").strip()

        # פרסינג JSON
        try:
            parsed = json.loads(content)
            summary = (parsed.get("summary", "") or "")[:2000]
        except Exception:
            parsed = None
            summary = content[:2000]

        # עדכון DB
        profile.ai_model = MODEL
        profile.ai_summary = summary
        profile.ai_json = content
        profile.ai_status = "done"
        db.commit()

        # עדכון Redis עם תוצאות + מטה
        try:
            snap["ai_status"] = "done"
            snap["ai_model"] = MODEL
            snap["ai_summary"] = summary
            snap["ai_json"] = content
            snap["ai_finished_at"] = now_iso()
            r.set(key, json.dumps(snap), ex=REDIS_TTL)

            meta = {
                "ai_input_source": source,
                "ai_started_at": snap.get("ai_started_at"),
                "ai_finished_at": snap.get("ai_finished_at"),
                "ai_status": "done",
            }
            r.set(f"{key}:ai_meta", json.dumps(meta), ex=REDIS_TTL)
        except Exception:
            pass

    except Exception as e:
        # סימון שגיאה ב-DB + ב-Redis
        try:
            profile = db.query(TraineeProfile).get(profile_id)
            if profile:
                profile.ai_status = "error"
                prev = profile.ai_summary or ""
                profile.ai_summary = (prev + f"\nAI error: {e}")[:4000]
                db.commit()
            try:
                raw = r.get(key)
                meta = {"ai_input_source": "unknown", "ai_status": "error", "ai_error": str(e), "ai_finished_at": now_iso()}
                if raw:
                    snap = json.loads(raw)
                    snap.update(meta)
                    r.set(key, json.dumps(snap), ex=REDIS_TTL)
                r.set(f"{key}:ai_meta", json.dumps(meta), ex=REDIS_TTL)
            except Exception:
                pass
        finally:
            pass
    finally:
        db.close()
