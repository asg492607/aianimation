import uuid
from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel, ConfigDict

from app.models.project import ProjectStatus
from app.models.script import ScriptStatus, SceneTransition
from app.models.media import AssetType, AssetSource, VoiceoverStatus, RenderStatus, ExportFormat, ExportStatus


# ── Project ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    prompt: str


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    status: Optional[ProjectStatus] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str]
    prompt: str
    status: ProjectStatus
    thumbnail_url: Optional[str]
    duration_seconds: Optional[float]
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class PaginatedProjects(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int


# ── Script ────────────────────────────────────────────────────────────────────

class ScriptGenerateRequest(BaseModel):
    prompt: str
    project_id: uuid.UUID
    num_scenes: int = 5


class SceneData(BaseModel):
    scene_number: int
    title: str
    duration_seconds: float
    narration: str
    visual_description: str
    camera_direction: Optional[str] = None
    transition_in: SceneTransition = SceneTransition.CUT
    transition_out: SceneTransition = SceneTransition.CUT


class ScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: Optional[str]
    content: Optional[str]
    status: ScriptStatus
    prompt: str
    project_id: uuid.UUID
    token_count: Optional[int]
    created_at: datetime
    updated_at: datetime


# ── Scene ─────────────────────────────────────────────────────────────────────

class SceneGenerateRequest(BaseModel):
    project_id: uuid.UUID
    script_id: uuid.UUID


class SceneCreate(BaseModel):
    scene_number: int
    title: Optional[str] = None
    duration_seconds: float = 5.0
    narration: Optional[str] = None
    visual_description: Optional[str] = None
    camera_direction: Optional[str] = None
    transition_in: SceneTransition = SceneTransition.CUT
    transition_out: SceneTransition = SceneTransition.CUT
    project_id: uuid.UUID
    script_id: Optional[uuid.UUID] = None


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scene_number: int
    title: Optional[str]
    duration_seconds: float
    narration: Optional[str]
    visual_description: Optional[str]
    camera_direction: Optional[str]
    transition_in: SceneTransition
    transition_out: SceneTransition
    project_id: uuid.UUID
    script_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


# ── Asset ─────────────────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    file_url: str
    content_type: str
    size_bytes: Optional[int]
    asset_type: AssetType
    source: AssetSource
    width: Optional[int]
    height: Optional[int]
    project_id: Optional[uuid.UUID]
    scene_id: Optional[uuid.UUID]
    created_at: datetime


class AssetGenerateRequest(BaseModel):
    prompt: str
    asset_type: AssetType = AssetType.IMAGE
    project_id: uuid.UUID
    scene_id: Optional[uuid.UUID] = None
    width: int = 1024
    height: int = 576


# ── Voiceover ─────────────────────────────────────────────────────────────────

class VoiceoverGenerateRequest(BaseModel):
    text: str
    project_id: uuid.UUID
    scene_id: Optional[uuid.UUID] = None
    voice_id: Optional[str] = None
    language: str = "en"
    speed: float = 1.0


class VoiceoverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    file_url: Optional[str]
    duration_seconds: Optional[float]
    status: VoiceoverStatus
    project_id: uuid.UUID
    scene_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime


# ── Render ────────────────────────────────────────────────────────────────────

class RenderStartRequest(BaseModel):
    project_id: uuid.UUID
    resolution: str = "1920x1080"
    fps: int = 30
    format: str = "mp4"


class RenderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: RenderStatus
    progress: int
    output_url: Optional[str]
    duration_seconds: Optional[float]
    resolution: Optional[str]
    fps: int
    format: str
    error_message: Optional[str]
    project_id: uuid.UUID
    celery_task_id: Optional[str]
    created_at: datetime
    updated_at: datetime


# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    project_id: uuid.UUID
    format: ExportFormat = ExportFormat.MP4


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    format: ExportFormat
    status: ExportStatus
    file_url: Optional[str]
    size_bytes: Optional[int]
    error_message: Optional[str]
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ── Template ──────────────────────────────────────────────────────────────────

class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    category: str
    thumbnail_url: Optional[str]
    is_public: bool
    is_featured: bool
    usage_count: int
    created_at: datetime


# ── Common ────────────────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    success: bool = True


class TaskResponse(BaseModel):
    task_id: str
    message: str
