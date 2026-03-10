interface StatusBadgeProps {
  value: string;
}

export function StatusBadge({ value }: StatusBadgeProps) {
  const normalized = value.toLowerCase();
  const className =
    normalized === "healthy" || normalized === "running"
      ? "badge badge-ok"
      : normalized === "degraded" || normalized === "starting"
        ? "badge badge-warn"
        : "badge badge-err";

  return <span className={className}>{value}</span>;
}
