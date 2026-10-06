import "server-only";

import { cookies } from "next/headers";

import type { ReferenceData, User } from "./types";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
export const SESSION_COOKIE = "propcheck_session";

export class ServerApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/** Server Component fetch: talks to the API directly and forwards the visitor's session cookie. */
export async function serverApi<T>(path: string, { auth = true }: { auth?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (auth) {
    const token = (await cookies()).get(SESSION_COOKIE)?.value;
    if (token) headers.Cookie = `${SESSION_COOKIE}=${token}`;
  }
  const res = await fetch(`${API}${path}`, { headers, cache: "no-store" });
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
  const res = await fetch(`${API}/api/reference`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new ServerApiError(res.status, "Could not load reference data");
  return res.json();
}
