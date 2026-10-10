import type {
  ChatResponse,
  LoginRequest,
  MessageCreate,
  MessageOut,
  SessionCreate,
  SessionOut,
  SessionUpdate,
  TokenResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** 无配置时使用相对路径 `/api`，依赖 Vite dev proxy；生产可设 `VITE_API_BASE_URL`。 */
export function getApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (raw == null || String(raw).trim() === "") return "";
  return String(raw).replace(/\/$/, "");
}

function buildUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const base = getApiBase();
  if (!path.startsWith("/")) return `${base}/${path}`;
  return `${base}${path}`;
}

async function parseErrorBody(res: Response): Promise<string> {
  const text = await res.text();
  if (!text) return res.statusText || `HTTP ${res.status}`;
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) return JSON.stringify(j.detail);
    if (j.detail != null) return String(j.detail);
  } catch {
    /* ignore */
  }
  return text;
}

export async function apiFetch(
  path: string,
  init: RequestInit & { token?: string | null } = {},
): Promise<Response> {
  const { token, headers: initHeaders, ...rest } = init;
  const headers = new Headers(initHeaders);
  if (
    rest.body != null &&
    !(rest.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(buildUrl(path), { ...rest, headers });
  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorBody(res));
  }
  return res;
}

export async function loginRequest(body: LoginRequest): Promise<TokenResponse> {
  const res = await apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return res.json() as Promise<TokenResponse>;
}

export async function listSessions(token: string): Promise<SessionOut[]> {
  const res = await apiFetch("/api/sessions", { method: "GET", token });
  return res.json() as Promise<SessionOut[]>;
}

export async function createSession(
  token: string,
  body: SessionCreate,
): Promise<SessionOut> {
  const res = await apiFetch("/api/sessions", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
  return res.json() as Promise<SessionOut>;
}

export async function updateSession(
  token: string,
  sessionId: string,
  body: SessionUpdate,
): Promise<SessionOut> {
  const res = await apiFetch(`/api/sessions/${sessionId}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(body),
  });
  return res.json() as Promise<SessionOut>;
}

export async function deleteSession(token: string, sessionId: string): Promise<void> {
  await apiFetch(`/api/sessions/${sessionId}`, { method: "DELETE", token });
}

export async function listMessages(
  token: string,
  sessionId: string,
): Promise<MessageOut[]> {
  const res = await apiFetch(`/api/sessions/${sessionId}/messages`, {
    method: "GET",
    token,
  });
  return res.json() as Promise<MessageOut[]>;
}

export async function postMessage(
  token: string,
  sessionId: string,
  body: MessageCreate,
): Promise<ChatResponse> {
  const res = await apiFetch(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    token,
    body: JSON.stringify(body),
  });
  return res.json() as Promise<ChatResponse>;
}
