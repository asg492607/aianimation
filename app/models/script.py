import enum
import uuid
from typing import Optional, List

from sqlalchemy import String, Text, ForeignKey, Enum, Integer, Float, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ScriptStatus(str, enum.Enum):
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    APPROVED = "approved"


class Script(BaseModel):
    __tablename__ = "scripts"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ScriptStatus] = mapped_column(Enum(ScriptStatus), default=ScriptStatus.GENERATING)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_ai_response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)

    project: Mapped["Project"] = relationship("Project", back_populates="scripts")
    scenes: Mapped[List["Scene"]] = relationship("Scene", back_populates="script", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Script {self.title}>"


class SceneTransition(str, enum.Enum):
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    ZOOM = "zoom"


class Scene(BaseModel):
    __tablename__ = "scenes"

    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    narration: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    camera_direction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transition_in: Mapped[SceneTransition] = mapped_column(Enum(SceneTransition), default=SceneTransition.CUT)
    transition_out: Mapped[SceneTransition] = mapped_column(Enum(SceneTransition), default=SceneTransition.CUT)
    background_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    script_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("scripts.id", ondelete="SET NULL"), nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="scenes")
    script: Mapped[Optional["Script"]] = relationship("Script", back_populates="scenes")
    storyboard: Mapped[Optional["Storyboard"]] = relationship("Storyboard", back_populates="scene", uselist=False, cascade="all, delete-orphan")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="scene")
    voiceovers: Mapped[List["Voiceover"]] = relationship("Voiceover", back_populates="scene")

    def __repr__(self) -> str:
        return f"<Scene {self.scene_number}>"


class Storyboard(BaseModel):
    __tablename__ = "storyboards"

    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    scene_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, unique=True)

    scene: Mapped["Scene"] = relationship("Scene", back_populates="storyboard")

    def __repr__(self) -> str:
        return f"<Storyboard scene={self.scene_id}>"
