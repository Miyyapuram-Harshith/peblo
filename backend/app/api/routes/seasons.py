from __future__ import annotations

"""Seasons routes."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_editor_or_admin
from app.db.session import get_db
from app.models import Episode, Season, Show, User
from app.schemas.schemas import SeasonCreate, SeasonResponse, SeasonUpdate

router = APIRouter(tags=["Seasons"])


def _season_to_response(season: Season, episode_count: int = 0) -> SeasonResponse:
    return SeasonResponse(
        id=season.id,
        show_id=season.show_id,
        season_number=season.season_number,
        title=season.title,
        episode_count=episode_count,
        created_at=season.created_at,
        updated_at=season.updated_at,
    )


@router.get("/admin/shows/{show_id}/seasons", response_model=list[SeasonResponse])
async def list_seasons(
    show_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """List all seasons for a show."""
    # Verify show exists
    show = await db.execute(select(Show).where(Show.id == show_id))
    if not show.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}})

    result = await db.execute(
        select(Season).where(Season.show_id == show_id).order_by(Season.season_number)
    )
    seasons = result.scalars().all()

    responses = []
    for season in seasons:
        count_result = await db.execute(
            select(func.count(Episode.id)).where(Episode.season_id == season.id)
        )
        ep_count = count_result.scalar() or 0
        responses.append(_season_to_response(season, ep_count))

    return responses


@router.post("/admin/shows/{show_id}/seasons", response_model=SeasonResponse, status_code=201)
async def create_season(
    show_id: uuid.UUID,
    body: SeasonCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Create a new season for a show."""
    show = await db.execute(select(Show).where(Show.id == show_id))
    if not show.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"error": {"code": "SHOW_NOT_FOUND", "message": "Show not found."}})

    # Check unique season number within show
    existing = await db.execute(
        select(Season).where(Season.show_id == show_id, Season.season_number == body.season_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "SEASON_EXISTS", "message": f"Season {body.season_number} already exists for this show."}},
        )

    season = Season(show_id=show_id, season_number=body.season_number, title=body.title)
    db.add(season)
    await db.commit()
    await db.refresh(season)
    return _season_to_response(season)


@router.patch("/admin/seasons/{season_id}", response_model=SeasonResponse)
async def update_season(
    season_id: uuid.UUID,
    body: SeasonUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Update a season."""
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalar_one_or_none()
    if not season:
        raise HTTPException(status_code=404, detail={"error": {"code": "SEASON_NOT_FOUND", "message": "Season not found."}})

    update_data = body.model_dump(exclude_unset=True)
    if "season_number" in update_data:
        season.season_number = update_data["season_number"]
    if "title" in update_data:
        season.title = update_data["title"]

    await db.commit()
    await db.refresh(season)
    return _season_to_response(season)


@router.delete("/admin/seasons/{season_id}", status_code=204)
async def delete_season(
    season_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
):
    """Delete a season and all its episodes."""
    result = await db.execute(select(Season).where(Season.id == season_id))
    season = result.scalar_one_or_none()
    if not season:
        raise HTTPException(status_code=404, detail={"error": {"code": "SEASON_NOT_FOUND", "message": "Season not found."}})

    await db.delete(season)
    await db.commit()
