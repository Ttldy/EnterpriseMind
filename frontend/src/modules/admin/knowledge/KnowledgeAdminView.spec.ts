import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus, {
  ElMessageBox,
} from "element-plus";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import KnowledgeAdminView from "./KnowledgeAdminView.vue";
import {
  fetchKnowledgeBases,
  removeKnowledgeBase,
  renameKnowledgeBase,
} from "./api";

vi.mock("./api", () => ({
  addPermission: vi.fn(),
  createKnowledgeBase: vi.fn(),
  fetchDocuments: vi.fn().mockResolvedValue([]),
  fetchKnowledgeBases: vi.fn(),
  removeDocument: vi.fn(),
  removeKnowledgeBase: vi.fn(),
  renameKnowledgeBase: vi.fn(),
  uploadDocument: vi.fn(),
}));

const base = {
  id: 7,
  name: "IT 知识库",
  domain: "it",
  sensitivity: "internal",
  is_public: false,
  permissions: [],
  document_count: 0,
};

describe("KnowledgeAdminView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(fetchKnowledgeBases).mockResolvedValue([base]);
  });

  it("renames a knowledge base and reloads the list", async () => {
    vi.mocked(renameKnowledgeBase).mockResolvedValue({
      id: 7,
      name: "IT 服务台",
    });
    const wrapper = mount(KnowledgeAdminView, {
      global: {
        plugins: [ElementPlus],
        stubs: { teleport: true },
      },
    });
    await flushPromises();

    await wrapper.get('[data-testid="rename-base-7"]').trigger("click");
    await wrapper.get('[data-testid="rename-input"]').setValue("IT 服务台");
    await wrapper.get('[data-testid="rename-submit"]').trigger("click");
    await flushPromises();

    expect(renameKnowledgeBase).toHaveBeenCalledWith(7, "IT 服务台");
    expect(fetchKnowledgeBases).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it("deletes a knowledge base after confirmation and reloads", async () => {
    const confirmed = "confirm" as unknown as Awaited<
      ReturnType<typeof ElMessageBox.confirm>
    >;
    vi.spyOn(ElMessageBox, "confirm").mockResolvedValue(confirmed);
    vi.mocked(removeKnowledgeBase).mockResolvedValue();
    const wrapper = mount(KnowledgeAdminView, {
      global: {
        plugins: [ElementPlus],
        stubs: { teleport: true },
      },
    });
    await flushPromises();

    await wrapper.get('[data-testid="delete-base-7"]').trigger("click");
    await flushPromises();

    expect(removeKnowledgeBase).toHaveBeenCalledWith(7);
    expect(fetchKnowledgeBases).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });
});
