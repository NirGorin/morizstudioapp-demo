







from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException,status
from .auth import get_current_user, db_dependecy
from ..schemas import CreateStudioRequest
from ..models import Studio, User






router = APIRouter(prefix="/studio", tags=["studio"])

@router.post("/create_studio", status_code=status.HTTP_201_CREATED)
async def create_studio(db: db_dependecy, studio: CreateStudioRequest, user: Annotated[dict, Depends(get_current_user)]):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="User role not allowed to create studio")
    studio_model = Studio(
        name=studio.Name,
        studio_email=studio.Email
    )
    db.add(studio_model)
    db.commit()
    user_model = db.query(User).filter(User.id == user['id']).first()
    user_model.studio_id = studio_model.id
    db.add(user_model)
    db.commit()
    
    return {"message": "Studio created successfully", "studio_id": studio_model.id}

@router.delete("/delete_studio/{studio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_studio(studio_id: int, db: db_dependecy, user: Annotated[dict, Depends(get_current_user)]):
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="User role not allowed to delete studio")
    
    studio = db.query(Studio).filter(Studio.id == studio_id).first()
    if not studio:
        raise HTTPException(status_code=404, detail="Studio not found")

    db.delete(studio)
    db.commit()
    return {"message": "Studio deleted successfully"}

@router.create("/registering_to_studio", status_code=status.HTTP_201_CREATED)
async def register_studio(
    db: db_dependecy,studio_name: str,user: Annotated[dict, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=401, detail="User not authenticated")
    if user['role'] == 'admin':
        raise HTTPException(status_code=403, detail="User role not allowed to register studio")
    user_model = db.query(User).filter(User.id == user['id']).first()
    if user_model.studio_id:
        raise HTTPException(status_code=400, detail="User already registered to a studio")
    existing_studio = db.query(Studio).filter(Studio.name == studio_name).first()
    if existing_studio:
        user_model.studio_id = existing_studio.id
        db.add(user_model)
        db.commit()
        return {"message": "User registered to studio successfully", "studio_id": existing_studio.id}
    else:
        raise HTTPException(status_code=404, detail="Studio not found")


     

