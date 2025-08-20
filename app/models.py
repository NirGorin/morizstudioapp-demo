
#models file:

from sqlalchemy import Column, String, Integer, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as PgEnum
from .enums import RoleEnum, GenderEnum, LevelEnum, NumberOfWeekTrainingEnum
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(30), index=True)
    last_name = Column(String(30), index=True)
    username = Column(String(30), unique=True, index=True)
    email = Column(String(50), unique=True, index=True)
    hashed_password = Column(String)
    role   = Column(PgEnum(RoleEnum,   name="role_enum"),   nullable=False, default=RoleEnum.trainee)
    phone_number = Column(String(15), unique=True, index=True)
    studio_id = Column(Integer, ForeignKey("studios.id"))
    trainee_id = Column(Integer, ForeignKey("trainee_profiles.id"))

class Studio(Base):
    __tablename__ = "studios"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    studio_email = Column(String, unique=True, index=True)
    
class TraineeProfile(Base):
    __tablename__ = "trainee_profiles"
    id = Column(Integer, primary_key=True, index=True)
    age = Column(Integer)
    gender = Column(PgEnum(GenderEnum,name="gender_enum"), nullable=False)
    height_cm = Column(Integer)
    weight_kg = Column(Integer)
    level = Column(PgEnum(LevelEnum, name="level_enum"), nullable=False, default=LevelEnum.beginner)
    number_of_week_training = Column(PgEnum(NumberOfWeekTrainingEnum, name="number_of_week_training_enum"), nullable=False, default=NumberOfWeekTrainingEnum.one)

    user_id = Column(Integer, ForeignKey("users.id"))
    limitations = Column(Text, nullable=True)
    ai_status  = Column(String(16), default="idle", nullable=False)  
    ai_model   = Column(String(64))
    ai_summary = Column(Text)
    ai_json    = Column(Text)


    
