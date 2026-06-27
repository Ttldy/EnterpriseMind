import { api } from "@/api/client";

export interface TraceListItem {
  trace_id: string;
  created_at: string;
  username: string;
  conversation_id: number;
  question: string;
  answer_preview: string;
  agent: string | null;
  model: string | null;
  citation_count: number;
}

export interface TraceCitation {
  document_id: number | null;
  filename: string;
  page: number;
  text: string;
  score: number;
}

export interface TraceDetail {
  trace_id: string;
  username: string;
  conversation_id: number;
  user_message: string;
  assistant_message: string;
  agent: string | null;
  model: string | null;
  citations: TraceCitation[];
  created_at: string;
}

export interface TraceListResponse {
  items: TraceListItem[];
  total: number;
  limit: number;
  offset: number;
}

export async function fetchTraces(
  params: {
    trace_id?: string;
    limit: number;
    offset: number;
  },
): Promise<TraceListResponse> {
  const response = await api.get<TraceListResponse>(
    "/admin/traces",
    { params },
  );
  return response.data;
}

export async function fetchTrace(
  traceId: string,
): Promise<TraceDetail> {
  const response = await api.get<TraceDetail>(
    `/admin/traces/${encodeURIComponent(traceId)}`,
  );
  return response.data;
}

