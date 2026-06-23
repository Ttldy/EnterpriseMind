export interface Citation {
  document_id: number;
  filename: string;
  page: number;
  text: string;
  score: number;
}

export interface ChatMetadata {
  conversation_id: number;
  message_id: number;
  agent: string;
  intent: string;
  model: string;
  provider: string;
  model_route_reason: string;
  external_sent: boolean;
  sensitivity: string;
  trace_id: string;
  refused: boolean;
  citations: Citation[];
  sql: string | null;
  row_count: number | null;
}

export interface ChatMessage {
  localId: string;
  id?: number;
  role: "user" | "assistant";
  content: string;
  pending?: boolean;
  metadata?: ChatMetadata | undefined;
}

export interface ConversationSummary {
  id: number;
  title: string;
}

export interface ConversationDetail {
  id: number;
  title: string;
  messages: Array<{
    id: number;
    role: "user" | "assistant";
    content: string;
    agent: string | null;
    model: string | null;
    trace_id: string | null;
    citations: Citation[];
  }>;
}

export type StreamEvent =
  | {
      event: "metadata";
      data: ChatMetadata;
    }
  | {
      event: "chunk";
      data: { text: string };
    }
  | {
      event: "done";
      data: { ok: boolean };
    };