import { apiRequest } from "./client";
import { AuditEvent } from "../types/api";

export function listAudit(limit = 200): Promise<{ items: AuditEvent[] }> {
  return apiRequest<{ items: AuditEvent[] }>(`/audit?limit=${limit}`);
}
