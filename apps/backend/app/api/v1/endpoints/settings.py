from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_client_ip,
    get_current_user,
    get_docker_gateway,
    get_settings_dep,
    require_admin,
)
from app.core.config import Settings
from app.db.session import get_db
from app.models.service import ManagedService, ServiceConfigVersion
from app.models.user import User
from app.schemas.service import ConfigApplyRequest
from app.schemas.settings import (
    DhcpLeaseEntry,
    DhcpLeasesResponse,
    DhcpReservation,
    DnsRecord,
    MailboxEntry,
    MailStackApplyResponse,
    MailStackProfile,
    NetworkServiceApplyResult,
    NetworkStackApplyResponse,
    NetworkStackProfile,
)
from app.services.audit.service import AuditService
from app.services.config.manager import ConfigManager
from app.services.docker_gateway import DockerGateway
from app.services.service_lifecycle import ServiceLifecycleManager

router = APIRouter()
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


@router.get("/profile")
def profile(
    current_user: User = Depends(get_current_user),
    _db: Session = Depends(get_db),
) -> dict[str, str]:
    # TODO(phase-5): replace this placeholder with persisted user settings + RBAC policy controls.
    return {
        "email": current_user.email,
        "role": current_user.role,
        "message": "RBAC and user self-service settings land in Phase 5.",
    }


def _service_or_404(db: Session, slug: str) -> ManagedService:
    service = db.scalar(select(ManagedService).where(ManagedService.slug == slug))
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {slug} not found",
        )
    return service


def _active_config_json(db: Session, slug: str) -> dict:
    active = db.scalar(
        select(ServiceConfigVersion).where(
            ServiceConfigVersion.service_slug == slug,
            ServiceConfigVersion.is_active.is_(True),
        )
    )
    if active and isinstance(active.config_json, dict):
        return active.config_json
    return {}


def _service_enabled_map(db: Session, slugs: list[str]) -> dict[str, bool]:
    rows = db.execute(
        select(ManagedService.slug, ManagedService.enabled).where(ManagedService.slug.in_(slugs))
    ).all()
    return {str(slug): bool(enabled) for slug, enabled in rows}


def _default_zone_serial() -> int:
    return int(datetime.now(timezone.utc).strftime("%Y%m%d01"))


def _string_list(value: object, fallback: list[str]) -> list[str]:
    if not isinstance(value, list):
        return fallback
    parsed = [str(item).strip() for item in value if str(item).strip()]
    return parsed if parsed else fallback


def _normalize_domain(value: str) -> str:
    return value.strip().strip(".").lower()


def _domain_list(value: object, fallback: list[str]) -> list[str]:
    source = value if isinstance(value, list) else fallback
    seen: set[str] = set()
    domains: list[str] = []
    for item in source:
        normalized = _normalize_domain(str(item))
        if not normalized or not DOMAIN_PATTERN.fullmatch(normalized) or normalized in seen:
            continue
        seen.add(normalized)
        domains.append(normalized)
    return domains


def _authoritative_domain_list(value: object, primary_domain: str) -> list[str]:
    normalized_primary = _normalize_domain(primary_domain)
    fallback = [normalized_primary] if normalized_primary else ["homelab.local"]
    domains = _domain_list(value, fallback=fallback)
    if normalized_primary and normalized_primary not in domains:
        domains.insert(0, normalized_primary)
    return domains if domains else fallback


def _bind9_zone_file_container_path(service: ManagedService, settings: Settings) -> str:
    config_path = Path(service.config_path)
    data_dir = Path(settings.data_dir)
    try:
        relative = config_path.relative_to(data_dir)
    except ValueError:
        return "/homelab-data/config/bind9/zones/db.homelab.local"
    return f"/homelab-data/{relative.as_posix()}"


