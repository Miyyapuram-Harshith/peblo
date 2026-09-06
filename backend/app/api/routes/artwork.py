"""Artwork upload, retrieval, and deletion routes."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_storage, require_editor_or_admin
from app.db.session import get_db
from app.models import Artwork, ArtworkType, Episode, OwnerType, Show, User
from app.schemas.schemas import ArtworkResponse
from app.services.artwork import ArtworkValidationError, validate_artwork
from app.storage.provider import StorageProvider, generate_storage_key

router = APIRouter(prefix="/admin/artwork", tags=["Artwork"])

MAX_UPLOAD_SIZE = 1024 * 1024  # 1MB hard limit (spec says 200KB, but we validate properly)


@router.post("", response_model=ArtworkResponse, status_code=201)
async def upload_artwork(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
    file: UploadFile = File(...),
    owner_type: str = Form(...),
    owner_id: str = Form(...),
    artwork_type: str = Form(...),
):
    """Upload and validate artwork."""
    # Validate enums
    try:
        ot = OwnerType(owner_type)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_OWNER_TYPE", "message": f"Invalid owner_type: {owner_type}. Must be 'show' or 'episode'."}})

    try:
        at = ArtworkType(artwork_type)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_ARTWORK_TYPE", "message": f"Invalid artwork_type: {artwork_type}. Must be 'poster', 'banner', or 'thumbnail'."}})

    try:
        owner_uuid = uuid.UUID(owner_id)
    except ValueError:
        raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_OWNER_ID", "message": "Invalid owner_id format."}})

    # Verify owner exists
    if ot == OwnerType.SHOW:
        result = await db.execute(select(Show).where(Show.id == owner_uuid))
    else:
        result = await db.execute(select(Episode).where(Episode.id == owner_uuid))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail={"error": {"code": "OWNER_NOT_FOUND", "message": f"{owner_type.capitalize()} not found."}})

    # Read file data
    file_data = await file.read()
    if len(file_data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail={"error": {"code": "FILE_TOO_LARGE", "message": "File exceeds maximum upload size of 1 MB."}})

    if len(file_data) == 0:
        raise HTTPException(status_code=422, detail={"error": {"code": "EMPTY_FILE", "message": "Uploaded file is empty."}})

    # Validate using Pillow (server-side, do NOT trust filename/Content-Type)
    try:
        validation_result = validate_artwork(file_data, at, file.filename)
    except ArtworkValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": e.code, "message": e.message, "details": e.details}},
        )

    # Generate safe storage key
    storage_key = generate_storage_key(
        f"artwork/{owner_type}/{artwork_type}",
        validation_result["extension"],
    )

    # Delete existing artwork of same type for same owner
    existing = await db.execute(
        select(Artwork).where(
            Artwork.owner_type == ot,
            Artwork.owner_id == owner_uuid,
            Artwork.artwork_type == at,
        )
    )
    existing_art = existing.scalar_one_or_none()
    if existing_art:
        await storage.delete(existing_art.storage_key)
        await db.delete(existing_art)
        await db.flush()

    # Store file
    await storage.put(storage_key, file_data, validation_result["mime_type"])

    # Create DB record
    artwork = Artwork(
        owner_type=ot,
        owner_id=owner_uuid,
        artwork_type=at,
        storage_key=storage_key,
        mime_type=validation_result["mime_type"],
        width=validation_result["width"],
        height=validation_result["height"],
        size_bytes=validation_result["size_bytes"],
        sha256=validation_result["sha256"],
    )
    db.add(artwork)
    await db.commit()
    await db.refresh(artwork)

    response = ArtworkResponse.model_validate(artwork)
    response.url = storage.public_url(storage_key)
    return response


@router.get("/{artwork_id}", response_model=ArtworkResponse)
async def get_artwork(
    artwork_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Get artwork metadata."""
    result = await db.execute(select(Artwork).where(Artwork.id == artwork_id))
    artwork = result.scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail={"error": {"code": "ARTWORK_NOT_FOUND", "message": "Artwork not found."}})

    response = ArtworkResponse.model_validate(artwork)
    response.url = storage.public_url(artwork.storage_key)
    return response


@router.delete("/{artwork_id}", status_code=204)
async def delete_artwork(
    artwork_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_editor_or_admin)],
    storage: Annotated[StorageProvider, Depends(get_storage)],
):
    """Delete artwork."""
    result = await db.execute(select(Artwork).where(Artwork.id == artwork_id))
    artwork = result.scalar_one_or_none()
    if not artwork:
        raise HTTPException(status_code=404, detail={"error": {"code": "ARTWORK_NOT_FOUND", "message": "Artwork not found."}})

    await storage.delete(artwork.storage_key)
    await db.delete(artwork)
    await db.commit()
