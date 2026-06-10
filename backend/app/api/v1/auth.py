"""
Auth router — register, login, refresh. All users stored in-memory.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
import re

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_users

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]{3,50}$", v):
            raise ValueError("Username must be 3-50 chars, alphanumeric, underscore or dash only")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    users = get_users()
    # Check for duplicate email
    for u in users.values():
        if u["email"] == req.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    users[user_id] = {
        "id": user_id,
        "email": req.email,
        "username": req.username,
        "full_name": req.full_name,
        "hashed_password": get_password_hash(req.password),
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
async def login(req: LoginRequest):
    users = get_users()
    user = next((u for u in users.values() if u["email"] == req.email), None)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(user["id"])
    refresh_token = create_refresh_token(user["id"])
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshTokenRequest):
    user_id = verify_token(req.refresh_token, "refresh")
    access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)
    return Token(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me")
async def get_me(token: str = ""):
    # Simple endpoint — real auth guard is in dependencies.py
    return {"message": "Use Authorization: Bearer <token> header"}
