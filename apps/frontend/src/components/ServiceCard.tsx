import { Link } from "react-router-dom";
import { ServiceState } from "../types/api";
import { StatusBadge } from "./StatusBadge";

interface ServiceCardProps {
  service: ServiceState;
}

export function ServiceCard({ service }: ServiceCardProps) {
  return (
    <Link className="service-card" to={`/services/${service.slug}`}>
      <div className="service-card-header">
        <h3>{service.name}</h3>
        <StatusBadge value={service.health || service.state} />
      </div>
      <p>{service.slug}</p>
      <p>State: {service.state}</p>
      <p>
        Ports: {service.ports.length > 0 ? service.ports.join(", ") : "none"}
      </p>
      <p>
        Last config:{" "}
        {service.last_config_version
          ? `v${service.last_config_version}`
          : "n/a"}
      </p>
    </Link>
  );
}
