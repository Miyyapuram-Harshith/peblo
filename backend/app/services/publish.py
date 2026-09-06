from __future__ import annotations

"""Publish service - orchestrates atomic catalogue publication."""
import time
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import ActiveCatalogue, PublishRun, PublishStatus
from app.schemas.schemas import PublishReceipt, PublishStage
from app.services.catalogue import CatalogueBuilder
from app.services.validation import run_validation
from app.storage.provider import StorageProvider

logger = get_logger("publish")


class PublishError(Exception):
    """Publication failure with error code."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def publish_catalogue(
    db: AsyncSession,
    user_id: str,
    user_email: str,
    storage: StorageProvider,
    idempotency_key: str | None = None,
) -> PublishReceipt:
    """
    Execute the full atomic publish pipeline.
    If anything fails before activation, the previous catalogue remains live.
    """
    start = time.monotonic()
    stages: list[PublishStage] = []
    settings = get_settings()

    # Check idempotency
    if idempotency_key:
        existing = await db.execute(
            select(PublishRun).where(PublishRun.idempotency_key == idempotency_key)
        )
        existing_run = existing.scalar_one_or_none()
        if existing_run and existing_run.status == PublishStatus.SUCCESS:
            logger.info("publish.idempotent", idempotency_key=idempotency_key, run_id=str(existing_run.id))
            return _build_receipt(existing_run, [
                PublishStage(name="Idempotent", status="success", message="Previously completed publish returned")
            ])

    # Acquire publish lock using SELECT ... FOR UPDATE
    # This prevents concurrent publishes
    lock_result = await db.execute(
        select(ActiveCatalogue).with_for_update(nowait=False).limit(1)
    )
    active = lock_result.scalar_one_or_none()

    # Determine next version
    next_version = (active.version + 1) if active else 1

    # Create publish run record
    run = PublishRun(
        triggered_by=user_id,
        idempotency_key=idempotency_key,
        status=PublishStatus.PENDING,
    )
    db.add(run)
    await db.flush()
    run_id = str(run.id)

    try:
        # Stage 1: Validation
        run.status = PublishStatus.VALIDATING
        await db.flush()
        stages.append(PublishStage(name="Validation", status="running"))

        report = await run_validation(db)
        if not report.ready:
            blocking_messages = [i.message for i in report.issues if i.severity == "blocking"]
            raise PublishError(
                code="VALIDATION_FAILED",
                message=f"{report.blocking_count} blocking issue(s): {'; '.join(blocking_messages[:3])}",
            )
        stages[-1] = PublishStage(name="Validation", status="success")

        # Stage 2: Build catalogue
        run.status = PublishStatus.BUILDING
        await db.flush()
        stages.append(PublishStage(name="Catalogue Build", status="running"))

        builder = CatalogueBuilder(db, storage)
        catalogue, canonical_json, stats = await builder.build(next_version)
        stages[-1] = PublishStage(name="Catalogue Build", status="success")

        stages.append(PublishStage(name="Language Grouping", status="success"))
        stages.append(PublishStage(name="Deterministic Ordering", status="success"))
        stages.append(PublishStage(name="Integrity Hash", status="success", message=catalogue.catalogue_hash[:16] + "..."))

        # Failure injection for testing
        if settings.publish_failure_injection:
            raise PublishError(
                code="INJECTED_FAILURE",
                message="Publish failure injection is enabled. This is a test failure.",
            )

        # Stage 3: Store immutable artifact
        run.status = PublishStatus.STORING
        await db.flush()
        stages.append(PublishStage(name="Immutable Storage", status="running"))

        catalogue_key = await builder.store_catalogue(canonical_json, catalogue.catalogue_hash)
        stages[-1] = PublishStage(name="Immutable Storage", status="success")

        # Stage 4: Atomic activation
        run.status = PublishStatus.ACTIVATING
        await db.flush()
        stages.append(PublishStage(name="Atomic Activation", status="running"))

        if active:
            active.active_catalogue_key = catalogue_key
            active.active_catalogue_hash = catalogue.catalogue_hash
            active.version = next_version
            active.updated_at = datetime.now(UTC)
        else:
            active = ActiveCatalogue(
                id=1,
                active_catalogue_key=catalogue_key,
                active_catalogue_hash=catalogue.catalogue_hash,
                version=next_version,
            )
            db.add(active)

        stages[-1] = PublishStage(name="Atomic Activation", status="success")

        # Record success
        elapsed_ms = int((time.monotonic() - start) * 1000)
        run.status = PublishStatus.SUCCESS
        run.completed_at = datetime.now(UTC)
        run.catalogue_key = catalogue_key
        run.catalogue_hash = catalogue.catalogue_hash
        run.shows_count = stats["shows_count"]
        run.episodes_count = stats["episodes_count"]
        run.language_group_count = stats["language_group_count"]
        run.duration_ms = elapsed_ms

        stages.append(PublishStage(name="Run Recorded", status="success"))

        await db.commit()

        logger.info(
            "publish.success",
            run_id=run_id,
            version=next_version,
            hash=catalogue.catalogue_hash,
            duration_ms=elapsed_ms,
            user=user_email,
        )

        return PublishReceipt(
            run_id=run.id,
            version=next_version,
            catalogue_hash=catalogue.catalogue_hash,
            triggered_by=user_email,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_ms=elapsed_ms,
            shows_count=stats["shows_count"],
            episodes_count=stats["episodes_count"],
            language_group_count=stats["language_group_count"],
            stages=stages,
            status="success",
        )

    except PublishError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stages.append(PublishStage(name="Failed", status="failed", message=e.message))

        if e.code == "VALIDATION_FAILED":
            run.status = PublishStatus.FAILED_VALIDATION
        elif e.code == "INJECTED_FAILURE":
            run.status = PublishStatus.FAILED_BUILD
        else:
            run.status = PublishStatus.FAILED_BUILD

        run.completed_at = datetime.now(UTC)
        run.duration_ms = elapsed_ms
        run.error_code = e.code
        run.error_message = e.message
        await db.commit()

        logger.warning(
            "publish.failed",
            run_id=run_id,
            error_code=e.code,
            error_message=e.message,
            duration_ms=elapsed_ms,
            user=user_email,
        )

        raise

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stages.append(PublishStage(name="Failed", status="failed", message=str(e)))

        run.status = PublishStatus.FAILED_BUILD
        run.completed_at = datetime.now(UTC)
        run.duration_ms = elapsed_ms
        run.error_code = "UNEXPECTED_ERROR"
        run.error_message = str(e)
        await db.commit()

        logger.error(
            "publish.unexpected_error",
            run_id=run_id,
            error=str(e),
            duration_ms=elapsed_ms,
            user=user_email,
        )
        raise PublishError(code="UNEXPECTED_ERROR", message=f"Unexpected error during publication: {str(e)}")


def _build_receipt(run: PublishRun, stages: list[PublishStage]) -> PublishReceipt:
    """Build a receipt from an existing run record."""
    return PublishReceipt(
        run_id=run.id,
        version=0,
        catalogue_hash=run.catalogue_hash or "",
        triggered_by=run.triggered_by_user.email if run.triggered_by_user else "unknown",
        started_at=run.started_at,
        completed_at=run.completed_at or run.started_at,
        duration_ms=run.duration_ms or 0,
        shows_count=run.shows_count or 0,
        episodes_count=run.episodes_count or 0,
        language_group_count=run.language_group_count or 0,
        stages=stages,
        status=run.status.value,
    )
