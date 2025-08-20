# app/services/ai_service.py
import os, json
from openai import OpenAI
from sqlalchemy.orm import Session
from ..database import SessionMoriz
from ..models import TraineeProfile

MODEL = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
print(f"[AI] Using model: {repr(MODEL)}", flush=True)

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

def process_profile_in_background(profile_id: int) -> None:
    db: Session = SessionMoriz()
    try:
        profile = db.query(TraineeProfile).get(profile_id)
        if not profile:
            return
        profile.ai_status = "processing"
        db.commit()

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        resp = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(profile)},
            ],
        )
        content = resp.choices[0].message.content.strip()

        # ננסה לפרסר JSON; אם לא מצליח—נשמור את הטקסט כמו שהוא
        summary = ""
        try:
            parsed = json.loads(content)
            summary = parsed.get("summary", "")[:2000]
        except Exception:
            parsed = None
            summary = content[:2000]

        profile.ai_model = MODEL
        profile.ai_summary = summary
        profile.ai_json = content
        profile.ai_status = "done"
        db.commit()

    except Exception as e:
        # ניסיון עדין לסמן שגיאה על הפרופיל
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
