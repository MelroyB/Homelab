from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.service import ManagedService


class ConfigRenderer(Protocol):
    def render(self, service: ManagedService, config_json: dict, raw_config: str) -> str: ...


class ConfigValidator(Protocol):
    def validate(self, service: ManagedService, rendered_config: str) -> tuple[bool, list[str]]: ...


class ServiceController(Protocol):
    def execute(self, service: ManagedService, action: str) -> tuple[bool, str]: ...


class HealthChecker(Protocol):
    def status(self, service: ManagedService) -> tuple[str, str]: ...


@dataclass
class ServiceAdapter:
    renderer: ConfigRenderer
    validator: ConfigValidator
    controller: ServiceController
    health_checker: HealthChecker
