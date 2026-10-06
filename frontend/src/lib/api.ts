// Browser-side API client. Requests go to the same origin (/api is rewritten to FastAPI),
// so the httpOnly session cookie is sent automatically.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public fieldErrors?: { field: string; message: string }[],
  ) {
    super(message);
  }
}

type Body = Record<string, unknown> | FormData | undefined;

export async function api<T>(path: string, init: { method?: string; body?: Body } = {}): Promise<T> {
  const { method = init.body ? "POST" : "GET", body } = init;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body && !isForm ? { "Content-Type": "application/json" } : undefined,
    body: body ? (isForm ? (body as FormData) : JSON.stringify(body)) : undefined,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, data.detail ?? "Something went wrong. Please try again.", data.code, data.errors);
  }
  return data as T;
}

export const post = <T>(path: string, body: Body = {}) => api<T>(path, { method: "POST", body });
export const patch = <T>(path: string, body: Body) => api<T>(path, { method: "PATCH", body });

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong. Please try again.";
}

export function qs(params: Record<string, string | number | boolean | null | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "" && v !== false) sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}
