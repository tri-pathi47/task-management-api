
from fastapi import FastAPI

from app.auth import router as auth_router

app = FastAPI(title="Task Management API")

app.include_router(auth_router)


@app.get("/")
def home():
    return {"message": "Task Management API is running"}
