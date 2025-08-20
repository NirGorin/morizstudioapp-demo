#main file:
from fastapi import FastAPI
from .routers import ai
from .database import engine, Base
from .routers import users, auth, limitations, admin

app=FastAPI()
Base.metadata.create_all(bind=engine)


# app.include_router(users.router)
app.include_router(auth.router)
app.include_router(ai.router)
# app.include_router(limitations.router)
# app.include_router(admin.router)