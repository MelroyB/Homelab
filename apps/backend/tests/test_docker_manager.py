from __future__ import annotations

from app.core.config import Settings
from app.services.docker_manager import DockerManagerService


def _login(client):
    client.post(
        "/api/v1/bootstrap/admin",
        json={"email": "admin@example.com", "password": "super-secure-password"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "super-secure-password"},
    )
    assert login.status_code == 200


def test_docker_manager_endpoints(client):
    _login(client)

    host = client.get("/api/v1/docker/host")
    assert host.status_code == 200
    assert "docker_available" in host.json()

    containers = client.get("/api/v1/docker/containers?scope=project")
    assert containers.status_code == 200
    assert containers.json()["scope"] == "project"
    if containers.json()["items"]:
        first = containers.json()["items"][0]
        assert "cpu_percent" in first
        assert "memory_percent" in first
        assert "restart_count" in first

    images = client.get("/api/v1/docker/images?scope=project")
    assert images.status_code == 200
    assert images.json()["scope"] == "project"

    updates = client.get("/api/v1/docker/images/updates?scope=project")
    assert updates.status_code == 200
    assert updates.json()["scope"] == "project"


class _DummyGateway:
    def client_or_none(self):
        return None


def test_project_container_detection_falls_back_to_name_prefix():
    manager = DockerManagerService(
        _DummyGateway(),
        Settings(
            secret_key="test-secret-key-change-me-123456",
            compose_project_name="homelab",
            docker_host="tcp://127.0.0.1:65535",
        ),
    )

    assert manager._is_project_container(project_label="homelab", container_name="random-name")
    assert manager._is_project_container(project_label=None, container_name="homelab-backend-1")
    assert manager._is_project_container(project_label=None, container_name="homelab_backend_1")
    assert not manager._is_project_container(project_label="other", container_name="container-1")


def test_ordered_unique_preserves_order_and_removes_duplicates():
    values = ["", "nginx:latest", "redis:7", "nginx:latest", " redis:7 ", "caddy:2"]
    assert DockerManagerService._ordered_unique(values) == [
        "nginx:latest",
        "redis:7",
        "caddy:2",
    ]
