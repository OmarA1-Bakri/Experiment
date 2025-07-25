from datetime import timedelta
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    oauth2_scheme,
    verify_password,
)
from api.middleware.rate_limiter import auth_rate_limit
from api.schemas.models import Token, UserCreate, UserResponse
from database.db_setup import get_db
from database.user import User
from services.auth_service import auth_service


class LoginRequest(BaseModel):
    email: str
    password: str

router = APIRouter()


class RegisterResponse(BaseModel):
    user: UserResponse
    tokens: Token

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit())],
)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(id=uuid4(), email=user.email, hashed_password=hashed_password, is_active=True)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create tokens for the new user (auto-login after registration)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(db_user.id)})

    return RegisterResponse(
        user=UserResponse(
            id=db_user.id,
            email=db_user.email,
            is_active=db_user.is_active,
            created_at=db_user.created_at
        ),
        tokens=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    )


@router.post("/token", response_model=Token, dependencies=[Depends(auth_rate_limit())])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
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

    # Create session for tracking
    await auth_service.create_user_session(
        user, access_token, metadata={"login_method": "form_data"}
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limit())])
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Login endpoint - accepts JSON data for compatibility with tests"""
    # Authenticate user
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Create session for tracking
    await auth_service.create_user_session(user, access_token, metadata={"login_method": "json"})

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token, dependencies=[Depends(auth_rate_limit())])
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    from api.dependencies.auth import decode_token

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(request: Request, token: str = Depends(oauth2_scheme)):
    """Logout endpoint that blacklists the current token and invalidates sessions."""
    from api.dependencies.auth import blacklist_token, decode_token
    
    if token:
        # Enhanced blacklist with metadata
        await blacklist_token(
            token, 
            reason="user_logout",
            ip_address=getattr(request.client, 'host', None),
            user_agent=request.headers.get('user-agent'),
            metadata={"logout_timestamp": datetime.utcnow().isoformat()}
        )

        # Also invalidate user sessions
        try:
            payload = decode_token(token)
            if payload and payload.get("sub"):
                user_id = UUID(payload["sub"])
                await auth_service.logout_user(user_id)
        except Exception:
            # If token decode fails, still consider logout successful
            pass

    return {"message": "Successfully logged out"}
