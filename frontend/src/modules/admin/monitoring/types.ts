export type HealthStatus = "HEALTHY" | "WARNING" | "DEGRADED" | "NO_DATA";

export interface MonitoringOverview {
  window_minutes: number;
  overall_health_score: number | null;
  overall_status: HealthStatus;
  total_events: number;
  success_rate: number;
  average_latency_ms: number;
  p95_latency_ms: number;
  timeout_rate: number;
  fallback_rate: number;
  circuit_open_rate: number;
  reasons: string[];
  penalties: Record<string, number>;
  generated_at: string;
}

export interface ComponentHealth {
  component: string;
  event_count: number;
  success_rate: number;
  average_latency_ms: number;
  p95_latency_ms: number;
  timeout_rate: number;
  fallback_rate: number;
  circuit_open_rate: number;
  health_score: number | null;
  status: HealthStatus;
  reasons: string[];
  penalties: Record<string, number>;
}

export interface ComponentHealthResponse {
  window_minutes: number;
  items: ComponentHealth[];
  generated_at: string;
}

export interface MonitoringEvent {
  id: number;
  trace_id: string | null;
  component: string;
  operation: string;
  success: boolean;
  latency_ms: number;
  error_code: string | null;
  timeout: boolean;
  fallback: boolean;
  circuit_open: boolean;
  created_at: string;
}

export interface MonitoringEventResponse {
  items: MonitoringEvent[];
  total: number;
  limit: number;
  offset: number;
}
