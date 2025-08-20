
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
import json
import os
from ..database import SessionMoriz
from ..models import TraineeProfile, User
from ..services.ai_service import process_profile_in_background, _build_user_prompt
from ..schemas import CreateTraineeProfileRequest
from ..routers.auth import get_current_user, db_dependecy






router = APIRouter(prefix="/trainee_profile", tags=["trainee_profile"])



@router.post("/create_trainee_profile", status_code=status.HTTP_201_CREATED)
async def create_trainee_profile(
    background_tasks: BackgroundTasks,
    db: db_dependecy,
    profile: CreateTraineeProfileRequest,
    user: Annotated[dict, Depends(get_current_user)],
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
    background_tasks.add_task(process_profile_in_background, trainee_profile.id)

    return {"message": "Trainee profile created successfully", "profile_id": trainee_profile.id}

@router.delete("/delete_trainee_profile/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trainee_profile(profile_id: int, db: db_dependecy, user: Annotated[dict, Depends(get_current_user)]):
    if user['role'] == 'trainer':
        raise HTTPException(status_code=403, detail="User role not allowed to delete trainee profile")
    
    profile = db.query(TraineeProfile).filter(TraineeProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Trainee profile not found")

    db.delete(profile)
    db.commit()
    return {"message": "Trainee profile deleted successfully"}

