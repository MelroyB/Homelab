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
            project_label = labels.get("com.docker.compose.project")
            managed_by_project = project_label == self.project_name
            if scope == "project" and not managed_by_project:
                continue

            state_info = attrs.get("State", {})
            created_at = self._parse_datetime(attrs.get("Created"))
            ports = self._parse_ports((attrs.get("NetworkSettings") or {}).get("Ports") or {})

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
                    project_name=project_label,
                    managed_by_project=managed_by_project,
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

        images = self.list_images(scope=scope)
        refs: list[str] = []
        for image in images:
            if image.repo_tags:
                refs.append(image.repo_tags[0])

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
