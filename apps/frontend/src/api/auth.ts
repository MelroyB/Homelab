import { apiRequest } from "./client";
import { BootstrapStatus, User } from "../types/api";

export async function getBootstrapStatus(): Promise<BootstrapStatus> {
  return apiRequest<BootstrapStatus>("/bootstrap/status");
}

export async function bootstrapAdmin(email: string, password: string): Promise<User> {
  return apiRequest<User>("/bootstrap/admin", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function login(email: string, password: string): Promise<{ user: User }> {
  return apiRequest<{ user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function logout(): Promise<void> {
  await apiRequest<void>("/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<{ user: User }> {
  return apiRequest<{ user: User }>("/auth/me");
}

export async function listUsers(): Promise<User[]> {
  return apiRequest<User[]>("/auth/users");
}
