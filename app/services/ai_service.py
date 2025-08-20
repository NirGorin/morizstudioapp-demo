# app/services/ai_service.py
import os, json, hashlib
from datetime import datetime, timezone
from openai import OpenAI
from sqlalchemy.orm import Session
from ..database import SessionMoriz
from ..models import TraineeProfile, User, Studio
from .storage_service import build_s3_key, put_json_to_s3
from .cache_service import cache_set
from .events_service import publish_ai_summary_created

MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
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

def _slugify(name: str) -> str:
    import re
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s_-]+", "", s)
    s = re.sub(r"[\s]+", "-", s)
    return s or "studio"

def _build_user_prompt(profile: TraineeProfile) -> str:
    gender = getattr(profile.gender, "name", None) or str(profile.gender)
    level  = getattr(profile.level, "name", None) or str(profile.level)
    freq   = getattr(profile.number_of_week_training, "name", None) or str(profile.number_of_week_training)
    return (
        f"age: {profile.age}\n"
        f"gender: {gender}\n"
        f"level: {level}\n"
        f"weekly_training_frequency: {freq}\n"
        f"medical_limitations_free_text: {profile.limitations or ''}\n"
        "Return JSON only."
    )

def _call_openai(prompt: str) -> dict:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content.strip()
    data = json.loads(content)  # אם זה ייכשל – החריג ייתפס למטה
    # Normalize structure
    return {
        "summary": data.get("summary", ""),
        "avoid":   data.get("avoid", []),
        "caution": data.get("caution", []),
        "safe":    data.get("safe", []),
    }

def process_profile_in_background(profile_id: int) -> None:
    db: Session = SessionMoriz()
    try:
        profile = db.query(TraineeProfile).get(profile_id)
        if not profile:
            return
        profile.ai_status = "processing"
        db.commit()

        # סטודיו (ל־slug) + user_id
        user = db.query(User).filter((User.trainee_id == profile.id) | (User.id == profile.user_id)).first()
        studio = db.query(Studio).get(user.studio_id) if user and user.studio_id else None
        studio_slug = _slugify(getattr(studio, "name", None))

        # 1) OpenAI → JSON
        prompt = _build_user_prompt(profile)
        ai_json = _call_openai(prompt)

        # 2) שמירה עמידה – S3
        s3_key = build_s3_key(studio_slug, user.id if user else profile.id)
        put_json_to_s3(ai_json, s3_key)

        # 3) מצביע ב־DB (בשדה הקיים ai_json) + תקציר טקסט קצר (ai_summary)
        pointer = {
            "s3_key": s3_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(json.dumps(ai_json, sort_keys=True).encode("utf-8")).hexdigest(),
            "version": 1,
        }
        profile.ai_model   = MODEL
        profile.ai_summary = (ai_json.get("summary") or "")[:2000]
        profile.ai_json    = json.dumps(pointer)  # << רק מצביע, לא כל ה-JSON
        profile.ai_status  = "ready"
        db.commit()

        # 4) קאש מהיר (Redis) – אופציונלי
        cache_set(user.id if user else profile.id, ai_json)

        # 5) אירוע מערכת (SNS)
        publish_ai_summary_created(user.id if user else profile.id, studio_slug, s3_key, inline_json=ai_json)

    except Exception as e:
        try:
            profile = db.query(TraineeProfile).get(profile_id)
            if profile:
                profile.ai_status = "error"
                prev = profile.ai_summary or ""
                profile.ai_summary = (prev + f"\nAI error: {e}")[:4000]
                db.commit()
        finally:
            pass
    finally:
        db.close()
