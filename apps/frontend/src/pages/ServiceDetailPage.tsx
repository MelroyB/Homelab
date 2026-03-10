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
  const [ntpForm, setNtpForm] = useState<NtpFormState>(DEFAULT_NTP_FORM);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isNtpService = service?.service.slug === "ntp";

  const parsedConfig = useMemo(() => {
    if (isNtpService) {
      return ntpFormToConfig(ntpForm);
    }
    try {
      return JSON.parse(formConfigText) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [formConfigText, isNtpService, ntpForm]);

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
    if (!service || service.service.slug !== "ntp") {
      return;
    }
    const configJson = service.active_config?.config_json as
      | Record<string, unknown>
      | undefined;
    setNtpForm(ntpConfigToForm(configJson));
    setRawConfig(service.active_config?.raw_config ?? "");
  }, [service]);

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
    if (isNtpService) {
      const ntpError = validateNtpForm(ntpForm);
      if (ntpError) {
        setError(ntpError);
        return;
      }
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
    if (isNtpService) {
      const ntpError = validateNtpForm(ntpForm);
      if (ntpError) {
        setError(ntpError);
        return;
      }
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
          {isNtpService ? (
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

              <h3>Raw Config Override (Optioneel)</h3>
              <textarea
                value={rawConfig}
                onChange={(e) => setRawConfig(e.target.value)}
                rows={8}
              />
            </>
          ) : (
            <>
              <h3>Form Config (JSON)</h3>
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
