import uuid
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.engines.render_engine import FFmpegRenderEngine, SceneFrame
from app.models.media import RenderJob, RenderStatus
from app.models.advanced import Timeline
from app.models.script import Scene
from app.core.logging import get_logger

logger = get_logger(__name__)

class RenderService:
    """
    Acts as the bridge between RenderJob DB records and FFmpeg execution.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = FFmpegRenderEngine()
        os.makedirs("media/renders", exist_ok=True)
        os.makedirs("media/temp", exist_ok=True)

    async def execute_render_job(self, job_id: uuid.UUID) -> str:
        job = await self.db.get(RenderJob, job_id)
        if not job:
            raise ValueError(f"Render job {job_id} not found")
            
        job.status = RenderStatus.PROCESSING
        await self.db.commit()

        try:
            # 1. Fetch Timeline Entries
            result = await self.db.execute(
                select(Timeline)
                .where(Timeline.project_id == job.project_id)
                .order_by(Timeline.start_time)
            )
            timelines = list(result.scalars().all())
            
            if not timelines:
                raise ValueError("No timeline entries found")

            # 2. Build Scene Frames
            scene_videos = []
            for t in timelines:
                scene = await self.db.get(Scene, t.scene_id)
                if not scene:
                    continue
                    
                # In MVP, we fetch the first voiceover and asset directly
                voiceover_url = None
                if scene.voiceovers and len(scene.voiceovers) > 0:
                    voiceover_url = scene.voiceovers[0].file_url
                    
                image_url = None
                if scene.assets and len(scene.assets) > 0:
                    image_url = scene.assets[0].file_url
                
                # If no image URL, it will fallback to background_color
                frame = SceneFrame(
                    duration=t.end_time - t.start_time,
                    background_color=scene.background_color or "#000000",
                    image_path=image_url if image_url and os.path.exists(image_url) else None,
                    audio_path=voiceover_url if voiceover_url and os.path.exists(voiceover_url) else None,
                    text=scene.narration if not voiceover_url else None, # Fallback to text if no audio
                    transition_in=t.meta.get("transition_in", "cut") if t.meta else "cut",
                    transition_out=t.meta.get("transition_out", "cut") if t.meta else "cut"
                )
                
                out_path = f"media/temp/{t.id}.mp4"
                await self.engine.render_scene_to_video(frame, out_path)
                scene_videos.append(out_path)

            # 3. Concatenate
            final_output = f"media/renders/{job.id}.mp4"
            await self.engine.concatenate_videos(scene_videos, final_output)

            # 4. Cleanup Temp
            for video in scene_videos:
                if os.path.exists(video):
                    os.remove(video)

            # 5. Update Job
            job.status = RenderStatus.COMPLETED
            job.output_url = final_output
            await self.db.commit()
            
            logger.info("render_service_completed", job_id=str(job.id))
            return final_output

        except Exception as e:
            job.status = RenderStatus.FAILED
            job.error_message = str(e)
            await self.db.commit()
            logger.error("render_service_failed", job_id=str(job.id), error=str(e))
            raise
