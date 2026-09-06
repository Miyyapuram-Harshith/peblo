"""Catalogue publishing and viewer routes."""
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_storage, require_admin, require_editor_or_admin
from app.db.session import get_db
from app.models import (
    ActiveCatalogue,
    ContentStatus,
    Episode,
    PublishRun,
    Season,
    Show,
    User,
)
from app.schemas.schemas import (
    CatalogueContract,
    PublishReceipt,
    PublishRequest,
    PublishRunListResponse,
    PublishRunResponse,
    ValidationReport,
)
from app.services.publish import PublishError, publish_catalogue
from app.services.validation import run_validation
from app.storage.provider import StorageProvider

admin_router = APIRouter(prefix="/admin/catalog", tags=["Publishing"])
viewer_router = APIRouter(prefix="/catalog", tags=["Viewer Catalogue"])


# --- Admin routes ---

@admin_router.post("/publish", response_model=PublishReceipt)
async def publish(
    body: PublishRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Publish catalogue (admin only). Atomic - if it fails, previous catalogue stays live."""
    try:
        receipt = await publish_catalogue(
            db=db,
            user_id=str(user.id),
            user_email=user.email,
            storage=storage,
            idempotency_key=body.idempotency_key,
        )
        return receipt
    except PublishError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": e.code, "message": e.message}},
        )


@admin_router.get("/publish-runs", response_model=PublishRunListResponse)
async def list_publish_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    limit: int = Query(20, ge=1, le=100),
):
    """List recent publish runs."""
    result = await db.execute(
        select(PublishRun)
        .options(selectinload(PublishRun.triggered_by_user))
        .order_by(desc(PublishRun.created_at))
        .limit(limit)
    )
    runs = result.scalars().all()

    total_result = await db.execute(select(func.count(PublishRun.id)))
    total = total_result.scalar() or 0

    items = []
    for run in runs:
        r = PublishRunResponse.model_validate(run)
        r.triggered_by_email = run.triggered_by_user.email if run.triggered_by_user else None
        items.append(r)

    return PublishRunListResponse(items=items, total=total)


@admin_router.get("/publish-runs/{run_id}", response_model=PublishRunResponse)
async def get_publish_run(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Get a specific publish run."""
    result = await db.execute(
        select(PublishRun)
        .options(selectinload(PublishRun.triggered_by_user))
        .where(PublishRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail={"error": {"code": "RUN_NOT_FOUND", "message": "Publish run not found."}})

    r = PublishRunResponse.model_validate(run)
    r.triggered_by_email = run.triggered_by_user.email if run.triggered_by_user else None
    return r


# --- Validation route ---

validation_router = APIRouter(prefix="/admin", tags=["Validation"])


@validation_router.get("/validation-report", response_model=ValidationReport)
async def get_validation_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Get comprehensive validation report for publishing readiness."""
    return await run_validation(db)


# --- Viewer routes (public, no auth) ---

@viewer_router.get("", response_model=CatalogueContract | dict)
async def get_catalogue(
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Get the currently active published catalogue."""
    result = await db.execute(select(ActiveCatalogue).where(ActiveCatalogue.id == 1))
    active = result.scalar_one_or_none()

    if not active:
        return {"version": 0, "generated_at": "", "catalogue_hash": "", "sections": []}

    # Read from storage
    data = await storage.get(active.active_catalogue_key)
    if data is None:
        raise HTTPException(status_code=503, detail={"error": {"code": "CATALOGUE_UNAVAILABLE", "message": "Active catalogue could not be loaded."}})

    return json.loads(data.decode("utf-8"))


@viewer_router.get("/search")
async def search_catalogue(
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
    q: str | None = None,
    category: str | None = None,
    language: str | None = None,
    section: str | None = None,
):
    """Search the catalogue using server-side PostgreSQL filtering."""
    # Build query for published shows
    query = (
        select(Show)
        .options(
            selectinload(Show.seasons).selectinload(Season.episodes),
            selectinload(Show.artwork),
        )
        .where(Show.status == ContentStatus.PUBLISHED)
    )

    if section:
        query = query.where(Show.section == section)
    if category:
        query = query.where(Show.category == category)

    result = await db.execute(query)
    shows = result.scalars().unique().all()

    # Filter further by text search and language
    filtered_shows = []
    for show in shows:
        # Text search on show title and category
        if q:
            q_lower = q.lower()
            title_match = q_lower in show.title.lower()
            cat_match = show.category and q_lower in show.category.lower()
            # Check episode titles too
            ep_match = False
            for season in show.seasons:
                for ep in season.episodes:
                    if ep.status == ContentStatus.PUBLISHED and q_lower in ep.title.lower():
                        ep_match = True
                        break
                if ep_match:
                    break

            if not (title_match or cat_match or ep_match):
                continue

        # Language filter
        if language:
            has_language = False
            for season in show.seasons:
                for ep in season.episodes:
                    if ep.status == ContentStatus.PUBLISHED and ep.language == language:
                        has_language = True
                        break
                if has_language:
                    break
            if not has_language:
                continue

        show_data = {
            "id": str(show.id),
            "title": show.title,
            "slug": show.slug,
            "synopsis": show.synopsis,
            "section": show.section,
            "category": show.category,
            "artwork": {},
        }
        for art in (show.artwork or []):
            show_data["artwork"][art.artwork_type.value] = storage.public_url(art.storage_key)

        # Collect languages
        languages = set()
        for season in show.seasons:
            for ep in season.episodes:
                if ep.status == ContentStatus.PUBLISHED:
                    languages.add(ep.language)
        show_data["languages"] = sorted(languages)

        filtered_shows.append(show_data)

    return {"results": filtered_shows, "total": len(filtered_shows)}
