import { useEffect, useState } from "react";
import {
  applyMailStackProfile,
  applyNetworkStackProfile,
  getDhcpLeases,
  getMailDnsSuggestions,
  getMailStackProfile,
  getNetworkStackProfile,
  getWebmailUrl
} from "../api/settings";
import {
  DnsRecord,
  MailSetupIssue,
  DhcpLeaseEntry,
  DhcpReservation,
  MailboxEntry,
  MailStackProfile,
  NetworkServiceApplyResult,
  NetworkStackProfile
} from "../types/api";
import { StatusBadge } from "../components/StatusBadge";

const DNS_RECORD_TYPES = [
  "A",
  "AAAA",
  "CNAME",
  "TXT",
  "MX",
  "NS",
  "SRV",
  "PTR",
  "CAA",
  "NAPTR",
  "SPF",
  "TLSA",
  "LOC"
] as const;

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function normalizeDomain(value: string): string {
  return value.trim().replace(/\.+$/, "").toLowerCase();
}

function formatExpiry(value: string | null): string {
  if (!value) {
    return "Never";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

export function SettingsPage() {
  const [profile, setProfile] = useState<NetworkStackProfile | null>(null);
  const [mailProfile, setMailProfile] = useState<MailStackProfile | null>(null);
  const [dnsServersText, setDnsServersText] = useState("");
  const [dhcpDnsServersText, setDhcpDnsServersText] = useState("");
  const [dhcpNtpServersText, setDhcpNtpServersText] = useState("");
  const [authoritativeDomainsText, setAuthoritativeDomainsText] = useState("");
  const [ntpServersText, setNtpServersText] = useState("");
  const [leases, setLeases] = useState<DhcpLeaseEntry[]>([]);
  const [results, setResults] = useState<NetworkServiceApplyResult[]>([]);
  const [mailResults, setMailResults] = useState<NetworkServiceApplyResult[]>(
    []
  );
  const [mailSuggestedDnsRecords, setMailSuggestedDnsRecords] = useState<
    DnsRecord[]
  >([]);
  const [mailSetupIssues, setMailSetupIssues] = useState<MailSetupIssue[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [mailError, setMailError] = useState<string | null>(null);
  const [mailResult, setMailResult] = useState<string | null>(null);
  const [webmailLaunchMailbox, setWebmailLaunchMailbox] = useState("");
  const [webmailLaunchUrl, setWebmailLaunchUrl] = useState<string | null>(null);

  const reload = async () => {
    const [profileData, leaseData, mailProfileData] = await Promise.all([
      getNetworkStackProfile(),
      getDhcpLeases(),
      getMailStackProfile()
    ]);
    setProfile(profileData);
    setMailProfile(mailProfileData);
    setDnsServersText(profileData.dns_upstream_servers.join("\n"));
    setDhcpDnsServersText(profileData.dhcp_dns_servers.join("\n"));
    setDhcpNtpServersText(profileData.dhcp_ntp_servers.join("\n"));
    setAuthoritativeDomainsText(profileData.authoritative_domains.join("\n"));
    setNtpServersText(profileData.ntp_servers.join("\n"));
    setLeases(leaseData.items);
  };

  useEffect(() => {
    reload().catch((err) =>
      setError(
        err instanceof Error ? err.message : "Failed to load settings profile"
      )
    );
  }, []);

  const updateProfile = (patch: Partial<NetworkStackProfile>) => {
    setProfile((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  const updateReservation = (
    index: number,
    patch: Partial<DhcpReservation>
  ) => {
    updateProfile({
      dhcp_reservations: (profile?.dhcp_reservations ?? []).map(
        (item, itemIndex) =>
          itemIndex === index ? { ...item, ...patch } : item
      )
    });
  };

  const updateDnsRecord = (index: number, patch: Partial<DnsRecord>) => {
    updateProfile({
      dns_records: (profile?.dns_records ?? []).map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item
      )
    });
  };

  const addDnsRecord = () => {
    updateProfile({
      dns_records: [
        ...(profile?.dns_records ?? []),
        { name: "", type: "A", value: "" }
      ]
    });
  };

  const removeDnsRecord = (index: number) => {
    updateProfile({
      dns_records: (profile?.dns_records ?? []).filter(
        (_item, itemIndex) => itemIndex !== index
      )
    });
  };

  const addReservation = () => {
    updateProfile({
      dhcp_reservations: [
        ...(profile?.dhcp_reservations ?? []),
        { mac: "", ip: "", hostname: null, lease: null }
      ]
    });
  };

  const removeReservation = (index: number) => {
    updateProfile({
      dhcp_reservations: (profile?.dhcp_reservations ?? []).filter(
        (_item, itemIndex) => itemIndex !== index
      )
    });
  };

  const updateMailProfile = (patch: Partial<MailStackProfile>) => {
    setMailProfile((prev) => (prev ? { ...prev, ...patch } : prev));
  };

  const updateMailbox = (index: number, patch: Partial<MailboxEntry>) => {
    updateMailProfile({
      mailboxes: (mailProfile?.mailboxes ?? []).map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item
      )
    });
  };

  const addMailbox = () => {
    updateMailProfile({
      mailboxes: [
        ...(mailProfile?.mailboxes ?? []),
        {
          email: "",
          password: null,
          has_password: false,
          display_name: null,
          quota_mb: 1024,
          enabled: true,
          aliases: []
        }
      ]
    });
  };

  const removeMailbox = (index: number) => {
    updateMailProfile({
      mailboxes: (mailProfile?.mailboxes ?? []).filter(
        (_item, itemIndex) => itemIndex !== index
      )
    });
  };

  const onRefreshLeases = async () => {
    setError(null);
    try {
      const leaseData = await getDhcpLeases();
      setLeases(leaseData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh leases");
    }
  };

  const onApply = async () => {
    if (!profile) {
      return;
    }

    setError(null);
    setResult(null);
    setResults([]);

    const dnsServers = splitLines(dnsServersText);
    const dhcpDnsServers = splitLines(dhcpDnsServersText);
    const dhcpNtpServers = splitLines(dhcpNtpServersText);
    const authoritativeDomains = Array.from(
      new Set(
        [profile.domain, ...splitLines(authoritativeDomainsText)]
          .map(normalizeDomain)
          .filter((item) => item.length > 0)
      )
    );
    const ntpServers = splitLines(ntpServersText);
    const sourceRecords = profile.dns_records ?? [];
    const hasIncompleteRecord = sourceRecords.some((record) => {
      const hasAny =
        record.name.trim() || record.type.trim() || record.value.trim();
      const hasAll =
        record.name.trim() && record.type.trim() && record.value.trim();
      return Boolean(hasAny && !hasAll);
    });
    if (profile.enable_bind9 && hasIncompleteRecord) {
      setError(
        "Vul elke DNS record volledig in (name, type, value) of maak de regel leeg."
      );
      return;
    }
    const dnsRecords = sourceRecords
      .map((record) => ({
        name: record.name.trim(),
        type: record.type.trim().toUpperCase(),
        value: record.value.trim()
      }))
      .filter((record) => record.name && record.type && record.value);

    if (profile.enable_dnsmasq && dnsServers.length === 0) {
      setError("Voeg minimaal 1 DNS upstream server toe.");
      return;
    }
    if (profile.enable_bind9 && authoritativeDomains.length === 0) {
      setError("Voeg minimaal 1 authoritative domein toe.");
      return;
    }
    if (
      profile.enable_ntp &&
      ntpServers.length === 0 &&
      !profile.ntp_local_clock
    ) {
      setError(
        "Voeg minimaal 1 NTP server toe of activeer local clock fallback."
      );
      return;
    }

    const reservations = profile.dhcp_reservations
      .map((item) => ({
        mac: item.mac.trim(),
        ip: item.ip.trim(),
        hostname: item.hostname?.trim() || null,
        lease: item.lease?.trim() || null
      }))
      .filter(
        (item) =>
          item.mac || item.ip || item.hostname !== null || item.lease !== null
      );

    if (profile.enable_dnsmasq) {
      for (const reservation of reservations) {
        if (!reservation.mac || !reservation.ip) {
          setError("Elke DHCP reservering moet minimaal MAC en IP bevatten.");
          return;
        }
      }
    }

    try {
      const response = await applyNetworkStackProfile({
        ...profile,
        dns_upstream_servers: dnsServers,
        dhcp_dns_servers: dhcpDnsServers,
        dhcp_ntp_servers: dhcpNtpServers,
        authoritative_domains: authoritativeDomains,
        ntp_servers: ntpServers,
        dns_records: dnsRecords,
        dhcp_reservations: reservations
      });
      setResults(response.results);
      setResult(
        response.success
          ? "Network stack toegepast voor DNS, DHCP en NTP."
          : "Apply gedeeltelijk mislukt. Controleer de serviceresultaten."
      );
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    }
  };

  const buildMailPayload = (): MailStackProfile | null => {
    if (!mailProfile) {
      return null;
    }
    return {
      ...mailProfile,
      domain: normalizeDomain(mailProfile.domain),
      hostname: mailProfile.hostname.trim().toLowerCase(),
      webmail_url: mailProfile.webmail_url?.trim() || null,
      postmaster_address: mailProfile.postmaster_address.trim().toLowerCase(),
      dkim_selector: mailProfile.dkim_selector.trim().toLowerCase(),
      dkim_public_key: mailProfile.dkim_public_key?.trim() || null,
      spf_policy: mailProfile.spf_policy.trim(),
      dmarc_policy: mailProfile.dmarc_policy.trim(),
      mailboxes: (mailProfile.mailboxes ?? []).map((item) => ({
        email: item.email.trim().toLowerCase(),
        password: item.password?.trim() || null,
        has_password: item.has_password,
        display_name: item.display_name?.trim() || null,
        quota_mb: item.quota_mb,
        enabled: item.enabled,
        aliases: (item.aliases ?? [])
          .map((alias) => alias.trim().toLowerCase())
          .filter((alias) => alias.length > 0)
      }))
    };
  };

  const onPreviewMailDns = async () => {
    const payload = buildMailPayload();
    if (!payload) {
      return;
    }

    setMailError(null);
    setMailResult(null);
    try {
      const response = await getMailDnsSuggestions(payload);
      setMailSuggestedDnsRecords(response.records);
      setMailSetupIssues(response.issues);
      setMailResult(
        response.valid
          ? "Mail DNS setup validatie is geslaagd."
          : "Mail DNS setup bevat fouten of waarschuwingen."
      );
    } catch (err) {
      setMailError(
        err instanceof Error ? err.message : "Mail DNS setup check mislukt"
      );
    }
  };

  const onApplyMail = async () => {
    const payload = buildMailPayload();
    if (!payload) {
      return;
    }

    setMailError(null);
    setMailResult(null);
    setMailResults([]);
    setMailSuggestedDnsRecords([]);
    setMailSetupIssues([]);

    try {
      const preview = await getMailDnsSuggestions(payload);
      setMailSuggestedDnsRecords(preview.records);
      setMailSetupIssues(preview.issues);
      if (!preview.valid) {
        setMailError(
          "Mail setup bevat fouten. Los eerst de fouten op in de setup check."
        );
        return;
      }

      const response = await applyMailStackProfile(payload);
      setMailResults(response.results);
      setMailSuggestedDnsRecords(response.suggested_dns_records);
      setMailResult(
        response.success
          ? "Mail stack toegepast (mailserver + webmail)."
          : "Mail apply gedeeltelijk mislukt. Controleer de resultaten."
      );
      await reload();
    } catch (err) {
      setMailError(err instanceof Error ? err.message : "Mail apply failed");
    }
  };

  const onOpenWebmail = async () => {
    setMailError(null);
    try {
      const mailbox = webmailLaunchMailbox.trim().toLowerCase() || null;
      const response = await getWebmailUrl(mailbox);
      setWebmailLaunchUrl(response.url);
      if (typeof window !== "undefined") {
        window.open(response.url, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      setMailError(
        err instanceof Error ? err.message : "Webmail URL ophalen mislukt"
      );
    }
  };

  if (!profile || !mailProfile) {
    return <div>Loading settings...</div>;
  }

  return (
    <section>
      <div className="page-header">
        <h2>Network Stack</h2>
        <button className="btn" onClick={onApply}>
          Apply DNS + DHCP + NTP
        </button>
      </div>

      <div className="card">
        <p>
          Beheer DNS, DHCP en NTP als één geheel. Deze actie schrijft in één
          keer naar `dnsmasq`, `bind9` en `ntp`.
        </p>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {result ? <div className="success">{result}</div> : null}

      <div className="two-column">
        <form
          className="card"
          onSubmit={(event) => {
            event.preventDefault();
            onApply();
          }}
        >
          <h3>DHCP + DNS Resolver (dnsmasq)</h3>
          <label>
            <input
              type="checkbox"
              checked={profile.enable_dnsmasq}
              onChange={(e) =>
                updateProfile({ enable_dnsmasq: e.target.checked })
              }
            />
            Functionaliteit inschakelen
          </label>
          {!profile.enable_dnsmasq ? (
            <p>
              dnsmasq is uitgeschakeld. De container wordt gestopt bij apply.
            </p>
          ) : null}

          <label>
            Domain
            <input
              value={profile.domain}
              onChange={(e) => updateProfile({ domain: e.target.value })}
            />
          </label>

          <label>
            Router IP
            <input
              disabled={!profile.enable_dnsmasq}
              value={profile.router_ip}
              onChange={(e) => updateProfile({ router_ip: e.target.value })}
            />
          </label>

          <label>
            DHCP start
            <input
              disabled={!profile.enable_dnsmasq}
              value={profile.dhcp_range_start}
              onChange={(e) =>
                updateProfile({ dhcp_range_start: e.target.value })
              }
            />
          </label>

          <label>
            DHCP end
            <input
              disabled={!profile.enable_dnsmasq}
              value={profile.dhcp_range_end}
              onChange={(e) =>
                updateProfile({ dhcp_range_end: e.target.value })
              }
            />
          </label>

          <label>
            DHCP lease
            <input
              disabled={!profile.enable_dnsmasq}
              value={profile.dhcp_lease}
              onChange={(e) => updateProfile({ dhcp_lease: e.target.value })}
              placeholder="12h"
            />
          </label>

          <label>
            <input
              type="checkbox"
              disabled={!profile.enable_dnsmasq}
              checked={profile.dhcp_authoritative}
              onChange={(e) =>
                updateProfile({ dhcp_authoritative: e.target.checked })
              }
            />
            DHCP authoritative
          </label>

          <label>
            DHCP domain-search (optioneel)
            <input
              disabled={!profile.enable_dnsmasq}
              value={profile.dhcp_domain_search ?? ""}
              onChange={(e) =>
                updateProfile({
                  dhcp_domain_search: e.target.value || null
                })
              }
              placeholder="homelab.local"
            />
          </label>

          <label>
            DHCP option DNS servers (1 per regel)
            <textarea
              disabled={!profile.enable_dnsmasq}
              rows={3}
              value={dhcpDnsServersText}
              onChange={(e) => setDhcpDnsServersText(e.target.value)}
            />
          </label>

          <label>
            DHCP option NTP servers (1 per regel)
            <textarea
              disabled={!profile.enable_dnsmasq}
              rows={3}
              value={dhcpNtpServersText}
              onChange={(e) => setDhcpNtpServersText(e.target.value)}
            />
          </label>

          <label>
            DNS cache size
            <input
              type="number"
              min={10}
              disabled={!profile.enable_dnsmasq}
              value={profile.dns_cache_size}
              onChange={(e) =>
                updateProfile({
                  dns_cache_size: Number.parseInt(e.target.value, 10) || 10
                })
              }
            />
          </label>

          <label>
            Upstream DNS servers (1 per regel)
            <textarea
              disabled={!profile.enable_dnsmasq}
              rows={4}
              value={dnsServersText}
              onChange={(e) => setDnsServersText(e.target.value)}
            />
          </label>

          <h3>DHCP reserveringen</h3>
          {(profile.dhcp_reservations ?? []).length === 0 ? (
            <p>Nog geen reserveringen ingesteld.</p>
          ) : null}
          {(profile.dhcp_reservations ?? []).map((item, index) => (
            <div
              key={`${index}-${item.mac}-${item.ip}`}
              className="inline-form"
            >
              <label>
                MAC
                <input
                  disabled={!profile.enable_dnsmasq}
                  value={item.mac}
                  onChange={(e) =>
                    updateReservation(index, { mac: e.target.value })
                  }
                  placeholder="AA:BB:CC:DD:EE:FF"
                />
              </label>
              <label>
                IP
                <input
                  disabled={!profile.enable_dnsmasq}
                  value={item.ip}
                  onChange={(e) =>
                    updateReservation(index, { ip: e.target.value })
                  }
                  placeholder="192.168.50.50"
                />
              </label>
              <label>
                Hostname
                <input
                  disabled={!profile.enable_dnsmasq}
                  value={item.hostname ?? ""}
                  onChange={(e) =>
                    updateReservation(index, {
                      hostname: e.target.value || null
                    })
                  }
                  placeholder="printer"
                />
              </label>
              <label>
                Lease
                <input
                  disabled={!profile.enable_dnsmasq}
                  value={item.lease ?? ""}
                  onChange={(e) =>
                    updateReservation(index, { lease: e.target.value || null })
                  }
                  placeholder="24h"
                />
              </label>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!profile.enable_dnsmasq}
                onClick={() => removeReservation(index)}
              >
                Verwijder
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!profile.enable_dnsmasq}
            onClick={addReservation}
          >
            Reservering toevoegen
          </button>

          <h3>Authoritative DNS (BIND9)</h3>
          <label>
            <input
              type="checkbox"
              checked={profile.enable_bind9}
              onChange={(e) =>
                updateProfile({ enable_bind9: e.target.checked })
              }
            />
            Functionaliteit inschakelen
          </label>
          {!profile.enable_bind9 ? (
            <p>bind9 is uitgeschakeld. De container wordt gestopt bij apply.</p>
          ) : null}

          <label>
            Authoritative domeinen (1 per regel)
            <textarea
              disabled={!profile.enable_bind9}
              rows={4}
              value={authoritativeDomainsText}
              onChange={(e) => setAuthoritativeDomainsText(e.target.value)}
              placeholder={"homelab.local\nvoorbeeld.nl"}
            />
          </label>
          <p>
            Alle domeinen in deze lijst worden als zone in BIND9 geladen met
            dezelfde records hieronder.
          </p>

          <label>
            Zone TTL
            <input
              type="number"
              min={60}
              disabled={!profile.enable_bind9}
              value={profile.zone_ttl}
              onChange={(e) =>
                updateProfile({
                  zone_ttl: Number.parseInt(e.target.value, 10) || 60
                })
              }
            />
          </label>

          <label>
            Zone serial
            <input
              type="number"
              min={1}
              disabled={!profile.enable_bind9}
              value={profile.zone_serial ?? 0}
              onChange={(e) =>
                updateProfile({
                  zone_serial: Number.parseInt(e.target.value, 10) || null
                })
              }
            />
          </label>

          <h3>DNS records (handmatig)</h3>
          <p>
            Voeg hier alle gewenste record types toe, zoals A, AAAA, CNAME, TXT,
            MX, NS, SRV, PTR, CAA, NAPTR.
          </p>
          <datalist id="dns-record-type-options">
            {DNS_RECORD_TYPES.map((recordType) => (
              <option key={recordType} value={recordType} />
            ))}
          </datalist>
          {(profile.dns_records ?? []).length === 0 ? (
            <p>Nog geen DNS records ingesteld.</p>
          ) : null}
          {(profile.dns_records ?? []).map((record, index) => (
            <div
              key={`${index}-${record.name}-${record.type}-${record.value}`}
              className="inline-form"
            >
              <label>
                Name
                <input
                  disabled={!profile.enable_bind9}
                  value={record.name}
                  onChange={(e) =>
                    updateDnsRecord(index, { name: e.target.value })
                  }
                  placeholder="api of @"
                />
              </label>
              <label>
                Type
                <input
                  disabled={!profile.enable_bind9}
                  list="dns-record-type-options"
                  value={record.type}
                  onChange={(e) =>
                    updateDnsRecord(index, {
                      type: e.target.value.toUpperCase()
                    })
                  }
                  placeholder="A"
                />
              </label>
              <label>
                Value
                <input
                  disabled={!profile.enable_bind9}
                  value={record.value}
                  onChange={(e) =>
                    updateDnsRecord(index, { value: e.target.value })
                  }
                  placeholder="192.168.50.10 of target.example."
                />
              </label>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!profile.enable_bind9}
                onClick={() => removeDnsRecord(index)}
              >
                Verwijder
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!profile.enable_bind9}
            onClick={addDnsRecord}
          >
            DNS record toevoegen
          </button>

          <h3>Zone defaults</h3>
          <label>
            NS host
            <input
              disabled={!profile.enable_bind9}
              value={profile.nameserver_host}
              onChange={(e) =>
                updateProfile({ nameserver_host: e.target.value })
              }
            />
          </label>
          <label>
            NS IP
            <input
              disabled={!profile.enable_bind9}
              value={profile.nameserver_ip}
              onChange={(e) => updateProfile({ nameserver_ip: e.target.value })}
            />
          </label>
          <label>
            API host
            <input
              disabled={!profile.enable_bind9}
              value={profile.api_host}
              onChange={(e) => updateProfile({ api_host: e.target.value })}
            />
          </label>
          <label>
            API IP
            <input
              disabled={!profile.enable_bind9}
              value={profile.api_ip}
              onChange={(e) => updateProfile({ api_ip: e.target.value })}
            />
          </label>
          <label>
            Dashboard host
            <input
              disabled={!profile.enable_bind9}
              value={profile.dashboard_host}
              onChange={(e) =>
                updateProfile({ dashboard_host: e.target.value })
              }
            />
          </label>
          <label>
            Dashboard IP
            <input
              disabled={!profile.enable_bind9}
              value={profile.dashboard_ip}
              onChange={(e) => updateProfile({ dashboard_ip: e.target.value })}
            />
          </label>

          <h3>NTP</h3>
          <label>
            <input
              type="checkbox"
              checked={profile.enable_ntp}
              onChange={(e) => updateProfile({ enable_ntp: e.target.checked })}
            />
            Functionaliteit inschakelen
          </label>
          {!profile.enable_ntp ? (
            <p>NTP is uitgeschakeld. De container wordt gestopt bij apply.</p>
          ) : null}
          <label>
            NTP servers (1 per regel)
            <textarea
              disabled={!profile.enable_ntp}
              rows={4}
              value={ntpServersText}
              onChange={(e) => setNtpServersText(e.target.value)}
            />
          </label>

          <label>
            <input
              type="checkbox"
              disabled={!profile.enable_ntp}
              checked={profile.ntp_iburst}
              onChange={(e) => updateProfile({ ntp_iburst: e.target.checked })}
            />
            Gebruik iburst
          </label>

          <label>
            <input
              type="checkbox"
              disabled={!profile.enable_ntp}
              checked={profile.ntp_disable_monitor}
              onChange={(e) =>
                updateProfile({ ntp_disable_monitor: e.target.checked })
              }
            />
            Disable monitor
          </label>

          <label>
            <input
              type="checkbox"
              disabled={!profile.enable_ntp}
              checked={profile.ntp_local_clock}
              onChange={(e) =>
                updateProfile({ ntp_local_clock: e.target.checked })
              }
            />
            Local clock fallback
          </label>

          <label>
            Local stratum
            <input
              type="number"
              min={1}
              max={15}
              disabled={!profile.enable_ntp || !profile.ntp_local_clock}
              value={profile.ntp_local_stratum}
              onChange={(e) =>
                updateProfile({
                  ntp_local_stratum: Number.parseInt(e.target.value, 10) || 1
                })
              }
            />
          </label>
        </form>

        <div className="card">
          <h3>Apply Results</h3>
          {results.length === 0 ? (
            <p>Nog geen apply uitgevoerd in deze sessie.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Version</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {results.map((item) => (
                  <tr key={item.service_slug}>
                    <td>{item.service_slug}</td>
                    <td>
                      <StatusBadge value={item.status} />
                    </td>
                    <td>{item.version ?? "-"}</td>
                    <td>{item.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="page-header">
            <h3>Actieve DHCP leases</h3>
            <button className="btn btn-secondary" onClick={onRefreshLeases}>
              Refresh leases
            </button>
          </div>
          {leases.length === 0 ? (
            <p>Geen DHCP leases gevonden.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>IP</th>
                  <th>MAC</th>
                  <th>Hostname</th>
                  <th>Expires</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {leases.map((item) => (
                  <tr
                    key={`${item.mac}-${item.ip}-${item.expires_at ?? "never"}`}
                  >
                    <td>{item.ip}</td>
                    <td className="mono">{item.mac}</td>
                    <td>{item.hostname ?? "-"}</td>
                    <td>{formatExpiry(item.expires_at)}</td>
                    <td>
                      <span
                        className={
                          item.is_expired
                            ? "badge badge-warn"
                            : "badge badge-ok"
                        }
                      >
                        {item.is_expired ? "expired" : "active"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="page-header">
        <h2>Mail Platform</h2>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button className="btn btn-secondary" onClick={onPreviewMailDns}>
            Check DNS setup
          </button>
          <button className="btn" onClick={onApplyMail}>
            Apply Mail Server + Webmail
          </button>
        </div>
      </div>

      <div className="card">
        <p>
          Beheer mail als één geheel: SMTP/IMAP, mailboxen, DKIM/SPF/DMARC en
          webmail.
        </p>
      </div>

      {mailError ? <div className="error">{mailError}</div> : null}
      {mailResult ? <div className="success">{mailResult}</div> : null}

      <div className="two-column">
        <form
          className="card"
          onSubmit={(event) => {
            event.preventDefault();
            onApplyMail();
          }}
        >
          <h3>Mail Services</h3>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_mailserver}
              onChange={(e) =>
                updateMailProfile({ enable_mailserver: e.target.checked })
              }
            />
            Mailserver inschakelen
          </label>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_webmail}
              onChange={(e) =>
                updateMailProfile({ enable_webmail: e.target.checked })
              }
            />
            Webmail inschakelen
          </label>

          <h3>Mail Domein</h3>
          <label>
            Domein
            <input
              value={mailProfile.domain}
              onChange={(e) => updateMailProfile({ domain: e.target.value })}
              placeholder="example.com"
            />
          </label>
          <label>
            Mail hostname
            <input
              value={mailProfile.hostname}
              onChange={(e) => updateMailProfile({ hostname: e.target.value })}
              placeholder="mail"
            />
          </label>
          <label>
            Webmail URL
            <input
              value={mailProfile.webmail_url ?? ""}
              onChange={(e) =>
                updateMailProfile({ webmail_url: e.target.value || null })
              }
              placeholder="https://webmail.example.com"
            />
          </label>
          <label>
            Postmaster e-mail
            <input
              value={mailProfile.postmaster_address}
              onChange={(e) =>
                updateMailProfile({ postmaster_address: e.target.value })
              }
              placeholder="postmaster@example.com"
            />
          </label>

          <h3>Protocol Opties</h3>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_imap}
              onChange={(e) =>
                updateMailProfile({ enable_imap: e.target.checked })
              }
            />
            IMAP
          </label>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_pop3}
              onChange={(e) =>
                updateMailProfile({ enable_pop3: e.target.checked })
              }
            />
            POP3
          </label>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_submission}
              onChange={(e) =>
                updateMailProfile({ enable_submission: e.target.checked })
              }
            />
            SMTP Submission (587)
          </label>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_submissions}
              onChange={(e) =>
                updateMailProfile({ enable_submissions: e.target.checked })
              }
            />
            SMTP Submissions TLS (465)
          </label>
          <label>
            <input
              type="checkbox"
              checked={mailProfile.enable_smtps}
              onChange={(e) =>
                updateMailProfile({ enable_smtps: e.target.checked })
              }
            />
            SMTPS legacy
          </label>

          <h3>DKIM / SPF / DMARC</h3>
          <label>
            DKIM selector
            <input
              value={mailProfile.dkim_selector}
              onChange={(e) =>
                updateMailProfile({ dkim_selector: e.target.value })
              }
              placeholder="mail"
            />
          </label>
          <label>
            DKIM key size
            <input
              type="number"
              min={1024}
              step={1024}
              value={mailProfile.dkim_key_size}
              onChange={(e) =>
                updateMailProfile({
                  dkim_key_size: Number.parseInt(e.target.value, 10) || 2048
                })
              }
            />
          </label>
          <label>
            DKIM public key (optioneel)
            <textarea
              rows={4}
              value={mailProfile.dkim_public_key ?? ""}
              onChange={(e) =>
                updateMailProfile({ dkim_public_key: e.target.value || null })
              }
              placeholder="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A..."
            />
          </label>
          <label>
            SPF policy
            <input
              value={mailProfile.spf_policy}
              onChange={(e) =>
                updateMailProfile({ spf_policy: e.target.value })
              }
              placeholder="v=spf1 mx -all"
            />
          </label>
          <label>
            DMARC policy
            <input
              value={mailProfile.dmarc_policy}
              onChange={(e) =>
                updateMailProfile({ dmarc_policy: e.target.value })
              }
              placeholder="v=DMARC1; p=quarantine; rua=mailto:postmaster@example.com"
            />
          </label>

          <h3>Mailboxen</h3>
          {(mailProfile.mailboxes ?? []).length === 0 ? (
            <p>Nog geen mailboxen ingesteld.</p>
          ) : null}
          {(mailProfile.mailboxes ?? []).map((item, index) => (
            <div key={`${index}-${item.email}`} className="inline-form">
              <label>
                E-mail
                <input
                  value={item.email}
                  onChange={(e) =>
                    updateMailbox(index, {
                      email: e.target.value.toLowerCase()
                    })
                  }
                  placeholder="user@example.com"
                />
              </label>
              <label>
                Wachtwoord
                <input
                  type="password"
                  value={item.password ?? ""}
                  onChange={(e) =>
                    updateMailbox(index, {
                      password: e.target.value || null,
                      has_password: e.target.value ? true : item.has_password
                    })
                  }
                  placeholder={
                    item.has_password
                      ? "Leeg laten om huidig wachtwoord te houden"
                      : "Nieuw wachtwoord"
                  }
                />
              </label>
              <label>
                Display name
                <input
                  value={item.display_name ?? ""}
                  onChange={(e) =>
                    updateMailbox(index, {
                      display_name: e.target.value || null
                    })
                  }
                  placeholder="Naam"
                />
              </label>
              <label>
                Quota MB
                <input
                  type="number"
                  min={10}
                  value={item.quota_mb}
                  onChange={(e) =>
                    updateMailbox(index, {
                      quota_mb: Number.parseInt(e.target.value, 10) || 10
                    })
                  }
                />
              </label>
              <label>
                Aliases (comma separated)
                <input
                  value={(item.aliases ?? []).join(", ")}
                  onChange={(e) =>
                    updateMailbox(index, {
                      aliases: e.target.value
                        .split(",")
                        .map((alias) => alias.trim().toLowerCase())
                        .filter((alias) => alias.length > 0)
                    })
                  }
                  placeholder="info@example.com, sales@example.com"
                />
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={item.enabled}
                  onChange={(e) =>
                    updateMailbox(index, { enabled: e.target.checked })
                  }
                />
                Mailbox actief
              </label>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => removeMailbox(index)}
              >
                Verwijder
              </button>
            </div>
          ))}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={addMailbox}
          >
            Mailbox toevoegen
          </button>
        </form>

        <div className="card">
          <h3>Mail Apply Results</h3>
          {mailResults.length === 0 ? (
            <p>Nog geen mail apply uitgevoerd in deze sessie.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Status</th>
                  <th>Version</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {mailResults.map((item) => (
                  <tr key={`mail-${item.service_slug}`}>
                    <td>{item.service_slug}</td>
                    <td>
                      <StatusBadge value={item.status} />
                    </td>
                    <td>{item.version ?? "-"}</td>
                    <td>{item.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Mail Setup Check</h3>
          {mailSetupIssues.length === 0 ? (
            <p>Nog geen setup-check uitgevoerd.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Level</th>
                  <th>Field</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {mailSetupIssues.map((issue, index) => (
                  <tr key={`mail-issue-${index}-${issue.field}`}>
                    <td>
                      <span
                        className={
                          issue.level === "error"
                            ? "badge badge-err"
                            : "badge badge-warn"
                        }
                      >
                        {issue.level}
                      </span>
                    </td>
                    <td>{issue.field}</td>
                    <td>{issue.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Aanbevolen DNS records</h3>
          {mailSuggestedDnsRecords.length === 0 ? (
            <p>
              Voer een DNS setup-check of mail apply uit om records te tonen.
            </p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {mailSuggestedDnsRecords.map((item, index) => (
                  <tr key={`mail-dns-${index}-${item.name}`}>
                    <td>{item.name}</td>
                    <td>{item.type}</td>
                    <td className="mono">{item.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3>Webmail</h3>
          <label>
            Mailbox voor launch-check (optioneel)
            <input
              value={webmailLaunchMailbox}
              onChange={(e) => setWebmailLaunchMailbox(e.target.value)}
              placeholder="admin@example.com"
            />
          </label>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onOpenWebmail}
          >
            Open webmail
          </button>
          {webmailLaunchUrl ? (
            <p>
              Webmail URL:{" "}
              <a href={webmailLaunchUrl} target="_blank" rel="noreferrer">
                {webmailLaunchUrl}
              </a>
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
