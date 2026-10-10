import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { loginRequest } from "../api/client";
import { STORAGE_TOKEN } from "../lib/storageKeys";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readToken(): string | null {
  try {
    return localStorage.getItem(STORAGE_TOKEN);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken);

  const login = useCallback(async (username: string, password: string) => {
    const data = await loginRequest({ username, password });
    localStorage.setItem(STORAGE_TOKEN, data.access_token);
    setToken(data.access_token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_TOKEN);
    setToken(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      login,
      logout,
    }),
    [token, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
