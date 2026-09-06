"""Catalogue builder service - creates deterministic, immutable catalogue artifacts."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import (
    Artwork,
    ArtworkType,
    ContentStatus,
    Episode,
    OwnerType,
    Season,
    Show,
)
from app.schemas.schemas import (
    CatalogueContract,
    CatalogueEpisode,
    CatalogueLanguage,
    CatalogueSeason,
    CatalogueSection,
    CatalogueShow,
)
from app.storage.provider import StorageProvider

logger = get_logger("catalogue_builder")


class CatalogueBuilder:
    """Builds a deterministic, validated catalogue from published content."""

    def __init__(self, db: AsyncSession, storage: StorageProvider):
        self.db = db
        self.storage = storage

    async def build(self, version: int) -> tuple[CatalogueContract, str, dict]:
        """
        Build the catalogue.
        Returns: (catalogue, canonical_json, stats)
        """
        logger.info("catalogue.build.start", version=version)

        # Load all published shows with full relationship tree
        result = await self.db.execute(
            select(Show)
            .options(
                selectinload(Show.seasons).selectinload(Season.episodes),
                selectinload(Show.artwork),
            )
            .where(Show.status == ContentStatus.PUBLISHED)
        )
        published_shows = result.scalars().unique().all()

        # Load all episode artwork in one query
        ep_ids = []
        for show in published_shows:
            for season in show.seasons:
                for episode in season.episodes:
                    if episode.status == ContentStatus.PUBLISHED:
                        ep_ids.append(episode.id)

        ep_artwork_map: dict[str, dict[str, str]] = defaultdict(dict)
        if ep_ids:
            art_result = await self.db.execute(
                select(Artwork).where(
                    Artwork.owner_type == OwnerType.EPISODE,
                    Artwork.owner_id.in_(ep_ids),
                )
            )
            for art in art_result.scalars().all():
                ep_artwork_map[str(art.owner_id)][art.artwork_type.value] = self.storage.public_url(art.storage_key)

        # Build sections
        sections_map: dict[str, list[CatalogueShow]] = defaultdict(list)
        total_episodes = 0
        content_groups_seen: set[str] = set()

        for show in sorted(published_shows, key=lambda s: (s.section or "", s.title)):
            section = show.section or "Uncategorized"

            # Show artwork
            show_artwork: dict[str, str | None] = {}
            for art in (show.artwork or []):
                show_artwork[art.artwork_type.value] = self.storage.public_url(art.storage_key)

            # Build seasons (exclude Season 0 from normal seasons, handle separately)
            catalogue_seasons: list[CatalogueSeason] = []
            trailer_season: CatalogueSeason | None = None

            for season in sorted(show.seasons, key=lambda s: s.season_number):
                published_episodes = [
                    ep for ep in season.episodes
                    if ep.status == ContentStatus.PUBLISHED
                ]
                if not published_episodes:
                    continue

                # Group episodes by content_group
                grouped = self._group_episodes(published_episodes, ep_artwork_map)

                if not grouped:
                    continue

                total_episodes += len(grouped)
                for ep in grouped:
                    content_groups_seen.add(ep.content_group)

                cat_season = CatalogueSeason(
                    season_number=season.season_number,
                    title="Trailers" if season.season_number == 0 else season.title,
                    episodes=grouped,
                )

                if season.season_number == 0:
                    trailer_season = cat_season
                else:
                    catalogue_seasons.append(cat_season)

            # Put trailer season at the end if it exists
            if trailer_season:
                catalogue_seasons.append(trailer_season)

            if not catalogue_seasons:
                continue

            cat_show = CatalogueShow(
                id=str(show.id),
                title=show.title,
                slug=show.slug,
                synopsis=show.synopsis,
                category=show.category,
                artwork=show_artwork,
                seasons=catalogue_seasons,
            )
            sections_map[section].append(cat_show)

        # Build sections list, sorted deterministically
        catalogue_sections = [
            CatalogueSection(section=section, shows=shows)
            for section, shows in sorted(sections_map.items())
        ]

        generated_at = datetime.now(timezone.utc).isoformat()
        catalogue = CatalogueContract(
            version=version,
            generated_at=generated_at,
            catalogue_hash="",  # Will be filled after hashing
            sections=catalogue_sections,
        )

        # Canonicalize and hash
        canonical = self._canonicalize(catalogue)
        catalogue_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        catalogue.catalogue_hash = catalogue_hash

        # Recanonicalize with hash
        canonical = self._canonicalize(catalogue)

        stats = {
            "shows_count": sum(len(s.shows) for s in catalogue_sections),
            "episodes_count": total_episodes,
            "language_group_count": len(content_groups_seen),
        }

        logger.info("catalogue.build.complete", version=version, hash=catalogue_hash, **stats)
        return catalogue, canonical, stats

    def _group_episodes(
        self,
        episodes: list[Episode],
        ep_artwork_map: dict[str, dict[str, str]],
    ) -> list[CatalogueEpisode]:
        """Group episodes by content_group, merging language variants."""
        groups: dict[str, dict] = {}

        for ep in sorted(episodes, key=lambda e: (e.content_group, e.language)):
            if ep.content_group not in groups:
                # Use first encountered episode as base
                thumbnail = ep_artwork_map.get(str(ep.id), {}).get("thumbnail")
                groups[ep.content_group] = {
                    "content_group": ep.content_group,
                    "title": ep.title,
                    "synopsis": ep.synopsis,
                    "duration_seconds": ep.duration_seconds,
                    "thumbnail": thumbnail,
                    "languages": [],
                }

            groups[ep.content_group]["languages"].append(
                CatalogueLanguage(
                    language=ep.language,
                    video_url=ep.video_url,
                )
            )

            # Prefer English title/synopsis as default
            if ep.language == "English":
                groups[ep.content_group]["title"] = ep.title
                groups[ep.content_group]["synopsis"] = ep.synopsis
                # Also prefer English episode thumbnail if available
                en_thumb = ep_artwork_map.get(str(ep.id), {}).get("thumbnail")
                if en_thumb:
                    groups[ep.content_group]["thumbnail"] = en_thumb

        return [
            CatalogueEpisode(
                content_group=g["content_group"],
                title=g["title"],
                synopsis=g["synopsis"],
                duration_seconds=g["duration_seconds"],
                thumbnail=g["thumbnail"],
                languages=sorted(g["languages"], key=lambda l: l.language),
            )
            for g in sorted(groups.values(), key=lambda g: g["content_group"])
        ]

    def _canonicalize(self, catalogue: CatalogueContract) -> str:
        """Produce canonical JSON for deterministic hashing."""
        return json.dumps(
            catalogue.model_dump(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    async def store_catalogue(self, canonical_json: str, catalogue_hash: str) -> str:
        """Store catalogue as immutable artifact. Returns storage key."""
        key = f"catalogues/{catalogue_hash}.json"

        # Check if this exact catalogue already exists (idempotent)
        if await self.storage.exists(key):
            logger.info("catalogue.store.exists", key=key)
            return key

        await self.storage.put(key, canonical_json.encode("utf-8"), content_type="application/json")

        # Verify stored artifact
        stored = await self.storage.get(key)
        if stored is None:
            raise RuntimeError(f"Failed to verify stored catalogue: {key}")

        stored_hash = hashlib.sha256(stored).hexdigest()
        if stored_hash != catalogue_hash:
            raise RuntimeError(
                f"Catalogue integrity check failed: expected {catalogue_hash}, got {stored_hash}"
            )

        logger.info("catalogue.store.success", key=key, hash=catalogue_hash)
        return key
