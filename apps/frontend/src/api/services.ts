import { apiRequest } from "./client";
import {
  ConfigApplyResponse,
  ConfigValidationResponse,
  ConfigVersion,
  DashboardOverview,
  ReadinessResponse,
  ServiceDetail,
  ServiceState
} from "../types/api";

export function getDashboardOverview(): Promise<DashboardOverview> {
  return apiRequest<DashboardOverview>("/dashboard/overview");
}

export function listServices(): Promise<ServiceState[]> {
  return apiRequest<ServiceState[]>("/services");
}

export function getService(slug: string): Promise<ServiceDetail> {
  return apiRequest<ServiceDetail>(`/services/${slug}`);
}

export function runServiceAction(slug: string, action: "start" | "stop" | "restart" | "reload") {
  return apiRequest<{ status: string; message: string }>(`/services/${slug}/actions`, {
    method: "POST",
    body: JSON.stringify({ action })
  });
}

export function listConfigVersions(slug: string): Promise<ConfigVersion[]> {
  return apiRequest<ConfigVersion[]>(`/services/${slug}/configs`);
}

export function validateConfig(slug: string, config_json: Record<string, unknown>, raw_config: string) {
  return apiRequest<ConfigValidationResponse>(`/services/${slug}/configs/validate`, {
    method: "POST",
    body: JSON.stringify({ config_json, raw_config })
  });
}

export function applyConfig(slug: string, config_json: Record<string, unknown>, raw_config: string) {
  return apiRequest<ConfigApplyResponse>(`/services/${slug}/configs/apply`, {
    method: "POST",
    body: JSON.stringify({ config_json, raw_config, auto_reload: true })
  });
}

export function rollbackConfig(slug: string, versionId: string) {
  return apiRequest<ConfigVersion>(`/services/${slug}/configs/${versionId}/rollback`, {
    method: "POST"
  });
}

export function getServiceLogs(slug: string, tail = 200): Promise<{ service: string; logs: string }> {
  return apiRequest<{ service: string; logs: string }>(`/services/${slug}/logs?tail=${tail}`);
}

export function getReadiness(): Promise<ReadinessResponse> {
  return apiRequest<ReadinessResponse>("/health/ready");
}
