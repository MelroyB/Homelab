from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.service import ManagedService, ServiceConfigVersion
from app.models.user import User
from app.schemas.service import ConfigApplyRequest
from app.services.adapters.implementations import build_adapter
from app.services.docker_gateway import DockerGateway
from app.utils.hash import sha256_text


class ConfigManager:
    def __init__(self, db: Session, docker_gateway: DockerGateway) -> None:
        self.db = db
        self.docker_gateway = docker_gateway

    def validate_candidate(
        self,
        *,
        service: ManagedService,
        config_json: dict,
        raw_config: str,
    ) -> tuple[bool, list[str], str]:
        adapter = build_adapter(service, self.docker_gateway)
        rendered = adapter.renderer.render(service, config_json, raw_config)
        valid, errors = adapter.validator.validate(service, rendered)
        return valid, errors, rendered

    def apply_candidate(
        self,
        *,
        service: ManagedService,
        actor: User,
        payload: ConfigApplyRequest,
    ) -> tuple[ServiceConfigVersion, list[str]]:
        valid, errors, rendered = self.validate_candidate(
            service=service,
            config_json=payload.config_json,
            raw_config=payload.raw_config,
        )

        max_version = self.db.scalar(
            select(func.max(ServiceConfigVersion.version)).where(
                ServiceConfigVersion.service_slug == service.slug
            )
        )
        next_version = int(max_version or 0) + 1

        version = ServiceConfigVersion(
            service_slug=service.slug,
            version=next_version,
            config_json=payload.config_json,
            raw_config=payload.raw_config,
            rendered_config=rendered,
            checksum=sha256_text(rendered),
            validation_status="valid" if valid else "invalid",
            validation_errors=errors,
            apply_status="pending",
            created_by_id=actor.id,
        )
        self.db.add(version)
        self.db.flush()

        warnings: list[str] = []
        if not valid:
            version.apply_status = "rejected"
            version.apply_message = "Validation failed"
            self.db.commit()
            self.db.refresh(version)
            return version, warnings

        self._write_rendered_config(service.config_path, rendered)
        version.applied_at = datetime.now(timezone.utc)

        if not service.enabled:
            version.apply_status = "applied"
            version.apply_message = "Config written (service disabled; no runtime reload triggered)"
        elif payload.auto_reload and service.supports_reload:
            ok, message = build_adapter(service, self.docker_gateway).controller.execute(
                service, "reload"
            )
            if not ok:
                warnings.append(message)
                ok_restart, restart_msg = build_adapter(
                    service, self.docker_gateway
                ).controller.execute(service, "restart")
                message = restart_msg
                ok = ok_restart
            version.apply_status = "applied" if ok else "failed"
            version.apply_message = message
        else:
            version.apply_status = "applied"
            version.apply_message = "Config written (no runtime reload triggered)"

        if version.apply_status == "applied":
            self.db.execute(
                update(ServiceConfigVersion)
                .where(ServiceConfigVersion.service_slug == service.slug)
                .values(is_active=False)
            )
            version.is_active = True

        self.db.commit()
        self.db.refresh(version)
        return version, warnings

    def rollback(
        self, *, service: ManagedService, actor: User, version_id: str
    ) -> ServiceConfigVersion:
        target = self.db.scalar(
            select(ServiceConfigVersion).where(
                ServiceConfigVersion.service_slug == service.slug,
                ServiceConfigVersion.id == version_id,
            )
        )
        if target is None:
            raise ValueError("Config version not found")

        payload = ConfigApplyRequest(
            config_json=target.config_json,
            raw_config=target.raw_config,
            auto_reload=True,
        )
        new_version, _warnings = self.apply_candidate(service=service, actor=actor, payload=payload)
        new_version.apply_message = (
            f"Rollback from version {target.version}. {new_version.apply_message}"
        )
        self.db.add(new_version)
        self.db.commit()
        self.db.refresh(new_version)
        return new_version

    @staticmethod
    def _write_rendered_config(config_path: str, rendered: str) -> None:
        if not config_path:
            return
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
