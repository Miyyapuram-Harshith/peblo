from __future__ import annotations

"""Peblo TV Mini Backend - Core Configuration."""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "peblo-tv-mini"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://peblo:peblo_dev@localhost:5432/peblo"
    database_url_sync: str = "postgresql://peblo:peblo_dev@localhost:5432/peblo"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 480

    # Storage
    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    storage_public_url_prefix: str = "/storage"

    # R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_url: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:5174"

    # Publishing
    publish_failure_injection: bool = False

    # Seed
    seed_on_startup: bool = True
    seed_data_path: str = "./data"

    # Demo Credentials
    demo_admin_email: str = "admin@peblo.test"
    demo_admin_password: str = "admin123"
    demo_editor_email: str = "editor@peblo.test"
    demo_editor_password: str = "editor123"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
