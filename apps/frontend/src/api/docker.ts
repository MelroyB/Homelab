import { apiRequest } from "./client";
import {
  DockerContainerActionResponse,
  DockerContainersResponse,
  DockerHostInfo,
  DockerImagesResponse,
  DockerImageUpdatesResponse
} from "../types/api";

export function getDockerHostInfo(): Promise<DockerHostInfo> {
  return apiRequest<DockerHostInfo>("/docker/host");
}

export function listDockerContainers(
  scope: "project" | "all"
): Promise<DockerContainersResponse> {
  return apiRequest<DockerContainersResponse>(
    `/docker/containers?scope=${scope}`
  );
}

export function dockerContainerAction(
  containerId: string,
  action: "start" | "stop" | "restart"
): Promise<DockerContainerActionResponse> {
  return apiRequest<DockerContainerActionResponse>(
    `/docker/containers/${containerId}/actions`,
    {
      method: "POST",
      body: JSON.stringify({ action })
    }
  );
}

export function listDockerImages(
  scope: "project" | "all"
): Promise<DockerImagesResponse> {
  return apiRequest<DockerImagesResponse>(`/docker/images?scope=${scope}`);
}

export function checkDockerImageUpdates(
  scope: "project" | "all"
): Promise<DockerImageUpdatesResponse> {
  return apiRequest<DockerImageUpdatesResponse>(
    `/docker/images/updates?scope=${scope}`
  );
}

export function pullDockerImage(
  imageRef: string
): Promise<{ status: "success" | "failed"; message: string }> {
  return apiRequest<{ status: "success" | "failed"; message: string }>(
    "/docker/images/pull",
    {
      method: "POST",
      body: JSON.stringify({ image_ref: imageRef })
    }
  );
}
