<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/modules/auth/store";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const activeMenu = computed(() => route.path);

async function logout(): Promise<void> {
  auth.logout();
  await router.replace("/login");
}
</script>

<template>
  <el-container class="app-layout">
    <el-aside width="224px" class="sidebar">
      <div class="logo">
        <span class="logo-mark">EM</span>
        <span>EnterpriseMind</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        router
        class="menu"
      >
        <el-menu-item index="/chat">
          员工问答
        </el-menu-item>
        <template v-if="auth.isAdmin">
          <el-menu-item index="/admin/users">
            用户与权限
          </el-menu-item>
          <el-menu-item index="/admin/knowledge">
            知识库与文档
          </el-menu-item>
          <el-menu-item index="/admin/evaluation">
            Prompt 与评测
          </el-menu-item>
          <el-menu-item index="/admin/monitoring">
            运行监控
          </el-menu-item>
          <el-menu-item index="/admin/traces">
            请求追踪
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <strong>
            {{ auth.user?.username }}
          </strong>
          <span class="user-meta">
            {{ auth.user?.department }}
          </span>
        </div>
        <div class="topbar-actions">
          <el-tag
            v-for="role in auth.user?.roles"
            :key="role"
            size="small"
          >
            {{ role }}
          </el-tag>
          <el-button text @click="logout">
            退出登录
          </el-button>
        </div>
      </el-header>
      <el-main class="content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

.sidebar {
  color: #dbeafe;
  background: #111827;
}

.logo {
  display: flex;
  height: 64px;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
  color: white;
  font-weight: 700;
}

.logo-mark {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 10px;
  background: #2563eb;
}

.menu {
  border-right: 0;
  background: transparent;
}

.menu :deep(.el-menu-item) {
  color: #cbd5e1;
}

.menu :deep(.el-menu-item.is-active) {
  color: white;
  background: #1d4ed8;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}

.user-meta {
  margin-left: 10px;
  color: #6b7280;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content {
  padding: 0;
  background: #f3f6fb;
}
</style>
