import { useCallback, useEffect, useMemo, useState } from "react";
import {
  checkDockerImageUpdates,
  dockerContainerAction,
  getDockerHostInfo,
  listDockerContainers,
  listDockerImages,
  pullDockerImage
} from "../api/docker";
import {
  DockerContainerItem,
  DockerHostInfo,
  DockerImageItem,
  DockerImageUpdateStatus
} from "../types/api";
import { StatusBadge } from "../components/StatusBadge";

function formatBytes(value: number | null): string {
  if (value === null) {
    return "n/a";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = value;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(1)} ${units[idx]}`;
}

export function DockerManagerPage() {
  const [scope, setScope] = useState<"project" | "all">("project");
  const [host, setHost] = useState<DockerHostInfo | null>(null);
  const [containers, setContainers] = useState<DockerContainerItem[]>([]);
  const [images, setImages] = useState<DockerImageItem[]>([]);
  const [updates, setUpdates] = useState<Record<string, DockerImageUpdateStatus>>({});
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const updatesByImage = useMemo(() => updates, [updates]);

  const reload = useCallback(async () => {
    const [hostInfo, containerResponse, imageResponse] = await Promise.all([
      getDockerHostInfo(),
      listDockerContainers(scope),
      listDockerImages(scope)
    ]);
    setHost(hostInfo);
    setContainers(containerResponse.items);
    setImages(imageResponse.items);
  }, [scope]);

  useEffect(() => {
    reload().catch((err) => {
      setError(err instanceof Error ? err.message : "Failed to load docker manager");
    });
  }, [reload]);

  const runContainerAction = async (
    containerId: string,
    action: "start" | "stop" | "restart",
    name: string
  ) => {
    setError(null);
    setResult(null);
    try {
      const response = await dockerContainerAction(containerId, action);
      setResult(`${action} ${name}: ${response.message}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Container action failed");
    }
  };

  const runUpdateCheck = async () => {
    setError(null);
    setResult(null);
    try {
      const response = await checkDockerImageUpdates(scope);
      const map: Record<string, DockerImageUpdateStatus> = {};
      response.items.forEach((item) => {
        map[item.image_ref] = item;
      });
      setUpdates(map);
      setResult("Image update check completed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update check failed");
    }
  };

  const runPull = async (imageRef: string) => {
    setError(null);
    setResult(null);
    try {
      const response = await pullDockerImage(imageRef);
      setResult(`${imageRef}: ${response.message}`);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Image pull failed");
    }
  };

  return (
    <section>
      <div className="page-header">
        <h2>Docker Manager</h2>
        <div className="action-row">
          <select value={scope} onChange={(e) => setScope(e.target.value as "project" | "all") }>
            <option value="project">Project containers</option>
            <option value="all">All host containers</option>
          </select>
          <button className="btn btn-secondary" onClick={() => reload()}>
            Refresh
          </button>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {result ? <div className="success">{result}</div> : null}

      <div className="stats-grid">
        <article className="stat-card">
          <h3>Docker</h3>
          <strong>{host?.docker_available ? "available" : "offline"}</strong>
        </article>
        <article className="stat-card">
          <h3>Engine</h3>
          <strong>{host?.server_version || "n/a"}</strong>
        </article>
        <article className="stat-card">
          <h3>Running</h3>
          <strong>{host?.containers_running ?? 0}</strong>
        </article>
        <article className="stat-card">
          <h3>Memory</h3>
          <strong>{formatBytes(host?.memory_total_bytes ?? null)}</strong>
        </article>
      </div>

      <div className="card">
        <h3>Containers</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Image</th>
              <th>Status</th>
              <th>Project</th>
              <th>Ports</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {containers.map((container) => (
              <tr key={container.id}>
                <td>{container.name}</td>
                <td className="mono">{container.image}</td>
                <td>
                  <StatusBadge value={container.health !== "unknown" ? container.health : container.status} />
                </td>
                <td>{container.project_name || "-"}</td>
                <td>{container.ports.length > 0 ? container.ports.join(", ") : "-"}</td>
                <td>
                  <div className="action-row">
                    <button
                      className="btn btn-secondary"
                      onClick={() => runContainerAction(container.id, "start", container.name)}
                    >
                      start
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => runContainerAction(container.id, "stop", container.name)}
                    >
                      stop
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => runContainerAction(container.id, "restart", container.name)}
                    >
                      restart
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="page-header">
          <h3>Images</h3>
          <button className="btn" onClick={runUpdateCheck}>
            Check updates
          </button>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Tag</th>
              <th>Size</th>
              <th>In use</th>
              <th>Update status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {images.map((image) => {
              const tag = image.repo_tags[0] || image.id;
              const update = updatesByImage[tag];
              return (
                <tr key={image.id}>
                  <td className="mono">{tag}</td>
                  <td>{formatBytes(image.size_bytes)}</td>
                  <td>{image.containers_using}</td>
                  <td>
                    {update ? (
                      <span title={update.detail}>
                        <StatusBadge value={update.status} />
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    <button className="btn btn-secondary" onClick={() => runPull(tag)}>
                      pull
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
