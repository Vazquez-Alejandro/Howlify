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
    frecuencia?: string; tipo?: string; source?: string; etiqueta?: string;
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

  huntSingle: (id: number) => request<{ message: string; results: { title: string; price: number; url: string; source: string }[]; personalized_price_warning?: string }>(
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

  exportSheets: (rows: Record<string, unknown>[], sheet_name: string) =>
    request<{ message: string }>("/api/export/sheets", {
      method: "POST", body: JSON.stringify({ rows, sheet_name }),
    }),

  adminUsers: () => request<{ users: Record<string, unknown>[] }>("/api/admin/users"),

  exportCsv: async (): Promise<{ blob?: Blob; error?: string }> => {
    const token = getToken();
    try {
      const res = await fetch(`${API_BASE}/api/export/csv`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.status === 401 && getRefreshToken()) {
        const refreshed = await tryRefresh();
        if (refreshed) {
          const retry = await fetch(`${API_BASE}/api/export/csv`, {
            headers: { Authorization: `Bearer ${getToken()}` },
          });
          if (!retry.ok) return { error: `Error ${retry.status}` };
          return { blob: await retry.blob() };
        }
        return { error: "Sesión expirada. Iniciá sesión de nuevo." };
      }
      if (!res.ok) return { error: `Error ${res.status}` };
      return { blob: await res.blob() };
    } catch (e: unknown) {
      return { error: e instanceof Error ? e.message : "Error de red" };
    }
  },
};

export interface Caza {
  id: number;
  producto?: string;
  keyword?: string;
  link?: string;
  url?: string;
  precio_max: number;
  frecuencia?: string;
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
  seller?: {
    seller_id: number;
    nickname: string;
    reputation: string;
    reputation_label: string;
    total_sales: number;
    completed_sales: number;
    positive_ratio: string | null;
    permalink: string;
  };
}


