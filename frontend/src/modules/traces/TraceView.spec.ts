import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import TraceView from "./TraceView.vue";
import { fetchTrace, fetchTraces } from "./api";

vi.mock("./api", () => ({
  fetchTrace: vi.fn(),
  fetchTraces: vi.fn(),
}));

const row = {
  trace_id: "trace-abc",
  created_at: "2026-06-28T00:00:00Z",
  username: "it01",
  conversation_id: 8,
  question: "VPN 无法连接怎么办？",
  answer_preview: "请先检查网络。",
  agent: "it",
  model: "qwen2.5:3b",
  citation_count: 1,
};

function mountView() {
  return mount(TraceView, {
    global: {
      plugins: [ElementPlus],
      stubs: { teleport: true },
    },
  });
}

describe("TraceView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders a real empty state without stage placeholder", async () => {
    vi.mocked(fetchTraces).mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    });
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).not.toContain("阶段 5");
    expect(wrapper.text()).toContain("暂无请求追踪记录");
    wrapper.unmount();
  });

  it("searches by trace id and opens associated detail", async () => {
    vi.mocked(fetchTraces).mockResolvedValue({
      items: [row],
      total: 1,
      limit: 20,
      offset: 0,
    });
    vi.mocked(fetchTrace).mockResolvedValue({
      trace_id: row.trace_id,
      username: row.username,
      conversation_id: row.conversation_id,
      user_message: row.question,
      assistant_message: row.answer_preview,
      agent: row.agent,
      model: row.model,
      citations: [
        {
          document_id: 3,
          filename: "vpn.md",
          page: 1,
          text: "VPN 排查",
          score: 0.9,
        },
      ],
      created_at: row.created_at,
    });
    const wrapper = mountView();
    await flushPromises();

    await wrapper.get('[data-testid="trace-search-input"] input').setValue(
      row.trace_id,
    );
    await wrapper.get('[data-testid="trace-search-submit"]').trigger("click");
    await flushPromises();
    expect(fetchTraces).toHaveBeenLastCalledWith({
      trace_id: row.trace_id,
      limit: 20,
      offset: 0,
    });

    await wrapper.get('[data-testid="trace-detail-trace-abc"]').trigger("click");
    await flushPromises();
    expect(fetchTrace).toHaveBeenCalledWith(row.trace_id);
    expect(wrapper.text()).toContain("VPN 无法连接怎么办？");
    expect(wrapper.text()).toContain("vpn.md");
    wrapper.unmount();
  });
});

