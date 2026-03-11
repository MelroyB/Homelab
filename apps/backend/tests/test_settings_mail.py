from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.service import ManagedService


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


def test_mail_profile_has_expected_fields(client):
    _login(client)
    response = client.get("/api/v1/settings/mail/profile")
    assert response.status_code == 200
    data = response.json()
    assert "domain" in data
    assert "enable_mailserver" in data
    assert "enable_webmail" in data
    assert "dkim_selector" in data
    assert "spf_policy" in data
    assert "dmarc_policy" in data
    assert isinstance(data.get("mailboxes"), list)


def test_mail_profile_apply_with_mailbox(client):
    csrf_token = _login(client)
    headers = {"x-csrf-token": csrf_token}
    with SessionLocal() as db:
        mailserver = db.scalar(
            select(ManagedService).where(ManagedService.slug == "mailserver")
        )
        assert mailserver is not None
        test_path = Path.cwd() / ".tmp" / "tests" / "mailserver.env"
        mailserver.config_path = str(test_path)
        db.add(mailserver)
        db.commit()

    payload = {
        "domain": "example.com",
        "hostname": "mail",
        "postmaster_address": "postmaster@example.com",
        "enable_mailserver": True,
        "enable_webmail": True,
        "enable_imap": True,
        "enable_pop3": False,
        "enable_submission": True,
        "enable_submissions": True,
        "enable_smtps": False,
        "dkim_selector": "mail",
        "dkim_key_size": 2048,
        "dkim_public_key": None,
        "spf_policy": "v=spf1 mx -all",
        "dmarc_policy": "v=DMARC1; p=quarantine; rua=mailto:postmaster@example.com",
        "mailboxes": [
            {
                "email": "admin@example.com",
                "password": "super-secret-mail-password",
                "display_name": "Admin Mailbox",
                "quota_mb": 2048,
                "enabled": True,
                "aliases": ["info@example.com"],
            }
        ],
    }

    apply_response = client.post(
        "/api/v1/settings/mail/apply",
        json=payload,
        headers=headers,
    )
    assert apply_response.status_code == 200
    apply_data = apply_response.json()
    assert apply_data["success"] is True
    assert isinstance(apply_data.get("results"), list)
    assert len(apply_data["results"]) == 2
    assert isinstance(apply_data.get("suggested_dns_records"), list)
    assert any(
        item.get("name") == "_dmarc" for item in apply_data.get("suggested_dns_records", [])
    )

    profile_response = client.get("/api/v1/settings/mail/profile")
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert len(profile.get("mailboxes", [])) == 1
    mailbox = profile["mailboxes"][0]
    assert mailbox["email"] == "admin@example.com"
    assert mailbox["has_password"] is True
    assert mailbox["password"] is None
