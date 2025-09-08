# app/routers/registrations.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Annotated

from ..models import Studio, User
from .auth import get_current_user, db_dependecy
from ..schemas import CreateStudioRequest
from ..services.events import publish_event

router = APIRouter(prefix="/registrations", tags=["registrations"])

@router.post("/registering_to_studio", status_code=status.HTTP_201_CREATED)
async def register_studio(
    db: db_dependecy,
    studio_name: str,
    user: Annotated[dict, Depends(get_current_user)]
):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authenticated")

    user_model = db.query(User).filter(User.id == user["id"]).first()
    if user_model.studio_id:
        raise HTTPException(status_code=400, detail="User already registered to a studio")

    existing_studio = db.query(Studio).filter(Studio.name == studio_name).first()
    if not existing_studio:
        raise HTTPException(status_code=404, detail="Studio not found")

    user_model.studio_id = existing_studio.id
    db.add(user_model)
    db.commit()

    # אירוע עסקי — השליח יהיה Lambda notification-dispatcher
    publish_event(
        "trainee.registered",
        {
            "studio_id": existing_studio.id,
            "studio_name": existing_studio.name,
            "trainee_user_id": user_model.id,
            "trainee_email": getattr(user_model, "email", None),
        },
    )

    return {"message": "User registered to studio successfully", "studio_id": existing_studio.id}
