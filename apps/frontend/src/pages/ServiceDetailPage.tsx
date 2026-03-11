import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  applyConfig,
  getService,
  listConfigVersions,
  rollbackConfig,
  runServiceAction,
  validateConfig
} from "../api/services";
import { ConfigVersion, ServiceDetail } from "../types/api";
import { StatusBadge } from "../components/StatusBadge";

const ACTIONS: Array<"start" | "stop" | "restart" | "reload"> = [
  "start",
  "stop",
  "restart",
  "reload"
];

type ConfigMode = "caddy" | "dnsmasq" | "bind9" | "ntp" | "json";

type CaddyFormState = {
  listenPort: number;
  backendUpstream: string;
  frontendUpstream: string;
  enableGzip: boolean;
  autoHttpsDisableRedirects: boolean;
};

type DnsmasqFormState = {
  upstreamServers: string;
  domain: string;
  cacheSize: number;
  dhcpRangeStart: string;
  dhcpRangeEnd: string;
  dhcpLease: string;
  router: string;
};

type Bind9Record = {
  name: string;
  type: string;
  value: string;
};

type Bind9FormState = {
  ttl: number;
  primaryNs: string;
  adminEmail: string;
  serial: number;
  records: Bind9Record[];
};

type NtpFormState = {
  servers: string;
  allowNetworks: string;
  listenInterfaces: string;
  iburst: boolean;
  disableMonitor: boolean;
  localClock: boolean;
  localStratum: number;
};

const DEFAULT_NTP_FORM: NtpFormState = {
  servers: "time.cloudflare.com\ntime.google.com",
  allowNetworks: "",
  listenInterfaces: "",
  iburst: true,
  disableMonitor: true,
  localClock: false,
  localStratum: 10
};

const DEFAULT_CADDY_FORM: CaddyFormState = {
  listenPort: 80,
  backendUpstream: "backend:8000",
  frontendUpstream: "frontend:4173",
  enableGzip: true,
  autoHttpsDisableRedirects: true
};

const DEFAULT_DNSMASQ_FORM: DnsmasqFormState = {
  upstreamServers: "1.1.1.1\n1.0.0.1",
  domain: "homelab.local",
  cacheSize: 1000,
  dhcpRangeStart: "192.168.50.100",
  dhcpRangeEnd: "192.168.50.200",
  dhcpLease: "12h",
  router: "192.168.50.1"
};

const DEFAULT_BIND9_FORM: Bind9FormState = {
  ttl: 3600,
  primaryNs: "ns1.homelab.local.",
  adminEmail: "admin.homelab.local.",
  serial: 2026031001,
  records: [
    { name: "ns1", type: "A", value: "192.168.50.2" },
    { name: "api", type: "A", value: "192.168.50.10" }
  ]
};

function getConfigMode(slug: string): ConfigMode {
  if (slug === "caddy") {
    return "caddy";
  }
  if (slug === "dnsmasq") {
    return "dnsmasq";
  }
  if (slug === "bind9") {
    return "bind9";
  }
  if (slug === "ntp") {
    return "ntp";
  }
  return "json";
}

