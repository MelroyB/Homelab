from __future__ import annotations

from dataclasses import dataclass, field

from app.models.service import ManagedService
from app.services.docker_gateway import DockerGateway

STARTABLE_STATES = {"created", "exited", "dead", "paused"}


@dataclass
class ServiceLifecycleResult:
    enabled: bool
    status: str
    message: str
    warnings: list[str] = field(default_factory=list)


class ServiceLifecycleManager:
    def __init__(self, docker_gateway: DockerGateway) -> None:
        self.docker_gateway = docker_gateway

    def reconcile_enabled(
        self, *, service: ManagedService, enabled: bool
    ) -> ServiceLifecycleResult:
        service.enabled = enabled
        runtime_state = self._runtime_state(service)

        if not enabled:
            return self._disable_service(service=service, runtime_state=runtime_state)
        return self._enable_service(service=service, runtime_state=runtime_state)

    def ensure_running_before_apply(self, *, service: ManagedService) -> list[str]:
        runtime_state = self._runtime_state(service)
        warnings: list[str] = []
        if runtime_state in STARTABLE_STATES:
            ok_start, start_result = self.docker_gateway.action(service.container_name, "start")
            if not ok_start:
                warnings.append(f"Start before apply failed: {start_result}")
        elif runtime_state == "not_found":
            warnings.append("Container not found; apply may fail on reload/restart.")
        return warnings

    def _disable_service(
        self, *, service: ManagedService, runtime_state: str
    ) -> ServiceLifecycleResult:
        if runtime_state == "running":
            ok_stop, stop_result = self.docker_gateway.action(service.container_name, "stop")
            if ok_stop:
                return ServiceLifecycleResult(
                    enabled=False,
                    status="stopped",
                    message="Service disabled and container stopped.",
                )
            return ServiceLifecycleResult(
                enabled=False,
                status="failed",
                message="Service disabled, but stopping container failed.",
                warnings=[stop_result],
            )
        if runtime_state == "not_found":
            return ServiceLifecycleResult(
                enabled=False,
                status="disabled",
                message="Service disabled; container not found.",
            )
        return ServiceLifecycleResult(
            enabled=False,
            status="disabled",
            message="Service disabled.",
        )

    def _enable_service(
        self, *, service: ManagedService, runtime_state: str
    ) -> ServiceLifecycleResult:
        if runtime_state in STARTABLE_STATES:
            ok_start, start_result = self.docker_gateway.action(service.container_name, "start")
            if ok_start:
                return ServiceLifecycleResult(
                    enabled=True,
                    status="started",
                    message="Service enabled and container started.",
                )
            return ServiceLifecycleResult(
                enabled=True,
                status="failed",
                message="Service enabled, but starting container failed.",
                warnings=[start_result],
            )
        if runtime_state == "running":
            return ServiceLifecycleResult(
                enabled=True,
                status="enabled",
                message="Service enabled; container already running.",
            )
        if runtime_state == "not_found":
            return ServiceLifecycleResult(
                enabled=True,
                status="enabled",
                message="Service enabled; container not found.",
            )
        return ServiceLifecycleResult(
            enabled=True,
            status="enabled",
            message="Service enabled.",
        )

    def _runtime_state(self, service: ManagedService) -> str:
        return str(
            self.docker_gateway.inspect(service.container_name).get("state", "unknown")
        ).lower()
