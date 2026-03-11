export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface BootstrapStatus {
  bootstrap_required: boolean;
}

export interface ServiceState {
  slug: string;
  name: string;
  category: string;
  container_name: string;
  enabled: boolean;
  state: string;
  health: string;
  uptime_seconds: number | null;
  ports: string[];
  config_validation_status: string | null;
  last_config_change: string | null;
  last_config_version: number | null;
}

export interface DashboardOverview {
  generated_at: string;
  service_count: number;
  healthy_service_count: number;
  degraded_service_count: number;
  services: ServiceState[];
}

export interface ConfigVersion {
  id: string;
  service_slug: string;
  version: number;
  config_json: Record<string, unknown>;
  raw_config: string;
  validation_status: string;
  apply_status: string;
  is_active: boolean;
  apply_message: string;
  created_by_id: string;
  created_at: string;
  applied_at: string | null;
}

export interface ServiceDetail {
  service: ServiceState;
  active_config: ConfigVersion | null;
}

export interface ServiceEnableResponse {
  slug: string;
  enabled: boolean;
  status: string;
  message: string;
  warnings: string[];
}

export interface ConfigValidationResponse {
  valid: boolean;
  errors: string[];
  rendered_config: string;
}

export interface ConfigApplyResponse {
  version: ConfigVersion;
  warnings: string[];
}

export interface BackupListItem {
  id: string;
  name: string;
  checksum: string;
  created_at: string;
  restored_at: string | null;
}

export interface BackupListResponse {
  items: BackupListItem[];
}

export interface AuditEvent {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  status: string;
  ip_address: string | null;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface ReadinessCheck {
  name: string;
  status: string;
  details: string;
}

export interface ReadinessResponse {
  status: string;
  timestamp: string;
  checks: ReadinessCheck[];
}

export interface DockerHostInfo {
  docker_available: boolean;
  name: string;
  server_version: string;
  operating_system: string;
  kernel_version: string;
  cpu_count: number | null;
  memory_total_bytes: number | null;
  containers_running: number | null;
  containers_total: number | null;
}

export interface DockerContainerItem {
  id: string;
  name: string;
  image: string;
  status: string;
  state: string;
  health: string;
  created_at: string | null;
  ports: string[];
  labels: Record<string, string>;
  project_name: string | null;
  managed_by_project: boolean;
  cpu_percent: number | null;
  memory_usage_bytes: number | null;
  memory_limit_bytes: number | null;
  memory_percent: number | null;
  restart_count: number | null;
}

export interface DockerContainersResponse {
  scope: "project" | "all";
  items: DockerContainerItem[];
}

export interface DockerContainerActionResponse {
  container_id: string;
  action: string;
  status: "success" | "failed";
  message: string;
}

export interface DockerImageItem {
  id: string;
  repo_tags: string[];
  created_at: string | null;
  size_bytes: number;
  containers_using: number;
}

export interface DockerImagesResponse {
  scope: "project" | "all";
  items: DockerImageItem[];
}

export interface DockerImageUpdateStatus {
  image_ref: string;
  status: "up_to_date" | "update_available" | "unknown" | "error";
  local_digests: string[];
  remote_digest: string | null;
  detail: string;
}

export interface DockerImageUpdatesResponse {
  scope: "project" | "all";
  items: DockerImageUpdateStatus[];
}

export interface NetworkStackProfile {
  domain: string;
  authoritative_domains: string[];
  enable_dnsmasq: boolean;
  enable_bind9: boolean;
  enable_ntp: boolean;
  router_ip: string;
  dhcp_range_start: string;
  dhcp_range_end: string;
  dhcp_lease: string;
  dhcp_authoritative: boolean;
  dhcp_dns_servers: string[];
  dhcp_ntp_servers: string[];
  dhcp_domain_search: string | null;
  dhcp_reservations: DhcpReservation[];
  dns_upstream_servers: string[];
  dns_cache_size: number;
  zone_ttl: number;
  zone_serial: number | null;
  nameserver_host: string;
  nameserver_ip: string;
  api_host: string;
  api_ip: string;
  dashboard_host: string;
  dashboard_ip: string;
  dns_records: DnsRecord[];
  ntp_servers: string[];
  ntp_iburst: boolean;
  ntp_disable_monitor: boolean;
  ntp_local_clock: boolean;
  ntp_local_stratum: number;
}

export interface MailboxEntry {
  email: string;
  password: string | null;
  has_password: boolean;
  display_name: string | null;
  quota_mb: number;
  enabled: boolean;
  aliases: string[];
}

export interface MailStackProfile {
  domain: string;
  hostname: string;
  postmaster_address: string;
  enable_mailserver: boolean;
  enable_webmail: boolean;
  enable_imap: boolean;
  enable_pop3: boolean;
  enable_submission: boolean;
  enable_submissions: boolean;
  enable_smtps: boolean;
  dkim_selector: string;
  dkim_key_size: number;
  dkim_public_key: string | null;
  spf_policy: string;
  dmarc_policy: string;
  mailboxes: MailboxEntry[];
}

export interface DnsRecord {
  name: string;
  type: string;
  value: string;
}

export interface DhcpReservation {
  mac: string;
  ip: string;
  hostname: string | null;
  lease: string | null;
}

export interface DhcpLeaseEntry {
  expires_at: string | null;
  is_expired: boolean;
  mac: string;
  ip: string;
  hostname: string | null;
  client_id: string | null;
}

export interface DhcpLeasesResponse {
  items: DhcpLeaseEntry[];
}

export interface NetworkServiceApplyResult {
  service_slug: string;
  status: string;
  version: number | null;
  message: string;
  warnings: string[];
}

export interface NetworkStackApplyResponse {
  success: boolean;
  results: NetworkServiceApplyResult[];
}

export interface MailStackApplyResponse {
  success: boolean;
  results: NetworkServiceApplyResult[];
  suggested_dns_records: DnsRecord[];
}
