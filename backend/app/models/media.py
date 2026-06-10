import enum
import uuid
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Enum, Integer, Float, JSON, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AssetType(str, enum.Enum):
    IMAGE = "image"
    ICON = "icon"
    BACKGROUND = "background"
    CHARACTER = "character"
    LOGO = "logo"
    AUDIO = "audio"
    VIDEO = "video"
    FONT = "font"
    OTHER = "other"


class AssetSource(str, enum.Enum):
    UPLOAD = "upload"
    GENERATED = "generated"
    TEMPLATE = "template"
    STOCK = "stock"


class Asset(BaseModel):
    __tablename__ = "assets"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType), default=AssetType.IMAGE)
    source: Mapped[AssetSource] = mapped_column(Enum(AssetSource), default=AssetSource.UPLOAD)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    generation_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True)

    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="assets")
    scene: Mapped[Optional["Scene"]] = relationship("Scene", back_populates="assets")

    def __repr__(self) -> str:
        return f"<Asset {self.name}>"


class VoiceoverStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class VoicoverEngine(str, enum.Enum):
    PIPER = "piper"
    COQUI = "coqui"
    GENERIC = "generic"


class Voiceover(BaseModel):
    __tablename__ = "voiceovers"

    text: Mapped[str] = mapped_column(Text, nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[VoiceoverStatus] = mapped_column(Enum(VoiceoverStatus), default=VoiceoverStatus.PENDING)
    engine: Mapped[VoicoverEngine] = mapped_column(Enum(VoicoverEngine), default=VoicoverEngine.PIPER)
    voice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="en")
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    subtitle_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="voiceovers")
    scene: Mapped[Optional["Scene"]] = relationship("Scene", back_populates="voiceovers")

    def __repr__(self) -> str:
        return f"<Voiceover {self.id}>"


class RenderStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderJob(BaseModel):
    __tablename__ = "render_jobs"

    status: Mapped[RenderStatus] = mapped_column(Enum(RenderStatus), default=RenderStatus.QUEUED)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    output_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution: Mapped[Optional[str]] = mapped_column(String(20), default="1920x1080")
    fps: Mapped[int] = mapped_column(Integer, default=30)
    format: Mapped[str] = mapped_column(String(10), default="mp4")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    render_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    project: Mapped["Project"] = relationship("Project", back_populates="render_jobs")

    def __repr__(self) -> str:
        return f"<RenderJob {self.id} status={self.status}>"


class ExportFormat(str, enum.Enum):
    MP4 = "mp4"
    JSON = "json"
    ZIP = "zip"
    PACKAGE = "package"


class ExportStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Export(BaseModel):
    __tablename__ = "exports"

    format: Mapped[ExportFormat] = mapped_column(Enum(ExportFormat), default=ExportFormat.MP4)
    status: Mapped[ExportStatus] = mapped_column(Enum(ExportStatus), default=ExportStatus.PENDING)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    project: Mapped["Project"] = relationship("Project", back_populates="exports")

    def __repr__(self) -> str:
        return f"<Export {self.id} format={self.format}>"
