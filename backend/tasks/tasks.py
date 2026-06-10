import asyncio
import uuid
import os
import tempfile
import zipfile
import json
from datetime import datetime, timezone

from celery import shared_task
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.core.logging import get_logger

logger = get_task_logger(__name__)


def run_async(coro):
    """Run async code in celery task context"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Script Tasks ──────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, name="app.tasks.script_tasks.generate_script")
def generate_script_task(self, project_id: str, prompt: str, num_scenes: int = 5):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.engines.script_engine import ScriptGenerator
        from app.models.project import ProjectStatus
        from app.repositories.project_repository import ProjectRepository

        async with AsyncSessionLocal() as db:
            project_repo = ProjectRepository(db)
            project = await project_repo.get(uuid.UUID(project_id))
            if not project:
                raise ValueError(f"Project {project_id} not found")

            await project_repo.update(project, {"status": ProjectStatus.GENERATING})

            try:
                generator = ScriptGenerator(db)
                result = await generator.generate(prompt, uuid.UUID(project_id), num_scenes)
                await db.commit()
                return {"script_id": str(result["script"].id), "status": "completed"}
            except Exception as e:
                await project_repo.update(project, {"status": ProjectStatus.FAILED})
                await db.commit()
                raise

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Scene Tasks ───────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, name="app.tasks.scene_tasks.generate_scenes")
def generate_scenes_task(self, project_id: str, script_id: str):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.engines.scene_engine import ScenePlanner

        async with AsyncSessionLocal() as db:
            planner = ScenePlanner(db)
            scenes = await planner.generate_scenes_from_script(
                uuid.UUID(project_id), uuid.UUID(script_id)
            )
            await db.commit()
            return {"scenes_created": len(scenes), "status": "completed"}

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Voice Tasks ───────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=3, default_retry_delay=30, name="app.tasks.voice_tasks.generate_voiceover")
def generate_voiceover_task(self, voiceover_id: str):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.engines.voice_engine import VoiceEngine
        from app.repositories.media_repository import VoiceoverRepository
        from app.models.media import VoiceoverStatus
        from app.storage.providers import storage_provider

        async with AsyncSessionLocal() as db:
            vo_repo = VoiceoverRepository(db)
            voiceover = await vo_repo.get(uuid.UUID(voiceover_id))
            if not voiceover:
                raise ValueError(f"Voiceover {voiceover_id} not found")

            await vo_repo.update(voiceover, {"status": VoiceoverStatus.GENERATING})
            await db.commit()

            try:
                engine = VoiceEngine()
                audio_data, duration = await engine.generate_voiceover(
                    voiceover.text,
                    voice_id=voiceover.voice_id,
                    speed=voiceover.speed,
                    language=voiceover.language,
                )

                key = storage_provider.generate_key("voiceovers", "audio.wav")
                url = await storage_provider.upload(audio_data, key, "audio/wav")

                await vo_repo.update(voiceover, {
                    "file_url": url,
                    "file_key": key,
                    "duration_seconds": duration,
                    "status": VoiceoverStatus.COMPLETED,
                })
                await db.commit()
                return {"voiceover_id": voiceover_id, "duration": duration, "status": "completed"}
            except Exception as e:
                await vo_repo.update(voiceover, {
                    "status": VoiceoverStatus.FAILED,
                    "error_message": str(e),
                })
                await db.commit()
                raise

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Render Tasks ──────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=2, default_retry_delay=60, name="app.tasks.render_tasks.render_project")
def render_project_task(self, render_job_id: str):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.engines.render_engine import FFmpegRenderEngine, RenderConfig, SceneFrame
        from app.repositories.project_repository import SceneRepository
        from app.repositories.media_repository import RenderJobRepository, AssetRepository, VoiceoverRepository
        from app.models.media import RenderStatus
        from app.storage.providers import storage_provider
        import time

        async with AsyncSessionLocal() as db:
            rj_repo = RenderJobRepository(db)
            render_job = await rj_repo.get(uuid.UUID(render_job_id))
            if not render_job:
                raise ValueError(f"RenderJob {render_job_id} not found")

            await rj_repo.update(render_job, {"status": RenderStatus.PROCESSING, "progress": 5})
            await db.commit()

            start_time = time.time()

            try:
                config = RenderConfig(
                    resolution=render_job.resolution or "1920x1080",
                    fps=render_job.fps,
                    format=render_job.format,
                )
                engine = FFmpegRenderEngine(config)

                scene_repo = SceneRepository(db)
                scenes = await scene_repo.get_by_project(render_job.project_id)

                if not scenes:
                    raise ValueError("No scenes found for project")

                vo_repo = VoiceoverRepository(db)
                asset_repo = AssetRepository(db)

                with tempfile.TemporaryDirectory() as tmpdir:
                    scene_videos = []

                    for i, scene in enumerate(scenes):
                        scene_output = os.path.join(tmpdir, f"scene_{i:03d}.mp4")

                        # Get audio
                        audio_path = None
                        voiceover = await vo_repo.get_by_scene(scene.id)
                        if voiceover and voiceover.file_key:
                            try:
                                audio_data = await storage_provider.download(voiceover.file_key)
                                audio_path = os.path.join(tmpdir, f"audio_{i}.wav")
                                with open(audio_path, "wb") as af:
                                    af.write(audio_data)
                            except Exception:
                                pass

                        frame = SceneFrame(
                            duration=scene.duration_seconds,
                            background_color=scene.background_color or "#1a1a2e",
                            audio_path=audio_path,
                            text=scene.narration[:200] if scene.narration else None,
                            transition_in=scene.transition_in.value if scene.transition_in else "cut",
                            transition_out=scene.transition_out.value if scene.transition_out else "cut",
                        )

                        await engine.render_scene_to_video(frame, scene_output)
                        scene_videos.append(scene_output)

                        progress = int(5 + (i + 1) / len(scenes) * 75)
                        await rj_repo.update(render_job, {"progress": progress})
                        await db.commit()

                    final_output = os.path.join(tmpdir, f"final.{config.format}")
                    if len(scene_videos) == 1:
                        import shutil
                        shutil.copy(scene_videos[0], final_output)
                    else:
                        await engine.concatenate_videos(scene_videos, final_output)

                    with open(final_output, "rb") as f:
                        video_data = f.read()

                    key = storage_provider.generate_key("renders", f"video.{config.format}")
                    url = await storage_provider.upload(video_data, key, f"video/{config.format}")

                    info = await engine.get_video_info(final_output)
                    duration = float(info.get("format", {}).get("duration", 0))

                    processing_time = time.time() - start_time
                    await rj_repo.update(render_job, {
                        "status": RenderStatus.COMPLETED,
                        "progress": 100,
                        "output_url": url,
                        "output_key": key,
                        "duration_seconds": duration,
                        "processing_time_seconds": processing_time,
                    })
                    await db.commit()
                    return {"render_job_id": render_job_id, "output_url": url, "status": "completed"}

            except Exception as e:
                await rj_repo.update(render_job, {
                    "status": RenderStatus.FAILED,
                    "error_message": str(e)[:500],
                })
                await db.commit()
                raise

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Export Tasks ──────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=2, name="app.tasks.export_tasks.export_project")
def export_project_task(self, export_id: str):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.repositories.media_repository import ExportRepository, RenderJobRepository
        from app.repositories.project_repository import ProjectRepository, ScriptRepository, SceneRepository
        from app.models.media import ExportStatus, ExportFormat, RenderStatus
        from app.storage.providers import storage_provider

        async with AsyncSessionLocal() as db:
            export_repo = ExportRepository(db)
            export = await export_repo.get(uuid.UUID(export_id))
            if not export:
                raise ValueError(f"Export {export_id} not found")

            await export_repo.update(export, {"status": ExportStatus.PROCESSING})
            await db.commit()

            try:
                if export.format == ExportFormat.JSON:
                    project_repo = ProjectRepository(db)
                    script_repo = ScriptRepository(db)
                    scene_repo = SceneRepository(db)

                    project = await project_repo.get(export.project_id)
                    scripts = await script_repo.get_by_project(export.project_id)
                    scenes = await scene_repo.get_by_project(export.project_id)

                    data = {
                        "project": project.to_dict() if project else {},
                        "scripts": [s.to_dict() for s in scripts],
                        "scenes": [s.to_dict() for s in scenes],
                        "exported_at": datetime.now(timezone.utc).isoformat(),
                    }
                    file_data = json.dumps(data, default=str).encode()
                    key = storage_provider.generate_key("exports", "project.json")
                    url = await storage_provider.upload(file_data, key, "application/json")
                    size = len(file_data)

                elif export.format == ExportFormat.MP4:
                    rj_repo = RenderJobRepository(db)
                    render_jobs = await rj_repo.get_by_project(export.project_id)
                    completed = [j for j in render_jobs if j.status == RenderStatus.COMPLETED]

                    if not completed:
                        raise ValueError("No completed render found for project")

                    latest_render = completed[0]
                    video_data = await storage_provider.download(latest_render.output_key)
                    key = storage_provider.generate_key("exports", "video.mp4")
                    url = await storage_provider.upload(video_data, key, "video/mp4")
                    size = len(video_data)

                elif export.format in (ExportFormat.ZIP, ExportFormat.PACKAGE):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        zip_path = os.path.join(tmpdir, "project_export.zip")
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            project_repo = ProjectRepository(db)
                            scene_repo = SceneRepository(db)
                            project = await project_repo.get(export.project_id)
                            scenes = await scene_repo.get_by_project(export.project_id)

                            meta = {
                                "project": project.to_dict() if project else {},
                                "scenes": [s.to_dict() for s in scenes],
                                "exported_at": datetime.now(timezone.utc).isoformat(),
                            }
                            zf.writestr("project.json", json.dumps(meta, default=str))

                        with open(zip_path, "rb") as f:
                            file_data = f.read()

                        key = storage_provider.generate_key("exports", "project.zip")
                        url = await storage_provider.upload(file_data, key, "application/zip")
                        size = len(file_data)
                else:
                    raise ValueError(f"Unsupported export format: {export.format}")

                await export_repo.update(export, {
                    "status": ExportStatus.COMPLETED,
                    "file_url": url,
                    "file_key": key,
                    "size_bytes": size,
                })
                await db.commit()
                return {"export_id": export_id, "url": url, "status": "completed"}

            except Exception as e:
                await export_repo.update(export, {
                    "status": ExportStatus.FAILED,
                    "error_message": str(e)[:500],
                })
                await db.commit()
                raise

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Cleanup Tasks ─────────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_files")
def cleanup_expired_files():
    logger.info("Running cleanup of expired files")
    # Add cleanup logic here based on expires_at field
    return {"status": "completed"}


# ── Notification Tasks ────────────────────────────────────────────────────────

@celery_app.task(name="app.tasks.notification_tasks.send_notification")
def send_notification_task(user_id: str, title: str, message: str, notification_type: str = "info"):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.repositories.system_repository import NotificationRepository

        async with AsyncSessionLocal() as db:
            notif_repo = NotificationRepository(db)
            await notif_repo.create({
                "user_id": uuid.UUID(user_id),
                "title": title,
                "message": message,
                "type": notification_type,
            })
            await db.commit()

    run_async(_run())
    return {"status": "sent"}

# ── Orchestrator Task ─────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=1, name="tasks.tasks.run_orchestrator")
def run_orchestrator_task(self, project_id: str):
    async def _run():
        from app.db.session import AsyncSessionLocal
        from app.agents.orchestrator_agent import OrchestratorAgent
        
        async with AsyncSessionLocal() as db:
            orchestrator = OrchestratorAgent(db)
            await orchestrator.run_pipeline(uuid.UUID(project_id))
            return {"project_id": project_id, "status": "completed"}

    try:
        return run_async(_run())
    except Exception as exc:
        raise self.retry(exc=exc)

