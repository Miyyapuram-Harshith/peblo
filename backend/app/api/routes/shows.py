"""Shows CRUD routes."""
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_storage, require_editor_or_admin
from app.db.session import get_db
from app.models import Artwork, ContentStatus, Season, Show, User
from app.schemas.schemas import (
    ArtworkResponse,
    ShowCreate,
    ShowListResponse,
    ShowResponse,
    ShowUpdate,
)
from app.storage.provider import StorageProvider

router = APIRouter(prefix="/admin/shows", tags=["Shows"])


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def _show_to_response(show: Show, storage: StorageProvider) -> ShowResponse:
    artwork_list = []
    for art in (show.artwork or []):
        ar = ArtworkResponse.model_validate(art)
        ar.url = storage.public_url(art.storage_key)
        artwork_list.append(ar)
    return ShowResponse(
        id=show.id,
        title=show.title,
        slug=show.slug,
        synopsis=show.synopsis,
        section=show.section,
        category=show.category,
        status=show.status.value,
        artwork=artwork_list,
        created_at=show.created_at,
        updated_at=show.updated_at,
    )


@router.get("", response_model=ShowListResponse)
async def list_shows(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    section: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
):
    """List shows with filtering and pagination."""
    query = select(Show).options(selectinload(Show.artwork))
    count_query = select(func.count(Show.id))

    if search:
        query = query.where(Show.title.ilike(f"%{search}%"))
        count_query = count_query.where(Show.title.ilike(f"%{search}%"))
    if section:
        query = query.where(Show.section == section)
        count_query = count_query.where(Show.section == section)
    if status_filter:
        try:
            cs = ContentStatus(status_filter)
            query = query.where(Show.status == cs)
            count_query = count_query.where(Show.status == cs)
        except ValueError:
            pass

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Show.title).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    shows = result.scalars().unique().all()

    return ShowListResponse(
        items=[_show_to_response(s, storage) for s in shows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{show_id}", response_model=ShowResponse)
async def get_show(
    show_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Get a single show by ID."""
    result = await db.execute(
        select(Show).options(selectinload(Show.artwork)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail={"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}})
    return _show_to_response(show, storage)


@router.post("", response_model=ShowResponse, status_code=201)
async def create_show(
    body: ShowCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Create a new show."""
    slug = _slugify(body.title)

    # Check unique slug
    existing = await db.execute(select(Show).where(Show.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "SLUG_CONFLICT", "message": f"A show with slug '{slug}' already exists."}},
        )

    try:
        show_status = ContentStatus(body.status) if body.status else ContentStatus.DRAFT
    except ValueError:
        show_status = ContentStatus.DRAFT

    show = Show(
        title=body.title,
        slug=slug,
        synopsis=body.synopsis,
        section=body.section,
        category=body.category,
        status=show_status,
    )
    db.add(show)
    await db.commit()
    await db.refresh(show)

    return _show_to_response(show, storage)


@router.patch("/{show_id}", response_model=ShowResponse)
async def update_show(
    show_id: uuid.UUID,
    body: ShowUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Update an existing show."""
    result = await db.execute(
        select(Show).options(selectinload(Show.artwork)).where(Show.id == show_id)
    )
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail={"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}})

    update_data = body.model_dump(exclude_unset=True)
    if "title" in update_data:
        show.title = update_data["title"]
        show.slug = _slugify(update_data["title"])
    if "synopsis" in update_data:
        show.synopsis = update_data["synopsis"]
    if "section" in update_data:
        show.section = update_data["section"]
    if "category" in update_data:
        show.category = update_data["category"]
    if "status" in update_data:
        try:
            show.status = ContentStatus(update_data["status"])
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={"error": {"code": "INVALID_STATUS", "message": f"Invalid status: {update_data['status']}"}},
            )

    await db.commit()
    await db.refresh(show)
    return _show_to_response(show, storage)


@router.delete("/{show_id}", status_code=204)
async def delete_show(
    show_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Delete a show and all its seasons/episodes."""
    result = await db.execute(select(Show).where(Show.id == show_id))
    show = result.scalar_one_or_none()
    if not show:
        raise HTTPException(status_code=404, detail={"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}})

    await db.delete(show)
    await db.commit()