def _write_bind9_named_conf(
    settings: Settings,
    *,
    authoritative_domains: list[str],
    zone_file_container_path: str,
) -> None:
    config_dir = Path(settings.data_dir) / "config" / "bind9"
    config_dir.mkdir(parents=True, exist_ok=True)
    named_conf_path = config_dir / "named.conf"

    zone_blocks = "\n\n".join(
        [
            (
                f'zone "{domain}" IN {{\n'
                "    type master;\n"
                f'    file "{zone_file_container_path}";\n'
                "};"
            )
            for domain in authoritative_domains
        ]
    )

    named_conf = (
        "options {\n"
        '    directory "/homelab-data/state/bind9/cache";\n'
        "    recursion no;\n"
        "    allow-query { any; };\n"
        "    dnssec-validation auto;\n"
        "    listen-on { any; };\n"
        "    listen-on-v6 { any; };\n"
        "};\n\n"
        f"{zone_blocks}\n"
    )
    named_conf_path.write_text(named_conf, encoding="utf-8")


def _reservation_list(value: object) -> list[DhcpReservation]:
    if not isinstance(value, list):
        return []
    reservations: list[DhcpReservation] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        mac = str(item.get("mac", "")).strip()
        ip = str(item.get("ip", "")).strip()
        if not mac or not ip:
            continue
        hostname_raw = str(item.get("hostname", "")).strip()
        lease_raw = str(item.get("lease", "")).strip()
        reservations.append(
            DhcpReservation(
                mac=mac,
                ip=ip,
                hostname=hostname_raw or None,
                lease=lease_raw or None,
            )
        )
    return reservations


