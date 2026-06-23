<script setup lang="ts">
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { errorMessage } from "@/api/client";
import { useAuthStore } from "./store";

const router = useRouter();
const auth = useAuthStore();
const form = reactive({
  username: "",
  password: "",
});

async function submit(): Promise<void> {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  try {
    await auth.login(
      form.username.trim(),
      form.password,
    );
    await router.replace("/chat");
  } catch (error) {
    ElMessage.error(errorMessage(error));
  }
}
</script>

<template>
  <main class="login-page">
    <section class="brand-panel">
      <div class="brand-mark">EM</div>
      <h1>EnterpriseMind</h1>
      <p>企业内部知识与数据助手</p>
      <ul>
        <li>权限感知知识检索</li>
        <li>敏感数据本地模型处理</li>
        <li>安全只读数据分析</li>
      </ul>
    </section>

    <section class="login-panel">
      <el-card class="login-card" shadow="never">
        <h2>员工登录</h2>
        <p class="muted">
          使用阶段 1 创建的演示账号
        </p>
        <el-form label-position="top" @submit.prevent>
          <el-form-item label="用户名">
            <div
              data-testid="username"
              class="input-wrapper"
            >
              <el-input
                v-model="form.username"
                autocomplete="username"
                @keyup.enter="submit"
              />
            </div>
          </el-form-item>
          <el-form-item label="密码">
            <div
              data-testid="password"
              class="input-wrapper"
            >
              <el-input
                v-model="form.password"
                type="password"
                show-password
                autocomplete="current-password"
                @keyup.enter="submit"
              />
            </div>
          </el-form-item>
          <el-button
            data-testid="submit"
            type="primary"
            size="large"
            :loading="auth.loading"
            class="submit-button"
            @click="submit"
          >
            登录
          </el-button>
        </el-form>
      </el-card>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  min-height: 100vh;
}

.brand-panel {
  padding: 100px 12%;
  color: white;
  background:
    radial-gradient(
      circle at 20% 20%,
      #3b82f6,
      transparent 35%
    ),
    linear-gradient(145deg, #0f172a, #1e3a8a);
}

.brand-mark {
  display: grid;
  width: 60px;
  height: 60px;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 35%);
  border-radius: 18px;
  background: rgb(255 255 255 / 12%);
  font-size: 22px;
  font-weight: 700;
}

.brand-panel h1 {
  margin: 32px 0 8px;
  font-size: 42px;
}

.brand-panel p {
  color: #bfdbfe;
  font-size: 18px;
}

.brand-panel ul {
  margin-top: 48px;
  padding-left: 22px;
  line-height: 2.2;
}

.login-panel {
  display: grid;
  padding: 40px;
  place-items: center;
}

.login-card {
  width: 420px;
  border: 0;
}

.submit-button {
  width: 100%;
}

.input-wrapper {
  width: 100%;
}
</style>