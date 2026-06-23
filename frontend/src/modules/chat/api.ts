import { api, readAccessToken } from "@/api/client";

import type {
  ChatMetadata,
  ConversationDetail,
  ConversationSummary,
  StreamEvent,
} from "./types";

export async function listConversations(): Promise<
  ConversationSummary[]
> {
  const response =
    await api.get<ConversationSummary[]>(
      "/conversations",
    );
  return response.data;
}

export async function getConversation(
  id: number,
): Promise<ConversationDetail> {
  const response =
    await api.get<ConversationDetail>(
      `/conversations/${id}`,
    );
  return response.data;
}

export async function deleteConversation(
  id: number,
): Promise<void> {
  await api.delete(`/conversations/${id}`);
}

export async function submitFeedback(
  messageId: number,
  rating: -1 | 1,
): Promise<void> {
  await api.post(
    `/conversations/messages/${messageId}/feedback`,
    {
      rating,
      comment: null,
    },
  );
}

function parseEvent(
  block: string,
): StreamEvent | null {
  const lines = block.split("\n");
  const eventName = lines
    .find((line) => line.startsWith("event: "))
    ?.slice(7);
  const dataText = lines
    .find((line) => line.startsWith("data: "))
    ?.slice(6);

  if (!eventName || !dataText) {
    return null;
  }

  const data = JSON.parse(dataText) as unknown;
  if (eventName === "metadata") {
    return {
      event: "metadata",
      data: data as ChatMetadata,
    };
  }
  if (eventName === "chunk") {
    return {
      event: "chunk",
      data: data as { text: string },
    };
  }
  if (eventName === "done") {
    return {
      event: "done",
      data: data as { ok: boolean },
    };
  }
  return null;
}

export async function streamChat(
  message: string,
  conversationId: number | null,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch(
    "/api/v1/chat/stream",
    {
      method: "POST",
      headers: {
        Authorization:
          `Bearer ${readAccessToken()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    },
  );

  if (!response.ok) {
    throw new Error(
      `问答请求失败：${response.status}`,
    );
  }
  if (!response.body) {
    throw new Error("浏览器不支持流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, {
      stream: !done,
    });

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const event = parseEvent(block);
      if (event) {
        onEvent(event);
      }
    }

    if (done) {
      break;
    }
  }
}