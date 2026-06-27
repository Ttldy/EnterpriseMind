<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { errorMessage } from "@/api/client";
import { fetchTrace, fetchTraces } from "./api";
import type {
  TraceDetail,
  TraceListItem,
} from "./api";

const rows = ref<TraceListItem[]>([]);
const total = ref(0);
const limit = 20;
const offset = ref(0);
const query = ref("");
const loading = ref(false);
const detailLoading = ref(false);
const detailVisible = ref(false);
const selected = ref<TraceDetail | null>(null);

async function load(): Promise<void> {
  loading.value = true;
  try {
    const traceId = query.value.trim();
    const result = await fetchTraces({
      limit,
      offset: offset.value,
      ...(traceId ? { trace_id: traceId } : {}),
    });
    rows.value = result.items;
    total.value = result.total;
  } catch (error) {
    ElMessage.error(errorMessage(error));
  } finally {
    loading.value = false;
  }
}

async function search(): Promise<void> {
  offset.value = 0;
  await load();
}

async function changePage(page: number): Promise<void> {
  offset.value = (page - 1) * limit;
  await load();
}

async function openDetail(traceId: string): Promise<void> {
  detailLoading.value = true;
  detailVisible.value = true;
  selected.value = null;
  try {
    selected.value = await fetchTrace(traceId);
  } catch (error) {
    detailVisible.value = false;
    ElMessage.error(errorMessage(error));
  } finally {
    detailLoading.value = false;
  }
}

function formatTime(value: string): string {
  return new Date(value).toLocaleString("zh-CN");
}

onMounted(load);
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h1 class="page-title">请求追踪</h1>
        <p class="muted">
          通过 trace_id 关联用户问题、Agent 路由、模型、引用与会话记录
        </p>
      </div>
    </div>

    <el-card shadow="never">
      <div class="trace-toolbar">
        <div data-testid="trace-search-input">
          <el-input
            v-model="query"
            clearable
            placeholder="输入完整 trace_id"
            @keyup.enter="search"
          />
        </div>
        <el-button
          type="primary"
          data-testid="trace-search-submit"
          :loading="loading"
          @click="search"
        >
          查询
        </el-button>
      </div>

      <el-table
        v-loading="loading"
        :data="rows"
        row-key="trace_id"
        empty-text="暂无请求追踪记录"
      >
        <el-table-column prop="created_at" label="时间" width="190">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户" width="110" />
        <el-table-column prop="question" label="问题" min-width="240" />
        <el-table-column prop="agent" label="Agent" width="110" />
        <el-table-column prop="model" label="模型" width="150" />
        <el-table-column prop="citation_count" label="引用" width="80" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button
              text
              type="primary"
              :data-testid="`trace-detail-${row.trace_id}`"
              @click="openDetail(row.trace_id)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > limit"
        class="pagination"
        layout="prev, pager, next, total"
        :page-size="limit"
        :total="total"
        :current-page="offset / limit + 1"
        @current-change="changePage"
      />
    </el-card>

    <el-dialog
      v-model="detailVisible"
      title="请求追踪详情"
      width="760px"
    >
      <div v-loading="detailLoading">
        <el-descriptions v-if="selected" :column="2" border>
          <el-descriptions-item label="Trace ID" :span="2">
            {{ selected.trace_id }}
          </el-descriptions-item>
          <el-descriptions-item label="用户">
            {{ selected.username }}
          </el-descriptions-item>
          <el-descriptions-item label="会话 ID">
            {{ selected.conversation_id }}
          </el-descriptions-item>
          <el-descriptions-item label="Agent">
            {{ selected.agent || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="模型">
            {{ selected.model || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="用户问题" :span="2">
            {{ selected.user_message }}
          </el-descriptions-item>
          <el-descriptions-item label="助手回答" :span="2">
            {{ selected.assistant_message }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selected" class="citation-list">
          <h3>引用（{{ selected.citations.length }}）</h3>
          <el-empty
            v-if="selected.citations.length === 0"
            description="本次回答没有引用"
            :image-size="60"
          />
          <el-card
            v-for="citation in selected.citations"
            :key="`${citation.document_id ?? citation.filename}-${citation.page}`"
            class="citation-card"
            shadow="never"
          >
            <strong>{{ citation.filename }} · 第 {{ citation.page }} 页</strong>
            <p>{{ citation.text }}</p>
          </el-card>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.trace-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.trace-toolbar > div {
  width: min(520px, 100%);
}

.pagination,
.citation-list {
  margin-top: 16px;
}

.citation-card {
  margin-top: 10px;
}

.citation-card p {
  margin-bottom: 0;
  color: #475569;
}
</style>
