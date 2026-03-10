import { FormEvent, useState } from "react";
import { getServiceLogs } from "../api/services";

export function LogsPage() {
  const [slug, setSlug] = useState("backend");
  const [tail, setTail] = useState(200);
  const [logs, setLogs] = useState("");
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    try {
      const response = await getServiceLogs(slug, tail);
      setLogs(response.logs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load logs");
    }
  };

  return (
    <section>
      <h2>Central Logs</h2>
      <form className="inline-form card" onSubmit={onSubmit}>
        <label>
          Service slug
          <input value={slug} onChange={(e) => setSlug(e.target.value)} />
        </label>
        <label>
          Tail
          <input
            type="number"
            min={10}
            max={5000}
            value={tail}
            onChange={(e) => setTail(Number(e.target.value))}
          />
        </label>
        <button className="btn" type="submit">
          Load logs
        </button>
      </form>
      {error ? <div className="error">{error}</div> : null}
      <pre className="log-viewer">{logs || "No logs loaded"}</pre>
    </section>
  );
}
