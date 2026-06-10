from typing import Optional
import uuid

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token, verify_password
from app.core.exceptions import UnauthorizedError, ForbiddenError
from app.db.session import get_db
from app.db.cache import get_cache_service, CacheService
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.system_repository import APIKeyRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
) -> User:
    if not token and not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token:
        if await cache.is_blacklisted(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

        user_id_str = verify_token(token, "access")
        user_repo = UserRepository(db)
        user = await user_repo.get_active_user_by_id_str(user_id_str)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    if api_key:
        if not api_key.startswith("aai_"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")
        prefix = api_key[:10]
        api_key_repo = APIKeyRepository(db)
        key_obj = await api_key_repo.get_by_prefix(prefix)
        if not key_obj:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        if not verify_password(api_key, key_obj.key_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        user_repo = UserRepository(db)
        user = await user_repo.get_active_user(key_obj.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def require_roles(*roles: UserRole):
    async def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in roles and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in roles]}",
            )
        return current_user
    return _check


def require_admin():
    return require_roles(UserRole.ADMIN)


def require_creator():
    return require_roles(UserRole.ADMIN, UserRole.CREATOR)


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        user_id_str = verify_token(token, "access")
        user_repo = UserRepository(db)
        return await user_repo.get_active_user_by_id_str(user_id_str)
    except Exception:
        return None
