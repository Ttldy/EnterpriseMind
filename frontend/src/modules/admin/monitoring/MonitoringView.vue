<script setup lang="ts">
import { onMounted, ref } from "vue";
import { errorMessage } from "@/api/client";
import { fetchMonitoringComponents, fetchMonitoringEvents, fetchMonitoringOverview } from "./api";
import type { ComponentHealth, HealthStatus, MonitoringEvent, MonitoringOverview } from "./types";

const windowMinutes = ref(5);
const overview = ref<MonitoringOverview | null>(null);
const components = ref<ComponentHealth[]>([]);
const events = ref<MonitoringEvent[]>([]);
const loading = ref(false);
const loadError = ref("");

function percent(value: number | null): string {
  return value === null ? "暂无数据" : `${Math.round(value * 100)}%`;
}
function statusType(status: HealthStatus): "success" | "warning" | "danger" | "info" {
  if (status === "HEALTHY") return "success";
  if (status === "WARNING") return "warning";
  if (status === "DEGRADED") return "danger";
  return "info";
}
function formatTime(value: string): string {
  return new Date(value).toLocaleString("zh-CN");
}
async function load(): Promise<void> {
  if (loading.value) return;
  loading.value = true;
  loadError.value = "";
  try {
    const [summary, componentResult, eventResult] = await Promise.all([
      fetchMonitoringOverview(windowMinutes.value),
      fetchMonitoringComponents(windowMinutes.value),
      fetchMonitoringEvents(windowMinutes.value),
    ]);
    overview.value = summary;
    components.value = componentResult.items;
    events.value = eventResult.items;
  } catch (error) {
    loadError.value = `监控数据加载失败：${errorMessage(error)}`;
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <div class="page-shell" v-loading="loading">
    <div class="page-header">
      <div><h1 class="page-title">运行监控</h1><p class="muted">基于真实运行事件展示最近时间窗口内的组件健康状态</p></div>
      <el-button type="primary" data-testid="monitor-refresh" :loading="loading" :disabled="loading" @click="load">手动刷新</el-button>
    </div>
    <el-alert v-if="loadError" :title="loadError" type="error" show-icon :closable="false" />
    <template v-if="overview">
      <div class="metric-grid">
        <el-card shadow="never"><span class="muted">总体健康分</span><strong class="metric">{{ percent(overview.overall_health_score) }}</strong><el-tag :type="statusType(overview.overall_status)">{{ overview.overall_status }}</el-tag></el-card>
        <el-card shadow="never"><span class="muted">事件数</span><strong class="metric">{{ overview.total_events }}</strong></el-card>
        <el-card shadow="never"><span class="muted">成功率</span><strong class="metric">{{ percent(overview.success_rate) }}</strong></el-card>
        <el-card shadow="never"><span class="muted">平均 / P95 延迟</span><strong class="metric">{{ Math.round(overview.average_latency_ms) }} / {{ overview.p95_latency_ms }} ms</strong></el-card>
        <el-card shadow="never"><span class="muted">超时率</span><strong class="metric">{{ percent(overview.timeout_rate) }}</strong></el-card>
        <el-card shadow="never"><span class="muted">Fallback / 熔断率</span><strong class="metric">{{ percent(overview.fallback_rate) }} / {{ percent(overview.circuit_open_rate) }}</strong></el-card>
      </div>
      <el-card shadow="never" class="section-card">
        <template #header>组件健康（最近 {{ overview.window_minutes }} 分钟）</template>
        <el-table :data="components" empty-text="暂无组件监控数据">
          <el-table-column prop="component" label="组件" min-width="150" />
          <el-table-column prop="event_count" label="事件数" width="90" />
          <el-table-column label="健康分" width="110"><template #default="{ row }">{{ percent(row.health_score) }}</template></el-table-column>
          <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column>
          <el-table-column label="成功率" width="100"><template #default="{ row }">{{ percent(row.success_rate) }}</template></el-table-column>
          <el-table-column prop="p95_latency_ms" label="P95(ms)" width="100" />
          <el-table-column label="原因" min-width="220"><template #default="{ row }">{{ row.reasons.join("；") }}</template></el-table-column>
        </el-table>
      </el-card>
      <el-card shadow="never" class="section-card">
        <template #header>最近异常事件</template>
        <el-table :data="events" empty-text="暂无异常事件">
          <el-table-column prop="created_at" label="时间" width="190"><template #default="{ row }">{{ formatTime(row.created_at) }}</template></el-table-column>
          <el-table-column prop="component" label="组件" width="150" />
          <el-table-column prop="operation" label="操作" width="160" />
          <el-table-column prop="error_code" label="错误码" min-width="160" />
          <el-table-column prop="latency_ms" label="耗时(ms)" width="100" />
          <el-table-column label="Trace ID" min-width="210"><template #default="{ row }"><router-link v-if="row.trace_id" :to="`/admin/traces?trace_id=${encodeURIComponent(row.trace_id)}`">{{ row.trace_id }}</router-link><span v-else>-</span></template></el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<style scoped>
.metric-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.metric { display: block; margin: 8px 0; font-size: 24px; }
.section-card { margin-top: 16px; }
@media (max-width: 900px) { .metric-grid { grid-template-columns: 1fr; } }
</style>
