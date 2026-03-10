# Backup and Restore

## Scope (v1)

- Snapshot export of active service config versions
- Snapshot list and restore API
- Metadata persisted in `backup_snapshots`

## Export

- API: `POST /api/v1/backups/export`
- UI: Backups page -> `Export Snapshot`

Snapshot file location:

- `/var/lib/homelab/backups/snapshot-<timestamp>.json`

## Restore

- API: `POST /api/v1/backups/restore`
- UI: Backups page -> `Restore`

Current restore behavior:

- Imports saved config payload into version history
- Marks restore event in backup metadata
- Does not yet automatically trigger apply for every restored service

## Encryption plan

Planned in later phase:

- Encrypted backup payloads
- key rotation strategy
- integrity verification policy + offsite sync integration
