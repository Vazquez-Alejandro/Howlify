const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ApiResult<T> {
  data?: T;
  error?: string;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResult<T>> {
  const token = localStorage.getItem("token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { error: body.detail || body.message || `Error ${res.status}` };
    }
    return { data: await res.json() };
  } catch (e: unknown) {
    return { error: e instanceof Error ? e.message : "Error de red" };
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),

  login: (email: string, password: string) =>
    request<{ user: { id: string; email: string }; token: string; refresh_token: string }>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    ),

  signup: (email: string, password: string, username: string, plan = "starter") =>
    request<{ message: string }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, username, plan }),
    }),

  listCazas: () => request<{ cazas: Caza[] }>("/api/cazas"),

  createCaza: (data: {
    keyword: string;
    url: string;
    precio_max: number;
    frecuencia?: string;
  }) => request<{ message: string }>("/api/cazas", { method: "POST", body: JSON.stringify(data) }),

  deleteCaza: (id: number) => request<{ message: string }>(`/api/cazas/${id}`, { method: "DELETE" }),

  huntSingle: (id: number) =>
    request<{ results: HuntResult[] }>(`/api/hunt/${id}`, { method: "POST" }),

  huntAll: () => request<{ results: Record<string, HuntResult[]> }>("/api/hunt/all", { method: "POST" }),

  forgotPassword: (email: string) =>
    request<{ message: string }>("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
};

export interface Caza {
  id: number;
  producto?: string;
  keyword?: string;
  link?: string;
  url?: string;
  precio_max: number;
  last_price?: number;
  estado?: string;
}

export interface HuntResult {
  title: string;
  price: number;
  url: string;
  source: string;
  score?: number;
}
