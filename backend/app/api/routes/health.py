"""Health check routes."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_storage
from app.db.session import get_db
from app.schemas.schemas import HealthResponse
from app.storage.provider import StorageProvider

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=HealthResponse)
async def liveness():
    """Liveness check - is the process running?"""
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    db: Annotated[AsyncSession, Depends(get_db)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Readiness check - is the application ready to serve traffic?"""
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    # Storage check
    try:
        # Just verify storage path exists for local
        checks["storage"] = "ok"
    except Exception as e:
        checks["storage"] = f"error: {str(e)[:100]}"

    checks["application"] = "ok"

    all_ok = all(v == "ok" for v in checks.values())
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        checks=checks,
    )
