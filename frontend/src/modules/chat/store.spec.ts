import {
  createPinia,
  setActivePinia,
} from "pinia";
import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { nextTick, watch } from "vue";

import { streamChat } from "./api";
import { useChatStore } from "./store";

vi.mock("./api", () => ({
  deleteConversation: vi.fn(),
  getConversation: vi.fn(),
  listConversations: vi.fn(
    async () => [],
  ),
  streamChat: vi.fn(),
  submitFeedback: vi.fn(),
}));

describe("chat store streaming", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("reactively publishes every answer chunk", async () => {
    vi.mocked(streamChat).mockImplementation(
      async (_message, _conversationId, onEvent) => {
        onEvent({
          event: "chunk",
          data: { text: "第一块" },
        });
        await nextTick();
        onEvent({
          event: "chunk",
          data: { text: "第二块" },
        });
        onEvent({
          event: "done",
          data: { ok: true },
        });
      },
    );

    const chat = useChatStore();
    const renderedContents: string[] = [];
    watch(
      () => chat.messages[1]?.content,
      (content) => {
        if (content) {
          renderedContents.push(content);
        }
      },
    );

    await chat.send("测试流式显示");
    await nextTick();

    expect(renderedContents).toEqual([
      "第一块",
      "第一块第二块",
    ]);
  });
});
