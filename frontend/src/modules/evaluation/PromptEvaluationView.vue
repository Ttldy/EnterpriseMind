<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import {
  activatePrompt,
  createPrompt,
  listPrompts,
  rollbackPrompt,
  runEvaluation,
} from "./api";
import type {
  EvaluationResult,
  PromptVersion,
} from "./api";

const prompts = ref<PromptVersion[]>([]);
const selected = ref<PromptVersion | null>(null);
const result = ref<EvaluationResult | null>(null);
const dialogVisible = ref(false);
const running = ref(false);
const form = reactive({
  prompt_key: "finance_agent",
  content: "",
});

async function load(): Promise<void> {
  prompts.value = await listPrompts();
}

async function create(): Promise<void> {
  await createPrompt(
    form.prompt_key,
    form.content,
  );
  dialogVisible.value = false;
  await load();
  ElMessage.success("候选版本已创建");
}

async function evaluate(
  item: PromptVersion,
): Promise<void> {
  selected.value = item;
  running.value = true;
  try {
    result.value = await runEvaluation(item.id);
  } finally {
    running.value = false;
  }
}

async function activate(
  item: PromptVersion,
): Promise<void> {
  await activatePrompt(item.id);
  await load();
  ElMessage.success("Prompt 已启用");
}

async function rollback(
  key: string,
): Promise<void> {
  await rollbackPrompt(key);
  await load();
  ElMessage.success("已回滚上一版本");
}

onMounted(load);
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h1 class="page-title">Prompt 与评测</h1>
        <p class="muted">
          候选版本必须通过发布门禁才能启用
        </p>
      </div>
      <el-button
        type="primary"
        @click="dialogVisible = true"
      >
        创建候选版本
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="prompts" row-key="id">
        <el-table-column
          prop="prompt_key"
          label="Prompt Key"
          width="190"
        />
        <el-table-column
          prop="version"
          label="版本"
          width="90"
        />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag
              :type="
                row.is_active
                  ? 'success'
                  : 'info'
              "
            >
              {{ row.is_active ? "启用" : "候选" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="content"
          label="内容"
          min-width="360"
          show-overflow-tooltip
        />
        <el-table-column label="操作" width="290">
          <template #default="{ row }">
            <el-button
              text
              :loading="running"
              @click="evaluate(row)"
            >
              运行评测
            </el-button>
            <el-button
              text
              type="success"
              :disabled="row.is_active"
              @click="activate(row)"
            >
              启用
            </el-button>
            <el-button
              text
              @click="rollback(row.prompt_key)"
            >
              回滚
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card
      v-if="result"
      class="result-card"
      shadow="never"
    >
      <h3>评测结果</h3>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="安全通过率">
          {{ (result.safety_pass_rate * 100).toFixed(1) }}%
        </el-descriptions-item>
        <el-descriptions-item label="发布">
          {{ result.release_allowed ? "允许" : "阻止" }}
        </el-descriptions-item>
        <el-descriptions-item label="耗时">
          {{ result.duration_ms }} ms
        </el-descriptions-item>
      </el-descriptions>
      <pre>{{ JSON.stringify(result.metrics, null, 2) }}</pre>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      title="创建候选 Prompt"
      width="720px"
    >
      <el-form label-position="top">
        <el-form-item label="Prompt Key">
          <el-select
            v-model="form.prompt_key"
            style="width: 100%"
          >
            <el-option label="HR" value="hr_agent" />
            <el-option label="IT" value="it_agent" />
            <el-option
              label="财务"
              value="finance_agent"
            />
            <el-option
              label="数据分析"
              value="data_analyst_agent"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Prompt 内容">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="12"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">
          取消
        </el-button>
        <el-button type="primary" @click="create">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.result-card {
  margin-top: 18px;
}

pre {
  padding: 14px;
  border-radius: 8px;
  background: #f8fafc;
}
</style>
