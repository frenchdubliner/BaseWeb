import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: `${API_URL}/api/auth`,
});

export function getTokens() {
  return {
    access: localStorage.getItem("access"),
    refresh: localStorage.getItem("refresh"),
  };
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem("access", access);
  if (refresh) localStorage.setItem("refresh", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
}

client.interceptors.request.use((config) => {
  const { access } = getTokens();
  if (access) {
    config.headers.Authorization = `Bearer ${access}`;
  }
  return config;
});

let refreshPromise = null;

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isAuthEndpoint = original?.url?.includes("/login") || original?.url?.includes("/register");

    if (error.response?.status === 401 && original && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      const { refresh } = getTokens();
      if (!refresh) {
        clearTokens();
        return Promise.reject(error);
      }

      try {
        if (!refreshPromise) {
          refreshPromise = client
            .post("/login/refresh/", { refresh })
            .finally(() => {
              refreshPromise = null;
            });
        }
        const { data } = await refreshPromise;
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

export default client;
