import axios from "axios";

import { clearTokens, getTokens, setTokens } from "./tokens";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

let refreshPromise = null;

function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) return Promise.reject(new Error("No refresh token"));

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_URL}/api/auth/login/refresh/`, { refresh })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/**
 * Creates an axios instance rooted at `${API_URL}${basePath}` that attaches
 * the JWT access token to every request and transparently refreshes it on a
 * 401 (shared across every client created this way, so concurrent requests
 * to different resources don't each trigger their own refresh).
 */
export function createApiClient(basePath) {
  const client = axios.create({ baseURL: `${API_URL}${basePath}` });

  client.interceptors.request.use((config) => {
    const { access } = getTokens();
    if (access) {
      config.headers.Authorization = `Bearer ${access}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error) => {
      const original = error.config;
      const isAuthEndpoint = original?.url?.includes("/login") || original?.url?.includes("/register");

      if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
        original._retry = true;
        try {
          const { data } = await refreshAccessToken();
          setTokens({ access: data.access });
          original.headers.Authorization = `Bearer ${data.access}`;
          return client(original);
        } catch (refreshError) {
          clearTokens();
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );

  return client;
}
