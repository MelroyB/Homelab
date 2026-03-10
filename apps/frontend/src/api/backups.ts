import { apiRequest } from "./client";
import { BackupListResponse } from "../types/api";

export function listBackups(): Promise<BackupListResponse> {
  return apiRequest<BackupListResponse>("/backups");
}

export function createBackup() {
  return apiRequest<{
    id: string;
    name: string;
    checksum: string;
    created_at: string;
  }>("/backups/export", {
    method: "POST"
  });
}

export function restoreBackup(snapshotId: string) {
  return apiRequest<{
    id: string;
    name: string;
    checksum: string;
    created_at: string;
  }>("/backups/restore", {
    method: "POST",
    body: JSON.stringify({ snapshot_id: snapshotId })
  });
}
