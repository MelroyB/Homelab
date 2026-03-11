from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    NetworkServiceApplyResult,
    NetworkStackApplyResponse,
    NetworkStackProfile,
)
from app.services.audit.service import AuditService
from app.services.config.manager import ConfigManager
from app.services.docker_gateway import DockerGateway

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
        service.enabled = service_enabled

        runtime_state = str(
            docker_gateway.inspect(service.container_name).get("state", "unknown")
        ).lower()

        if not service_enabled:
            stop_status = "disabled"
            stop_message = "Service disabled; container already stopped."
            warnings: list[str] = []
            if runtime_state == "running":
                ok_stop, stop_result = docker_gateway.action(service.container_name, "stop")
                if ok_stop:
                    stop_status = "stopped"
                    stop_message = "Service disabled and container stopped."
                else:
                    stop_status = "failed"
                    stop_message = "Service disabled, but stopping container failed."
                    warnings.append(stop_result)
            elif runtime_state == "not_found":
                stop_message = "Service disabled; container not found."

            results.append(
                NetworkServiceApplyResult(
                    service_slug=service_slug,
                    status=stop_status,
                    version=None,
                    message=stop_message,
                    warnings=warnings,
                )
            )
            continue

        pre_warnings: list[str] = []
        if runtime_state in {"created", "exited", "dead", "paused"}:
            ok_start, start_result = docker_gateway.action(service.container_name, "start")
            if not ok_start:
                pre_warnings.append(f"Start before apply failed: {start_result}")
        elif runtime_state == "not_found":
            pre_warnings.append("Container not found; apply may fail on reload/restart.")

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
