import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { api } from "../api/client";

interface AuthContextType {
  token: string | null;
  refresh_token: string | null;
  user: { id: string; email: string } | null;
  login: (token: string, refresh_token: string, user: { id: string; email: string }) => void;
  logout: () => void;
  refreshSession: () => Promise<string | null>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("token"));
  const [refresh_token, setRefreshToken] = useState<string | null>(localStorage.getItem("refresh_token"));
  const [user, setUser] = useState<{ id: string; email: string } | null>(() => {
    const u = localStorage.getItem("user");
    return u ? JSON.parse(u) : null;
  });

  useEffect(() => {
    if (token) localStorage.setItem("token", token);
    else localStorage.removeItem("token");
  }, [token]);

  useEffect(() => {
    if (refresh_token) localStorage.setItem("refresh_token", refresh_token);
    else localStorage.removeItem("refresh_token");
  }, [refresh_token]);

  useEffect(() => {
    if (user) localStorage.setItem("user", JSON.stringify(user));
    else localStorage.removeItem("user");
  }, [user]);

  const login = (t: string, rt: string, u: { id: string; email: string }) => {
    setToken(t);
    setRefreshToken(rt);
    setUser(u);
  };

  const logout = () => {
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  };

  const refreshSession = useCallback(async () => {
    if (!refresh_token) return null;
    try {
      const res = await api.refreshToken(refresh_token);
      if (res.data?.token) {
        setToken(res.data.token);
        if (res.data.refresh_token) setRefreshToken(res.data.refresh_token);
        return res.data.token;
      }
    } catch {
      logout();
    }
    return null;
  }, [refresh_token]);

  return (
    <AuthContext.Provider value={{ token, refresh_token, user, login, logout, refreshSession, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
