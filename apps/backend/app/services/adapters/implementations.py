from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.models.service import ManagedService
from app.services.adapters.base import (
    ConfigRenderer,
    ConfigValidator,
    HealthChecker,
    ServiceAdapter,
    ServiceController,
)
from app.services.docker_gateway import DockerGateway


def template_env() -> Environment:
    template_dir = Path(__file__).resolve().parents[2] / "templates"
    return Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)


class TemplateRenderer(ConfigRenderer):
    def __init__(self) -> None:
        self.env = template_env()

    def render(self, service: ManagedService, config_json: dict, raw_config: str) -> str:
        if raw_config.strip():
            return raw_config

        template_name = f"{service.slug}.j2"
        try:
            template = self.env.get_template(template_name)
            return template.render(config=config_json).strip() + "\n"
        except TemplateNotFound:
            if not config_json:
                return ""
            return json.dumps(config_json, indent=2, sort_keys=True) + "\n"


class DefaultValidator(ConfigValidator):
    def validate(self, service: ManagedService, rendered_config: str) -> tuple[bool, list[str]]:
        if not service.config_path:
            return True, []
        if not rendered_config.strip():
            return False, ["Rendered config is empty"]
        return True, []


class DnsmasqValidator(ConfigValidator):
    def validate(self, service: ManagedService, rendered_config: str) -> tuple[bool, list[str]]:
        # TODO(phase-2): call native `dnsmasq --test` inside the target container before apply.
        errors: list[str] = []
        if "dhcp-range" not in rendered_config:
            errors.append("dnsmasq config should include at least one dhcp-range")
        if "domain=" not in rendered_config:
            errors.append("dnsmasq config should set domain=")
        return (len(errors) == 0, errors)


class Bind9Validator(ConfigValidator):
    def validate(self, service: ManagedService, rendered_config: str) -> tuple[bool, list[str]]:
        # TODO(phase-2): run `named-checkzone` with rendered zone file for strict validation.
        errors: list[str] = []
        if "SOA" not in rendered_config:
            errors.append("BIND zone must include SOA record")
        if " NS " not in f" {rendered_config} ":
            errors.append("BIND zone must include NS record")
        return (len(errors) == 0, errors)


class NtpValidator(ConfigValidator):
    def validate(self, service: ManagedService, rendered_config: str) -> tuple[bool, list[str]]:
        errors: list[str] = []
        server_lines = [
            line.strip()
            for line in rendered_config.splitlines()
            if line.strip().startswith("server ")
        ]
        if not server_lines:
            errors.append("NTP config should include at least one server line")

        for line in server_lines:
            parts = line.split()
            if len(parts) < 2 or not parts[1].strip():
                errors.append("Invalid NTP server line detected")
                break

        for line in rendered_config.splitlines():
            stripped = line.strip()
            if not stripped.startswith("fudge 127.127.1.0 stratum "):
                continue
            try:
                stratum = int(stripped.rsplit(" ", 1)[-1])
            except ValueError:
                errors.append("local_stratum must be an integer between 1 and 15")
                continue
            if stratum < 1 or stratum > 15:
                errors.append("local_stratum must be between 1 and 15")

        return (len(errors) == 0, errors)


class DockerServiceController(ServiceController):
    def __init__(self, docker_gateway: DockerGateway) -> None:
        self.docker_gateway = docker_gateway

    def execute(self, service: ManagedService, action: str) -> tuple[bool, str]:
        return self.docker_gateway.action(service.container_name, action)


class DockerHealthChecker(HealthChecker):
    def __init__(self, docker_gateway: DockerGateway) -> None:
        self.docker_gateway = docker_gateway

    def status(self, service: ManagedService) -> tuple[str, str]:
        info = self.docker_gateway.inspect(service.container_name)
        state = info.get("state", "unknown")
        health = info.get("health", "unknown")
        if state == "running" and health in {"healthy", "unknown"}:
            return "healthy", f"state={state}, health={health}"
        if state == "not_found":
            return "critical", "container not found"
        return "degraded", f"state={state}, health={health}"


def build_adapter(service: ManagedService, docker_gateway: DockerGateway) -> ServiceAdapter:
    validator: ConfigValidator = DefaultValidator()
    if service.slug == "dnsmasq":
        validator = DnsmasqValidator()
    elif service.slug == "bind9":
        validator = Bind9Validator()
    elif service.slug == "ntp":
        validator = NtpValidator()

    return ServiceAdapter(
        renderer=TemplateRenderer(),
        validator=validator,
        controller=DockerServiceController(docker_gateway),
        health_checker=DockerHealthChecker(docker_gateway),
    )
