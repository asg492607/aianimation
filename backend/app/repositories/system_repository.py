from typing import Optional, List
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import Notification, AuditLog, ActivityLog, APIKey, Template, Setting
from app.repositories.base import BaseRepository
from app.core.security import generate_api_key, get_password_hash


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)

    async def get_by_user(self, user_id: uuid.UUID, unread_only: bool = False) -> List[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        query = query.order_by(Notification.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        from sqlalchemy import update
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id)
            .values(is_read=True)
        )


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(AuditLog, db)

    async def log(
        self,
        action: str,
        user_id: Optional[uuid.UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        return await self.create({
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
            "user_agent": user_agent,
        })


class ActivityLogRepository(BaseRepository[ActivityLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(ActivityLog, db)

    async def log(self, user_id: uuid.UUID, event: str, description: str = "", meta: Optional[dict] = None):
        return await self.create({
            "user_id": user_id,
            "event": event,
            "description": description,
            "meta": meta,
        })


class APIKeyRepository(BaseRepository[APIKey]):
    def __init__(self, db: AsyncSession):
        super().__init__(APIKey, db)

    async def create_key(self, user_id: uuid.UUID, name: str, scopes: Optional[dict] = None) -> tuple[APIKey, str]:
        raw_key = generate_api_key()
        key_hash = get_password_hash(raw_key)
        prefix = raw_key[:10]

        api_key = await self.create({
            "user_id": user_id,
            "name": name,
            "key_hash": key_hash,
            "key_prefix": prefix,
            "scopes": scopes,
        })
        return api_key, raw_key

    async def get_by_prefix(self, prefix: str) -> Optional[APIKey]:
        result = await self.db.execute(
            select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: uuid.UUID) -> List[APIKey]:
        result = await self.db.execute(
            select(APIKey).where(APIKey.user_id == user_id, APIKey.is_active == True)
        )
        return result.scalars().all()


class TemplateRepository(BaseRepository[Template]):
    def __init__(self, db: AsyncSession):
        super().__init__(Template, db)

    async def get_public(self, page: int = 1, size: int = 20):
        return await self.get_multi(
            page=page,
            size=size,
            filters=[Template.is_public == True],
        )

    async def get_featured(self) -> List[Template]:
        result = await self.db.execute(
            select(Template).where(Template.is_featured == True, Template.is_public == True)
        )
        return result.scalars().all()
