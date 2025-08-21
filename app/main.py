#main file:
from fastapi import FastAPI
from .routers import ai
from .database import engine, Base
<<<<<<< Updated upstream
from .routers import users, auth, limitations, admin
=======
from .routers import auth,studio, trainee_profile,users
>>>>>>> Stashed changes

app=FastAPI()
Base.metadata.create_all(bind=engine)


# app.include_router(users.router)
app.include_router(auth.router)
<<<<<<< Updated upstream
app.include_router(ai.router)
=======
app.include_router(studio.router)
app.include_router(trainee_profile.router)
app.include_router(users.router)

>>>>>>> Stashed changes
# app.include_router(limitations.router)
# app.include_router(admin.router)