<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import {
  ElMessage,
  ElMessageBox,
  type UploadFile,
} from "element-plus";

import { errorMessage } from "@/api/client";
import DocumentStatus from "./DocumentStatus.vue";
import {
  addPermission,
  createKnowledgeBase,
  fetchDocuments,
  fetchKnowledgeBases,
  removeDocument,
  uploadDocument,
} from "./api";
import type {
  DocumentRow,
  KnowledgeBaseRow,
} from "./api";

const bases = ref<KnowledgeBaseRow[]>([]);
const documents = ref<DocumentRow[]>([]);
const activeBaseId = ref<number | null>(null);
const loading = ref(false);
const createVisible = ref(false);
const permissionVisible = ref(false);
const uploadVisible = ref(false);
const selectedFile = ref<File | null>(null);

const baseForm = reactive({
  name: "",
  domain: "it",
  sensitivity: "internal",
  is_public: false,
});

const permissionForm = reactive({
  subject_type: "ROLE" as
    | "ROLE"
    | "DEPARTMENT",
  subject_value: "",
});

async function loadBases(): Promise<void> {
  loading.value = true;
  try {
    bases.value = await fetchKnowledgeBases();
    if (
      activeBaseId.value === null &&
      bases.value[0]
    ) {
      await selectBase(bases.value[0].id);
    }
  } finally {
    loading.value = false;
  }
}

async function selectBase(id: number): Promise<void> {
  activeBaseId.value = id;
  documents.value = await fetchDocuments(id);
}

async function submitBase(): Promise<void> {
  try {
    const result = await createKnowledgeBase(
      baseForm,
    );
    createVisible.value = false;
    await loadBases();
    await selectBase(result.id);
    ElMessage.success("知识库创建成功");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}

async function submitPermission(): Promise<void> {
  if (!activeBaseId.value) {
    return;
  }
  try {
    await addPermission(
      activeBaseId.value,
      permissionForm,
    );
    permissionVisible.value = false;
    await loadBases();
    ElMessage.success("权限添加成功");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}

function chooseFile(file: UploadFile): void {
  selectedFile.value = file.raw ?? null;
}

async function submitUpload(): Promise<void> {
  if (!activeBaseId.value || !selectedFile.value) {
    ElMessage.warning("请选择文件");
    return;
  }
  try {
    await uploadDocument(
      activeBaseId.value,
      selectedFile.value,
    );
    uploadVisible.value = false;
    selectedFile.value = null;
    await selectBase(activeBaseId.value);
    await loadBases();
    ElMessage.success("文件上传并入库成功");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}

async function deleteFile(id: number): Promise<void> {
  await ElMessageBox.confirm(
    "删除后会同步删除向量和原文件，是否继续？",
    "删除文档",
    { type: "warning" },
  );
  await removeDocument(id);
  if (activeBaseId.value) {
    await selectBase(activeBaseId.value);
  }
  await loadBases();
}

onMounted(loadBases);
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h1 class="page-title">知识库与文档</h1>
        <p class="muted">
          管理知识库、角色/部门权限和文档
        </p>
      </div>
      <el-button
        type="primary"
        @click="createVisible = true"
      >
        创建知识库
      </el-button>
    </div>

    <div class="knowledge-grid">
      <el-card shadow="never">
        <template #header>知识库</template>
        <div
          v-for="item in bases"
          :key="item.id"
          class="base-item"
          :class="{
            active: item.id === activeBaseId,
          }"
          @click="selectBase(item.id)"
        >
          <div>
            <strong>{{ item.name }}</strong>
            <div class="base-tags">
              <el-tag size="small">
                {{ item.domain }}
              </el-tag>
              <el-tag size="small" type="info">
                {{ item.sensitivity }}
              </el-tag>
            </div>
          </div>
          <span>{{ item.document_count }} 个文档</span>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="document-header">
            <span>文档</span>
            <div>
              <el-button
                :disabled="!activeBaseId"
                @click="permissionVisible = true"
              >
                添加权限
              </el-button>
              <el-button
                type="primary"
                :disabled="!activeBaseId"
                @click="uploadVisible = true"
              >
                上传文件
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          v-loading="loading"
          :data="documents"
          row-key="id"
        >
          <el-table-column
            prop="filename"
            label="文件名"
            min-width="260"
          />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <DocumentStatus
                :status="row.status"
                :error="row.error_message"
              />
            </template>
          </el-table-column>
          <el-table-column
            prop="sensitivity"
            label="敏感等级"
            width="120"
          />
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button
                text
                type="danger"
                @click="deleteFile(row.id)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog
      v-model="createVisible"
      title="创建知识库"
      width="520px"
    >
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="baseForm.name" />
        </el-form-item>
        <el-form-item label="领域">
          <el-select
            v-model="baseForm.domain"
            class="full-width"
          >
            <el-option label="人事" value="hr" />
            <el-option label="IT" value="it" />
            <el-option
              label="财务"
              value="finance"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="敏感等级">
          <el-select
            v-model="baseForm.sensitivity"
            class="full-width"
          >
            <el-option
              label="公开"
              value="public"
            />
            <el-option
              label="内部"
              value="internal"
            />
            <el-option
              label="敏感"
              value="sensitive"
            />
          </el-select>
        </el-form-item>
        <el-checkbox v-model="baseForm.is_public">
          所有员工可访问
        </el-checkbox>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="submitBase"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="permissionVisible"
      title="添加访问权限"
      width="480px"
    >
      <el-form label-position="top">
        <el-form-item label="授权类型">
          <el-select
            v-model="permissionForm.subject_type"
            class="full-width"
          >
            <el-option label="角色" value="ROLE" />
            <el-option
              label="部门"
              value="DEPARTMENT"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="角色或部门名称">
          <el-input
            v-model="permissionForm.subject_value"
            placeholder="例如 it_staff 或 IT"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button
          @click="permissionVisible = false"
        >
          取消
        </el-button>
        <el-button
          type="primary"
          @click="submitPermission"
        >
          添加
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="uploadVisible"
      title="上传文档"
      width="520px"
    >
      <el-upload
        :auto-upload="false"
        :limit="1"
        accept=".pdf,.docx,.md,.txt"
        @change="chooseFile"
      >
        <el-button>选择文件</el-button>
        <template #tip>
          <div class="muted">
            支持 PDF、DOCX、Markdown 和 TXT，
            最大 10 MB
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="uploadVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          @click="submitUpload"
        >
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.knowledge-grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 18px;
}

.base-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
}

.base-item:hover,
.base-item.active {
  background: #eff6ff;
}

.base-tags {
  display: flex;
  gap: 5px;
  margin-top: 7px;
}

.document-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.full-width {
  width: 100%;
}
</style>