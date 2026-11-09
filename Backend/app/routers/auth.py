from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
):
    # Normalize email
    email = str(data.email).lower()

    # Check whether username or email already exists
    existing_user = db.scalar(
        select(User).where(
            or_(
                User.username == data.username,
                User.email == email,
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    # Hash password
    try:
        password_hash = hash_password(data.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # Create user
    user = User(
        username=data.username,
        email=email,
        password_hash=password_hash,
        role=UserRole.user,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    db.refresh(user)

    # Generate JWT
    token = create_access_token(user)

    return RegisterResponse(
        user=UserResponse.model_validate(user),
        token=token,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    email = str(data.email).lower()

    # Find user
    user = db.scalar(select(User).where(User.email == email))

    # Verify credentials
    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT
    token = create_access_token(user)

    return TokenResponse(token=token)


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user
