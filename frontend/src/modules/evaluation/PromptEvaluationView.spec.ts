import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus, { ElMessage } from "element-plus";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import PromptEvaluationView from "./PromptEvaluationView.vue";
import { createPrompt, listPrompts } from "./api";

vi.mock("./api", () => ({
  activatePrompt: vi.fn(),
  createPrompt: vi.fn(),
  listPrompts: vi.fn(),
  rollbackPrompt: vi.fn(),
  runEvaluation: vi.fn(),
}));

const candidate = {
  id: 12,
  prompt_key: "it_agent",
  version: 2,
  content: "You are the internal IT support agent.",
  content_sha256: "0".repeat(64),
  is_active: false,
  status: "candidate" as const,
  created_at: "2026-06-28T00:00:00Z",
};

function mountView() {
  return mount(PromptEvaluationView, {
    global: {
      plugins: [ElementPlus],
      stubs: {
        teleport: true,
        ElSelect: {
          template: "<div><slot /></div>",
        },
        ElOption: true,
      },
    },
  });
}

describe("PromptEvaluationView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(listPrompts).mockResolvedValue([]);
  });

  it("creates a real candidate and reloads the version list", async () => {
    vi.mocked(createPrompt).mockResolvedValue(candidate);
    vi.mocked(listPrompts)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([candidate]);
    const wrapper = mountView();
    await flushPromises();

    await wrapper.get('[data-testid="open-prompt-create"]').trigger("click");
    await wrapper
      .get('[data-testid="prompt-content"]')
      .setValue(candidate.content);
    await wrapper.get('[data-testid="prompt-create-submit"]').trigger("click");
    await flushPromises();

    expect(createPrompt).toHaveBeenCalledWith(
      "finance_agent",
      candidate.content,
    );
    expect(listPrompts).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("候选");
    expect(wrapper.text()).toContain("2");
    wrapper.unmount();
  });

  it("shows the API error and never reports false success", async () => {
    vi.mocked(createPrompt).mockRejectedValue(new Error("create failed"));
    const success = vi.spyOn(ElMessage, "success");
    const error = vi.spyOn(ElMessage, "error");
    const wrapper = mountView();
    await flushPromises();

    await wrapper.get('[data-testid="open-prompt-create"]').trigger("click");
    await wrapper
      .get('[data-testid="prompt-content"]')
      .setValue(candidate.content);
    await wrapper.get('[data-testid="prompt-create-submit"]').trigger("click");
    await flushPromises();

    expect(error).toHaveBeenCalled();
    expect(success).not.toHaveBeenCalled();
    expect(listPrompts).toHaveBeenCalledOnce();
    wrapper.unmount();
  });
});
