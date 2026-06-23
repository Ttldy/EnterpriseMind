<script setup lang="ts">
import { ElMessage } from "element-plus";

import CitationCard from "./CitationCard.vue";
import SqlDetails from "./SqlDetails.vue";
import type { ChatMessage } from "./types";

const props = defineProps<{
  message: ChatMessage;
}>();

const emit = defineEmits<{
  feedback: [messageId: number, rating: -1 | 1];
}>();

function feedback(rating: -1 | 1): void {
  if (!props.message.id) {
    ElMessage.warning("消息尚未保存");
    return;
  }
  emit("feedback", props.message.id, rating);
}
</script>

<template>
  <article
    class="message"
    :class="`message-${message.role}`"
  >
    <div class="message-head">
      <strong>
        {{ message.role === "user" ? "你" : "助手" }}
      </strong>
      <div
        v-if="message.metadata"
        class="message-tags"
      >
        <el-tag size="small">
          {{ message.metadata.agent }}
        </el-tag>
        <el-tag
          size="small"
          :type="
            message.metadata.external_sent
              ? 'warning'
              : 'success'
          "
        >
          {{ message.metadata.provider }}
        </el-tag>
        <el-tag size="small" type="info">
          {{ message.metadata.sensitivity }}
        </el-tag>
      </div>
    </div>

    <div class="message-content">
      {{ message.content }}
      <span v-if="message.pending" class="cursor" />
    </div>

    <el-alert
      v-if="message.metadata?.refused"
      type="warning"
      title="系统已安全拒答"
      :closable="false"
      show-icon
    />

    <CitationCard
      v-for="citation in message.metadata?.citations"
      :key="
        `${citation.document_id}-${citation.page}`
      "
      :citation="citation"
    />

    <SqlDetails
      v-if="message.metadata?.sql"
      :sql="message.metadata.sql"
      :row-count="message.metadata.row_count"
    />

    <div
      v-if="
        message.role === 'assistant' &&
        message.id &&
        !message.pending
      "
      class="message-actions"
    >
      <el-button text @click="feedback(1)">
        有帮助
      </el-button>
      <el-button text @click="feedback(-1)">
        没帮助
      </el-button>
      <span
        v-if="message.metadata?.trace_id"
        class="trace-id"
      >
        trace: {{ message.metadata.trace_id }}
      </span>
    </div>
  </article>
</template>

<style scoped>
.message {
  max-width: 860px;
  margin: 0 auto 18px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: white;
}

.message-user {
  border-color: #bfdbfe;
  background: #eff6ff;
}

.message-head,
.message-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.message-head {
  justify-content: space-between;
}

.message-tags {
  display: flex;
  gap: 6px;
}

.message-content {
  margin: 14px 0;
  line-height: 1.8;
  white-space: pre-wrap;
}

.cursor {
  display: inline-block;
  width: 7px;
  height: 16px;
  margin-left: 3px;
  background: #2563eb;
  animation: blink 0.8s infinite;
}

.trace-id {
  margin-left: auto;
  color: #94a3b8;
  font-size: 12px;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}
</style>