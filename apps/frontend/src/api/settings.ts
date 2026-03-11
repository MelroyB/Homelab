import { apiRequest } from "./client";
import {
  DhcpLeasesResponse,
  NetworkStackApplyResponse,
  NetworkStackProfile
} from "../types/api";

export function getNetworkStackProfile(): Promise<NetworkStackProfile> {
  return apiRequest<NetworkStackProfile>("/settings/network/profile");
}

export function applyNetworkStackProfile(
  profile: NetworkStackProfile
): Promise<NetworkStackApplyResponse> {
  return apiRequest<NetworkStackApplyResponse>("/settings/network/apply", {
    method: "POST",
    body: JSON.stringify(profile)
  });
}

export function getDhcpLeases(): Promise<DhcpLeasesResponse> {
  return apiRequest<DhcpLeasesResponse>("/settings/network/dhcp/leases");
}
