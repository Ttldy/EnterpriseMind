import { api } from "@/api/client";
import type { ComponentHealthResponse, MonitoringEventResponse, MonitoringOverview } from "./types";

export async function fetchMonitoringOverview(windowMinutes: number): Promise<MonitoringOverview> {
  const response = await api.get<MonitoringOverview>("/admin/monitoring/overview", { params: { window_minutes: windowMinutes } });
  return response.data;
}

export async function fetchMonitoringComponents(windowMinutes: number): Promise<ComponentHealthResponse> {
  const response = await api.get<ComponentHealthResponse>("/admin/monitoring/components", { params: { window_minutes: windowMinutes } });
  return response.data;
}

export async function fetchMonitoringEvents(windowMinutes: number): Promise<MonitoringEventResponse> {
  const response = await api.get<MonitoringEventResponse>("/admin/monitoring/events", {
    params: { window_minutes: windowMinutes, success: false, limit: 20, offset: 0 },
  });
  return response.data;
}
