from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.backup import BackupSnapshot
from app.models.service import ServiceConfigVersion
from app.models.user import User
from app.utils.hash import sha256_text


class BackupService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.backup_dir = settings.data_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self, actor: User) -> BackupSnapshot:
        active_configs = self.db.scalars(
            select(ServiceConfigVersion).where(ServiceConfigVersion.is_active.is_(True))
        ).all()
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "encryption_enabled": self.settings.backup_encryption_enabled,
            "items": [
                {
                    "service_slug": item.service_slug,
                    "version": item.version,
                    "config_json": item.config_json,
                    "raw_config": item.raw_config,
                    "rendered_config": item.rendered_config,
                    "checksum": item.checksum,
                }
                for item in active_configs
            ],
        }
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        checksum = sha256_text(serialized)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        name = f"snapshot-{stamp}.json"
        path = self.backup_dir / name
        path.write_text(serialized, encoding="utf-8")

        snapshot = BackupSnapshot(
            name=name,
            file_path=str(path),
            checksum=checksum,
            created_by_id=actor.id,
            metadata_json={"item_count": len(payload["items"]), "encrypted": False},
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def list_snapshots(self) -> list[BackupSnapshot]:
        return self.db.scalars(
            select(BackupSnapshot).order_by(BackupSnapshot.created_at.desc())
        ).all()

    def restore_snapshot(self, *, snapshot_id: str) -> BackupSnapshot:
        snapshot = self.db.scalar(select(BackupSnapshot).where(BackupSnapshot.id == snapshot_id))
        if snapshot is None:
            raise ValueError("Snapshot not found")

        path = Path(snapshot.file_path)
        if not path.exists():
            raise ValueError("Snapshot file missing")

        payload = json.loads(path.read_text(encoding="utf-8"))
        # TODO(phase-4): apply restored configs back to runtime service files with validation gates.
        for item in payload.get("items", []):
            self.db.add(
                ServiceConfigVersion(
                    service_slug=item["service_slug"],
                    version=item["version"],
                    config_json=item.get("config_json", {}),
                    raw_config=item.get("raw_config", ""),
                    rendered_config=item.get("rendered_config", ""),
                    checksum=item.get("checksum", ""),
                    validation_status="valid",
                    validation_errors=[],
                    apply_status="restored",
                    apply_message=f"Restored from {snapshot.name}",
                    is_active=False,
                    created_by_id=snapshot.created_by_id,
                )
            )

        snapshot.restored_at = datetime.now(timezone.utc)
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot
