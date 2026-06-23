<script setup lang="ts">
import {
  nextTick,
  onMounted,
  ref,
} from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import MessageBubble from "./MessageBubble.vue";
import { useChatStore } from "./store";

const chat = useChatStore();
const input = ref("");
const messageArea = ref<HTMLElement | null>(null);

async function scrollToBottom(): Promise<void> {
  await nextTick();
  messageArea.value?.scrollTo({
    top: messageArea.value.scrollHeight,
    behavior: "smooth",
  });
}

async function send(): Promise<void> {
  const message = input.value;
  if (!message.trim()) {
    return;
  }
  input.value = "";
  try {
    const promise = chat.send(message);
    await scrollToBottom();
    await promise;
    await scrollToBottom();
  } catch {
    ElMessage.error("问答失败，请检查后端和 Ollama");
  }
}

async function removeConversation(
  id: number,
): Promise<void> {
  await ElMessageBox.confirm(
    "确认删除该会话？",
    "删除会话",
    { type: "warning" },
  );
  await chat.removeConversation(id);
}

async function feedback(
  messageId: number,
  rating: -1 | 1,
): Promise<void> {
  try {
    await chat.feedback(messageId, rating);
    ElMessage.success("反馈已提交");
  } catch {
    ElMessage.error(
      "该消息可能已经提交过反馈",
    );
  }
}

onMounted(async () => {
  await chat.loadConversations();
});
</script>

<template>
  <div class="chat-layout">
    <aside class="conversation-panel">
      <el-button
        type="primary"
        class="new-button"
        @click="chat.startNewConversation"
      >
        新建会话
      </el-button>

      <div class="conversation-list">
        <div
          v-for="item in chat.conversations"
          :key="item.id"
          class="conversation-item"
          :class="{
            active:
              item.id === chat.activeConversationId,
          }"
        >
          <button
            class="conversation-title"
            @click="chat.openConversation(item.id)"
          >
            {{ item.title }}
          </button>
          <el-button
            text
            type="danger"
            @click="removeConversation(item.id)"
          >
            删除
          </el-button>
        </div>
      </div>
    </aside>

    <section class="chat-main">
      <header class="chat-header">
        <div>
          <h1>企业知识助手</h1>
          <p>
            人事制度 · IT 运维 · 财务报销 ·
            只读数据统计
          </p>
        </div>
        <el-tag type="success">
          权限由后端实时计算
        </el-tag>
      </header>

      <div ref="messageArea" class="message-area">
        <div
          v-if="chat.messages.length === 0"
          class="empty-state"
        >
          <h2>今天想了解什么？</h2>
          <p>
            例如：VPN 无法连接怎么办？
            或统计各部门报销金额。
          </p>
        </div>

        <MessageBubble
          v-for="message in chat.messages"
          :key="message.localId"
          :message="message"
          @feedback="feedback"
        />
      </div>

      <footer class="composer">
        <div data-testid="chat-input">
          <el-input
            v-model="input"
            type="textarea"
            :rows="3"
            resize="none"
            maxlength="4000"
            show-word-limit
            placeholder="请输入企业制度、IT、财务或统计问题"
            @keydown.ctrl.enter="send"
          />
        </div>
        <div class="composer-footer">
          <span>
            Ctrl + Enter 发送；敏感问题只走本地模型
          </span>
          <el-button
            data-testid="chat-send"
            type="primary"
            :loading="chat.sending"
            @click="send"
          >
            发送
          </el-button>
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.chat-layout {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  height: calc(100vh - 60px);
}

.conversation-panel {
  overflow-y: auto;
  padding: 16px;
  border-right: 1px solid #e5e7eb;
  background: white;
}

.new-button {
  width: 100%;
}

.conversation-list {
  margin-top: 16px;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 6px;
  border-radius: 8px;
}

.conversation-item.active {
  background: #eff6ff;
}

.conversation-title {
  overflow: hidden;
  flex: 1;
  padding: 10px;
  border: 0;
  background: transparent;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.chat-main {
  display: grid;
  min-width: 0;
  grid-template-rows: auto 1fr auto;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 28px;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}

.chat-header h1 {
  margin: 0;
  font-size: 20px;
}

.chat-header p {
  margin: 6px 0 0;
  color: #64748b;
}

.message-area {
  overflow-y: auto;
  padding: 28px;
}

.empty-state {
  margin: 120px auto;
  color: #64748b;
  text-align: center;
}

.composer {
  padding: 16px 28px 20px;
  border-top: 1px solid #e5e7eb;
  background: white;
}

.composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
}
</style>