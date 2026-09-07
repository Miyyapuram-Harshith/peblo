from __future__ import annotations

"""Catalogue builder service - creates deterministic, immutable catalogue artifacts."""

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models import (
    Artwork,
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

        Returns:
            (catalogue, canonical_json, stats)
        """
        logger.info("catalogue.build.start", version=version)

        # Load all published shows with their full relationship tree.
        result = await self.db.execute(
            select(Show)
            .options(
                selectinload(Show.seasons).selectinload(Season.episodes),
                selectinload(Show.artwork),
            )
            .where(Show.status == ContentStatus.PUBLISHED)
        )

        published_shows = result.scalars().unique().all()

        # Load all published episode artwork in one query.
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
                ep_artwork_map[str(art.owner_id)][
                    art.artwork_type.value
                ] = self.storage.public_url(art.storage_key)

        # Build sections.
        sections_map: dict[str, list[CatalogueShow]] = defaultdict(list)

        total_episodes = 0
        content_groups_seen: set[str] = set()

        for show in sorted(
            published_shows,
            key=lambda s: (s.section or "", s.title),
        ):
            section = show.section or "Uncategorized"

            # Build show artwork URLs.
            show_artwork: dict[str, str | None] = {}

            for art in show.artwork or []:
                show_artwork[art.artwork_type.value] = (
                    self.storage.public_url(art.storage_key)
                )

            # Build seasons.
            # Season 0 is reserved for trailers and is kept separate
            # from normal numbered seasons.
            catalogue_seasons: list[CatalogueSeason] = []
            trailer_season: CatalogueSeason | None = None

            for season in sorted(
                show.seasons,
                key=lambda s: s.season_number,
            ):
                published_episodes = [
                    ep
                    for ep in season.episodes
                    if ep.status == ContentStatus.PUBLISHED
                ]

                if not published_episodes:
                    continue

                # Group language variants by content_group.
                grouped = self._group_episodes(
                    published_episodes,
                    ep_artwork_map,
                )

                if not grouped:
                    continue

                total_episodes += len(grouped)

                for episode in grouped:
                    content_groups_seen.add(episode.content_group)

                catalogue_season = CatalogueSeason(
                    season_number=season.season_number,
                    title=(
                        "Trailers"
                        if season.season_number == 0
                        else season.title
                    ),
                    episodes=grouped,
                )

                if season.season_number == 0:
                    trailer_season = catalogue_season
                else:
                    catalogue_seasons.append(catalogue_season)

            # Keep trailers at the end of the show's catalogue.
            if trailer_season:
                catalogue_seasons.append(trailer_season)

            if not catalogue_seasons:
                continue

            catalogue_show = CatalogueShow(
                id=str(show.id),
                title=show.title,
                slug=show.slug,
                synopsis=show.synopsis,
                category=show.category,
                artwork=show_artwork,
                seasons=catalogue_seasons,
            )

            sections_map[section].append(catalogue_show)

        # Build sections list in deterministic order.
        catalogue_sections = [
            CatalogueSection(
                section=section,
                shows=shows,
            )
            for section, shows in sorted(sections_map.items())
        ]

        generated_at = datetime.now(UTC).isoformat()

        catalogue = CatalogueContract(
            version=version,
            generated_at=generated_at,
            catalogue_hash="",
            sections=catalogue_sections,
        )

        # ------------------------------------------------------------
        # Canonicalize and hash
        # ------------------------------------------------------------
        #
        # The catalogue_hash field itself must not participate in the
        # hash calculation because that would create a circular hash.
        #
        # We therefore calculate the hash with catalogue_hash="",
        # then store the resulting hash inside the final catalogue.
        #
        canonical_for_hash = self._canonicalize(catalogue)

        catalogue_hash = hashlib.sha256(
            canonical_for_hash.encode("utf-8")
        ).hexdigest()

        catalogue.catalogue_hash = catalogue_hash

        # Final catalogue JSON includes the hash for consumers.
        canonical = self._canonicalize(catalogue)

        stats = {
            "shows_count": sum(
                len(section.shows)
                for section in catalogue_sections
            ),
            "episodes_count": total_episodes,
            "language_group_count": len(content_groups_seen),
        }

        logger.info(
            "catalogue.build.complete",
            version=version,
            hash=catalogue_hash,
            **stats,
        )

        return catalogue, canonical, stats

    def _group_episodes(
        self,
        episodes: list[Episode],
        ep_artwork_map: dict[str, dict[str, str]],
    ) -> list[CatalogueEpisode]:
        """Group episodes by content_group, merging language variants."""

        groups: dict[str, dict] = {}

        for episode in sorted(
            episodes,
            key=lambda e: (e.content_group, e.language),
        ):
            if episode.content_group not in groups:
                thumbnail = ep_artwork_map.get(
                    str(episode.id),
                    {},
                ).get("thumbnail")

                groups[episode.content_group] = {
                    "content_group": episode.content_group,
                    "title": episode.title,
                    "synopsis": episode.synopsis,
                    "duration_seconds": episode.duration_seconds,
                    "thumbnail": thumbnail,
                    "languages": [],
                }

            groups[episode.content_group]["languages"].append(
                CatalogueLanguage(
                    language=episode.language,
                    video_url=episode.video_url,
                )
            )

            # Prefer English title and synopsis as the default.
            if episode.language == "English":
                groups[episode.content_group]["title"] = episode.title
                groups[episode.content_group]["synopsis"] = (
                    episode.synopsis
                )

                # Prefer English episode thumbnail when available.
                english_thumbnail = ep_artwork_map.get(
                    str(episode.id),
                    {},
                ).get("thumbnail")

                if english_thumbnail:
                    groups[episode.content_group][
                        "thumbnail"
                    ] = english_thumbnail

        return [
            CatalogueEpisode(
                content_group=group["content_group"],
                title=group["title"],
                synopsis=group["synopsis"],
                duration_seconds=group["duration_seconds"],
                thumbnail=group["thumbnail"],
                languages=sorted(
                    group["languages"],
                    key=lambda language: language.language,
                ),
            )
            for group in sorted(
                groups.values(),
                key=lambda group: group["content_group"],
            )
        ]

    def _canonicalize(
        self,
        catalogue: CatalogueContract,
    ) -> str:
        """Produce canonical JSON for deterministic hashing."""

        return json.dumps(
            catalogue.model_dump(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    async def store_catalogue(
        self,
        canonical_json: str,
        catalogue_hash: str,
    ) -> str:
        """Store catalogue as an immutable artifact."""

        key = f"catalogues/{catalogue_hash}.json"

        # Check if this exact catalogue already exists.
        # This makes storage idempotent.
        if await self.storage.exists(key):
            logger.info(
                "catalogue.store.exists",
                key=key,
            )
            return key

        await self.storage.put(
            key,
            canonical_json.encode("utf-8"),
            content_type="application/json",
        )

        # ------------------------------------------------------------
        # Verify stored artifact.
        # ------------------------------------------------------------
        #
        # The catalogue hash is defined over the canonical payload
        # with catalogue_hash blanked out.
        #
        # The stored artifact contains the actual hash value, so we
        # must blank that field before calculating the verification
        # hash.
        #
        stored = await self.storage.get(key)

        if stored is None:
            raise RuntimeError(
                f"Failed to verify stored catalogue: {key}"
            )

        try:
            stored_payload = json.loads(
                stored.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Stored catalogue is not valid UTF-8 JSON: {key}"
            ) from exc

        stored_payload["catalogue_hash"] = ""

        stored_canonical = json.dumps(
            stored_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        stored_hash = hashlib.sha256(
            stored_canonical.encode("utf-8")
        ).hexdigest()

        if stored_hash != catalogue_hash:
            raise RuntimeError(
                "Catalogue integrity check failed: "
                f"expected {catalogue_hash}, "
                f"got {stored_hash}"
            )

        logger.info(
            "catalogue.store.success",
            key=key,
            hash=catalogue_hash,
        )

        return key