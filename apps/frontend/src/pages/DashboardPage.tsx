import { useEffect, useState } from "react";
import { getDashboardOverview } from "../api/services";
import { ServiceCard } from "../components/ServiceCard";
import { DashboardOverview } from "../types/api";

export function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardOverview()
      .then(setData)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      });
  }, []);

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!data) {
    return <div>Loading dashboard...</div>;
  }

  return (
    <section>
      <div className="stats-grid">
        <article className="stat-card">
          <h3>Services</h3>
          <strong>{data.service_count}</strong>
        </article>
        <article className="stat-card">
          <h3>Healthy</h3>
          <strong>{data.healthy_service_count}</strong>
        </article>
        <article className="stat-card">
          <h3>Degraded</h3>
          <strong>{data.degraded_service_count}</strong>
        </article>
      </div>

      <h2>Service status</h2>
      <div className="service-grid">
        {data.services.map((service) => (
          <ServiceCard key={service.slug} service={service} />
        ))}
      </div>
    </section>
  );
}
