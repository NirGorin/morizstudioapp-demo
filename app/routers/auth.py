#routers.auth file:
from datetime import timedelta, datetime, UTC
from typing import Annotated
from ..services.ai_service import process_profile_in_background
from fastapi import HTTPException, Depends, APIRouter, status,BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
from sqlalchemy.testing.pickleable import User
<<<<<<< Updated upstream
=======
from app.schemas import CreateUserRequest, CreateTraineeProfileRequest, Token
>>>>>>> Stashed changes

from ..database import SessionMoriz
from ..models import Studio, User, TraineeProfile

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
token_jwt = Annotated[str,Depends(oauth2_scheme)]

bcryptcontext=CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db=SessionMoriz()
    try:
        yield db
    finally:
        db.close()

db_dependecy = Annotated[Session,Depends(get_db)]

ALGORITHM = os.getenv("ALGORITHM")
SECRET_KEY= os.getenv("SECRET_KEY") 
class CreateUserRequest(BaseModel):
    First_Name : str
    Last_Name : str
    Username : str
    Email : str
    Password : str
    Role: str
    Phone_Number: str

class CreateTraineeProfileRequest(BaseModel):
    Age: int
    Gender: str
    Height: int
    Weight: int
    Level: str
    Number_Of_Week_Training: str
    Limitation: str = None

class CreateStudioRequest(BaseModel):
    Name: str
    Email: str


    


class Token(BaseModel):
    access_token: str
    token_type: str

def authenticate_user(username: str, password: str, db: db_dependecy):
    user_model= db.query(User).filter(User.username == username).first()
    if not user_model or not bcryptcontext.verify(password, user_model.hashed_password):
        return False
    return user_model


def create_access_token(username: str,id: int, Role: str, expires_delta: timedelta ):
    to_encode = {"username": username, "id": id, "role": Role}
    expires_time = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expires_time})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: token_jwt):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        username: str = payload.get('username')
        user_id: str = payload.get('id')
        role: str = payload.get('role')
        if not username or not user_id:
            raise HTTPException(status_code=401, detail="Username not found")
        return {'username': username, 'id': user_id, 'role': role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate user")

@router.post("/create_trainer",status_code=status.HTTP_201_CREATED)
async def create_trainer(db: db_dependecy, user: CreateUserRequest):
    user_model=User(
        first_name=user.First_Name,
        last_name=user.Last_Name,
        username=user.Username,
        email=user.Email,
        hashed_password=bcryptcontext.hash(user.Password),
        phone_number=user.Phone_Number,
        role=user.Role,
        )
    db.add(user_model)
    db.commit()

@router.post("/login",response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],db: db_dependecy):
    user_model = authenticate_user(form_data.username, form_data.password, db)
    if not user_model:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(user_model.username, user_model.id, user_model.role, timedelta(minutes=20))
    return {'access_token': token, 'token_type': 'bearer'}


# @router.post("/create_trainee_profile", status_code=status.HTTP_201_CREATED)
# async def create_trainee_profile(db: db_dependecy, profile: CreateTraineeProfileRequest, user: token_jwt = Depends(get_current_user)):
#     if user['role'] == 'trainer':
#         raise HTTPException(status_code=403, detail="User role not allowed to create trainee profile")
#     trainee_profile = TraineeProfile(
#         age=profile.Age,
#         height_cm=profile.Height,
#         weight_kg=profile.Weight,
#         level=profile.Level,
#         number_of_week_training=profile.Number_Of_Week_Training,
#         limitations=profile.Limitation,
#         user_id=user['id'],
#     )
#     db.add(trainee_profile)
#     db.commit()
#     return {"message": "Trainee profile created successfully", "profile_id": trainee_profile.id}
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
    return {"message": "Studio created successfully", "studio_id": studio_model.id}

# יצירת פרופיל — הוספת BackgroundTasks ושיגור AI
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

    # ✅ משימת רקע — לא חוסם את הבקשה
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

