import { useEffect, useState } from "react";
import {
  applyNetworkStackProfile,
  getDhcpLeases,
  getNetworkStackProfile
} from "../api/settings";
import {
  DhcpLeaseEntry,
  DhcpReservation,
  NetworkServiceApplyResult,
  NetworkStackProfile
} from "../types/api";
import { StatusBadge } from "../components/StatusBadge";

function splitLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
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
  const [dnsServersText, setDnsServersText] = useState("");
  const [dhcpDnsServersText, setDhcpDnsServersText] = useState("");
  const [dhcpNtpServersText, setDhcpNtpServersText] = useState("");
  const [ntpServersText, setNtpServersText] = useState("");
  const [leases, setLeases] = useState<DhcpLeaseEntry[]>([]);
  const [results, setResults] = useState<NetworkServiceApplyResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const reload = async () => {
    const [profileData, leaseData] = await Promise.all([
      getNetworkStackProfile(),
      getDhcpLeases()
    ]);
    setProfile(profileData);
    setDnsServersText(profileData.dns_upstream_servers.join("\n"));
    setDhcpDnsServersText(profileData.dhcp_dns_servers.join("\n"));
    setDhcpNtpServersText(profileData.dhcp_ntp_servers.join("\n"));
    setNtpServersText(profileData.ntp_servers.join("\n"));
    setLeases(leaseData.items);
  };

  useEffect(() => {
    reload().catch((err) =>
      setError(
        err instanceof Error ? err.message : "Failed to load network profile"
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
        (item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)
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
    const ntpServers = splitLines(ntpServersText);

    if (dnsServers.length === 0) {
      setError("Voeg minimaal 1 DNS upstream server toe.");
      return;
    }
    if (ntpServers.length === 0 && !profile.ntp_local_clock) {
      setError("Voeg minimaal 1 NTP server toe of activeer local clock fallback.");
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
        (item) => item.mac || item.ip || item.hostname !== null || item.lease !== null
      );

    for (const reservation of reservations) {
      if (!reservation.mac || !reservation.ip) {
        setError(
          "Elke DHCP reservering moet minimaal MAC en IP bevatten."
        );
        return;
      }
    }

    try {
      const response = await applyNetworkStackProfile({
        ...profile,
        dns_upstream_servers: dnsServers,
        dhcp_dns_servers: dhcpDnsServers,
        dhcp_ntp_servers: dhcpNtpServers,
        ntp_servers: ntpServers,
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

  if (!profile) {
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
            Domain
            <input
              value={profile.domain}
              onChange={(e) => updateProfile({ domain: e.target.value })}
            />
          </label>

          <label>
            Router IP
            <input
              value={profile.router_ip}
              onChange={(e) => updateProfile({ router_ip: e.target.value })}
            />
          </label>

          <label>
            DHCP start
            <input
              value={profile.dhcp_range_start}
              onChange={(e) =>
                updateProfile({ dhcp_range_start: e.target.value })
              }
            />
          </label>

          <label>
            DHCP end
            <input
              value={profile.dhcp_range_end}
              onChange={(e) => updateProfile({ dhcp_range_end: e.target.value })}
            />
          </label>

          <label>
            DHCP lease
            <input
              value={profile.dhcp_lease}
              onChange={(e) => updateProfile({ dhcp_lease: e.target.value })}
              placeholder="12h"
            />
          </label>

          <label>
            <input
              type="checkbox"
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
              rows={3}
              value={dhcpDnsServersText}
              onChange={(e) => setDhcpDnsServersText(e.target.value)}
            />
          </label>

          <label>
            DHCP option NTP servers (1 per regel)
            <textarea
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
            <div key={`${index}-${item.mac}-${item.ip}`} className="inline-form">
              <label>
                MAC
                <input
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
                  value={item.hostname ?? ""}
                  onChange={(e) =>
                    updateReservation(index, { hostname: e.target.value || null })
                  }
                  placeholder="printer"
                />
              </label>
              <label>
                Lease
                <input
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
                onClick={() => removeReservation(index)}
              >
                Verwijder
              </button>
            </div>
          ))}
          <button type="button" className="btn btn-secondary" onClick={addReservation}>
            Reservering toevoegen
          </button>

          <h3>Authoritative DNS (BIND9)</h3>

          <label>
            Zone TTL
            <input
              type="number"
              min={60}
              value={profile.zone_ttl}
              onChange={(e) =>
                updateProfile({ zone_ttl: Number.parseInt(e.target.value, 10) || 60 })
              }
            />
          </label>

          <label>
            Zone serial
            <input
              type="number"
              min={1}
              value={profile.zone_serial ?? 0}
              onChange={(e) =>
                updateProfile({
                  zone_serial: Number.parseInt(e.target.value, 10) || null
                })
              }
            />
          </label>

          <h3>Core host records</h3>
          <label>
            NS host
            <input
              value={profile.nameserver_host}
              onChange={(e) =>
                updateProfile({ nameserver_host: e.target.value })
              }
            />
          </label>
          <label>
            NS IP
            <input
              value={profile.nameserver_ip}
              onChange={(e) => updateProfile({ nameserver_ip: e.target.value })}
            />
          </label>
          <label>
            API host
            <input
              value={profile.api_host}
              onChange={(e) => updateProfile({ api_host: e.target.value })}
            />
          </label>
          <label>
            API IP
            <input
              value={profile.api_ip}
              onChange={(e) => updateProfile({ api_ip: e.target.value })}
            />
          </label>
          <label>
            Dashboard host
            <input
              value={profile.dashboard_host}
              onChange={(e) =>
                updateProfile({ dashboard_host: e.target.value })
              }
            />
          </label>
          <label>
            Dashboard IP
            <input
              value={profile.dashboard_ip}
              onChange={(e) => updateProfile({ dashboard_ip: e.target.value })}
            />
          </label>

          <h3>NTP</h3>
          <label>
            NTP servers (1 per regel)
            <textarea
              rows={4}
              value={ntpServersText}
              onChange={(e) => setNtpServersText(e.target.value)}
            />
          </label>

          <label>
            <input
              type="checkbox"
              checked={profile.ntp_iburst}
              onChange={(e) => updateProfile({ ntp_iburst: e.target.checked })}
            />
            Gebruik iburst
          </label>

          <label>
            <input
              type="checkbox"
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
              disabled={!profile.ntp_local_clock}
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
                  <tr key={`${item.mac}-${item.ip}-${item.expires_at ?? "never"}`}>
                    <td>{item.ip}</td>
                    <td className="mono">{item.mac}</td>
                    <td>{item.hostname ?? "-"}</td>
                    <td>{formatExpiry(item.expires_at)}</td>
                    <td>
                      <span
                        className={item.is_expired ? "badge badge-warn" : "badge badge-ok"}
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
    </section>
  );
}
