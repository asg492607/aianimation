import enum
import uuid
from typing import Optional, List

from sqlalchemy import String, Text, ForeignKey, Enum, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Character(BaseModel):
    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hair: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    outfit: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g. Business, Teacher
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<Character {self.name}>"


class AnimationPreset(BaseModel):
    __tablename__ = "animation_presets"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    ffmpeg_filter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class RenderProfile(BaseModel):
    __tablename__ = "render_profiles"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True) # e.g. 1080p, TikTok
    resolution: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. 1920x1080, 1080x1920
    fps: Mapped[int] = mapped_column(Integer, default=30)
    video_bitrate: Mapped[str] = mapped_column(String(20), default="4000k")
    audio_bitrate: Mapped[str] = mapped_column(String(20), default="192k")


class CameraMovement(BaseModel):
    __tablename__ = "camera_movements"

    style: Mapped[str] = mapped_column(String(100), nullable=False) # Zoom In, Pan Left, etc.
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    scene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)


class Timeline(BaseModel):
    __tablename__ = "timelines"

    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    layer: Mapped[int] = mapped_column(Integer, default=0) # Z-index or layer track

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True)
    asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    animation_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("animation_presets.id", ondelete="SET NULL"), nullable=True)
    
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class MusicTrack(BaseModel):
    __tablename__ = "music_tracks"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    mood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)


class AIJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AIJob(BaseModel):
    __tablename__ = "ai_jobs"

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. director_agent, scene_agent
    status: Mapped[AIJobStatus] = mapped_column(Enum(AIJobStatus), default=AIJobStatus.QUEUED)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
