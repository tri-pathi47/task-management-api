
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models
from app.auth import router as auth_router
from app.database import initialize_database
from app.routes import router as tasks_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Task Management API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(tasks_router)


@app.get("/")
def home():
    return {"message": "Task Management API is running"}
