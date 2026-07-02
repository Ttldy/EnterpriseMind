import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import { describe, expect, it, vi } from "vitest";

import AppLayout from "./AppLayout.vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({ path: "/admin/monitoring" }),
  useRouter: () => ({ replace: vi.fn() }),
}));

describe("AppLayout admin monitoring navigation", () => {
  it("shows the monitoring menu to administrators", () => {
    const wrapper = mount(AppLayout, {
      global: {
        plugins: [
          createTestingPinia({
            createSpy: vi.fn,
            initialState: {
              auth: {
                token: "test-token",
                user: {
                  id: 1,
                  username: "admin",
                  department: "GENERAL",
                  roles: ["admin"],
                },
              },
            },
          }),
          ElementPlus,
        ],
        stubs: { RouterView: true },
      },
    });

    expect(wrapper.text()).toContain("运行监控");
    expect(
      wrapper.find('[index="/admin/monitoring"]').exists(),
    ).toBe(true);
    wrapper.unmount();
  });
});
