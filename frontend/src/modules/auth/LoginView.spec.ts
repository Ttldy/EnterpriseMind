import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import { createRouter, createWebHistory } from "vue-router";
import { describe, expect, it, vi } from "vitest";

import LoginView from "./LoginView.vue";

describe("LoginView", () => {
  it("accepts username and password", async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: "/",
          component: LoginView,
        },
      ],
    });
    const wrapper = mount(LoginView, {
      global: {
        plugins: [
          ElementPlus,
          router,
          createTestingPinia({
            createSpy: vi.fn,
          }),
        ],
      },
    });

    await wrapper
      .get('[data-testid="username"] input')
      .setValue("it01");
    await wrapper
      .get('[data-testid="password"] input')
      .setValue("ItPassw0rd!");

    expect(
      (
        wrapper.get(
          '[data-testid="username"] input',
        ).element as HTMLInputElement
      ).value,
    ).toBe("it01");

    wrapper.unmount();
  });
});