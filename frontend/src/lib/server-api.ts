import "server-only";

import { cookies, headers as requestHeaders } from "next/headers";

import type { ReferenceData, User } from "./types";

// No trailing slash, so `${API}/api/...` never becomes `//api/...`.
const API = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/+$/, "");
export const SESSION_COOKIE = "propcheck_session";

/** fetch() that says which API address failed: a bare "fetch failed / ECONNREFUSED" hides it. */
async function apiFetch(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (e) {
    const reason = (e as { cause?: { code?: string } }).cause?.code ?? String(e);
    throw new Error(`Could not reach the PropCheck API at ${API} (${reason}). Is API_INTERNAL_URL set?`, {
      cause: e,
    });
  }
}

export class ServerApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** The visitor's address chain, so the API's per-IP rate limits count visitors, not this server. */
async function forwardedFor(): Promise<string | null> {
  try {
    return (await requestHeaders()).get("x-forwarded-for");
  } catch {
    return null; // outside a request (e.g. build time)
  }
}

/** Server Component fetch: talks to the API directly and forwards the visitor's session cookie and IP. */
export async function serverApi<T>(path: string, { auth = true }: { auth?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const visitor = await forwardedFor();
  if (visitor) headers["X-Forwarded-For"] = visitor;
  if (auth) {
    const token = (await cookies()).get(SESSION_COOKIE)?.value;
    if (token) headers.Cookie = `${SESSION_COOKIE}=${token}`;
  }
  const res = await apiFetch(`${API}${path}`, { headers, cache: "no-store" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ServerApiError(res.status, data.detail ?? `API error ${res.status}`);
  }
  return res.json() as Promise<T>;
}

/** Returns null instead of throwing for 404s, for pages that call notFound(). */
export async function serverApiOrNull<T>(path: string): Promise<T | null> {
  try {
    return await serverApi<T>(path);
  } catch (e) {
    if (e instanceof ServerApiError && (e.status === 404 || e.status === 422)) return null;
    throw e;
  }
}

export async function getCurrentUser(): Promise<User | null> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return null;
  try {
    return await serverApi<User>("/api/auth/me");
  } catch {
    return null;
  }
}


/** Static lookup data (states, cities, enums). Cached for an hour. */
export async function getReference(): Promise<ReferenceData> {
  const res = await apiFetch(`${API}/api/reference`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new ServerApiError(res.status, "Could not load reference data");
  return res.json();
}
