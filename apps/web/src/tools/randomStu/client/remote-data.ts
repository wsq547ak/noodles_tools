import type { RandomStuData } from "../lib/types";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

type SessionResponse = { authenticated: boolean };
type RemoteStateResponse = {
  data: RandomStuData | null;
  revision: number;
  updatedAt: string | null;
};

export class RemoteApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function checkRandomStuSession(): Promise<boolean> {
  const result = await requestJson<SessionResponse>("/api/randomStu/session");
  return result.authenticated;
}

export async function loginRandomStu(password: string): Promise<void> {
  await requestJson<SessionResponse>("/api/randomStu/login", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ password }),
  });
}

export async function logoutRandomStu(): Promise<void> {
  await requestJson<SessionResponse>("/api/randomStu/logout", { method: "POST" });
}

export function loadRemoteRandomStuData(): Promise<RemoteStateResponse> {
  return requestJson<RemoteStateResponse>("/api/randomStu/data", { cache: "no-store" });
}

export function saveRemoteRandomStuData(
  data: RandomStuData,
  revision: number,
): Promise<RemoteStateResponse> {
  return requestJson<RemoteStateResponse>("/api/randomStu/data", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ data, revision }),
  });
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${basePath}${path}`, {
    credentials: "same-origin",
    ...init,
  });
  const result = (await response.json().catch(() => null)) as
    | T
    | { error?: string }
    | null;
  if (!response.ok) {
    throw new RemoteApiError(
      result && typeof result === "object" && "error" in result && result.error
        ? result.error
        : "远端数据请求失败。",
      response.status,
    );
  }
  return result as T;
}
