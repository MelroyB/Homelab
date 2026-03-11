from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.api.deps import settings_singleton
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
    assert "webmail_url" in data
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
        webmail = db.scalar(select(ManagedService).where(ManagedService.slug == "webmail"))
        assert mailserver is not None
        assert webmail is not None
        test_path = Path.cwd() / ".tmp" / "tests" / "mailserver.env"
        webmail_path = Path.cwd() / ".tmp" / "tests" / "webmail.env"
        mailserver.config_path = str(test_path)
        webmail.config_path = str(webmail_path)
        db.add(mailserver)
        db.add(webmail)
        db.commit()

    payload = {
        "domain": "example.com",
        "hostname": "mail",
        "webmail_url": "https://webmail.example.com",
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

    suggestions_response = client.post(
        "/api/v1/settings/mail/dns/suggestions",
        json=payload,
        headers=headers,
    )
    assert suggestions_response.status_code == 200
    suggestions_payload = suggestions_response.json()
    assert suggestions_payload["valid"] is True
    assert isinstance(suggestions_payload.get("records"), list)
    assert any(item.get("name") == "_dmarc" for item in suggestions_payload["records"])

    previous_data_dir = settings_singleton.data_dir
    data_dir = Path.cwd() / ".tmp" / "tests" / "mail"
    settings_singleton.data_dir = data_dir
    try:
        apply_response = client.post(
            "/api/v1/settings/mail/apply",
            json=payload,
            headers=headers,
        )
    finally:
        settings_singleton.data_dir = previous_data_dir

    assert apply_response.status_code == 200
    apply_data = apply_response.json()
    assert apply_data["success"] is True
    assert isinstance(apply_data.get("results"), list)
    assert len(apply_data["results"]) == 2
    assert isinstance(apply_data.get("suggested_dns_records"), list)
    assert any(
        item.get("name") == "_dmarc" for item in apply_data.get("suggested_dns_records", [])
    )

    accounts_file = data_dir / "config" / "mailserver" / "accounts.cf"
    aliases_file = data_dir / "config" / "mailserver" / "aliases.cf"
    manifest_file = data_dir / "config" / "mailserver" / "mailboxes.json"
    dms_accounts_file = data_dir / "config" / "mailserver" / "postfix-accounts.cf"
    dms_virtual_file = data_dir / "config" / "mailserver" / "postfix-virtual.cf"
    webmail_env_file = Path.cwd() / ".tmp" / "tests" / "webmail.env"
    assert accounts_file.exists()
    assert aliases_file.exists()
    assert manifest_file.exists()
    assert dms_accounts_file.exists()
    assert dms_virtual_file.exists()
    assert webmail_env_file.exists()
    assert "admin@example.com|super-secret-mail-password" in accounts_file.read_text(
        encoding="utf-8"
    )
    assert "{SHA512-CRYPT}" in dms_accounts_file.read_text(encoding="utf-8")
    assert 'ROUNDCUBEMAIL_DEFAULT_HOST="mailserver"' in webmail_env_file.read_text(
        encoding="utf-8"
    )

    profile_response = client.get("/api/v1/settings/mail/profile")
    assert profile_response.status_code == 200
    profile = profile_response.json()
    assert len(profile.get("mailboxes", [])) == 1
    mailbox = profile["mailboxes"][0]
    assert mailbox["email"] == "admin@example.com"
    assert mailbox["has_password"] is True
    assert mailbox["password"] is None

    webmail_response = client.get(
        "/api/v1/settings/mail/webmail/url?mailbox=admin@example.com"
    )
    assert webmail_response.status_code == 200
    webmail_payload = webmail_response.json()
    assert webmail_payload["mailbox"] == "admin@example.com"
    assert isinstance(webmail_payload.get("url"), str)


def test_mail_dns_suggestions_report_validation_errors(client):
    csrf_token = _login(client)
    headers = {"x-csrf-token": csrf_token}
    response = client.post(
        "/api/v1/settings/mail/dns/suggestions",
        json={
            "domain": "invalid_domain",
            "hostname": "mail host",
            "webmail_url": "not-a-url",
            "postmaster_address": "postmasterexample.com",
            "enable_mailserver": True,
            "enable_webmail": True,
            "enable_imap": True,
            "enable_pop3": False,
            "enable_submission": True,
            "enable_submissions": True,
            "enable_smtps": False,
            "dkim_selector": "mail",
            "dkim_key_size": 2048,
            "dkim_public_key": "abc",
            "spf_policy": "mx -all",
            "dmarc_policy": "p=quarantine",
            "mailboxes": [],
        },
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert payload["records"] == []
    assert any(
        issue.get("field") == "domain" and issue.get("level") == "error"
        for issue in payload.get("issues", [])
    )
