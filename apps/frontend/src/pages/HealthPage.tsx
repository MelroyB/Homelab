import { useEffect, useState } from "react";
import { getReadiness } from "../api/services";
import { ReadinessResponse } from "../types/api";
import { StatusBadge } from "../components/StatusBadge";

export function HealthPage() {
  const [status, setStatus] = useState<ReadinessResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReadiness()
      .then(setStatus)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Failed to load health status"
        )
      );
  }, []);

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!status) {
    return <div>Loading health checks...</div>;
  }

  return (
    <section>
      <div className="page-header">
        <h2>Readiness</h2>
        <StatusBadge value={status.status} />
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Check</th>
              <th>Status</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {status.checks.map((check) => (
              <tr key={check.name}>
                <td>{check.name}</td>
                <td>
                  <StatusBadge value={check.status} />
                </td>
                <td>{check.details || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
