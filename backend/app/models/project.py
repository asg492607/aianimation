import enum
import uuid
from typing import Optional, List

from sqlalchemy import String, Text, ForeignKey, Enum, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProjectStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class Project(BaseModel):
    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="projects")
    scripts: Mapped[List["Script"]] = relationship("Script", back_populates="project", cascade="all, delete-orphan")
    scenes: Mapped[List["Scene"]] = relationship("Scene", back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[List["Asset"]] = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    voiceovers: Mapped[List["Voiceover"]] = relationship("Voiceover", back_populates="project", cascade="all, delete-orphan")
    render_jobs: Mapped[List["RenderJob"]] = relationship("RenderJob", back_populates="project", cascade="all, delete-orphan")
    exports: Mapped[List["Export"]] = relationship("Export", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project {self.title}>"
