from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    secret_key: str = Field(default="change-me-insecure-dev-key", min_length=16)
    access_token_expire_minutes: int = Field(default=15)
    refresh_token_expire_days: int = Field(default=7)
    auth_cookie_secure: bool = Field(default=False)
    auth_cookie_samesite: str = Field(default="lax")
    csrf_cookie_secure: bool = Field(default=False)

    database_url: str = Field(default="sqlite+pysqlite:///./homelab.db")
    redis_url: str = Field(default="redis://redis:6379/0")
    docker_host: str = Field(default="tcp://socket-proxy:2375")

    backup_encryption_enabled: bool = Field(default=False)
    backup_encryption_key: str = Field(default="")
    compose_project_name: str = Field(default="homelab")

    bootstrap_admin_email: str = Field(
        default="admin@example.com",
        validation_alias=AliasChoices("BOOTSTRAP_ADMIN_EMAIL", "INITIAL_ADMIN_EMAIL"),
    )
    bootstrap_admin_password: str = Field(
        default="",
        validation_alias=AliasChoices("BOOTSTRAP_ADMIN_PASSWORD", "INITIAL_ADMIN_PASSWORD"),
    )

    data_dir: Path = Field(default=Path("/var/lib/homelab"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
