from __future__ import annotations

"""Validation engine for content publishing readiness."""
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import (
    ArtworkType,
    ContentStatus,
    Season,
    Show,
)
from app.schemas.schemas import ValidationIssue, ValidationReport

logger = get_logger("validation")


def _load_reference() -> dict:
    """Load reference.json for validation specs."""
    settings = get_settings()
    ref_path = Path(settings.seed_data_path) / "reference.json"
    if ref_path.exists():
        return json.loads(ref_path.read_text())
    # Fallback defaults
    return {
        "sections": ["Featured", "Adventure", "Learning", "Stories"],
        "categories": ["Animation", "Educational", "Adventure", "Comedy", "Drama", "Musical"],
        "artwork": {
            "poster": {"width": 600, "height": 900, "max_size_bytes": 204800},
            "banner": {"width": 1280, "height": 720, "max_size_bytes": 204800},
            "thumbnail": {"width": 640, "height": 360, "max_size_bytes": 204800},
        },
    }


async def run_validation(db: AsyncSession) -> ValidationReport:
    """Run all validation rules and return a comprehensive report."""
    issues: list[ValidationIssue] = []
    ref = _load_reference()
    valid_sections = ref.get("sections", [])

    # Load all published shows with relationships
    result = await db.execute(
        select(Show)
        .options(
            selectinload(Show.seasons).selectinload(Season.episodes),
            selectinload(Show.artwork),
        )
        .where(Show.status == ContentStatus.PUBLISHED)
    )
    published_shows = result.scalars().unique().all()

    # Also load all shows for general checks
    all_shows_result = await db.execute(
        select(Show).options(
            selectinload(Show.seasons).selectinload(Season.episodes),
            selectinload(Show.artwork),
        )
    )
    all_shows = all_shows_result.scalars().unique().all()

    # --- CONTENT RULES ---

    # ShowSectionRule: Published shows must have a valid section
    for show in published_shows:
        if not show.section:
            issues.append(ValidationIssue(
                code="SHOW_MISSING_SECTION",
                severity="blocking",
                category="content",
                entity_type="show",
                entity_id=str(show.id),
                entity_name=show.title,
                message=f'Show "{show.title}" is published but has no section assigned.',
                suggested_action="Assign a section (e.g., Featured, Adventure, Learning, Stories) to this show.",
            ))
        elif show.section not in valid_sections:
            issues.append(ValidationIssue(
                code="SHOW_INVALID_SECTION",
                severity="blocking",
                category="content",
                entity_type="show",
                entity_id=str(show.id),
                entity_name=show.title,
                message=f'Show "{show.title}" has section "{show.section}" which is not a recognized section.',
                suggested_action=f"Change the section to one of: {', '.join(valid_sections)}.",
            ))

    # EpisodeDurationRule: Published episodes must have duration
    for show in all_shows:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.status == ContentStatus.PUBLISHED:
                    if not episode.duration_seconds or episode.duration_seconds <= 0:
                        issues.append(ValidationIssue(
                            code="EPISODE_MISSING_DURATION",
                            severity="blocking",
                            category="content",
                            entity_type="episode",
                            entity_id=str(episode.id),
                            entity_name=f"{show.title} → {episode.title}",
                            message=f'Episode "{episode.title}" in "{show.title}" is published but has no duration set.',
                            suggested_action="Set the episode duration in seconds. This is required for published episodes.",
                        ))

    # --- ARTWORK RULES ---

    # Show artwork check
    for show in published_shows:
        show_artwork_types = {a.artwork_type for a in (show.artwork or [])}
        for art_type in [ArtworkType.POSTER, ArtworkType.BANNER]:
            if art_type not in show_artwork_types:
                issues.append(ValidationIssue(
                    code=f"SHOW_MISSING_{art_type.value.upper()}",
                    severity="blocking",
                    category="artwork",
                    entity_type="show",
                    entity_id=str(show.id),
                    entity_name=show.title,
                    message=f'Show "{show.title}" is missing {art_type.value} artwork.',
                    suggested_action=f"Upload a {art_type.value} image for this show.",
                ))

    # Episode artwork check - thumbnail for published episodes
    for show in all_shows:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.status == ContentStatus.PUBLISHED:
                    ep_artwork_types = {a.artwork_type for a in (episode.artwork or [])}
                    if ArtworkType.THUMBNAIL not in ep_artwork_types:
                        issues.append(ValidationIssue(
                            code="EPISODE_MISSING_THUMBNAIL",
                            severity="warning",
                            category="artwork",
                            entity_type="episode",
                            entity_id=str(episode.id),
                            entity_name=f"{show.title} → {episode.title}",
                            message=f'Episode "{episode.title}" in "{show.title}" has no thumbnail.',
                            suggested_action="Upload a thumbnail image for this episode.",
                        ))

    # --- LANGUAGE RULES ---

    # ContentGroupLanguageRule: Check for content_group/language uniqueness
    # (DB constraint handles this, but report as validation)
    content_group_map: dict[str, list[dict]] = {}
    for show in all_shows:
        for season in show.seasons:
            for episode in season.episodes:
                key = f"{episode.content_group}:{episode.language}"
                if key not in content_group_map:
                    content_group_map[key] = []
                content_group_map[key].append({
                    "episode_id": str(episode.id),
                    "title": episode.title,
                    "show": show.title,
                })

    for key, entries in content_group_map.items():
        if len(entries) > 1:
            cg, lang = key.split(":", 1)
            issues.append(ValidationIssue(
                code="DUPLICATE_CONTENT_GROUP_LANGUAGE",
                severity="blocking",
                category="languages",
                entity_type="episode",
                entity_id=entries[0]["episode_id"],
                entity_name=f"{cg} ({lang})",
                message=f"Content group '{cg}' has {len(entries)} episodes with language '{lang}'. Each content_group + language combination must be unique.",
                suggested_action="Remove or reassign duplicate episodes so each content group has at most one episode per language.",
            ))

    # --- PUBLISHING RULES ---

    # PublishedContentRule: At least one published show with published episodes needed
    has_publishable = False
    for show in published_shows:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.status == ContentStatus.PUBLISHED:
                    has_publishable = True
                    break
            if has_publishable:
                break
        if has_publishable:
            break

    if not has_publishable:
        issues.append(ValidationIssue(
            code="NO_PUBLISHABLE_CONTENT",
            severity="blocking",
            category="publishing",
            entity_type="catalogue",
            entity_id=None,
            entity_name=None,
            message="No publishable content found. At least one published show with published episodes is required.",
            suggested_action="Publish at least one show and its episodes before attempting catalogue publication.",
        ))

    blocking_count = sum(1 for i in issues if i.severity == "blocking")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    return ValidationReport(
        ready=blocking_count == 0,
        total_issues=len(issues),
        blocking_count=blocking_count,
        warning_count=warning_count,
        issues=issues,
    )