def _mailbox_aliases(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    aliases: list[str] = []
    seen: set[str] = set()
    for item in value:
        alias = str(item).strip().lower()
        if not alias or alias in seen:
            continue
        seen.add(alias)
        aliases.append(alias)
    return aliases


def _mailbox_list(value: object) -> list[MailboxEntry]:
    if not isinstance(value, list):
        return []

    mailboxes: list[MailboxEntry] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        email = str(item.get("email", "")).strip().lower()
        if not email:
            continue
        password_raw = str(item.get("password", "")).strip()
        display_name_raw = str(item.get("display_name", "")).strip()
        quota_raw = item.get("quota_mb", 1024)
        try:
            quota_mb = int(quota_raw)
        except (TypeError, ValueError):
            quota_mb = 1024
        if quota_mb < 10:
            quota_mb = 10
        mailboxes.append(
            MailboxEntry(
                email=email,
                password=password_raw or None,
                has_password=bool(password_raw),
                display_name=display_name_raw or None,
                quota_mb=quota_mb,
                enabled=bool(item.get("enabled", True)),
                aliases=_mailbox_aliases(item.get("aliases")),
            )
        )
    return mailboxes


def _mailbox_list_for_profile(value: object) -> list[MailboxEntry]:
    items = _mailbox_list(value)
    return [
        item.model_copy(update={"password": None, "has_password": item.has_password})
        for item in items
    ]


def _normalize_mailboxes_for_storage(
    requested: list[MailboxEntry], existing_items: list[MailboxEntry]
) -> list[dict]:
    existing_by_email = {item.email.lower(): item for item in existing_items}
    normalized: list[dict] = []
    for item in requested:
        email = item.email.strip().lower()
        if not email:
            continue
        password = (item.password or "").strip()
        if not password:
            existing = existing_by_email.get(email)
            password = existing.password if existing and existing.password else ""

        aliases = []
        seen: set[str] = set()
        for alias in item.aliases:
            normalized_alias = alias.strip().lower()
            if not normalized_alias or normalized_alias == email or normalized_alias in seen:
                continue
            seen.add(normalized_alias)
            aliases.append(normalized_alias)

        normalized.append(
            {
                "email": email,
                "password": password or None,
                "display_name": item.display_name.strip() if item.display_name else None,
                "quota_mb": max(10, int(item.quota_mb)),
                "enabled": bool(item.enabled),
                "aliases": aliases,
            }
        )
    return normalized


def _suggest_mail_dns_records(payload: MailStackProfile) -> list[DnsRecord]:
    domain = _normalize_domain(payload.domain) or "example.com"
    hostname = payload.hostname.strip().lower() or "mail"
    dkim_selector = payload.dkim_selector.strip().lower() or "mail"
    dkim_public_key = (payload.dkim_public_key or "").strip()
    dkim_value = (
        f"v=DKIM1; k=rsa; p={dkim_public_key}"
        if dkim_public_key
        else "v=DKIM1; k=rsa; p=PASTE_DKIM_PUBLIC_KEY_HERE"
    )
    return [
        DnsRecord(name="@", type="MX", value=f"10 {hostname}.{domain}."),
        DnsRecord(name="@", type="TXT", value=payload.spf_policy.strip()),
        DnsRecord(name="_dmarc", type="TXT", value=payload.dmarc_policy.strip()),
        DnsRecord(name=f"{dkim_selector}._domainkey", type="TXT", value=dkim_value),
    ]


def _write_mail_runtime_files(
    settings: Settings,
    *,
    domain: str,
    postmaster_address: str,
    mailboxes: list[dict],
) -> dict[str, str]:
    config_dir = Path(settings.data_dir) / "config" / "mailserver"
    config_dir.mkdir(parents=True, exist_ok=True)

    accounts_path = config_dir / "accounts.cf"
    aliases_path = config_dir / "aliases.cf"
    manifest_path = config_dir / "mailboxes.json"

    accounts_lines: list[str] = []
    alias_lines: list[str] = []
    for mailbox in mailboxes:
        email = str(mailbox.get("email", "")).strip().lower()
        password = str(mailbox.get("password", "")).strip()
        enabled = bool(mailbox.get("enabled", True))
        if email and password and enabled:
            accounts_lines.append(f"{email}|{password}")

        aliases = mailbox.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                normalized_alias = str(alias).strip().lower()
                if normalized_alias and email and enabled:
                    alias_lines.append(f"{normalized_alias}|{email}")

    if postmaster_address not in [line.split("|", 1)[0] for line in accounts_lines if "|" in line]:
        account_domain = postmaster_address.split("@")[-1].strip().lower()
        if account_domain == domain:
            alias_lines.append(f"postmaster@{domain}|{postmaster_address}")

    accounts_text = ("\n".join(accounts_lines) + "\n") if accounts_lines else ""
    aliases_text = ("\n".join(alias_lines) + "\n") if alias_lines else ""
    accounts_path.write_text(accounts_text, encoding="utf-8")
    aliases_path.write_text(aliases_text, encoding="utf-8")
    manifest_path.write_text(
        json.dumps({"domain": domain, "mailboxes": mailboxes}, indent=2),
        encoding="utf-8",
    )

    return {
        "accounts_path": str(accounts_path),
        "aliases_path": str(aliases_path),
        "manifest_path": str(manifest_path),
    }


def _dns_record_list(
    value: object, fallback: list[dict[str, str]] | None = None
) -> list[DnsRecord]:
    if not isinstance(value, list):
        value = fallback or []

    records: list[DnsRecord] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        record_type = str(item.get("type", "")).strip().upper()
        record_value = str(item.get("value", "")).strip()
        if not name or not record_type or not record_value:
            continue
        records.append(DnsRecord(name=name, type=record_type, value=record_value))

    if records:
        return records
    if fallback:
        return _dns_record_list(fallback, fallback=None)
    return []


def _to_fqdn(host: str, domain: str) -> str:
    host_value = host.strip().rstrip(".")
    domain_value = domain.strip().strip(".")
    if not host_value:
        return f"ns1.{domain_value}."
    if host_value.endswith(domain_value):
        return f"{host_value}."
    return f"{host_value}.{domain_value}."


def _split_dhcp_range(value: str) -> tuple[str, str, str]:
    start, end, lease = "", "", ""
    if value:
        parts = [item.strip() for item in value.split(",")]
        if len(parts) > 0:
            start = parts[0]
        if len(parts) > 1:
            end = parts[1]
        if len(parts) > 2:
            lease = parts[2]
    return start, end, lease


def _parse_lease_line(line: str) -> DhcpLeaseEntry | None:
    parts = line.strip().split(maxsplit=4)
    if len(parts) < 3:
        return None

    expiry_raw = parts[0]
    mac = parts[1].strip()
    ip = parts[2].strip()
    hostname = parts[3].strip() if len(parts) > 3 else ""
    client_id = parts[4].strip() if len(parts) > 4 else ""

    expires_at = None
    is_expired = False
    try:
        expiry_epoch = int(expiry_raw)
        if expiry_epoch > 0:
            expires_at = datetime.fromtimestamp(expiry_epoch, tz=timezone.utc)
            is_expired = expires_at < datetime.now(timezone.utc)
    except ValueError:
        expires_at = None
        is_expired = False

    return DhcpLeaseEntry(
        expires_at=expires_at,
        is_expired=is_expired,
        mac=mac,
        ip=ip,
        hostname=None if hostname in {"", "*"} else hostname,
        client_id=None if client_id in {"", "*"} else client_id,
    )


@router.get("/network/dhcp/leases", response_model=DhcpLeasesResponse)
def dhcp_leases(
    settings: Settings = Depends(get_settings_dep),
    _admin_user: User = Depends(require_admin),
) -> DhcpLeasesResponse:
    lease_path = Path(settings.data_dir) / "state" / "dnsmasq" / "dnsmasq.leases"
    if not lease_path.exists():
        return DhcpLeasesResponse(items=[])

    items: list[DhcpLeaseEntry] = []
    for line in lease_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        parsed = _parse_lease_line(line)
        if parsed is not None:
            items.append(parsed)

    return DhcpLeasesResponse(items=items)


@router.get("/mail/profile", response_model=MailStackProfile)
def mail_profile(
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
) -> MailStackProfile:
    mail_cfg = _active_config_json(db, "mailserver")
    webmail_cfg = _active_config_json(db, "webmail")
    enable_flags = _service_enabled_map(db, ["mailserver", "webmail"])

    domain = _normalize_domain(str(mail_cfg.get("domain", "example.com"))) or "example.com"
    postmaster_address = (
        str(mail_cfg.get("postmaster_address", f"postmaster@{domain}")).strip()
        or f"postmaster@{domain}"
    )
    dkim_public_key = str(mail_cfg.get("dkim_public_key", "")).strip() or None

    return MailStackProfile(
        domain=domain,
        hostname=str(mail_cfg.get("hostname", "mail")).strip() or "mail",
        webmail_url=(
            str(webmail_cfg.get("webmail_url", f"https://webmail.{domain}")).strip()
            or f"https://webmail.{domain}"
        ),
        postmaster_address=postmaster_address,
        enable_mailserver=enable_flags.get("mailserver", True),
        enable_webmail=enable_flags.get("webmail", True),
        enable_imap=bool(mail_cfg.get("enable_imap", True)),
        enable_pop3=bool(mail_cfg.get("enable_pop3", False)),
        enable_submission=bool(mail_cfg.get("enable_submission", True)),
        enable_submissions=bool(mail_cfg.get("enable_submissions", True)),
        enable_smtps=bool(mail_cfg.get("enable_smtps", False)),
        dkim_selector=str(mail_cfg.get("dkim_selector", "mail")).strip() or "mail",
        dkim_key_size=int(mail_cfg.get("dkim_key_size", 2048)),
        dkim_public_key=dkim_public_key,
        spf_policy=str(mail_cfg.get("spf_policy", "v=spf1 mx -all")).strip() or "v=spf1 mx -all",
        dmarc_policy=(
            str(
                mail_cfg.get(
                    "dmarc_policy",
                    f"v=DMARC1; p=quarantine; rua=mailto:{postmaster_address}",
                )
            ).strip()
            or f"v=DMARC1; p=quarantine; rua=mailto:{postmaster_address}"
        ),
        mailboxes=_mailbox_list_for_profile(mail_cfg.get("mailboxes")),
    )


@router.post("/mail/apply", response_model=MailStackApplyResponse)
def apply_mail_profile(
    payload: MailStackProfile,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> MailStackApplyResponse:
    manager = ConfigManager(db, docker_gateway)
    lifecycle_manager = ServiceLifecycleManager(docker_gateway)

    domain = _normalize_domain(payload.domain)
    if not domain or not DOMAIN_PATTERN.fullmatch(domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mail domain is invalid. Use a valid fqdn like example.com.",
        )

    postmaster_address = payload.postmaster_address.strip().lower()
    if "@" not in postmaster_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Postmaster address must contain '@'.",
        )
    if payload.dkim_key_size < 1024 or payload.dkim_key_size > 4096:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DKIM key size must be between 1024 and 4096.",
        )

    existing_mail_cfg = _active_config_json(db, "mailserver")
    existing_mailboxes = _mailbox_list(existing_mail_cfg.get("mailboxes"))
    normalized_mailboxes = _normalize_mailboxes_for_storage(payload.mailboxes, existing_mailboxes)

    mailbox_emails: set[str] = set()
    for mailbox in normalized_mailboxes:
        email = str(mailbox.get("email", "")).lower()
        if email in mailbox_emails:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mailbox email duplicated: {email}",
            )
        mailbox_emails.add(email)
        if not email.endswith(f"@{domain}"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mailbox must match mail domain {domain}: {email}",
            )

    hostname = payload.hostname.strip().lower() or "mail"
    mail_host = f"{hostname}.{domain}"
    webmail_url = (
        payload.webmail_url.strip()
        if payload.webmail_url and payload.webmail_url.strip()
        else f"https://webmail.{domain}"
    )
    dkim_selector = payload.dkim_selector.strip().lower() or "mail"
    dkim_public_key = (payload.dkim_public_key or "").strip() or None
    runtime_paths = _write_mail_runtime_files(
        settings,
        domain=domain,
        postmaster_address=postmaster_address,
        mailboxes=normalized_mailboxes,
    )

    service_payloads: list[tuple[str, bool, dict]] = [
        (
            "mailserver",
            payload.enable_mailserver,
            {
                "domain": domain,
                "hostname": hostname,
                "postmaster_address": postmaster_address,
                "enable_imap": payload.enable_imap,
                "enable_pop3": payload.enable_pop3,
                "enable_submission": payload.enable_submission,
                "enable_submissions": payload.enable_submissions,
                "enable_smtps": payload.enable_smtps,
                "dkim_selector": dkim_selector,
                "dkim_key_size": payload.dkim_key_size,
                "dkim_public_key": dkim_public_key,
                "spf_policy": payload.spf_policy.strip(),
                "dmarc_policy": payload.dmarc_policy.strip(),
                "mailboxes": normalized_mailboxes,
                "runtime_accounts_path": runtime_paths["accounts_path"],
                "runtime_aliases_path": runtime_paths["aliases_path"],
                "runtime_manifest_path": runtime_paths["manifest_path"],
            },
        ),
        (
            "webmail",
            payload.enable_webmail,
            {
                "mail_domain": domain,
                "mail_host": mail_host,
                "webmail_url": webmail_url,
                "imap_port": 993,
                "smtp_submission_port": 587,
                "mailbox_count": len(normalized_mailboxes),
            },
        ),
    ]

    results: list[NetworkServiceApplyResult] = []
    for service_slug, service_enabled, config_json in service_payloads:
        service = _service_or_404(db, service_slug)
        if not service_enabled:
            lifecycle_result = lifecycle_manager.reconcile_enabled(service=service, enabled=False)
            results.append(
                NetworkServiceApplyResult(
                    service_slug=service_slug,
                    status=lifecycle_result.status,
                    version=None,
                    message=lifecycle_result.message,
                    warnings=lifecycle_result.warnings,
                )
            )
            continue

        lifecycle_result = lifecycle_manager.reconcile_enabled(service=service, enabled=True)
        pre_warnings = list(lifecycle_result.warnings)
        if lifecycle_result.status != "failed":
            pre_warnings += lifecycle_manager.ensure_running_before_apply(service=service)

        version, warnings = manager.apply_candidate(
            service=service,
            actor=current_user,
            payload=ConfigApplyRequest(
                config_json=config_json,
                raw_config="",
                auto_reload=True,
            ),
        )
        warnings = pre_warnings + warnings
        results.append(
            NetworkServiceApplyResult(
                service_slug=service_slug,
                status=version.apply_status,
                version=version.version,
                message=version.apply_message,
                warnings=warnings,
            )
        )

    success = all(item.status in {"applied", "disabled", "stopped"} for item in results)
    suggestions = _suggest_mail_dns_records(payload)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="mail_stack_apply",
        resource_type="settings",
        resource_id="mail-stack",
        status="success" if success else "failed",
        ip_address=get_client_ip(request),
        after={"profile": payload.model_dump(exclude={"mailboxes"})},
        metadata_json={
            "results": [item.model_dump() for item in results],
            "mailbox_count": len(normalized_mailboxes),
            "suggested_dns_records": [item.model_dump() for item in suggestions],
        },
    )
    db.commit()

    return MailStackApplyResponse(
        success=success,
        results=results,
        suggested_dns_records=suggestions,
    )


