import { createContext, useCallback, useContext, useEffect, useState } from "react";

import client, { clearTokens, getTokens, setTokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(async () => {
    try {
      const { data } = await client.get("/profile/");
      setUser(data);
      return data;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const { access } = getTokens();
    if (access) {
      fetchProfile().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [fetchProfile]);

  const login = async (credentials) => {
    const { data } = await client.post("/login/", credentials);
    setTokens({ access: data.access, refresh: data.refresh });
    setUser(data.user);
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await client.post("/register/", payload);
    return data;
  };

  const logout = async () => {
    const { refresh } = getTokens();
    try {
      await client.post("/logout/", { refresh });
    } catch {
      // best-effort - proceed with local logout regardless
    }
    clearTokens();
    setUser(null);
  };

  const value = { user, loading, login, register, logout, fetchProfile, setUser };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
