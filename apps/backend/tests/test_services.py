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


def test_list_services(client):
    _login(client)
    response = client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["slug"] == "dnsmasq" for item in data)
