from __future__ import annotations


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

    images = client.get("/api/v1/docker/images?scope=project")
    assert images.status_code == 200
    assert images.json()["scope"] == "project"

    updates = client.get("/api/v1/docker/images/updates?scope=project")
    assert updates.status_code == 200
    assert updates.json()["scope"] == "project"
