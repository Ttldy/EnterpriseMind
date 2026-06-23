import { defineStore } from "pinia";

import {
  api,
  clearAccessToken,
  readAccessToken,
  saveAccessToken,
} from "@/api/client";

import type {
  CurrentUser,
  LoginResponse,
} from "./types";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: readAccessToken(),
    user: null as CurrentUser | null,
    loading: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    isAdmin: (state) =>
      state.user?.roles.includes("admin") ?? false,
  },
  actions: {
    async login(
      username: string,
      password: string,
    ): Promise<void> {
      this.loading = true;
      try {
        const form = new URLSearchParams();
        form.set("username", username);
        form.set("password", password);
        const response = await api.post<LoginResponse>(
          "/auth/login",
          form,
          {
            headers: {
              "Content-Type":
                "application/x-www-form-urlencoded",
            },
          },
        );
        this.token = response.data.access_token;
        saveAccessToken(this.token);
        await this.loadCurrentUser();
      } finally {
        this.loading = false;
      }
    },
    async loadCurrentUser(): Promise<void> {
      if (!this.token) {
        this.user = null;
        return;
      }
      const response =
        await api.get<CurrentUser>("/auth/me");
      this.user = response.data;
    },
    logout(): void {
      clearAccessToken();
      this.token = "";
      this.user = null;
    },
  },
});