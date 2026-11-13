import type {
  AnalyzeResponse,
  Dashboard,
  JobAccepted,
  Paginated,
  PostWithPrediction,
  Query,
  Sentiment,
  TimeRange,
  User,
} from "@/lib/types";

export type ApiError = Error & { status?: number };

type ApiRequestOptions = Omit<RequestInit, "body"> & { body?: unknown; redirectOn401?: boolean };

export function isApiError(error: unknown, status?: number): error is ApiError {
  return error instanceof Error && "status" in error && (status === undefined || (error as ApiError).status === status);
}

/** A backend route from the plan that is not implemented on the API yet. */
export function isNotAvailable(error: unknown): boolean {
  return isApiError(error, 404) || isApiError(error, 405);
}

async function request<T>(path: string, { redirectOn401 = true, ...options }: ApiRequestOptions = {}): Promise<T> {
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;
  const isJson = options.body !== undefined && !isForm;

  let response: Response;
  try {
    response = await fetch(path, {
      ...options,
      credentials: "same-origin",
      headers: { Accept: "application/json", ...(isJson ? { "Content-Type": "application/json" } : {}), ...options.headers },
      body: options.body === undefined ? undefined : isForm ? (options.body as FormData) : JSON.stringify(options.body),
    });
  } catch {
    throw Object.assign(new Error("We could not reach SentiBoard. Check your connection and try again."), { status: 0 });
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && redirectOn401 && typeof window !== "undefined" && path.startsWith("/api/backend/")) {
      const next = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.assign(`/login?next=${next}`);
    }
    const error = new Error(extractMessage(payload) ?? friendlyStatusMessage(response.status)) as ApiError;
    error.status = response.status;
    throw error;
  }
  return payload as T;
}

function extractMessage(payload: unknown): string | undefined {
  if (!payload || typeof payload !== "object") return;
  const record = payload as Record<string, unknown>;
  const detail = record.detail ?? record.message ?? record.error;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => item && typeof item === "object" && "msg" in item ? String(item.msg) : "").filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
}

function friendlyStatusMessage(status: number): string {
  if (status === 400 || status === 401 || status === 422) return "Check your details and try again.";
  if (status === 404) return "We could not find what you were looking for.";
  if (status === 409) return "An account with those details already exists.";
  if (status >= 500) return "SentiBoard is having trouble right now. Please try again shortly.";
  return "We could not complete that request. Please try again.";
}

const backend = (path: string) => `/api/backend/${path}`;

function qs(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== "") search.set(key, String(value));
  const text = search.toString();
  return text ? `?${text}` : "";
}

export type AuthResponse = { user?: Partial<User>; message?: string };

export const api = {
  // Auth (same-origin route handlers that set the HttpOnly session cookie)
  login: (credentials: { email: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", { method: "POST", body: credentials }),
  register: (credentials: { username: string; email: string; password: string }) =>
    request<AuthResponse>("/api/auth/register", { method: "POST", body: credentials }),
  logout: () => request<{ ok: boolean }>("/api/auth/logout", { method: "POST" }),
  me: () => request<User>(backend("auth/me"), { redirectOn401: false }),

  // Single text → ML model(s), synchronous
  analyzeText: (text: string, compare = false) =>
    request<AnalyzeResponse>(backend("analyze"), { method: "POST", body: { text, compare } }),

  // Background jobs
  startKeywordJob: (body: { keyword: string; limit: number; time_range: TimeRange }) =>
    request<JobAccepted>(backend("queries/keyword"), { method: "POST", body }),
  startCsvJob: (file: File, textColumn: string, dateColumn?: string) => {
    const form = new FormData();
    form.set("file", file);
    form.set("text_column", textColumn);
    if (dateColumn) form.set("date_column", dateColumn);
    return request<JobAccepted>(backend("queries/csv"), { method: "POST", body: form });
  },

  // Results
  listQueries: (page = 1, pageSize = 20) =>
    request<Paginated<Query>>(backend(`queries${qs({ page, page_size: pageSize })}`)),
  getQuery: (id: number) => request<Query>(backend(`queries/${id}`)),
  getDashboard: (id: number) => request<Dashboard>(backend(`queries/${id}/dashboard`)),
  getPosts: (id: number, page = 1, pageSize = 20, label?: Sentiment) =>
    request<Paginated<PostWithPrediction>>(backend(`queries/${id}/posts${qs({ page, page_size: pageSize, label })}`)),
  exportUrl: (id: number) => backend(`queries/${id}/export`),
};
