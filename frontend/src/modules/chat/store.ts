import { defineStore } from "pinia";

import {
  deleteConversation,
  getConversation,
  listConversations,
  streamChat,
  submitFeedback,
} from "./api";
import type {
  ChatMessage,
  ConversationSummary,
} from "./types";

function localId(): string {
  return crypto.randomUUID();
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    conversations: [] as ConversationSummary[],
    activeConversationId: null as number | null,
    messages: [] as ChatMessage[],
    sending: false,
  }),
  actions: {
    async loadConversations(): Promise<void> {
      this.conversations = await listConversations();
    },
    async openConversation(id: number): Promise<void> {
      const detail = await getConversation(id);
      this.activeConversationId = id;
      this.messages = detail.messages.map(
        (message) => ({
          localId: localId(),
          id: message.id,
          role: message.role,
          content: message.content,
          metadata:
            message.role === "assistant"
              ? {
                  conversation_id: id,
                  message_id: message.id,
                  agent: message.agent ?? "unknown",
                  intent: "history",
                  model: message.model ?? "unknown",
                  provider: "history",
                  model_route_reason:
                    "loaded_from_history",
                  external_sent: false,
                  sensitivity: "unknown",
                  trace_id:
                    message.trace_id ?? "",
                  refused: false,
                  citations: message.citations,
                  sql: null,
                  row_count: null,
                }
              : undefined,
        }),
      );
    },
    startNewConversation(): void {
      this.activeConversationId = null;
      this.messages = [];
    },
    async removeConversation(id: number): Promise<void> {
      await deleteConversation(id);
      if (this.activeConversationId === id) {
        this.startNewConversation();
      }
      await this.loadConversations();
    },
    async send(message: string): Promise<void> {
      const trimmed = message.trim();
      if (!trimmed || this.sending) {
        return;
      }

      this.messages.push({
        localId: localId(),
        role: "user",
        content: trimmed,
      });
      const assistant: ChatMessage = {
        localId: localId(),
        role: "assistant",
        content: "",
        pending: true,
      };
      this.messages.push(assistant);
      const reactiveAssistant =
        this.messages[this.messages.length - 1];
      if (!reactiveAssistant) {
        throw new Error("无法创建助手消息");
      }
      this.sending = true;

      try {
        await streamChat(
          trimmed,
          this.activeConversationId,
          (event) => {
            if (event.event === "metadata") {
              reactiveAssistant.metadata = event.data;
              reactiveAssistant.id =
                event.data.message_id;
              this.activeConversationId =
                event.data.conversation_id;
            } else if (event.event === "chunk") {
              reactiveAssistant.content +=
                event.data.text;
            } else {
              reactiveAssistant.pending = false;
            }
          },
        );
        await this.loadConversations();
      } catch (error) {
        reactiveAssistant.pending = false;
        reactiveAssistant.content =
          error instanceof Error
            ? error.message
            : "问答失败";
        throw error;
      } finally {
        this.sending = false;
      }
    },
    async feedback(
      messageId: number,
      rating: -1 | 1,
    ): Promise<void> {
      await submitFeedback(messageId, rating);
    },
  },
});
