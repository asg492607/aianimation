from typing import Optional, List
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Asset, Voiceover, RenderJob, Export, RenderStatus
from app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[Asset]):
    def __init__(self, db: AsyncSession):
        super().__init__(Asset, db)

    async def get_by_project(self, project_id: uuid.UUID) -> List[Asset]:
        result = await self.db.execute(
            select(Asset)
            .where(Asset.project_id == project_id)
            .order_by(Asset.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_scene(self, scene_id: uuid.UUID) -> List[Asset]:
        result = await self.db.execute(
            select(Asset).where(Asset.scene_id == scene_id)
        )
        return result.scalars().all()


class VoiceoverRepository(BaseRepository[Voiceover]):
    def __init__(self, db: AsyncSession):
        super().__init__(Voiceover, db)

    async def get_by_project(self, project_id: uuid.UUID) -> List[Voiceover]:
        result = await self.db.execute(
            select(Voiceover)
            .where(Voiceover.project_id == project_id)
            .order_by(Voiceover.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_scene(self, scene_id: uuid.UUID) -> Optional[Voiceover]:
        result = await self.db.execute(
            select(Voiceover)
            .where(Voiceover.scene_id == scene_id)
            .order_by(Voiceover.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class RenderJobRepository(BaseRepository[RenderJob]):
    def __init__(self, db: AsyncSession):
        super().__init__(RenderJob, db)

    async def get_by_project(self, project_id: uuid.UUID) -> List[RenderJob]:
        result = await self.db.execute(
            select(RenderJob)
            .where(RenderJob.project_id == project_id)
            .order_by(RenderJob.created_at.desc())
        )
        return result.scalars().all()

    async def get_active_job(self, project_id: uuid.UUID) -> Optional[RenderJob]:
        result = await self.db.execute(
            select(RenderJob)
            .where(
                RenderJob.project_id == project_id,
                RenderJob.status.in_([RenderStatus.QUEUED, RenderStatus.PROCESSING]),
            )
            .order_by(RenderJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_celery_task(self, task_id: str) -> Optional[RenderJob]:
        result = await self.db.execute(
            select(RenderJob).where(RenderJob.celery_task_id == task_id)
        )
        return result.scalar_one_or_none()


class ExportRepository(BaseRepository[Export]):
    def __init__(self, db: AsyncSession):
        super().__init__(Export, db)

    async def get_by_project(self, project_id: uuid.UUID) -> List[Export]:
        result = await self.db.execute(
            select(Export)
            .where(Export.project_id == project_id)
            .order_by(Export.created_at.desc())
        )
        return result.scalars().all()
