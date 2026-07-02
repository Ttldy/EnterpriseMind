import { flushPromises, mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MonitoringView from "./MonitoringView.vue";
import {
  fetchMonitoringComponents,
  fetchMonitoringEvents,
  fetchMonitoringOverview,
} from "./api";

vi.mock("./api", () => ({
  fetchMonitoringComponents: vi.fn(),
  fetchMonitoringEvents: vi.fn(),
  fetchMonitoringOverview: vi.fn(),
}));

const overview = {
  window_minutes: 5,
  overall_health_score: 0.92,
  overall_status: "HEALTHY" as const,
  total_events: 12,
  success_rate: 0.92,
  average_latency_ms: 120,
  p95_latency_ms: 260,
  timeout_rate: 0,
  fallback_rate: 0.08,
  circuit_open_rate: 0,
  reasons: ["运行正常"],
  penalties: {},
  generated_at: "2026-07-02T00:00:00Z",
};

function arrange(): void {
  vi.mocked(fetchMonitoringOverview).mockResolvedValue(overview);
  vi.mocked(fetchMonitoringComponents).mockResolvedValue({
    window_minutes: 5,
    generated_at: overview.generated_at,
    items: [
      {
        component: "retrieval",
        event_count: 5,
        success_rate: 1,
        average_latency_ms: 100,
        p95_latency_ms: 160,
        timeout_rate: 0,
        fallback_rate: 0,
        circuit_open_rate: 0,
        health_score: 1,
        status: "HEALTHY",
        reasons: ["运行正常"],
        penalties: {},
      },
    ],
  });
  vi.mocked(fetchMonitoringEvents).mockResolvedValue({
    items: [],
    total: 0,
    limit: 20,
    offset: 0,
  });
}

function mountView() {
  return mount(MonitoringView, {
    global: { plugins: [ElementPlus] },
  });
}

describe("MonitoringView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    arrange();
  });

  it("loads real overview and component health", async () => {
    const wrapper = mountView();
    await flushPromises();

    expect(fetchMonitoringOverview).toHaveBeenCalledWith(5);
    expect(wrapper.text()).toContain("92%");
    expect(wrapper.text()).toContain("retrieval");
    expect(wrapper.text()).toContain("暂无异常事件");
    wrapper.unmount();
  });

  it("renders NO_DATA and supports guarded manual refresh", async () => {
    vi.mocked(fetchMonitoringOverview).mockResolvedValue({
      ...overview,
      overall_health_score: null,
      overall_status: "NO_DATA",
      total_events: 0,
    });
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).toContain("暂无数据");
    const button = wrapper.get('[data-testid="monitor-refresh"]');
    await button.trigger("click");
    await button.trigger("click");
    await flushPromises();
    expect(fetchMonitoringOverview).toHaveBeenCalledTimes(2);
    wrapper.unmount();
  });

  it("shows an error state without crashing", async () => {
    vi.mocked(fetchMonitoringOverview).mockRejectedValue(
      new Error("monitor unavailable"),
    );
    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.text()).toContain("监控数据加载失败");
    wrapper.unmount();
  });
});