function splitMultiline(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

function readStringArray(
  config: Record<string, unknown>,
  key: string,
  fallback: string[]
): string[] {
  const value = config[key];
  if (!Array.isArray(value)) {
    return fallback;
  }
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter((item) => item.length > 0);
}

function readString(
  config: Record<string, unknown>,
  key: string,
  fallback: string
): string {
  return typeof config[key] === "string" ? String(config[key]) : fallback;
}

function readBoolean(
  config: Record<string, unknown>,
  key: string,
  fallback: boolean
): boolean {
  return typeof config[key] === "boolean" ? Boolean(config[key]) : fallback;
}

function readNumber(
  config: Record<string, unknown>,
  key: string,
  fallback: number
): number {
  const value = config[key];
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function isConfigObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function caddyConfigToForm(
  config: Record<string, unknown> | null | undefined
): CaddyFormState {
  const safe = config ?? {};
  return {
    listenPort: readNumber(safe, "listen_port", 80),
    backendUpstream: readString(safe, "backend_upstream", "backend:8000"),
    frontendUpstream: readString(safe, "frontend_upstream", "frontend:4173"),
    enableGzip: readBoolean(safe, "enable_gzip", true),
    autoHttpsDisableRedirects: readBoolean(
      safe,
      "auto_https_disable_redirects",
      true
    )
  };
}

function caddyFormToConfig(form: CaddyFormState): Record<string, unknown> {
  return {
    listen_port: form.listenPort,
    backend_upstream: form.backendUpstream.trim(),
    frontend_upstream: form.frontendUpstream.trim(),
    enable_gzip: form.enableGzip,
    auto_https_disable_redirects: form.autoHttpsDisableRedirects
  };
}

function validateCaddyForm(form: CaddyFormState): string | null {
  if (!Number.isInteger(form.listenPort) || form.listenPort < 1 || form.listenPort > 65535) {
    return "Listen poort moet tussen 1 en 65535 liggen.";
  }
  if (!form.backendUpstream.trim()) {
    return "Backend upstream is verplicht.";
  }
  if (!form.frontendUpstream.trim()) {
    return "Frontend upstream is verplicht.";
  }
  return null;
}

function parseDhcpRange(rangeValue: string): {
  start: string;
  end: string;
  lease: string;
} {
  const [start = "", end = "", lease = ""] = rangeValue.split(",").map((item) => item.trim());
  return { start, end, lease };
}

function dnsmasqConfigToForm(
  config: Record<string, unknown> | null | undefined
): DnsmasqFormState {
  const safe = config ?? {};
  const ranges = readStringArray(
    safe,
    "dhcp_ranges",
    [DEFAULT_DNSMASQ_FORM.dhcpRangeStart + "," + DEFAULT_DNSMASQ_FORM.dhcpRangeEnd + "," + DEFAULT_DNSMASQ_FORM.dhcpLease]
  );
  const primaryRange = parseDhcpRange(ranges[0] ?? "");
  return {
    upstreamServers: readStringArray(safe, "upstream_servers", ["1.1.1.1", "1.0.0.1"]).join(
      "\n"
    ),
    domain: readString(safe, "domain", "homelab.local"),
    cacheSize: readNumber(safe, "cache_size", 1000),
    dhcpRangeStart: primaryRange.start || DEFAULT_DNSMASQ_FORM.dhcpRangeStart,
    dhcpRangeEnd: primaryRange.end || DEFAULT_DNSMASQ_FORM.dhcpRangeEnd,
    dhcpLease: primaryRange.lease || DEFAULT_DNSMASQ_FORM.dhcpLease,
    router: readString(safe, "router", DEFAULT_DNSMASQ_FORM.router)
  };
}

function dnsmasqFormToConfig(form: DnsmasqFormState): Record<string, unknown> {
  return {
    upstream_servers: splitMultiline(form.upstreamServers),
    domain: form.domain.trim(),
    cache_size: form.cacheSize,
    dhcp_ranges: [
      `${form.dhcpRangeStart.trim()},${form.dhcpRangeEnd.trim()},${form.dhcpLease.trim()}`
    ],
    router: form.router.trim()
  };
}

function validateDnsmasqForm(form: DnsmasqFormState): string | null {
  if (splitMultiline(form.upstreamServers).length === 0) {
    return "Voeg minimaal 1 upstream DNS server toe.";
  }
  if (!form.domain.trim()) {
    return "Domain is verplicht.";
  }
  if (!Number.isInteger(form.cacheSize) || form.cacheSize < 10) {
    return "Cache size moet minimaal 10 zijn.";
  }
  if (!form.dhcpRangeStart.trim() || !form.dhcpRangeEnd.trim() || !form.dhcpLease.trim()) {
    return "DHCP range start, end en lease zijn verplicht.";
  }
  return null;
}

function readBind9Records(config: Record<string, unknown>): Bind9Record[] {
  const value = config["records"];
  if (!Array.isArray(value)) {
    return DEFAULT_BIND9_FORM.records;
  }

  const parsed = value
    .map((item) => {
      if (!isConfigObject(item)) {
        return null;
      }
      const name = typeof item["name"] === "string" ? item["name"].trim() : "";
      const type = typeof item["type"] === "string" ? item["type"].trim().toUpperCase() : "";
      const recordValue =
        typeof item["value"] === "string" ? item["value"].trim() : "";
      if (!name || !type || !recordValue) {
        return null;
      }
      return { name, type, value: recordValue };
    })
    .filter((item): item is Bind9Record => item !== null);

  return parsed.length > 0 ? parsed : DEFAULT_BIND9_FORM.records;
}

function bind9ConfigToForm(
  config: Record<string, unknown> | null | undefined
): Bind9FormState {
  const safe = config ?? {};
  return {
    ttl: readNumber(safe, "ttl", DEFAULT_BIND9_FORM.ttl),
    primaryNs: readString(safe, "primary_ns", DEFAULT_BIND9_FORM.primaryNs),
    adminEmail: readString(safe, "admin_email", DEFAULT_BIND9_FORM.adminEmail),
    serial: readNumber(safe, "serial", DEFAULT_BIND9_FORM.serial),
    records: readBind9Records(safe)
  };
}

function bind9FormToConfig(form: Bind9FormState): Record<string, unknown> {
  return {
    ttl: form.ttl,
    primary_ns: form.primaryNs.trim(),
    admin_email: form.adminEmail.trim(),
    serial: form.serial,
    records: form.records
      .map((record) => ({
        name: record.name.trim(),
        type: record.type.trim().toUpperCase(),
        value: record.value.trim()
      }))
      .filter((record) => record.name && record.type && record.value)
  };
}

function validateBind9Form(form: Bind9FormState): string | null {
  if (!Number.isInteger(form.ttl) || form.ttl < 60) {
    return "TTL moet minimaal 60 seconden zijn.";
  }
  if (!Number.isInteger(form.serial) || form.serial < 1) {
    return "Serial moet een positief getal zijn.";
  }
  if (!form.primaryNs.trim()) {
    return "Primary NS is verplicht.";
  }
  if (!form.adminEmail.trim()) {
    return "Admin email is verplicht.";
  }
  const validRecords = form.records.filter(
    (record) => record.name.trim() && record.type.trim() && record.value.trim()
  );
  if (validRecords.length === 0) {
    return "Voeg minimaal 1 DNS record toe.";
  }
  return null;
}

function ntpConfigToForm(
  config: Record<string, unknown> | null | undefined
): NtpFormState {
  const safe = config ?? {};
  return {
    servers: readStringArray(safe, "servers", ["time.cloudflare.com", "time.google.com"]).join(
      "\n"
    ),
    allowNetworks: readStringArray(safe, "allow_networks", []).join("\n"),
    listenInterfaces: readStringArray(safe, "listen_interfaces", []).join("\n"),
    iburst: readBoolean(safe, "iburst", true),
    disableMonitor: readBoolean(safe, "disable_monitor", true),
    localClock: readBoolean(safe, "local_clock", false),
    localStratum: readNumber(safe, "local_stratum", 10)
  };
}

function ntpFormToConfig(form: NtpFormState): Record<string, unknown> {
  return {
    servers: splitMultiline(form.servers),
    allow_networks: splitMultiline(form.allowNetworks),
    listen_interfaces: splitMultiline(form.listenInterfaces),
    iburst: form.iburst,
    disable_monitor: form.disableMonitor,
    local_clock: form.localClock,
    local_stratum: form.localStratum
  };
}

function validateNtpForm(form: NtpFormState): string | null {
  const servers = splitMultiline(form.servers);
  if (servers.length === 0 && !form.localClock) {
    return "Voeg minimaal 1 NTP-server toe of zet Local Clock fallback aan.";
  }
  if (!Number.isInteger(form.localStratum) || form.localStratum < 1 || form.localStratum > 15) {
    return "Local stratum moet tussen 1 en 15 liggen.";
  }
  return null;
}

export function ServiceDetailPage() {
  const { slug = "" } = useParams();
  const [service, setService] = useState<ServiceDetail | null>(null);
  const [versions, setVersions] = useState<ConfigVersion[]>([]);
  const [rawConfig, setRawConfig] = useState("");
  const [formConfigText, setFormConfigText] = useState('{\n  "records": []\n}');
  const [caddyForm, setCaddyForm] = useState<CaddyFormState>(DEFAULT_CADDY_FORM);
  const [dnsmasqForm, setDnsmasqForm] =
    useState<DnsmasqFormState>(DEFAULT_DNSMASQ_FORM);
  const [bind9Form, setBind9Form] = useState<Bind9FormState>(DEFAULT_BIND9_FORM);
  const [ntpForm, setNtpForm] = useState<NtpFormState>(DEFAULT_NTP_FORM);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const configMode = getConfigMode(service?.service.slug ?? slug);
  const usesGuidedForm = configMode !== "json";

  const parsedConfig = useMemo(() => {
    if (configMode === "caddy") {
      return caddyFormToConfig(caddyForm);
    }
    if (configMode === "dnsmasq") {
      return dnsmasqFormToConfig(dnsmasqForm);
    }
    if (configMode === "bind9") {
      return bind9FormToConfig(bind9Form);
    }
    if (configMode === "ntp") {
      return ntpFormToConfig(ntpForm);
    }
    try {
      return JSON.parse(formConfigText) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [bind9Form, caddyForm, configMode, dnsmasqForm, formConfigText, ntpForm]);

  const reload = useCallback(async () => {
    const [serviceData, versionData] = await Promise.all([
      getService(slug),
      listConfigVersions(slug)
    ]);
    setService(serviceData);
    setVersions(versionData);
  }, [slug]);

  useEffect(() => {
    reload().catch((err) =>
      setError(err instanceof Error ? err.message : "Failed to load service")
    );
  }, [reload]);

  useEffect(() => {
    if (!service) {
      return;
    }

    const configJson = service.active_config?.config_json as
      | Record<string, unknown>
      | undefined;
    setRawConfig(service.active_config?.raw_config ?? "");
    const mode = getConfigMode(service.service.slug);
    if (mode === "caddy") {
      setCaddyForm(caddyConfigToForm(configJson));
      return;
    }
    if (mode === "dnsmasq") {
      setDnsmasqForm(dnsmasqConfigToForm(configJson));
      return;
    }
    if (mode === "bind9") {
      setBind9Form(bind9ConfigToForm(configJson));
      return;
    }
    if (mode === "ntp") {
      setNtpForm(ntpConfigToForm(configJson));
      return;
    }
    if (configJson) {
      setFormConfigText(JSON.stringify(configJson, null, 2));
    }
  }, [service]);

  const updateBind9Record = (
    index: number,
    field: keyof Bind9Record,
    value: string
  ) => {
    setBind9Form((prev) => ({
      ...prev,
      records: prev.records.map((record, recordIndex) =>
        recordIndex === index ? { ...record, [field]: value } : record
      )
    }));
  };

  const addBind9Record = () => {
    setBind9Form((prev) => ({
      ...prev,
      records: [...prev.records, { name: "", type: "A", value: "" }]
    }));
  };

  const removeBind9Record = (index: number) => {
    setBind9Form((prev) => ({
      ...prev,
      records:
        prev.records.length > 1
          ? prev.records.filter((_, recordIndex) => recordIndex !== index)
          : prev.records
    }));
  };

  const validateGuidedForm = (): string | null => {
    if (configMode === "caddy") {
      return validateCaddyForm(caddyForm);
    }
    if (configMode === "dnsmasq") {
      return validateDnsmasqForm(dnsmasqForm);
    }
    if (configMode === "bind9") {
      return validateBind9Form(bind9Form);
    }
    if (configMode === "ntp") {
      return validateNtpForm(ntpForm);
    }
    return null;
  };

  const onAction = async (action: "start" | "stop" | "restart" | "reload") => {
    setError(null);
    setResult(null);
    try {
      const response = await runServiceAction(slug, action);
      setResult(`${action}: ${response.message}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${action} failed`);
    }
  };

  const onValidate = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setResult(null);
    const guidedError = validateGuidedForm();
    if (guidedError) {
      setError(guidedError);
      return;
    }
    if (!parsedConfig) {
      setError("Form JSON is invalid");
      return;
    }
    try {
      const response = await validateConfig(slug, parsedConfig, rawConfig);
      if (response.valid) {
        setResult("Validation passed");
      } else {
        setError(`Validation failed: ${response.errors.join(", ")}`);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Validation request failed"
      );
    }
  };

  const onApply = async () => {
    setError(null);
    setResult(null);
    const guidedError = validateGuidedForm();
    if (guidedError) {
      setError(guidedError);
      return;
    }
    if (!parsedConfig) {
      setError("Form JSON is invalid");
      return;
    }
    try {
      const response = await applyConfig(slug, parsedConfig, rawConfig);
      setResult(
        `Applied version ${response.version.version}: ${response.version.apply_message}`
      );
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Apply failed");
    }
  };

  const onRollback = async (versionId: string) => {
    setError(null);
    setResult(null);
    try {
      const response = await rollbackConfig(slug, versionId);
      setResult(`Rolled back via version ${response.version}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rollback failed");
    }
  };

  if (!service) {
    return <div>Loading service...</div>;
  }

  return (
    <section>
      <div className="page-header">
        <h2>{service.service.name}</h2>
        <StatusBadge value={service.service.health || service.service.state} />
      </div>

      <div className="action-row">
        {ACTIONS.map((action) => (
          <button
            key={action}
            className="btn btn-secondary"
            onClick={() => onAction(action)}
          >
            {action}
          </button>
        ))}
      </div>

      {error ? <div className="error">{error}</div> : null}
      {result ? <div className="success">{result}</div> : null}

      <div className="two-column">
        <form className="card" onSubmit={onValidate}>
          {configMode === "caddy" ? (
            <>
              <h3>Caddy Instellingen</h3>
              <p>Duidelijke velden voor reverse proxy instellingen.</p>

              <label>
                Listen poort
                <input
                  type="number"
                  min={1}
                  max={65535}
                  value={caddyForm.listenPort}
                  onChange={(e) =>
                    setCaddyForm((prev) => ({
                      ...prev,
                      listenPort: Number.parseInt(e.target.value, 10) || 80
                    }))
                  }
                />
              </label>

              <label>
                Backend upstream
                <input
                  value={caddyForm.backendUpstream}
                  onChange={(e) =>
                    setCaddyForm((prev) => ({
                      ...prev,
                      backendUpstream: e.target.value
                    }))
                  }
                  placeholder="backend:8000"
                />
              </label>

              <label>
                Frontend upstream
                <input
                  value={caddyForm.frontendUpstream}
                  onChange={(e) =>
                    setCaddyForm((prev) => ({
                      ...prev,
                      frontendUpstream: e.target.value
                    }))
                  }
                  placeholder="frontend:4173"
                />
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={caddyForm.enableGzip}
                  onChange={(e) =>
                    setCaddyForm((prev) => ({
                      ...prev,
                      enableGzip: e.target.checked
                    }))
                  }
                />
                Gzip compression inschakelen
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={caddyForm.autoHttpsDisableRedirects}
                  onChange={(e) =>
                    setCaddyForm((prev) => ({
                      ...prev,
                      autoHttpsDisableRedirects: e.target.checked
                    }))
                  }
                />
                HTTPS redirects uitschakelen (Synology/NAT setup)
              </label>
            </>
          ) : configMode === "dnsmasq" ? (
            <>
              <h3>dnsmasq Instellingen</h3>
              <p>Beheer DNS en DHCP met duidelijke velden.</p>

              <label>
                Upstream DNS servers (1 per regel)
                <textarea
                  value={dnsmasqForm.upstreamServers}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({
                      ...prev,
                      upstreamServers: e.target.value
                    }))
                  }
                  rows={4}
                />
              </label>

              <label>
                Domain
                <input
                  value={dnsmasqForm.domain}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({ ...prev, domain: e.target.value }))
                  }
                  placeholder="homelab.local"
                />
              </label>

              <label>
                Cache size
                <input
                  type="number"
                  min={10}
                  value={dnsmasqForm.cacheSize}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({
                      ...prev,
                      cacheSize: Number.parseInt(e.target.value, 10) || 10
                    }))
                  }
                />
              </label>

              <h3>DHCP range</h3>
              <label>
                Start IP
                <input
                  value={dnsmasqForm.dhcpRangeStart}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({
                      ...prev,
                      dhcpRangeStart: e.target.value
                    }))
                  }
                  placeholder="192.168.50.100"
                />
              </label>

              <label>
                End IP
                <input
                  value={dnsmasqForm.dhcpRangeEnd}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({
                      ...prev,
                      dhcpRangeEnd: e.target.value
                    }))
                  }
                  placeholder="192.168.50.200"
                />
              </label>

              <label>
                Lease time
                <input
                  value={dnsmasqForm.dhcpLease}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({ ...prev, dhcpLease: e.target.value }))
                  }
                  placeholder="12h"
                />
              </label>

              <label>
                Router IP (optioneel)
                <input
                  value={dnsmasqForm.router}
                  onChange={(e) =>
                    setDnsmasqForm((prev) => ({ ...prev, router: e.target.value }))
                  }
                  placeholder="192.168.50.1"
                />
              </label>
            </>
          ) : configMode === "bind9" ? (
            <>
              <h3>BIND9 Instellingen</h3>
              <p>Beheer zone-instellingen en records zonder ruwe JSON.</p>

              <label>
                TTL (seconds)
                <input
                  type="number"
                  min={60}
                  value={bind9Form.ttl}
                  onChange={(e) =>
                    setBind9Form((prev) => ({
                      ...prev,
                      ttl: Number.parseInt(e.target.value, 10) || 60
                    }))
                  }
                />
              </label>

              <label>
                Primary NS
                <input
                  value={bind9Form.primaryNs}
                  onChange={(e) =>
                    setBind9Form((prev) => ({ ...prev, primaryNs: e.target.value }))
                  }
                  placeholder="ns1.homelab.local."
                />
              </label>

              <label>
                Admin email (BIND format)
                <input
                  value={bind9Form.adminEmail}
                  onChange={(e) =>
                    setBind9Form((prev) => ({ ...prev, adminEmail: e.target.value }))
                  }
                  placeholder="admin.homelab.local."
                />
              </label>

              <label>
                Serial
                <input
                  type="number"
                  min={1}
                  value={bind9Form.serial}
                  onChange={(e) =>
                    setBind9Form((prev) => ({
                      ...prev,
                      serial: Number.parseInt(e.target.value, 10) || 1
                    }))
                  }
                />
              </label>

              <h3>DNS records</h3>
              {bind9Form.records.map((record, index) => (
                <div key={`${index}-${record.name}-${record.type}`} className="inline-form">
                  <label>
                    Name
                    <input
                      value={record.name}
                      onChange={(e) => updateBind9Record(index, "name", e.target.value)}
                      placeholder="api"
                    />
                  </label>
                  <label>
                    Type
                    <select
                      value={record.type}
                      onChange={(e) => updateBind9Record(index, "type", e.target.value)}
                    >
                      <option value="A">A</option>
                      <option value="AAAA">AAAA</option>
                      <option value="CNAME">CNAME</option>
                      <option value="TXT">TXT</option>
                      <option value="MX">MX</option>
                      <option value="NS">NS</option>
                      <option value="SRV">SRV</option>
                      <option value="PTR">PTR</option>
                    </select>
                  </label>
                  <label>
                    Value
                    <input
                      value={record.value}
                      onChange={(e) => updateBind9Record(index, "value", e.target.value)}
                      placeholder="192.168.50.10"
                    />
                  </label>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => removeBind9Record(index)}
                  >
                    Verwijder
                  </button>
                </div>
              ))}
              <button type="button" className="btn btn-secondary" onClick={addBind9Record}>
                Record toevoegen
              </button>
            </>
          ) : configMode === "ntp" ? (
            <>
              <h3>NTP Instellingen</h3>
              <p>Stel hier NTP duidelijk in zonder losse JSON velden.</p>

              <label>
                Upstream NTP servers (1 per regel)
                <textarea
                  value={ntpForm.servers}
                  onChange={(e) =>
                    setNtpForm((prev) => ({ ...prev, servers: e.target.value }))
                  }
                  rows={6}
                />
              </label>

              <label>
                Toegestane client netwerken (CIDR, optioneel, 1 per regel)
                <textarea
                  value={ntpForm.allowNetworks}
                  onChange={(e) =>
                    setNtpForm((prev) => ({
                      ...prev,
                      allowNetworks: e.target.value
                    }))
                  }
                  rows={4}
                />
              </label>

              <label>
                Listen interfaces (optioneel, 1 per regel)
                <textarea
                  value={ntpForm.listenInterfaces}
                  onChange={(e) =>
                    setNtpForm((prev) => ({
                      ...prev,
                      listenInterfaces: e.target.value
                    }))
                  }
                  rows={3}
                />
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={ntpForm.iburst}
                  onChange={(e) =>
                    setNtpForm((prev) => ({ ...prev, iburst: e.target.checked }))
                  }
                />
                Gebruik iburst voor snellere initiële sync
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={ntpForm.disableMonitor}
                  onChange={(e) =>
                    setNtpForm((prev) => ({
                      ...prev,
                      disableMonitor: e.target.checked
                    }))
                  }
                />
                Disable monitor (aanbevolen)
              </label>

              <label>
                <input
                  type="checkbox"
                  checked={ntpForm.localClock}
                  onChange={(e) =>
                    setNtpForm((prev) => ({ ...prev, localClock: e.target.checked }))
                  }
                />
                Local Clock fallback activeren
              </label>

              <label>
                Local stratum (1-15)
                <input
                  type="number"
                  min={1}
                  max={15}
                  value={ntpForm.localStratum}
                  onChange={(e) =>
                    setNtpForm((prev) => ({
                      ...prev,
                      localStratum: Number.parseInt(e.target.value, 10) || 1
                    }))
                  }
                  disabled={!ntpForm.localClock}
                />
              </label>
            </>
          ) : (
            <>
              <h3>Expert Config (JSON)</h3>
              <textarea
                value={formConfigText}
                onChange={(e) => setFormConfigText(e.target.value)}
                rows={12}
              />
              <h3>Raw Config Override</h3>
              <textarea
                value={rawConfig}
                onChange={(e) => setRawConfig(e.target.value)}
                rows={12}
              />
            </>
          )}
          {usesGuidedForm ? (
            <>
              <h3>Raw Config Override (Optioneel)</h3>
              <p>Laat leeg om bovenstaande velden te gebruiken.</p>
              <textarea
                value={rawConfig}
                onChange={(e) => setRawConfig(e.target.value)}
                rows={8}
              />
            </>
          ) : null}
          <div className="action-row">
            <button type="submit" className="btn btn-secondary">
              Validate
            </button>
            <button type="button" className="btn" onClick={onApply}>
              Apply
            </button>
          </div>
        </form>

        <div className="card">
          <h3>Config Versions</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Status</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((version) => (
                <tr key={version.id}>
                  <td>{version.version}</td>
                  <td>
                    <StatusBadge value={version.apply_status} />
                  </td>
                  <td>{new Date(version.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="btn btn-secondary"
                      onClick={() => onRollback(version.id)}
                    >
                      Rollback
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
