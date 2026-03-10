import { useEffect, useState } from "react";
import { listServices } from "../api/services";
import { ServiceCard } from "../components/ServiceCard";
import { ServiceState } from "../types/api";

export function ServicesPage() {
  const [services, setServices] = useState<ServiceState[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listServices()
      .then(setServices)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load services"));
  }, []);

  return (
    <section>
      <h2>Managed Services</h2>
      {error ? <div className="error">{error}</div> : null}
      <div className="service-grid">
        {services.map((service) => (
          <ServiceCard key={service.slug} service={service} />
        ))}
      </div>
    </section>
  );
}
