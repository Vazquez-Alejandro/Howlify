const API_BASE = import.meta.env.VITE_API_URL || "";

interface ApiResult<T> {
  data?: T;
  error?: string;
}

let refreshPromise: Promise<{ token: string; refresh_token: string } | null> | null = null;

function getToken() {
  return localStorage.getItem("token");
}

function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

function setTokens(token: string, refresh_token: string) {
  localStorage.setItem("token", token);
  localStorage.setItem("refresh_token", refresh_token);
}

function clearTokens() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

async function tryRefresh(): Promise<boolean> {
  const rt = getRefreshToken();
  if (!rt) return false;

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    }).then(async (res) => {
      if (!res.ok) throw new Error("refresh failed");
      return res.json();
    }).catch(() => null);
  }

  const result = await refreshPromise;
  refreshPromise = null;
  if (result?.token) {
    setTokens(result.token, result.refresh_token || rt);
    return true;
  }
  clearTokens();
  return false;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResult<T>> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (res.status === 401 && getRefreshToken()) {
      const refreshed = await tryRefresh();
      if (refreshed) {
        headers["Authorization"] = `Bearer ${getToken()}`;
        const retry = await fetch(`${API_BASE}${path}`, { ...options, headers });
        if (!retry.ok) {
          const body = await retry.json().catch(() => ({}));
          return { error: body.detail || body.message || `Error ${retry.status}` };
        }
        return { data: await retry.json() };
      }
      return { error: "Sesión expirada. Iniciá sesión de nuevo." };
    }
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
    keyword: string; url: string; precio_max: number;
    frecuencia?: string; tipo?: string;
  }) => request<{ message: string }>("/api/cazas", {
    method: "POST", body: JSON.stringify(data),
  }),

  updateCaza: (id: number, data: {
    keyword: string; url: string; precio_max: number;
    frecuencia?: string; tipo?: string; etiqueta?: string;
  }) => request<{ message: string }>(`/api/cazas/${id}`, {
    method: "PUT", body: JSON.stringify(data),
  }),

  deleteCaza: (id: number) => request<{ message: string }>(`/api/cazas/${id}`, { method: "DELETE" }),

  hunt: (id: number) => request<{ message: string; results: { title: string; price: number; url: string; source: string }[]; personalized_price_warning?: string }>(
    `/api/hunt/${id}`, { method: "POST" }
  ),

  huntAll: () => request<{ message: string }>("/api/hunt/all", { method: "POST" }),

  forgotPassword: (email: string) =>
    request<{ message: string }>("/api/auth/forgot-password", {
      method: "POST", body: JSON.stringify({ email }),
    }),

  resendVerification: (email: string) =>
    request<{ message: string }>("/api/auth/resend-verification", {
      method: "POST", body: JSON.stringify({ email }),
    }),

  resetPassword: (access_token: string, refresh_token: string, password: string) =>
    request<{ message: string }>("/api/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ access_token, refresh_token, password }),
    }),

  refreshToken: (refresh_token: string) =>
    request<{ token: string; refresh_token: string }>("/api/auth/refresh", {
      method: "POST", body: JSON.stringify({ refresh_token }),
    }),

  getProfile: () => request<{ profile: Record<string, unknown> }>("/api/auth/profile"),

  updateProfile: (data: Record<string, unknown>) =>
    request<{ message: string }>("/api/auth/profile", {
      method: "PUT", body: JSON.stringify(data),
    }),

  testNotification: (data: { canal: string }) =>
    request<{ message: string }>("/api/auth/test-notification", {
      method: "POST", body: JSON.stringify(data),
    }),

  getHistory: (cazaId: number) =>
    request<{ history: { price: number; checked_at: string }[] }>(`/api/history/${cazaId}`),

  monitorRules: () => request<{ rules: MonitorRule[] }>("/api/monitor/rules"),

  upsertMonitorRule: (caza_id: number, data: Record<string, unknown>) =>
    request<{ message: string }>(`/api/monitor/rules/${caza_id}`, {
      method: "PUT", body: JSON.stringify(data),
    }),

  deleteMonitorRule: (caza_id: number) =>
    request<{ message: string }>(`/api/monitor/rules/${caza_id}`, { method: "DELETE" }),

  monitorInfracciones: () => request<{ infracciones: Infraccion[] }>("/api/monitor/infracciones"),

  monitorGrupos: () => request<{ grupos: Grupo[] }>("/api/monitor/grupos"),

  createMonitorGrupo: (nombre: string, color: string) =>
    request<{ message: string }>("/api/monitor/grupos", {
      method: "POST", body: JSON.stringify({ nombre, color }),
    }),

  deleteMonitorGrupo: (id: number) =>
    request<{ message: string }>(`/api/monitor/grupos/${id}`, { method: "DELETE" }),

  monitorGrupoCazas: () => request<{ relaciones: { caza_id: number; grupo_id: number }[] }>("/api/monitor/grupo-cazas"),

  assignMonitorGrupo: (caza_id: number, grupo_id: number) =>
    request<{ message: string }>("/api/monitor/grupo-cazas", {
      method: "PUT", body: JSON.stringify({ caza_id, grupo_id }),
    }),

  monitorPriceHistory: (caza_id: number) =>
    request<{ history: { price: number; checked_at: string }[] }>(`/api/monitor/price-history/${caza_id}`),

  monitorLatestPrices: () =>
    request<{ prices: Record<string, { price: number; checked_at: string }> }>("/api/monitor/latest-prices"),

  monitorAllHistory: () =>
    request<{ history: { caza_id: number; price: number; checked_at: string }[] }>("/api/monitor/all-history"),

  exportSheets: (rows: Record<string, unknown>[], sheet_name: string) =>
    request<{ message: string }>("/api/export/sheets", {
      method: "POST", body: JSON.stringify({ rows, sheet_name }),
    }),

  adminUsers: () => request<{ users: Record<string, unknown>[] }>("/api/admin/users"),
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
  tipo_alerta?: string;
  created_at?: string;
  updated_at?: string;
  etiqueta?: string;
}

export interface HuntResult {
  title: string;
  price: number;
  url: string;
  source: string;
  score?: number;
  price_error?: boolean;
  price_avg?: number;
}

export interface MonitorRule {
  caza_id: number;
  min_price_allowed: number;
  max_price_allowed: number;
  is_active: boolean;
}

export interface Infraccion {
  id: number;
  caza_id: number;
  precio_detectado: number;
  fecha: string;
  status: string;
}

export interface Grupo {
  id: number;
  nombre: string;
  color: string;
}