@router.get("/mail/webmail/url")
def mail_webmail_url(
    mailbox: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
) -> dict[str, str | None]:
    mail_cfg = _active_config_json(db, "mailserver")
    webmail_cfg = _active_config_json(db, "webmail")
    domain = _normalize_domain(str(mail_cfg.get("domain", "example.com"))) or "example.com"
    url = (
        str(webmail_cfg.get("webmail_url", f"https://webmail.{domain}")).strip()
        or f"https://webmail.{domain}"
    )

    mailbox_value = mailbox.strip().lower() if mailbox else None
    if mailbox_value:
        mailboxes = _mailbox_list(mail_cfg.get("mailboxes"))
        if not any(item.email == mailbox_value and item.enabled for item in mailboxes):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Mailbox not found or disabled: {mailbox_value}",
            )

    return {"url": url, "mailbox": mailbox_value}


@router.get("/network/profile", response_model=NetworkStackProfile)
def network_profile(
    db: Session = Depends(get_db),
    _admin_user: User = Depends(require_admin),
) -> NetworkStackProfile:
    dnsmasq_cfg = _active_config_json(db, "dnsmasq")
    bind9_cfg = _active_config_json(db, "bind9")
    ntp_cfg = _active_config_json(db, "ntp")

    dhcp_ranges = dnsmasq_cfg.get("dhcp_ranges", [])
    primary_range = dhcp_ranges[0] if isinstance(dhcp_ranges, list) and dhcp_ranges else ""
    dhcp_start, dhcp_end, dhcp_lease = _split_dhcp_range(str(primary_range))

    records = bind9_cfg.get("records", [])
    records_by_name: dict[str, dict] = {}
    if isinstance(records, list):
        for item in records:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                records_by_name[item["name"]] = item

    nameserver_host = str(bind9_cfg.get("nameserver_host", "ns1"))
    api_host = str(bind9_cfg.get("api_host", "api"))
    dashboard_host = str(bind9_cfg.get("dashboard_host", "dashboard"))
    nameserver_record = records_by_name.get(nameserver_host, {})
    api_record = records_by_name.get(api_host, {})
    dashboard_record = records_by_name.get(dashboard_host, {})
    default_dns_records = [
        {
            "name": nameserver_host,
            "type": "A",
            "value": str(nameserver_record.get("value", "192.168.50.2")),
        },
        {
            "name": api_host,
            "type": "A",
            "value": str(api_record.get("value", "192.168.50.10")),
        },
        {
            "name": dashboard_host,
            "type": "A",
            "value": str(dashboard_record.get("value", "192.168.50.10")),
        },
    ]
    dns_records = _dns_record_list(bind9_cfg.get("records"), fallback=default_dns_records)

    dns_servers = dnsmasq_cfg.get("upstream_servers", ["1.1.1.1", "1.0.0.1"])
    ntp_servers = ntp_cfg.get("servers", ["time.cloudflare.com", "time.google.com"])

    domain = _normalize_domain(str(dnsmasq_cfg.get("domain", "homelab.local"))) or "homelab.local"
    authoritative_domains = _authoritative_domain_list(
        bind9_cfg.get("authoritative_domains"),
        primary_domain=domain,
    )
    enable_flags = _service_enabled_map(db, ["dnsmasq", "bind9", "ntp"])

    return NetworkStackProfile(
        domain=domain,
        authoritative_domains=authoritative_domains,
        enable_dnsmasq=enable_flags.get("dnsmasq", True),
        enable_bind9=enable_flags.get("bind9", True),
        enable_ntp=enable_flags.get("ntp", True),
        router_ip=str(dnsmasq_cfg.get("router", "192.168.50.1")),
        dhcp_range_start=dhcp_start or "192.168.50.100",
        dhcp_range_end=dhcp_end or "192.168.50.200",
        dhcp_lease=dhcp_lease or "12h",
        dhcp_authoritative=bool(dnsmasq_cfg.get("dhcp_authoritative", True)),
        dhcp_dns_servers=_string_list(dnsmasq_cfg.get("dhcp_dns_servers"), []),
        dhcp_ntp_servers=_string_list(dnsmasq_cfg.get("dhcp_ntp_servers"), []),
        dhcp_domain_search=str(dnsmasq_cfg.get("dhcp_domain_search", "")).strip() or None,
        dhcp_reservations=_reservation_list(dnsmasq_cfg.get("dhcp_reservations")),
        dns_upstream_servers=_string_list(dns_servers, ["1.1.1.1", "1.0.0.1"]),
        dns_cache_size=int(dnsmasq_cfg.get("cache_size", 1000)),
        zone_ttl=int(bind9_cfg.get("ttl", 3600)),
        zone_serial=int(bind9_cfg.get("serial", _default_zone_serial())),
        nameserver_host=nameserver_host,
        nameserver_ip=str(nameserver_record.get("value", "192.168.50.2")),
        api_host=api_host,
        api_ip=str(api_record.get("value", "192.168.50.10")),
        dashboard_host=dashboard_host,
        dashboard_ip=str(dashboard_record.get("value", "192.168.50.10")),
        dns_records=dns_records,
        ntp_servers=_string_list(ntp_servers, ["time.cloudflare.com", "time.google.com"]),
        ntp_iburst=bool(ntp_cfg.get("iburst", True)),
        ntp_disable_monitor=bool(ntp_cfg.get("disable_monitor", True)),
        ntp_local_clock=bool(ntp_cfg.get("local_clock", False)),
        ntp_local_stratum=int(ntp_cfg.get("local_stratum", 10)),
    )


