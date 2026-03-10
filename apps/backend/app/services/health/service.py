from __future__ import annotations

from datetime import datetime, timezone

from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.schemas.health import ReadinessCheck, ReadinessResponse
from app.services.docker_gateway import DockerGateway


class ReadinessService:
    def __init__(self, db: Session, settings: Settings, docker_gateway: DockerGateway) -> None:
        self.db = db
        self.settings = settings
        self.docker_gateway = docker_gateway

    def check(self) -> ReadinessResponse:
        checks: list[ReadinessCheck] = []

        try:
            self.db.execute(text("SELECT 1"))
            checks.append(ReadinessCheck(name="database", status="ok"))
        except Exception as exc:  # noqa: BLE001
            checks.append(ReadinessCheck(name="database", status="error", details=str(exc)))

        try:
            redis_client = Redis.from_url(self.settings.redis_url)
            redis_client.ping()
            checks.append(ReadinessCheck(name="redis", status="ok"))
        except Exception as exc:  # noqa: BLE001
            checks.append(ReadinessCheck(name="redis", status="error", details=str(exc)))

        if self.docker_gateway.ping():
            checks.append(ReadinessCheck(name="docker", status="ok"))
        else:
            checks.append(
                ReadinessCheck(name="docker", status="error", details="Docker API unavailable")
            )

        overall = "ok" if all(check.status == "ok" for check in checks) else "degraded"
        return ReadinessResponse(
            status=overall, timestamp=datetime.now(timezone.utc), checks=checks
        )
