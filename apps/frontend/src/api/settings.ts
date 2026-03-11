import { apiRequest } from "./client";
import {
  DhcpLeasesResponse,
  MailDnsSuggestionsResponse,
  MailStackApplyResponse,
  MailStackProfile,
  NetworkStackApplyResponse,
  NetworkStackProfile,
  WebmailUrlResponse
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

export function getMailDnsSuggestions(
  profile: MailStackProfile
): Promise<MailDnsSuggestionsResponse> {
  return apiRequest<MailDnsSuggestionsResponse>(
    "/settings/mail/dns/suggestions",
    {
      method: "POST",
      body: JSON.stringify(profile)
    }
  );
}

export function getWebmailUrl(
  mailbox?: string | null
): Promise<WebmailUrlResponse> {
  const query = mailbox ? `?mailbox=${encodeURIComponent(mailbox)}` : "";
  return apiRequest<WebmailUrlResponse>(`/settings/mail/webmail/url${query}`);
}