@router.post("/network/apply", response_model=NetworkStackApplyResponse)
def apply_network_profile(
    payload: NetworkStackProfile,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
    current_user: User = Depends(require_admin),
    docker_gateway: DockerGateway = Depends(get_docker_gateway),
) -> NetworkStackApplyResponse:
    manager = ConfigManager(db, docker_gateway)
    lifecycle_manager = ServiceLifecycleManager(docker_gateway)
    domain = _normalize_domain(payload.domain)
    if not domain or not DOMAIN_PATTERN.fullmatch(domain):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Domain is invalid. Use a valid fqdn like example.com.",
        )
    authoritative_domains = _authoritative_domain_list(
        payload.authoritative_domains,
        primary_domain=domain,
    )
    dns_servers = [item.strip() for item in payload.dns_upstream_servers if item.strip()]
    dhcp_dns_servers = [item.strip() for item in payload.dhcp_dns_servers if item.strip()]
    dhcp_ntp_servers = [item.strip() for item in payload.dhcp_ntp_servers if item.strip()]
    ntp_servers = [item.strip() for item in payload.ntp_servers if item.strip()]

    bind_records = [
        {
            "name": item.name.strip(),
            "type": item.type.strip().upper(),
            "value": item.value.strip(),
        }
        for item in payload.dns_records
        if item.name.strip() and item.type.strip() and item.value.strip()
    ]
    if not bind_records:
        bind_records = [
            {
                "name": payload.nameserver_host.strip(),
                "type": "A",
                "value": payload.nameserver_ip.strip(),
            },
            {"name": payload.api_host.strip(), "type": "A", "value": payload.api_ip.strip()},
            {
                "name": payload.dashboard_host.strip(),
                "type": "A",
                "value": payload.dashboard_ip.strip(),
            },
        ]
    bind_records = [
        record for record in bind_records if record["name"] and record["type"] and record["value"]
    ]
    dnsmasq_reservations = [
        {
            "mac": item.mac.strip().lower(),
            "ip": item.ip.strip(),
            "hostname": item.hostname.strip() if item.hostname else None,
            "lease": item.lease.strip() if item.lease else None,
        }
        for item in payload.dhcp_reservations
        if item.mac.strip() and item.ip.strip()
    ]

    service_payloads: list[tuple[str, bool, dict]] = [
        (
            "dnsmasq",
            payload.enable_dnsmasq,
            {
                "upstream_servers": dns_servers,
                "domain": domain,
                "cache_size": payload.dns_cache_size,
                "dhcp_ranges": [
                    f"{payload.dhcp_range_start.strip()},{payload.dhcp_range_end.strip()},{payload.dhcp_lease.strip()}"
                ],
                "router": payload.router_ip.strip(),
                "dhcp_authoritative": payload.dhcp_authoritative,
                "dhcp_dns_servers": dhcp_dns_servers,
                "dhcp_ntp_servers": dhcp_ntp_servers,
                "dhcp_domain_search": (
                    payload.dhcp_domain_search.strip() if payload.dhcp_domain_search else None
                ),
                "dhcp_reservations": dnsmasq_reservations,
            },
        ),
        (
            "bind9",
            payload.enable_bind9,
            {
                "ttl": payload.zone_ttl,
                "primary_ns": _to_fqdn(payload.nameserver_host, domain),
                "admin_email": f"admin.{domain.strip('.')}." if domain else "admin.homelab.local.",
                "serial": payload.zone_serial or _default_zone_serial(),
                "nameserver_host": payload.nameserver_host.strip(),
                "nameserver_ip": payload.nameserver_ip.strip(),
                "api_host": payload.api_host.strip(),
                "api_ip": payload.api_ip.strip(),
                "dashboard_host": payload.dashboard_host.strip(),
                "dashboard_ip": payload.dashboard_ip.strip(),
                "records": bind_records,
                "authoritative_domains": authoritative_domains,
            },
        ),
        (
            "ntp",
            payload.enable_ntp,
            {
                "servers": ntp_servers,
                "iburst": payload.ntp_iburst,
                "disable_monitor": payload.ntp_disable_monitor,
                "local_clock": payload.ntp_local_clock,
                "local_stratum": payload.ntp_local_stratum,
            },
        ),
    ]

    results: list[NetworkServiceApplyResult] = []
    for service_slug, service_enabled, config_json in service_payloads:
        service = _service_or_404(db, service_slug)
        if not service_enabled:
            lifecycle_result = lifecycle_manager.reconcile_enabled(service=service, enabled=False)
            results.append(
                NetworkServiceApplyResult(
                    service_slug=service_slug,
                    status=lifecycle_result.status,
                    version=None,
                    message=lifecycle_result.message,
                    warnings=lifecycle_result.warnings,
                )
            )
            continue

        lifecycle_result = lifecycle_manager.reconcile_enabled(service=service, enabled=True)
        pre_warnings = list(lifecycle_result.warnings)
        if lifecycle_result.status != "failed":
            pre_warnings += lifecycle_manager.ensure_running_before_apply(service=service)

        if service_slug == "bind9":
            _write_bind9_named_conf(
                settings,
                authoritative_domains=authoritative_domains,
                zone_file_container_path=_bind9_zone_file_container_path(service, settings),
            )
        version, warnings = manager.apply_candidate(
            service=service,
            actor=current_user,
            payload=ConfigApplyRequest(
                config_json=config_json,
                raw_config="",
                auto_reload=True,
            ),
        )
        warnings = pre_warnings + warnings
        results.append(
            NetworkServiceApplyResult(
                service_slug=service_slug,
                status=version.apply_status,
                version=version.version,
                message=version.apply_message,
                warnings=warnings,
            )
        )

    success = all(item.status in {"applied", "disabled", "stopped"} for item in results)

    audit = AuditService(db)
    audit.record(
        actor_user_id=current_user.id,
        action="network_stack_apply",
        resource_type="settings",
        resource_id="network-stack",
        status="success" if success else "failed",
        ip_address=get_client_ip(request),
        after={"profile": payload.model_dump()},
        metadata_json={"results": [item.model_dump() for item in results]},
    )
    db.commit()

    return NetworkStackApplyResponse(success=success, results=results)
