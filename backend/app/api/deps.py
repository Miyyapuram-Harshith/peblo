"""API dependencies - authentication, authorization, common deps."""
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole
from app.storage.provider import StorageProvider, create_storage_provider

security_scheme = HTTPBearer()

_storage: StorageProvider | None = None


def get_storage() -> StorageProvider:
    """Get the configured storage provider (singleton)."""
    global _storage
    if _storage is None:
        _storage = create_storage_provider()
    return _storage


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate JWT and return the current user."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Invalid or expired authentication token."}},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": "Token missing user identifier."}},
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User account not found."}},
        )

    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ADMIN_REQUIRED", "message": "This action requires administrator privileges."}},
        )
    return user


async def require_editor_or_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require at least editor role."""
    if user.role not in (UserRole.EDITOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "You do not have permission to perform this action."}},
        )
    return user
