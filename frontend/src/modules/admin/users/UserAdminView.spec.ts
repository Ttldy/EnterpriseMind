import {
  flushPromises,
  mount,
} from "@vue/test-utils";
import ElementPlus from "element-plus";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import UserAdminView from "./UserAdminView.vue";
import {
  fetchUserOptions,
  fetchUsers,
} from "./api";

vi.mock("./api", () => ({
  createUser: vi.fn(),
  fetchUserOptions: vi.fn(),
  fetchUsers: vi.fn(),
  updateUser: vi.fn(),
}));

describe("UserAdminView", () => {
  beforeEach(() => {
    vi.mocked(fetchUsers).mockResolvedValue([
      {
        id: 5,
        username: "admin",
        department: {
          id: 1,
          name: "GENERAL",
        },
        roles: [
          {
            id: 5,
            name: "admin",
          },
        ],
        is_active: true,
      },
    ]);
    vi.mocked(
      fetchUserOptions,
    ).mockResolvedValue({
      departments: [
        {
          id: 1,
          name: "GENERAL",
        },
      ],
      roles: [
        {
          id: 5,
          name: "admin",
        },
      ],
    });
  });

  it("loads users when mounted", async () => {
    const wrapper = mount(UserAdminView, {
      global: {
        plugins: [ElementPlus],
      },
    });

    await flushPromises();

    expect(fetchUsers).toHaveBeenCalledOnce();
    expect(
      fetchUserOptions,
    ).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain("admin");

    wrapper.unmount();
  });
});
