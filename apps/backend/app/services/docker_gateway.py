from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import docker
from docker.errors import DockerException, NotFound

from app.core.config import Settings


class DockerGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: docker.DockerClient | None = None

    def _client_or_none(self) -> docker.DockerClient | None:
        if self._client is not None:
            return self._client
        try:
            self._client = docker.DockerClient(base_url=self.settings.docker_host, timeout=5)
            return self._client
        except DockerException:
            return None

    def client_or_none(self) -> docker.DockerClient | None:
        return self._client_or_none()

    def ping(self) -> bool:
        client = self._client_or_none()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except DockerException:
            return False

    def inspect(self, container_name: str) -> dict[str, Any]:
        client = self._client_or_none()
        if client is None:
            return {"state": "unknown", "health": "unknown", "ports": [], "uptime_seconds": None}

        try:
            container = client.containers.get(container_name)
            attrs = container.attrs
            state = attrs.get("State", {})
            network_settings = attrs.get("NetworkSettings", {})
            ports_map = network_settings.get("Ports", {})
            ports: list[str] = []
            for internal, bindings in ports_map.items():
                if not bindings:
                    ports.append(internal)
                    continue
                for binding in bindings:
                    host_ip = binding.get("HostIp", "")
                    host_port = binding.get("HostPort", "")
                    ports.append(f"{host_ip}:{host_port}->{internal}")
            uptime_seconds = self._uptime_seconds(state.get("StartedAt"))
            return {
                "state": state.get("Status", "unknown"),
                "health": (state.get("Health") or {}).get("Status", "unknown"),
                "ports": ports,
                "uptime_seconds": uptime_seconds,
            }
        except NotFound:
            return {"state": "not_found", "health": "unknown", "ports": [], "uptime_seconds": None}
        except DockerException:
            return {"state": "unknown", "health": "unknown", "ports": [], "uptime_seconds": None}

    def action(self, container_name: str, action: str) -> tuple[bool, str]:
        client = self._client_or_none()
        if client is None:
            return False, "Docker API unavailable"
        try:
            container = client.containers.get(container_name)
            if action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=20)
            elif action == "restart":
                container.restart(timeout=20)
            elif action == "reload":
                container.kill(signal="SIGHUP")
            else:
                return False, f"Unsupported action: {action}"
            return True, "Action executed"
        except NotFound:
            return False, "Container not found"
        except DockerException as exc:
            return False, f"Docker action failed: {exc}"

    def logs(self, container_name: str, *, tail: int = 200) -> str:
        client = self._client_or_none()
        if client is None:
            return "Docker API unavailable"
        try:
            container = client.containers.get(container_name)
            output = container.logs(tail=tail, timestamps=True)
            return output.decode("utf-8", errors="replace")
        except NotFound:
            return "Container not found"
        except DockerException as exc:
            return f"Failed to read logs: {exc}"

    @staticmethod
    def _uptime_seconds(started_at: str | None) -> int | None:
        if not started_at:
            return None
        try:
            normalized = started_at.replace("Z", "+00:00")
            start = datetime.fromisoformat(normalized)
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            return int((datetime.now(timezone.utc) - start).total_seconds())
        except ValueError:
            return None
