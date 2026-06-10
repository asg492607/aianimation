from typing import Optional, List
import uuid

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.script import Script, Scene, Storyboard
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, db: AsyncSession):
        super().__init__(Project, db)

    async def get_by_owner(self, owner_id: uuid.UUID, page: int = 1, size: int = 20):
        return await self.get_multi(
            page=page,
            size=size,
            filters=[Project.owner_id == owner_id],
        )

    async def get_with_details(self, project_id: uuid.UUID) -> Optional[Project]:
        result = await self.db.execute(
            select(Project)
            .options(
                selectinload(Project.scripts),
                selectinload(Project.scenes),
                selectinload(Project.render_jobs),
            )
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_owner_project(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[Project]:
        result = await self.db.execute(
            select(Project).where(
                and_(Project.id == project_id, Project.owner_id == owner_id)
            )
        )
        return result.scalar_one_or_none()


class ScriptRepository(BaseRepository[Script]):
    def __init__(self, db: AsyncSession):
        super().__init__(Script, db)

    async def get_by_project(self, project_id: uuid.UUID) -> List[Script]:
        result = await self.db.execute(
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.created_at.desc())
        )
        return result.scalars().all()

    async def get_latest_for_project(self, project_id: uuid.UUID) -> Optional[Script]:
        result = await self.db.execute(
            select(Script)
            .where(Script.project_id == project_id)
            .order_by(Script.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


class SceneRepository(BaseRepository[Scene]):
    def __init__(self, db: AsyncSession):
        super().__init__(Scene, db)

    async def get_by_project(self, project_id: uuid.UUID) -> List[Scene]:
        result = await self.db.execute(
            select(Scene)
            .where(Scene.project_id == project_id)
            .order_by(Scene.scene_number)
        )
        return result.scalars().all()

    async def get_by_script(self, script_id: uuid.UUID) -> List[Scene]:
        result = await self.db.execute(
            select(Scene)
            .where(Scene.script_id == script_id)
            .order_by(Scene.scene_number)
        )
        return result.scalars().all()


class StoryboardRepository(BaseRepository[Storyboard]):
    def __init__(self, db: AsyncSession):
        super().__init__(Storyboard, db)

    async def get_by_scene(self, scene_id: uuid.UUID) -> Optional[Storyboard]:
        result = await self.db.execute(
            select(Storyboard).where(Storyboard.scene_id == scene_id)
        )
        return result.scalar_one_or_none()
