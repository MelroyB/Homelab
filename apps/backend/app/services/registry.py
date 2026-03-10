from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceMeta:
    slug: str
    name: str
    category: str
    description: str
    container_name: str
    config_path: str
    template_name: str
    supports_reload: bool = False
    supports_raw_edit: bool = True


SERVICE_CATALOG: list[ServiceMeta] = [
    ServiceMeta(
        slug="frontend",
        name="Frontend UI",
        category="platform",
        description="React operations dashboard",
        container_name="homelab-frontend-1",
        config_path="",
        template_name="",
    ),
    ServiceMeta(
        slug="backend",
        name="Backend API",
        category="platform",
        description="FastAPI control plane",
        container_name="homelab-backend-1",
        config_path="",
        template_name="",
    ),
    ServiceMeta(
        slug="caddy",
        name="Reverse Proxy",
        category="ingress",
        description="Caddy ingress and TLS termination",
        container_name="homelab-caddy-1",
        config_path="/var/lib/homelab/config/caddy/Caddyfile",
        template_name="caddy.j2",
        supports_reload=True,
    ),
    ServiceMeta(
        slug="dnsmasq",
        name="DNS Resolver + DHCP",
        category="network",
        description="dnsmasq resolver and DHCP scope",
        container_name="homelab-dnsmasq-1",
        config_path="/var/lib/homelab/config/dnsmasq/runtime/generated.conf",
        template_name="dnsmasq.j2",
        supports_reload=True,
    ),
    ServiceMeta(
        slug="bind9",
        name="Authoritative DNS",
        category="network",
        description="BIND9 authoritative zones",
        container_name="homelab-bind9-1",
        config_path="/var/lib/homelab/config/bind9/zones/db.homelab.local",
        template_name="bind9.j2",
        supports_reload=True,
    ),
    ServiceMeta(
        slug="ntp",
        name="NTP",
        category="network",
        description="NTP service",
        container_name="homelab-ntp-1",
        config_path="/var/lib/homelab/config/ntp/ntp.conf",
        template_name="ntp.j2",
        supports_reload=True,
    ),
    ServiceMeta(
        slug="postgres",
        name="PostgreSQL",
        category="data",
        description="State and config metadata",
        container_name="homelab-postgres-1",
        config_path="",
        template_name="",
        supports_raw_edit=False,
    ),
    ServiceMeta(
        slug="redis",
        name="Redis",
        category="data",
        description="Cache and queue",
        container_name="homelab-redis-1",
        config_path="",
        template_name="",
        supports_raw_edit=False,
    ),
]

SERVICE_CATALOG_BY_SLUG = {item.slug: item for item in SERVICE_CATALOG}
CONFIG_MANAGED_SERVICES = {item.slug for item in SERVICE_CATALOG if bool(item.config_path)}
