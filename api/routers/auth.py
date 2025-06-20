from datetime import timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.dependencies.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    validate_password,
    verify_password,
)
from api.middleware.rate_limiter import auth_rate_limit
from api.schemas.models import Token, UserCreate, UserResponse
from database.db_setup import get_db
from database.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse, dependencies=[Depends(auth_rate_limit())])
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Validate password
    is_valid, message = validate_password(user.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        id=uuid4(),
        email=user.email,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@router.post("/token", response_model=Token, dependencies=[Depends(auth_rate_limit())])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Authenticate user
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=Token, dependencies=[Depends(auth_rate_limit())])
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    from api.dependencies.auth import decode_token

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout():
    # In a JWT-based system, logout is typically handled client-side
    # You could implement token blacklisting here if needed
    return {"message": "Successfully logged out"}
