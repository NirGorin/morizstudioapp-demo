#database file:
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

engine=create_engine(DATABASE_URL,pool_pre_ping=True)
SessionMoriz=sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base=declarative_base()