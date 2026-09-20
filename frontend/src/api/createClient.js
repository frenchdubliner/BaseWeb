import axios from "axios";

import { clearTokens, getTokens, setTokens } from "./tokens";

const _RAW_API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
// Unlike FRONTEND_URL (parsed server-side, comma-separated values allowed),
// VITE_API_URL is baked into this bundle as-is at build time with no
// parsing anywhere - there is exactly one place the frontend calls home to.
// If it's accidentally set to a comma-separated list (an easy mistake given
// FRONTEND_URL's different rule), fail soft by using just the first entry
// and say so loudly, rather than silently building a malformed base URL
// that breaks every single request with no useful error.
const API_URL = _RAW_API_URL.split(",")[0].trim();
if (_RAW_API_URL.includes(",")) {
  // eslint-disable-next-line no-console
  console.warn(
    `VITE_API_URL is set to multiple comma-separated values ("${_RAW_API_URL}"). ` +
      `It must be a single URL - using only the first one ("${API_URL}"). ` +
      "Fix VITE_API_URL in your .env and rebuild."
  );
}

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
