#main file:
from fastapi import FastAPI

from .database import engine, Base
from .routers import auth,studio, trainee_profile,users

app=FastAPI()
Base.metadata.create_all(bind=engine)


# app.include_router(users.router)
app.include_router(auth.router)
app.include_router(studio.router)
app.include_router(trainee_profile.router)
app.include_router(users.router)

# app.include_router(limitations.router)
# app.include_router(admin.router)