"""SQLAlchemy ORM models."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()


# --- Enums ---

class UserRole(str, enum.Enum):
    EDITOR = "editor"
    ADMIN = "admin"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ArtworkType(str, enum.Enum):
    POSTER = "poster"
    BANNER = "banner"
    THUMBNAIL = "thumbnail"


class OwnerType(str, enum.Enum):
    SHOW = "show"
    EPISODE = "episode"


class PublishStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    BUILDING = "building"
    STORING = "storing"
    ACTIVATING = "activating"
    SUCCESS = "success"
    FAILED_VALIDATION = "failed_validation"
    FAILED_BUILD = "failed_build"
    FAILED_STORAGE = "failed_storage"
    FAILED_ACTIVATION = "failed_activation"


# --- Models ---

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EDITOR)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Show(Base):
    __tablename__ = "shows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    title = Column(String(500), nullable=False)
    slug = Column(String(500), unique=True, nullable=False, index=True)
    synopsis = Column(Text, nullable=True)
    section = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(Enum(ContentStatus), nullable=False, default=ContentStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    seasons = relationship("Season", back_populates="show", cascade="all, delete-orphan", order_by="Season.season_number")
    artwork = relationship("Artwork", primaryjoin="and_(Artwork.owner_id==Show.id, Artwork.owner_type=='show')", foreign_keys="Artwork.owner_id", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_shows_status", "status"),
        Index("ix_shows_section", "section"),
        Index("ix_shows_category", "category"),
    )


class Season(Base):
    __tablename__ = "seasons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    show_id = Column(UUID(as_uuid=True), ForeignKey("shows.id", ondelete="CASCADE"), nullable=False)
    season_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    show = relationship("Show", back_populates="seasons")
    episodes = relationship("Episode", back_populates="season", cascade="all, delete-orphan", order_by="Episode.created_at")

    __table_args__ = (
        UniqueConstraint("show_id", "season_number", name="uq_season_show_number"),
        Index("ix_seasons_show_id", "show_id"),
    )


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    season_id = Column(UUID(as_uuid=True), ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    synopsis = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    language = Column(String(50), nullable=False)
    content_group = Column(String(255), nullable=False)
    video_url = Column(String(2000), nullable=True)
    status = Column(Enum(ContentStatus), nullable=False, default=ContentStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    season = relationship("Season", back_populates="episodes")
    artwork = relationship("Artwork", primaryjoin="and_(Artwork.owner_id==Episode.id, Artwork.owner_type=='episode')", foreign_keys="Artwork.owner_id", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("content_group", "language", name="uq_episode_content_group_language"),
        Index("ix_episodes_season_id", "season_id"),
        Index("ix_episodes_content_group", "content_group"),
        Index("ix_episodes_language", "language"),
        Index("ix_episodes_status", "status"),
    )


class Artwork(Base):
    __tablename__ = "artwork"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    owner_type = Column(Enum(OwnerType), nullable=False)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    artwork_type = Column(Enum(ArtworkType), nullable=False)
    storage_key = Column(String(500), nullable=False, unique=True)
    mime_type = Column(String(100), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "artwork_type", name="uq_artwork_owner_type"),
        Index("ix_artwork_owner", "owner_type", "owner_id"),
    )


class PublishRun(Base):
    __tablename__ = "publish_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(PublishStatus), nullable=False, default=PublishStatus.PENDING)
    catalogue_key = Column(String(500), nullable=True)
    catalogue_hash = Column(String(64), nullable=True)
    shows_count = Column(Integer, nullable=True)
    episodes_count = Column(Integer, nullable=True)
    language_group_count = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    triggered_by_user = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("ix_publish_runs_status", "status"),
        Index("ix_publish_runs_created_at", "created_at"),
    )


class ActiveCatalogue(Base):
    __tablename__ = "active_catalogue"

    id = Column(Integer, primary_key=True, default=1)
    active_catalogue_key = Column(String(500), nullable=False)
    active_catalogue_hash = Column(String(64), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
