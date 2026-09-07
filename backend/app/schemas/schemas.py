from __future__ import annotations

"""Pydantic schemas for API request/response validation."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# --- Auth ---

class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Show ---

class ShowCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    synopsis: str | None = None
    section: str | None = None
    category: str | None = None
    status: str = "draft"


class ShowUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    synopsis: str | None = None
    section: str | None = None
    category: str | None = None
    status: str | None = None


class ArtworkResponse(BaseModel):
    id: uuid.UUID
    owner_type: str
    owner_id: uuid.UUID
    artwork_type: str
    storage_key: str
    url: str | None = None
    mime_type: str
    width: int
    height: int
    size_bytes: int
    sha256: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ShowResponse(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    synopsis: str | None
    section: str | None
    category: str | None
    status: str
    artwork: list[ArtworkResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShowListResponse(BaseModel):
    items: list[ShowResponse]
    total: int
    page: int
    page_size: int


# --- Season ---

class SeasonCreate(BaseModel):
    season_number: int = Field(ge=0)
    title: str | None = None


class SeasonUpdate(BaseModel):
    season_number: int | None = Field(None, ge=0)
    title: str | None = None


class SeasonResponse(BaseModel):
    id: uuid.UUID
    show_id: uuid.UUID
    season_number: int
    title: str | None
    episode_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Episode ---

class EpisodeCreate(BaseModel):
    season_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    synopsis: str | None = None
    duration_seconds: int | None = Field(None, ge=0)
    language: str = Field(min_length=1, max_length=50)
    content_group: str = Field(min_length=1, max_length=255)
    video_url: str | None = None
    status: str = "draft"


class EpisodeUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    synopsis: str | None = None
    duration_seconds: int | None = Field(None, ge=0)
    language: str | None = Field(None, min_length=1)
    content_group: str | None = Field(None, min_length=1)
    video_url: str | None = None
    status: str | None = None


class EpisodeResponse(BaseModel):
    id: uuid.UUID
    season_id: uuid.UUID
    title: str
    synopsis: str | None
    duration_seconds: int | None
    language: str
    content_group: str
    video_url: str | None
    status: str
    artwork: list[ArtworkResponse] = []
    show_title: str | None = None
    season_number: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EpisodeListResponse(BaseModel):
    items: list[EpisodeResponse]
    total: int
    page: int
    page_size: int


# --- Validation ---

class ValidationIssue(BaseModel):
    code: str
    severity: str  # "blocking" or "warning"
    category: str  # "content", "artwork", "languages", "publishing"
    entity_type: str
    entity_id: str | None = None
    entity_name: str | None = None
    message: str
    suggested_action: str


class ValidationReport(BaseModel):
    ready: bool
    total_issues: int
    blocking_count: int
    warning_count: int
    issues: list[ValidationIssue]


# --- Publish ---

class PublishRequest(BaseModel):
    idempotency_key: str | None = None


class PublishRunResponse(BaseModel):
    id: uuid.UUID
    triggered_by: uuid.UUID
    triggered_by_email: str | None = None
    started_at: datetime
    completed_at: datetime | None
    status: str
    catalogue_key: str | None
    catalogue_hash: str | None
    shows_count: int | None
    episodes_count: int | None
    language_group_count: int | None
    duration_ms: int | None
    error_code: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PublishRunListResponse(BaseModel):
    items: list[PublishRunResponse]
    total: int


class PublishStage(BaseModel):
    name: str
    status: str  # "pending", "running", "success", "failed"
    message: str | None = None


class PublishReceipt(BaseModel):
    run_id: uuid.UUID
    version: int
    catalogue_hash: str
    triggered_by: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    shows_count: int
    episodes_count: int
    language_group_count: int
    stages: list[PublishStage]
    status: str


# --- Catalogue (Viewer) ---

class CatalogueLanguage(BaseModel):
    language: str
    video_url: str | None = None


class CatalogueEpisode(BaseModel):
    content_group: str
    title: str
    synopsis: str | None
    duration_seconds: int | None
    thumbnail: str | None = None
    languages: list[CatalogueLanguage]


class CatalogueSeason(BaseModel):
    season_number: int
    title: str | None
    episodes: list[CatalogueEpisode]


class CatalogueShow(BaseModel):
    id: str
    title: str
    slug: str
    synopsis: str | None
    category: str | None
    artwork: dict[str, str | None] = {}
    seasons: list[CatalogueSeason]


class CatalogueSection(BaseModel):
    section: str
    shows: list[CatalogueShow]


class CatalogueContract(BaseModel):
    version: int
    generated_at: str
    catalogue_hash: str
    sections: list[CatalogueSection]


# --- Search ---

class SearchRequest(BaseModel):
    q: str | None = None
    category: str | None = None
    language: str | None = None
    section: str | None = None


# --- Error ---

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    checks: dict[str, str] | None = None
