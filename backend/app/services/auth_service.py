from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    create_password_reset_token,
    create_email_verification_token,
)
from app.core.exceptions import UnauthorizedError, ConflictError, ValidationError, NotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, LoginRequest, Token
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: RegisterRequest) -> User:
        if await self.user_repo.email_exists(data.email.lower()):
            raise ConflictError("Email already registered")
        if await self.user_repo.username_exists(data.username.lower()):
            raise ConflictError("Username already taken")

        user = await self.user_repo.create({
            "email": data.email.lower(),
            "username": data.username.lower(),
            "hashed_password": get_password_hash(data.password),
            "full_name": data.full_name,
            "is_active": True,
            "is_verified": False,
        })
        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    async def login(self, data: LoginRequest) -> Token:
        user = await self.user_repo.get_by_email(data.email.lower())
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is deactivated")

        extra = {"role": user.role.value, "username": user.username}
        access_token = create_access_token(user.id, extra)
        refresh_token = create_refresh_token(user.id)

        logger.info("user_logged_in", user_id=str(user.id))
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_tokens(self, refresh_token: str) -> Token:
        user_id = verify_token(refresh_token, "refresh")
        user = await self.user_repo.get_active_user_by_id_str(user_id)
        if not user:
            raise UnauthorizedError("User not found or inactive")

        extra = {"role": user.role.value, "username": user.username}
        new_access = create_access_token(user.id, extra)
        new_refresh = create_refresh_token(user.id)
        return Token(access_token=new_access, refresh_token=new_refresh)

    async def forgot_password(self, email: str) -> str:
        user = await self.user_repo.get_by_email(email.lower())
        if not user:
            # Don't reveal if email exists
            return "If that email is registered, a reset link has been sent."
        token = create_password_reset_token(email)
        # In production: send email with reset link
        logger.info("password_reset_requested", email=email)
        return token

    async def reset_password(self, token: str, new_password: str) -> bool:
        email = verify_token(token, "access")  # password reset uses access secret
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError("User", email)
        await self.user_repo.update(user, {"hashed_password": get_password_hash(new_password)})
        logger.info("password_reset_completed", email=email)
        return True

    async def verify_email(self, token: str) -> bool:
        email = verify_token(token, "access")
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise NotFoundError("User", email)
        await self.user_repo.update(user, {"is_verified": True})
        logger.info("email_verified", email=email)
        return True

    async def get_email_verification_token(self, email: str) -> str:
        return create_email_verification_token(email)
