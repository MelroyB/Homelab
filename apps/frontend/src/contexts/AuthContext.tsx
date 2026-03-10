import { createContext, useEffect, useMemo, useState } from "react";
import { getBootstrapStatus, getMe, login as loginApi, logout as logoutApi } from "../api/auth";
import { User } from "../types/api";

interface AuthContextValue {
  loading: boolean;
  bootstrapRequired: boolean;
  user: User | null;
  refreshSession: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  markBootstrapCompleted: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [bootstrapRequired, setBootstrapRequired] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const refreshSession = async () => {
    const bootstrap = await getBootstrapStatus();
    setBootstrapRequired(bootstrap.bootstrap_required);

    if (bootstrap.bootstrap_required) {
      setUser(null);
      return;
    }

    try {
      const me = await getMe();
      setUser(me.user);
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    refreshSession()
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      loading,
      bootstrapRequired,
      user,
      refreshSession,
      login: async (email: string, password: string) => {
        const response = await loginApi(email, password);
        setUser(response.user);
      },
      logout: async () => {
        try {
          await logoutApi();
        } finally {
          setUser(null);
        }
      },
      markBootstrapCompleted: () => {
        setBootstrapRequired(false);
      }
    }),
    [loading, bootstrapRequired, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { AuthContext, type AuthContextValue };
