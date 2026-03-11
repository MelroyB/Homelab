from __future__ import annotations

from app.api.deps import settings_singleton


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


def test_network_profile_has_dhcp_and_ntp_fields(client):
    _login(client)
    response = client.get("/api/v1/settings/network/profile")
    assert response.status_code == 200
    data = response.json()
    assert "dhcp_authoritative" in data
    assert "dhcp_reservations" in data
    assert "dhcp_dns_servers" in data
    assert "dhcp_ntp_servers" in data
    assert "ntp_servers" in data


def test_network_dhcp_leases_reads_dnsmasq_leasefile(client, tmp_path):
    _login(client)

    lease_dir = tmp_path / "state" / "dnsmasq"
    lease_dir.mkdir(parents=True, exist_ok=True)
    lease_file = lease_dir / "dnsmasq.leases"
    lease_file.write_text(
        "1893456000 aa:bb:cc:dd:ee:ff 192.168.50.120 printer *\n",
        encoding="utf-8",
    )

    previous_data_dir = settings_singleton.data_dir
    settings_singleton.data_dir = tmp_path
    try:
        response = client.get("/api/v1/settings/network/dhcp/leases")
    finally:
        settings_singleton.data_dir = previous_data_dir

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload.get("items"), list)
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["mac"] == "aa:bb:cc:dd:ee:ff"
    assert item["ip"] == "192.168.50.120"
    assert item["hostname"] == "printer"
