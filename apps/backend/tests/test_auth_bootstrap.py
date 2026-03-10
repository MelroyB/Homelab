from __future__ import annotations


def test_bootstrap_and_login_flow(client):
    status = client.get("/api/v1/bootstrap/status")
    assert status.status_code == 200
    assert status.json()["bootstrap_required"] is True

    create = client.post(
        "/api/v1/bootstrap/admin",
        json={"email": "admin@example.com", "password": "super-secure-password"},
    )
    assert create.status_code == 201
    assert create.json()["email"] == "admin@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "super-secure-password"},
    )
    assert login.status_code == 200
    assert "hl_access" in login.cookies
    assert "hl_refresh" in login.cookies
    assert "hl_csrf" in login.cookies

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "admin@example.com"
