from __future__ import annotations

"""Database seeder - loads seed data idempotently."""
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models import ContentStatus, Episode, Season, Show, User, UserRole

logger = get_logger("seeder")


def _slugify(text: str) -> str:
    """Generate a URL-safe slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


async def seed_users(db: AsyncSession) -> None:
    """Create demo users if they don't exist."""
    settings = get_settings()

    for email, password, role in [
        (settings.demo_admin_email, settings.demo_admin_password, UserRole.ADMIN),
        (settings.demo_editor_email, settings.demo_editor_password, UserRole.EDITOR),
    ]:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none() is None:
            user = User(
                email=email,
                password_hash=hash_password(password),
                role=role,
            )
            db.add(user)
            logger.info("seeder.user_created", email=email, role=role.value)

    await db.commit()


async def seed_shows(db: AsyncSession) -> None:
    """Load shows from seed_shows.json idempotently."""
    settings = get_settings()
    seed_path = Path(settings.seed_data_path) / "seed_shows.json"

    if not seed_path.exists():
        logger.warning("seeder.no_seed_file", path=str(seed_path))
        return

    data = json.loads(seed_path.read_text(encoding="utf-8"))
    shows_data = data.get("shows", [])

    for show_data in shows_data:
        slug = _slugify(show_data["title"])

        # Check if already exists
        result = await db.execute(select(Show).where(Show.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            logger.info("seeder.show_exists", title=show_data["title"], slug=slug)
            continue

        # Create show
        status_str = show_data.get("status", "draft")
        try:
            status = ContentStatus(status_str)
        except ValueError:
            status = ContentStatus.DRAFT

        show = Show(
            title=show_data["title"],
            slug=slug,
            synopsis=show_data.get("synopsis"),
            section=show_data.get("section"),
            category=show_data.get("category"),
            status=status,
        )
        db.add(show)
        await db.flush()

        # Create seasons
        for season_data in show_data.get("seasons", []):
            season = Season(
                show_id=show.id,
                season_number=season_data["season_number"],
                title=season_data.get("title"),
            )
            db.add(season)
            await db.flush()

            # Create episodes
            for ep_data in season_data.get("episodes", []):
                ep_status_str = ep_data.get("status", "draft")
                try:
                    ep_status = ContentStatus(ep_status_str)
                except ValueError:
                    ep_status = ContentStatus.DRAFT

                episode = Episode(
                    season_id=season.id,
                    title=ep_data["title"],
                    synopsis=ep_data.get("synopsis"),
                    duration_seconds=ep_data.get("duration_seconds"),
                    language=ep_data["language"],
                    content_group=ep_data["content_group"],
                    video_url=ep_data.get("video_url"),
                    status=ep_status,
                )
                db.add(episode)

        logger.info("seeder.show_created", title=show_data["title"], slug=slug)

    await db.commit()
    logger.info("seeder.complete", shows_count=len(shows_data))


async def run_seed(db: AsyncSession) -> None:
    """Run all seeders."""
    logger.info("seeder.start")
    await seed_users(db)
    await seed_shows(db)
    logger.info("seeder.done")
