from typing import Annotated

import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


router = APIRouter(prefix="/auth", tags=["authentication"])


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        if credentials is None:
            raise unauthorized

        token = credentials.credentials
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not isinstance(user_id, str) or not user_id.isdigit():
            raise unauthorized

    except jwt.InvalidTokenError:
        raise unauthorized

    user = db.query(User).filter(User.id == int(user_id)).first()

    if user is None or not user.is_active:
        raise unauthorized

    return user

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    existing_user = db.query(User).filter(
        (User.email == user_data.email)
        | (User.username == user_data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user = User(
        username=user_data.username,
        email=str(user_data.email),
        hashed_password=hash_password(user_data.password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    return user


@router.post("/login", response_model=TokenResponse)
def login_user(
    credentials: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    user = db.query(User).filter(
        User.email == str(credentials.email)
    ).first()

    if (
        user is None
        or not verify_password(
            credentials.password,
            user.hashed_password,
        )
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))

    return TokenResponse(access_token=token)



@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user
