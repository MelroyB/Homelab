from __future__ import annotations

from datetime import datetime
from typing import Any

from docker.errors import APIError, DockerException, ImageNotFound, NotFound

from app.core.config import Settings
from app.schemas.docker_manager import (
    DockerContainerItem,
    DockerHostInfoResponse,
    DockerImageItem,
    DockerImageUpdateStatus,
)
from app.services.docker_gateway import DockerGateway


class DockerManagerService:
    def __init__(self, gateway: DockerGateway, settings: Settings) -> None:
        self.gateway = gateway
        self.settings = settings

    @property
    def project_name(self) -> str:
        return self.settings.compose_project_name

    def host_info(self) -> DockerHostInfoResponse:
        client = self.gateway.client_or_none()
        if client is None:
            return DockerHostInfoResponse(docker_available=False)

        try:
            info = client.info()
            return DockerHostInfoResponse(
                docker_available=True,
                name=str(info.get("Name", "")),
                server_version=str(info.get("ServerVersion", "")),
                operating_system=str(info.get("OperatingSystem", "")),
                kernel_version=str(info.get("KernelVersion", "")),
                cpu_count=info.get("NCPU"),
                memory_total_bytes=info.get("MemTotal"),
                containers_running=info.get("ContainersRunning"),
                containers_total=info.get("Containers"),
            )
        except DockerException:
            return DockerHostInfoResponse(docker_available=False)

    def list_containers(self, *, scope: str) -> list[DockerContainerItem]:
        client = self.gateway.client_or_none()
        if client is None:
            return []

        try:
            containers = client.containers.list(all=True)
        except DockerException:
            return []

        result: list[DockerContainerItem] = []
        for container in containers:
            attrs = container.attrs or {}
            config = attrs.get("Config", {})
            labels = config.get("Labels") or {}
            project_label = str(labels.get("com.docker.compose.project") or "").strip() or None
            managed_by_project = self._is_project_container(
                project_label=project_label,
                container_name=container.name,
            )
            if scope == "project" and not managed_by_project:
                continue

            state_info = attrs.get("State", {})
            created_at = self._parse_datetime(attrs.get("Created"))
            ports = self._parse_ports((attrs.get("NetworkSettings") or {}).get("Ports") or {})
            perf = self._container_perf(container, state_info=state_info)

            result.append(
                DockerContainerItem(
                    id=container.id,
                    name=container.name,
                    image=str((attrs.get("Config") or {}).get("Image") or ""),
                    status=str(state_info.get("Status", "unknown")),
                    state=str(state_info.get("Status", "unknown")),
                    health=str((state_info.get("Health") or {}).get("Status", "unknown")),
                    created_at=created_at,
                    ports=ports,
                    labels={str(k): str(v) for k, v in labels.items()},
                    project_name=project_label
                    or (self.project_name if managed_by_project else None),
                    managed_by_project=managed_by_project,
                    cpu_percent=perf["cpu_percent"],
                    memory_usage_bytes=perf["memory_usage_bytes"],
                    memory_limit_bytes=perf["memory_limit_bytes"],
                    memory_percent=perf["memory_percent"],
                    restart_count=perf["restart_count"],
                )
            )

        result.sort(key=lambda item: (not item.managed_by_project, item.name))
        return result

    def container_action(self, container_id: str, action: str) -> tuple[bool, str]:
        client = self.gateway.client_or_none()
        if client is None:
            return False, "Docker API unavailable"

        try:
            container = client.containers.get(container_id)
            if action == "start":
                container.start()
            elif action == "stop":
                container.stop(timeout=20)
            elif action == "restart":
                container.restart(timeout=20)
            else:
                return False, f"Unsupported action: {action}"
            return True, "Action executed"
        except NotFound:
            return False, "Container not found"
        except DockerException as exc:
            return False, f"Docker action failed: {exc}"

    def list_images(self, *, scope: str) -> list[DockerImageItem]:
        client = self.gateway.client_or_none()
        if client is None:
            return []

        containers = self.list_containers(scope=scope)
        in_use_counts: dict[str, int] = {}
        for container in containers:
            image_ref = container.image
            in_use_counts[image_ref] = in_use_counts.get(image_ref, 0) + 1

        try:
            images = client.images.list()
        except DockerException:
            return []

        items: list[DockerImageItem] = []
        for image in images:
            tags = [tag for tag in (image.tags or []) if tag and not tag.startswith("<none>")]
            if scope == "project":
                if not tags:
                    continue
                if not any(in_use_counts.get(tag, 0) > 0 for tag in tags):
                    continue

            attrs = image.attrs or {}
            created_at = self._parse_datetime(str(attrs.get("Created", "")))
            size_bytes = int(attrs.get("Size", 0) or 0)
            containers_using = sum(in_use_counts.get(tag, 0) for tag in tags)

            items.append(
                DockerImageItem(
                    id=image.id,
                    repo_tags=tags,
                    created_at=created_at,
                    size_bytes=size_bytes,
                    containers_using=containers_using,
                )
            )

        items.sort(
            key=lambda item: (
                item.containers_using == 0,
                item.repo_tags[0] if item.repo_tags else "",
            )
        )
        return items

    def check_updates(self, *, scope: str) -> list[DockerImageUpdateStatus]:
        client = self.gateway.client_or_none()
        if client is None:
            return []

        containers = self.list_containers(scope=scope)
        images = self.list_images(scope=scope)
        refs: list[str] = [container.image for container in containers if container.image]
        for image in images:
            if image.repo_tags:
                refs.append(image.repo_tags[0])
        refs = self._ordered_unique(refs)

        results: list[DockerImageUpdateStatus] = []
        for ref in refs:
            try:
                image = client.images.get(ref)
            except ImageNotFound:
                results.append(
                    DockerImageUpdateStatus(
                        image_ref=ref,
                        status="error",
                        detail="Image not found locally",
                    )
                )
                continue
            except DockerException as exc:
                results.append(
                    DockerImageUpdateStatus(
                        image_ref=ref,
                        status="error",
                        detail=f"Failed to inspect local image: {exc}",
                    )
                )
                continue

            local_digests = self._extract_local_digests(image.attrs)
            try:
                registry_data = client.images.get_registry_data(ref)
                descriptor = registry_data.attrs.get("Descriptor") or {}
                remote_digest = descriptor.get("digest")
            except APIError as exc:
                results.append(
                    DockerImageUpdateStatus(
                        image_ref=ref,
                        status="unknown",
                        local_digests=local_digests,
                        detail=f"Registry lookup unavailable: {exc.explanation}",
                    )
                )
                continue
            except DockerException as exc:
                results.append(
                    DockerImageUpdateStatus(
                        image_ref=ref,
                        status="unknown",
                        local_digests=local_digests,
                        detail=f"Registry lookup failed: {exc}",
                    )
                )
                continue

            if not remote_digest:
                results.append(
                    DockerImageUpdateStatus(
                        image_ref=ref,
                        status="unknown",
                        local_digests=local_digests,
                        detail="No remote digest returned",
                    )
                )
                continue

            if remote_digest in local_digests:
                status = "up_to_date"
                detail = "Local image digest matches remote"
            elif local_digests:
                status = "update_available"
                detail = "Remote digest differs from local image"
            else:
                status = "unknown"
                detail = "Local digest unavailable; cannot compare"

            results.append(
                DockerImageUpdateStatus(
                    image_ref=ref,
                    status=status,
                    local_digests=local_digests,
                    remote_digest=remote_digest,
                    detail=detail,
                )
            )

        return results

    def pull_image(self, *, image_ref: str) -> tuple[bool, str]:
        client = self.gateway.client_or_none()
        if client is None:
            return False, "Docker API unavailable"

        try:
            client.images.pull(image_ref)
            return True, "Image pulled"
        except DockerException as exc:
            return False, f"Failed to pull image: {exc}"

    @staticmethod
    def _extract_local_digests(attrs: dict[str, Any]) -> list[str]:
        digests = []
        for item in attrs.get("RepoDigests") or []:
            if "@" not in item:
                continue
            digests.append(item.split("@", 1)[1])
        return digests

    @staticmethod
    def _parse_datetime(raw: str | None) -> datetime | None:
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _parse_ports(ports_map: dict[str, Any]) -> list[str]:
        ports: list[str] = []
        for internal, bindings in ports_map.items():
            if not bindings:
                ports.append(internal)
                continue
            for binding in bindings:
                host_ip = binding.get("HostIp", "")
                host_port = binding.get("HostPort", "")
                ports.append(f"{host_ip}:{host_port}->{internal}")
        return ports

    def _container_perf(self, container: Any, *, state_info: dict[str, Any]) -> dict[str, Any]:
        restart_count = state_info.get("RestartCount")
        status = str(state_info.get("Status") or "").lower()
        if status != "running":
            return {
                "cpu_percent": None,
                "memory_usage_bytes": None,
                "memory_limit_bytes": None,
                "memory_percent": None,
                "restart_count": int(restart_count) if isinstance(restart_count, int) else None,
            }

        try:
            stats = container.stats(stream=False) or {}
        except DockerException:
            return {
                "cpu_percent": None,
                "memory_usage_bytes": None,
                "memory_limit_bytes": None,
                "memory_percent": None,
                "restart_count": int(restart_count) if isinstance(restart_count, int) else None,
            }

        cpu_percent = self._cpu_percent_from_stats(stats)
        memory_stats = stats.get("memory_stats") or {}
        memory_usage = memory_stats.get("usage")
        memory_limit = memory_stats.get("limit")
        memory_percent = None
        if isinstance(memory_usage, (int, float)) and isinstance(memory_limit, (int, float)):
            if memory_limit > 0:
                memory_percent = (float(memory_usage) / float(memory_limit)) * 100.0

        return {
            "cpu_percent": cpu_percent,
            "memory_usage_bytes": int(memory_usage)
            if isinstance(memory_usage, (int, float))
            else None,
            "memory_limit_bytes": int(memory_limit)
            if isinstance(memory_limit, (int, float))
            else None,
            "memory_percent": memory_percent,
            "restart_count": int(restart_count) if isinstance(restart_count, int) else None,
        }

    @staticmethod
    def _cpu_percent_from_stats(stats: dict[str, Any]) -> float | None:
        cpu_stats = stats.get("cpu_stats") or {}
        precpu_stats = stats.get("precpu_stats") or {}
        cpu_usage = cpu_stats.get("cpu_usage") or {}
        precpu_usage = precpu_stats.get("cpu_usage") or {}

        total = cpu_usage.get("total_usage")
        pre_total = precpu_usage.get("total_usage")
        system = cpu_stats.get("system_cpu_usage")
        pre_system = precpu_stats.get("system_cpu_usage")
        if not isinstance(total, (int, float)) or not isinstance(pre_total, (int, float)):
            return None
        if not isinstance(system, (int, float)) or not isinstance(pre_system, (int, float)):
            return None

        cpu_delta = float(total) - float(pre_total)
        system_delta = float(system) - float(pre_system)
        if cpu_delta <= 0 or system_delta <= 0:
            return 0.0

        online_cpus = cpu_stats.get("online_cpus")
        if not isinstance(online_cpus, int) or online_cpus <= 0:
            percpu_usage = cpu_usage.get("percpu_usage")
            if isinstance(percpu_usage, list) and percpu_usage:
                online_cpus = len(percpu_usage)
            else:
                online_cpus = 1

        return (cpu_delta / system_delta) * float(online_cpus) * 100.0

    def _is_project_container(self, *, project_label: str | None, container_name: str) -> bool:
        if project_label == self.project_name:
            return True
        name = container_name.strip()
        return name.startswith(f"{self.project_name}-") or name.startswith(f"{self.project_name}_")

    @staticmethod
    def _ordered_unique(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = value.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result
