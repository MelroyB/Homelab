import { useEffect, useState } from "react";
import { createBackup, listBackups, restoreBackup } from "../api/backups";
import { BackupListItem } from "../types/api";

export function BackupsPage() {
  const [items, setItems] = useState<BackupListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const reload = async () => {
    const response = await listBackups();
    setItems(response.items);
  };

  useEffect(() => {
    reload().catch((err) => setError(err instanceof Error ? err.message : "Failed to load backups"));
  }, []);

  const onCreate = async () => {
    setError(null);
    setResult(null);
    try {
      const snapshot = await createBackup();
      setResult(`Snapshot created: ${snapshot.name}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup export failed");
    }
  };

  const onRestore = async (snapshotId: string) => {
    setError(null);
    setResult(null);
    try {
      const snapshot = await restoreBackup(snapshotId);
      setResult(`Snapshot restored: ${snapshot.name}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backup restore failed");
    }
  };

  return (
    <section>
      <div className="page-header">
        <h2>Backups</h2>
        <button className="btn" onClick={onCreate}>
          Export Snapshot
        </button>
      </div>
      {error ? <div className="error">{error}</div> : null}
      {result ? <div className="success">{result}</div> : null}

      <table className="table card">
        <thead>
          <tr>
            <th>Name</th>
            <th>Created</th>
            <th>Checksum</th>
            <th>Restore</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.name}</td>
              <td>{new Date(item.created_at).toLocaleString()}</td>
              <td className="mono">{item.checksum.slice(0, 16)}...</td>
              <td>
                <button className="btn btn-secondary" onClick={() => onRestore(item.id)}>
                  Restore
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
