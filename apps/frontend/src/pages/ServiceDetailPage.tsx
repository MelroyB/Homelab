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

const ACTIONS: Array<"start" | "stop" | "restart" | "reload"> = ["start", "stop", "restart", "reload"];

export function ServiceDetailPage() {
  const { slug = "" } = useParams();
  const [service, setService] = useState<ServiceDetail | null>(null);
  const [versions, setVersions] = useState<ConfigVersion[]>([]);
  const [rawConfig, setRawConfig] = useState("");
  const [formConfigText, setFormConfigText] = useState('{\n  "records": []\n}');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const parsedConfig = useMemo(() => {
    try {
      return JSON.parse(formConfigText) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [formConfigText]);

  const reload = useCallback(async () => {
    const [serviceData, versionData] = await Promise.all([getService(slug), listConfigVersions(slug)]);
    setService(serviceData);
    setVersions(versionData);
  }, [slug]);

  useEffect(() => {
    reload().catch((err) => setError(err instanceof Error ? err.message : "Failed to load service"));
  }, [reload]);

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
      setError(err instanceof Error ? err.message : "Validation request failed");
    }
  };

  const onApply = async () => {
    setError(null);
    setResult(null);
    if (!parsedConfig) {
      setError("Form JSON is invalid");
      return;
    }
    try {
      const response = await applyConfig(slug, parsedConfig, rawConfig);
      setResult(`Applied version ${response.version.version}: ${response.version.apply_message}`);
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
          <button key={action} className="btn btn-secondary" onClick={() => onAction(action)}>
            {action}
          </button>
        ))}
      </div>

      {error ? <div className="error">{error}</div> : null}
      {result ? <div className="success">{result}</div> : null}

      <div className="two-column">
        <form className="card" onSubmit={onValidate}>
          <h3>Form Config (JSON)</h3>
          <textarea value={formConfigText} onChange={(e) => setFormConfigText(e.target.value)} rows={12} />
          <h3>Raw Config Override</h3>
          <textarea value={rawConfig} onChange={(e) => setRawConfig(e.target.value)} rows={12} />
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
                    <button className="btn btn-secondary" onClick={() => onRollback(version.id)}>
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
