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

  updateCaza: (id: number, data: {
    keyword: string;
    url: string;
    precio_max: number;
    frecuencia?: string;
    tipo?: string;
  }) => request<{ message: string }>(`/api/cazas/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  deleteCaza: (id: number) => request<{ message: string }>(`/api/cazas/${id}`, { method: "DELETE" }),

  huntSingle: (id: number) =>
    request<{ results: HuntResult[] }>(`/api/hunt/${id}`, { method: "POST" }),

  huntAll: () => request<{ results: Record<string, HuntResult[]> }>("/api/hunt/all", { method: "POST" }),

  forgotPassword: (email: string) =>
    request<{ message: string }>("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  getProfile: () => request<{ profile: { role?: string; plan?: string } }>("/api/auth/profile"),

  adminUsers: () => request<{ users: Record<string, unknown>[] }>("/api/admin/users"),

  // Monitor
  monitorRules: () => request<{ rules: MonitorRule[] }>("/api/monitor/rules"),
  upsertMonitorRule: (cazaId: number, data: {
    product_name: string; product_url: string; source?: string;
    target_price?: number; min_price_allowed: number; max_price_allowed: number;
  }) => request<{ message: string }>(`/api/monitor/rules/${cazaId}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteMonitorRule: (cazaId: number) => request<{ message: string }>(`/api/monitor/rules/${cazaId}`, { method: "DELETE" }),
  monitorInfracciones: () => request<{ infracciones: Infraccion[] }>("/api/monitor/infracciones"),
  monitorGrupos: () => request<{ grupos: Grupo[] }>("/api/monitor/grupos"),
  createMonitorGrupo: (nombre: string, color: string) =>
    request<{ message: string }>("/api/monitor/grupos", { method: "POST", body: JSON.stringify({ nombre, color }) }),
  deleteMonitorGrupo: (id: number) => request<{ message: string }>(`/api/monitor/grupos/${id}`, { method: "DELETE" }),
  monitorGrupoCazas: () => request<{ relaciones: { caza_id: number; grupo_id: number }[] }>("/api/monitor/grupo-cazas"),
  assignMonitorGrupo: (cazaId: number, grupoId: number | null) =>
    request<{ message: string }>("/api/monitor/grupo-cazas", { method: "PUT", body: JSON.stringify({ caza_id: cazaId, grupo_id: grupoId }) }),
  monitorPriceHistory: (cazaId: number) =>
    request<{ history: { checked_at: string; price: number }[] }>(`/api/monitor/price-history/${cazaId}`),
  monitorLatestPrices: () => request<{ prices: Record<string, { price: number; checked_at: string }> }>("/api/monitor/latest-prices"),
  monitorAllHistory: () => request<{ history: { caza_id: number; price: number; checked_at: string }[] }>("/api/monitor/all-history"),
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

export interface MonitorRule {
  id?: number;
  user_id: string;
  caza_id: number;
  product_name: string;
  product_url: string;
  source: string;
  target_price: number;
  min_price_allowed: number;
  max_price_allowed: number;
  is_active?: boolean;
}

export interface Infraccion {
  id?: number;
  caza_id: number;
  url_captura?: string;
  precio_detectado?: number;
  status?: string;
  error?: string;
  fecha?: string;
}

export interface Grupo {
  id: number;
  nombre: string;
  color: string;
}
