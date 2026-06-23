import axios from "axios";

const TOKEN_KEY = "enterprisemind_access_token";

export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30_000,
});

export function readAccessToken(): string {
  return sessionStorage.getItem(TOKEN_KEY) ?? "";
}

export function saveAccessToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = readAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (
      axios.isAxiosError(error) &&
      error.response?.status === 401
    ) {
      clearAccessToken();
      window.dispatchEvent(
        new CustomEvent("auth:expired"),
      );
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (error.code === "ECONNABORTED") {
      return "请求超时，请稍后重试";
    }
  }
  return "请求失败，请检查后端服务";
}