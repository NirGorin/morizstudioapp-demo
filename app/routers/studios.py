# app/routers/studios.py
import re
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Annotated
from ..models import Studio, User
from ..schemas import CreateStudioRequest
from ..services.events import publish_event
from .auth import get_current_user,db_dependecy

router = APIRouter(prefix="/studios", tags=["studios"])

def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "studio"

@router.post("/create_studio", status_code=status.HTTP_201_CREATED)
async def create_studio(
    db: db_dependecy,
    studio: CreateStudioRequest,
    user: Annotated[dict, Depends(get_current_user)]
):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="User role not allowed to create studio")

    studio_model = Studio(name=studio.Name, studio_email=studio.Email)
    db.add(studio_model)
    db.commit()
    db.refresh(studio_model)

    # משייכים את המשתמש לסטודיו שנוצר
    user_model = db.query(User).filter(User.id == user["id"]).first()
    user_model.studio_id = studio_model.id
    db.add(user_model)
    db.commit()

    # מפרסמים אירוע provisioning אסינכרוני
    publish_event(
        "studio.created",
        {
            "studio_id": studio_model.id,
            "studio_name": studio_model.name,
            "studio_slug": _slugify(studio_model.name),
            "studio_email": studio_model.studio_email,
            "owner_user_id": user_model.id,
        },
    )

    return {
        "message": "Studio created successfully",
        "studio_id": studio_model.id
    }
