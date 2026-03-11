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
    csrf_token = login.cookies.get("hl_csrf")
    assert csrf_token
    return csrf_token


def test_list_services(client):
    _login(client)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["slug"] == "dnsmasq" for item in data)
    assert any(item["slug"] == "mailserver" for item in data)
    assert any(item["slug"] == "webmail" for item in data)


def test_service_enable_toggle(client):
    csrf_token = _login(client)
    headers = {"x-csrf-token": csrf_token}

    disable_response = client.post(
        "/api/v1/services/dnsmasq/enabled",
        json={"enabled": False},
        headers=headers,
    )
    assert disable_response.status_code == 200
    disable_payload = disable_response.json()
    assert disable_payload["slug"] == "dnsmasq"
    assert disable_payload["enabled"] is False
    assert disable_payload["status"] in {"disabled", "stopped", "failed"}

    detail_disabled = client.get("/api/v1/services/dnsmasq")
    assert detail_disabled.status_code == 200
    assert detail_disabled.json()["service"]["enabled"] is False

    enable_response = client.post(
        "/api/v1/services/dnsmasq/enabled",
        json={"enabled": True},
        headers=headers,
    )
    assert enable_response.status_code == 200
    enable_payload = enable_response.json()
    assert enable_payload["slug"] == "dnsmasq"
    assert enable_payload["enabled"] is True
    assert enable_payload["status"] in {"enabled", "started", "failed"}

    detail_enabled = client.get("/api/v1/services/dnsmasq")
    assert detail_enabled.status_code == 200
    assert detail_enabled.json()["service"]["enabled"] is True
