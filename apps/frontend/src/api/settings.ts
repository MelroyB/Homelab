import { apiRequest } from "./client";
import {
  DhcpLeasesResponse,
  MailStackApplyResponse,
  MailStackProfile,
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

export function getMailStackProfile(): Promise<MailStackProfile> {
  return apiRequest<MailStackProfile>("/settings/mail/profile");
}

export function applyMailStackProfile(
  profile: MailStackProfile
): Promise<MailStackApplyResponse> {
  return apiRequest<MailStackApplyResponse>("/settings/mail/apply", {
    method: "POST",
    body: JSON.stringify(profile)
  });
}
