"""User system — registration, authentication, JWT tokens."""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
JWT_SECRET = os.getenv("GODOTFORGE_JWT_SECRET", "godotforge-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("GODOTFORGE_JWT_EXPIRE_MINUTES", "1440"))  # 24h

USERS_FILE = Path(os.getenv("GODOTFORGE_USERS_FILE", "/tmp/godotforge/users.json"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(default="", max_length=64)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ---------------------------------------------------------------------------
# JSON file store helpers
# ---------------------------------------------------------------------------

def _ensure_store() -> Path:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]")
    return USERS_FILE


def _load_users() -> list[dict]:
    _ensure_store()
    try:
        data = json.loads(USERS_FILE.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_users(users: list[dict]) -> None:
    _ensure_store()
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False))


def _find_user(*, username: str | None = None, user_id: str | None = None, email: str | None = None) -> dict | None:
    for u in _load_users():
        if username and u["username"] == username:
            return u
        if user_id and u["id"] == user_id:
            return u
        if email and u["email"] == email:
            return u
    return None


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_token(user_id: str, username: str) -> tuple[str, int]:
    expires = JWT_EXPIRE_MINUTES
    payload = {
        "sub": user_id,
        "username": username,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires * 60  # seconds


def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    """FastAPI dependency that extracts and validates the current user from a JWT."""
    payload = _decode_token(token)
    user = _find_user(user_id=payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate):
    """Create a new user account and return a JWT token."""
    if _find_user(username=body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if _find_user(email=body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": uuid.uuid4().hex,
        "username": body.username,
        "email": body.email,
        "display_name": body.display_name or body.username,
        "password_hash": _hash_password(body.password),
        "created_at": now,
    }

    users = _load_users()
    users.append(user)
    _save_users(users)

    token, expires_in = _create_token(user["id"], user["username"])
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            display_name=user["display_name"],
            created_at=user["created_at"],
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Authenticate with username + password, return JWT."""
    user = _find_user(username=form.username)
    if user is None or not _verify_password(form.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token, expires_in = _create_token(user["id"], user["username"])
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            display_name=user["display_name"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"],
        display_name=current_user["display_name"],
        created_at=current_user["created_at"],
    )
