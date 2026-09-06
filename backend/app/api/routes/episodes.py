"""Episodes CRUD routes."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_storage, require_editor_or_admin
from app.db.session import get_db
from app.models import Artwork, ContentStatus, Episode, Season, Show, User
from app.schemas.schemas import (
    ArtworkResponse,
    EpisodeCreate,
    EpisodeListResponse,
    EpisodeResponse,
    EpisodeUpdate,
)
from app.storage.provider import StorageProvider

router = APIRouter(prefix="/admin/episodes", tags=["Episodes"])


def _episode_to_response(episode: Episode, storage: StorageProvider, show_title: str | None = None, season_number: int | None = None) -> EpisodeResponse:
    artwork_list = []
    for art in (episode.artwork or []):
        ar = ArtworkResponse.model_validate(art)
        ar.url = storage.public_url(art.storage_key)
        artwork_list.append(ar)
    return EpisodeResponse(
        id=episode.id,
        season_id=episode.season_id,
        title=episode.title,
        synopsis=episode.synopsis,
        duration_seconds=episode.duration_seconds,
        language=episode.language,
        content_group=episode.content_group,
        video_url=episode.video_url,
        status=episode.status.value,
        artwork=artwork_list,
        show_title=show_title,
        season_number=season_number,
        created_at=episode.created_at,
        updated_at=episode.updated_at,
    )


@router.get("", response_model=EpisodeListResponse)
async def list_episodes(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    language: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    show_id: uuid.UUID | None = None,
    season_id: uuid.UUID | None = None,
):
    """List episodes with filtering and pagination."""
    query = (
        select(Episode)
        .join(Season, Episode.season_id == Season.id)
        .join(Show, Season.show_id == Show.id)
        .options(selectinload(Episode.artwork))
    )
    count_query = (
        select(func.count(Episode.id))
        .join(Season, Episode.season_id == Season.id)
        .join(Show, Season.show_id == Show.id)
    )

    if search:
        query = query.where(Episode.title.ilike(f"%{search}%"))
        count_query = count_query.where(Episode.title.ilike(f"%{search}%"))
    if language:
        query = query.where(Episode.language == language)
        count_query = count_query.where(Episode.language == language)
    if status_filter:
        try:
            cs = ContentStatus(status_filter)
            query = query.where(Episode.status == cs)
            count_query = count_query.where(Episode.status == cs)
        except ValueError:
            pass
    if show_id:
        query = query.where(Show.id == show_id)
        count_query = count_query.where(Show.id == show_id)
    if season_id:
        query = query.where(Episode.season_id == season_id)
        count_query = count_query.where(Episode.season_id == season_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.add_columns(Show.title.label("show_title"), Season.season_number)
    query = query.order_by(Show.title, Season.season_number, Episode.created_at)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    items = [_episode_to_response(row[0], storage, row[1], row[2]) for row in rows]

    return EpisodeListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Get a single episode by ID."""
    result = await db.execute(
        select(Episode)
        .join(Season, Episode.season_id == Season.id)
        .join(Show, Season.show_id == Show.id)
        .options(selectinload(Episode.artwork))
        .add_columns(Show.title.label("show_title"), Season.season_number)
        .where(Episode.id == episode_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail={"error": {"code": "EPISODE_NOT_FOUND", "message": "Episode not found."}})
    return _episode_to_response(row[0], storage, row[1], row[2])


@router.post("", response_model=EpisodeResponse, status_code=201)
async def create_episode(
    body: EpisodeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Create a new episode."""
    # Verify season exists
    season_result = await db.execute(
        select(Season).join(Show, Season.show_id == Show.id)
        .add_columns(Show.title.label("show_title"))
        .where(Season.id == body.season_id)
    )
    season_row = season_result.first()
    if not season_row:
        raise HTTPException(status_code=404, detail={"error": {"code": "SEASON_NOT_FOUND", "message": "Season not found."}})

    try:
        ep_status = ContentStatus(body.status) if body.status else ContentStatus.DRAFT
    except ValueError:
        ep_status = ContentStatus.DRAFT

    episode = Episode(
        season_id=body.season_id,
        title=body.title,
        synopsis=body.synopsis,
        duration_seconds=body.duration_seconds,
        language=body.language,
        content_group=body.content_group,
        video_url=body.video_url,
        status=ep_status,
    )
    db.add(episode)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        if "uq_episode_content_group_language" in str(e):
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "DUPLICATE_CONTENT_GROUP_LANGUAGE", "message": f"An episode with content_group '{body.content_group}' and language '{body.language}' already exists."}},
            )
        raise

    await db.refresh(episode)
    return _episode_to_response(episode, storage, season_row[1], season_row[0].season_number)


@router.patch("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    episode_id: uuid.UUID,
    body: EpisodeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Update an episode."""
    result = await db.execute(
        select(Episode).options(selectinload(Episode.artwork)).where(Episode.id == episode_id)
    )
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail={"error": {"code": "EPISODE_NOT_FOUND", "message": "Episode not found."}})

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status":
            try:
                setattr(episode, field, ContentStatus(value))
            except ValueError:
                raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_STATUS", "message": f"Invalid status: {value}"}})
        else:
            setattr(episode, field, value)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        if "uq_episode_content_group_language" in str(e):
            raise HTTPException(
                status_code=409,
                detail={"error": {"code": "DUPLICATE_CONTENT_GROUP_LANGUAGE", "message": f"This content_group + language combination already exists."}},
            )
        raise

    await db.refresh(episode)
    return _episode_to_response(episode, storage)


@router.delete("/{episode_id}", status_code=204)
async def delete_episode(
    episode_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Delete an episode."""
    result = await db.execute(select(Episode).where(Episode.id == episode_id))
    episode = result.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail={"error": {"code": "EPISODE_NOT_FOUND", "message": "Episode not found."}})

    await db.delete(episode)
    await db.commit()
