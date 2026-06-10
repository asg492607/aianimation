import uuid
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.media import Asset, AssetType, AssetSource
from app.models.script import Scene
from app.core.logging import get_logger

logger = get_logger(__name__)

class AssetAgent:
    """
    Agent that orchestrates asset generation (images) for scenes.
    Currently mocks generation by creating DB records with metadata.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        # Ensure media directory exists
        os.makedirs("media/assets", exist_ok=True)

    async def generate_assets(self, project_id: uuid.UUID) -> list[Asset]:
        # 1. Fetch scenes
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.scene_number)
        )
        scenes = list(result.scalars().all())
        
        assets = []
        for scene in scenes:
            # MVP: We just create metadata records.
            # In the future, this calls FLUX/ComfyUI/Stable Diffusion
            asset = Asset(
                project_id=project_id,
                scene_id=scene.id,
                name=f"scene_{scene.scene_number}_bg",
                file_url="mock_url.png", # To be generated
                file_key=f"{scene.id}_bg.png",
                content_type="image/png",
                asset_type=AssetType.BACKGROUND,
                source=AssetSource.GENERATED,
                generation_prompt=scene.visual_description,
                meta={"status": "pending_generation"} # Mark as pending for future workers
            )
            self.db.add(asset)
            assets.append(asset)
            logger.info("asset_agent_planned", scene_id=str(scene.id))

        await self.db.commit()
        return assets
