from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DhcpReservation(BaseModel):
    mac: str
    ip: str
    hostname: str | None = None
    lease: str | None = None


class DnsRecord(BaseModel):
    name: str
    type: str
    value: str


class MailboxEntry(BaseModel):
    email: str
    password: str | None = None
    has_password: bool = False
    display_name: str | None = None
    quota_mb: int = 1024
    enabled: bool = True
    aliases: list[str] = Field(default_factory=list)


class NetworkStackProfile(BaseModel):
    domain: str = "homelab.local"
    authoritative_domains: list[str] = Field(default_factory=lambda: ["homelab.local"])
    enable_dnsmasq: bool = True
    enable_bind9: bool = True
    enable_ntp: bool = True
    router_ip: str = "192.168.50.1"
    dhcp_range_start: str = "192.168.50.100"
    dhcp_range_end: str = "192.168.50.200"
    dhcp_lease: str = "12h"
    dhcp_authoritative: bool = True
    dhcp_dns_servers: list[str] = Field(default_factory=list)
    dhcp_ntp_servers: list[str] = Field(default_factory=list)
    dhcp_domain_search: str | None = None
    dhcp_reservations: list[DhcpReservation] = Field(default_factory=list)
    dns_upstream_servers: list[str] = Field(default_factory=lambda: ["1.1.1.1", "1.0.0.1"])
    dns_cache_size: int = 1000
    zone_ttl: int = 3600
    zone_serial: int | None = None
    nameserver_host: str = "ns1"
    nameserver_ip: str = "192.168.50.2"
    api_host: str = "api"
    api_ip: str = "192.168.50.10"
    dashboard_host: str = "dashboard"
    dashboard_ip: str = "192.168.50.10"
    dns_records: list[DnsRecord] = Field(default_factory=list)
    ntp_servers: list[str] = Field(
        default_factory=lambda: ["time.cloudflare.com", "time.google.com"]
    )
    ntp_iburst: bool = True
    ntp_disable_monitor: bool = True
    ntp_local_clock: bool = False
    ntp_local_stratum: int = 10


class NetworkServiceApplyResult(BaseModel):
    service_slug: str
    status: str
    version: int | None = None
    message: str
    warnings: list[str] = Field(default_factory=list)


class NetworkStackApplyResponse(BaseModel):
    success: bool
    results: list[NetworkServiceApplyResult] = Field(default_factory=list)


class MailStackProfile(BaseModel):
    domain: str = "example.com"
    hostname: str = "mail"
    webmail_url: str | None = "https://webmail.example.com"
    postmaster_address: str = "postmaster@example.com"
    enable_mailserver: bool = True
    enable_webmail: bool = True
    enable_imap: bool = True
    enable_pop3: bool = False
    enable_submission: bool = True
    enable_submissions: bool = True
    enable_smtps: bool = False
    dkim_selector: str = "mail"
    dkim_key_size: int = 2048
    dkim_public_key: str | None = None
    spf_policy: str = "v=spf1 mx -all"
    dmarc_policy: str = "v=DMARC1; p=quarantine; rua=mailto:postmaster@example.com"
    mailboxes: list[MailboxEntry] = Field(default_factory=list)


class MailStackApplyResponse(BaseModel):
    success: bool
    results: list[NetworkServiceApplyResult] = Field(default_factory=list)
    suggested_dns_records: list[DnsRecord] = Field(default_factory=list)


class DhcpLeaseEntry(BaseModel):
    expires_at: datetime | None = None
    is_expired: bool
    mac: str
    ip: str
    hostname: str | None = None
    client_id: str | None = None


class DhcpLeasesResponse(BaseModel):
    items: list[DhcpLeaseEntry] = Field(default_factory=list)
