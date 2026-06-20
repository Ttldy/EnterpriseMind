# 阶段 3：员工问答端与管理后台实施计划

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 构建 Vue 员工问答体验，以及覆盖身份权限、知识管理、Prompt/评测和请求追踪的四页管理后台。

**架构策略：** 单个 Vue 应用使用路由守卫与 Pinia Store。API 客户端具备类型并按模块隔离；前端绝不提交授权上下文，只展示后端返回的决策。

**技术栈：** Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Vitest、Playwright

---

## 文件结构

```text
frontend/src/
├── main.ts
├── router.ts
├── api/client.ts
├── modules/auth/
├── modules/chat/
├── modules/admin/users/
├── modules/admin/knowledge/
├── modules/evaluation/
└── modules/traces/
```

### 任务 1：前端脚手架、认证与路由守卫

**文件：**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/router.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/modules/auth/store.ts`
- Create: `frontend/src/modules/auth/LoginView.vue`
- Test: `frontend/src/modules/auth/LoginView.spec.ts`

- [ ] **步骤 1：编写登录组件测试**

```ts
import { mount } from "@vue/test-utils";
import { createTestingPinia } from "@pinia/testing";
import LoginView from "./LoginView.vue";

it("submits username and password", async () => {
  const wrapper = mount(LoginView, { global: { plugins: [createTestingPinia()] } });
  await wrapper.get('[data-testid="username"]').setValue("it01");
  await wrapper.get('[data-testid="password"]').setValue("Passw0rd!");
  await wrapper.get('[data-testid="submit"]').trigger("click");
  expect(wrapper.text()).not.toContain("用户名不能为空");
});
```

- [ ] **步骤 2：确认 RED**

运行：`cd frontend; npm install; npm run test -- LoginView.spec.ts`

预期：FAIL，因为 Vue 应用尚不存在。

- [ ] **步骤 3：实现最小认证 Store 与页面**

```ts
// frontend/src/modules/auth/store.ts
import { defineStore } from "pinia";
import { api } from "../../api/client";

export const useAuthStore = defineStore("auth", {
  state: () => ({ accessToken: "", roles: [] as string[] }),
  actions: {
    async login(username: string, password: string) {
      const { data } = await api.post("/auth/login", { username, password });
      this.accessToken = data.access_token;
      this.roles = data.roles;
    },
  },
});
```

`LoginView.vue` 必须使用 Element Plus 输入框和按钮，并保留上述精确测试 ID。`router.ts` 必须把未登录用户重定向到 `/login`；如果 `roles` 不包含 `admin`，则拒绝访问 `/admin/*`。

- [ ] **步骤 4：确认 GREEN**

运行：`cd frontend; npm run test -- LoginView.spec.ts; npm run typecheck`

预期：登录测试与 TypeScript 检查通过。

- [ ] **步骤 5：提交**

```bash
git add frontend
git commit -m "feat: add Vue authentication shell"
```

### 任务 2：员工问答、SSE、引用与 SQL 展示

**文件：**
- Create: `frontend/src/modules/chat/types.ts`
- Create: `frontend/src/modules/chat/store.ts`
- Create: `frontend/src/modules/chat/ChatView.vue`
- Create: `frontend/src/modules/chat/CitationCard.vue`
- Create: `frontend/src/modules/chat/SqlDetails.vue`
- Test: `frontend/src/modules/chat/ChatView.spec.ts`

- [ ] **步骤 1：编写渲染测试**

```ts
import { mount } from "@vue/test-utils";
import ChatView from "./ChatView.vue";

it("renders citation and model route", () => {
  const wrapper = mount(ChatView, {
    props: {
      initialMessages: [{
        role: "assistant",
        content: "报销应在十个工作日内提交。",
        agent: "finance",
        modelRoute: "ollama",
        citations: [{ filename: "报销制度.pdf", page: 6, text: "十个工作日内" }],
      }],
    },
  });
  expect(wrapper.text()).toContain("报销制度.pdf");
  expect(wrapper.text()).toContain("第 6 页");
  expect(wrapper.text()).toContain("ollama");
});
```

- [ ] **步骤 2：确认 RED**

运行：`cd frontend; npm run test -- ChatView.spec.ts`

预期：FAIL，因为问答组件尚不存在。

- [ ] **步骤 3：实现强类型问答状态**

```ts
// frontend/src/modules/chat/types.ts
export interface Citation {
  filename: string;
  page: number;
  text: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  agent?: string;
  modelRoute?: string;
  traceId?: string;
  sql?: string;
  citations: Citation[];
}
```

`ChatView.vue` 必须展示消息、Agent/模型标签、引用卡片、拒答状态、可展开 SQL 区域和追踪链接。`store.ts` 必须消费后端 SSE 流并增量追加文本，不得把凭证保存到 localStorage。

- [ ] **步骤 4：验证**

运行：`cd frontend; npm run test -- ChatView.spec.ts; npm run typecheck`

预期：问答渲染与类型检查通过。

- [ ] **步骤 5：提交**

```bash
git add frontend/src/modules/chat
git commit -m "feat: add cited employee chat UI"
```

### 任务 3：用户权限与知识文档管理页面

**文件：**
- Create: `frontend/src/modules/admin/users/UserAdminView.vue`
- Create: `frontend/src/modules/admin/knowledge/KnowledgeAdminView.vue`
- Create: `frontend/src/modules/admin/knowledge/DocumentStatus.vue`
- Test: `frontend/src/modules/admin/knowledge/KnowledgeAdminView.spec.ts`

- [ ] **步骤 1：编写文档状态测试**

```ts
import { mount } from "@vue/test-utils";
import DocumentStatus from "./DocumentStatus.vue";

it("shows failed document and retry action", () => {
  const wrapper = mount(DocumentStatus, {
    props: { status: "FAILED", error: "PDF parse failed" },
  });
  expect(wrapper.text()).toContain("解析失败");
  expect(wrapper.get('[data-testid="retry"]').exists()).toBe(true);
});
```

- [ ] **步骤 2：确认 RED**

运行：`cd frontend; npm run test -- KnowledgeAdminView.spec.ts`

预期：FAIL，因为知识管理组件尚不存在。

- [ ] **步骤 3：实现管理后台交互契约**

`UserAdminView.vue` 必须列出用户，支持创建/禁用用户、分配一个部门和多个角色，并展示数据集查询权限。`KnowledgeAdminView.vue` 必须支持创建知识库、分配角色/部门授权、上传文件、展示 `PROCESSING|READY|FAILED`、预览分块、重试失败任务和删除文档。每个模块使用明确的 API 函数，不使用全局无类型 Service。

- [ ] **步骤 4：验证**

运行：`cd frontend; npm run test; npm run typecheck`

预期：所有前端单元测试与类型检查通过。

- [ ] **步骤 5：提交**

```bash
git add frontend/src/modules/admin
git commit -m "feat: add identity and knowledge admin UI"
```

### 任务 4：Prompt/评测与请求追踪页面及浏览器端到端测试

**文件：**
- Create: `frontend/src/modules/evaluation/PromptEvaluationView.vue`
- Create: `frontend/src/modules/traces/TraceView.vue`
- Create: `frontend/e2e/core-flow.spec.ts`
- Modify: `frontend/src/router.ts`

- [ ] **步骤 1：编写浏览器流程测试**

```ts
import { test, expect } from "@playwright/test";

test("admin uploads knowledge and employee receives a cited answer", async ({ page }) => {
  await page.goto("/login");
  await page.getByTestId("username").fill("admin");
  await page.getByTestId("password").fill("AdminPassw0rd!");
  await page.getByTestId("submit").click();
  await page.goto("/admin/knowledge");
  await expect(page.getByText("知识库与文档")).toBeVisible();
  await page.goto("/chat");
  await page.getByTestId("chat-input").fill("报销需要在多久内提交？");
  await page.getByTestId("chat-send").click();
  await expect(page.getByText("报销制度.pdf")).toBeVisible();
});
```

- [ ] **步骤 2：确认 RED**

运行：`cd frontend; npx playwright test e2e/core-flow.spec.ts`

预期：FAIL，因为路由和页面尚未完整实现。

- [ ] **步骤 3：实现页面**

`PromptEvaluationView.vue` 必须列出启用版与候选 Prompt，支持创建候选版、运行评测、展示指标差异、启用和回滚。`TraceView.vue` 必须按顺序展示 `AUTH`、`ROUTE`、`RETRIEVAL|SQL`、`MODEL_ROUTE`、`GENERATION`、`RESPONSE`，并显示耗时和清洗后的元数据。

- [ ] **步骤 4：运行阶段验证**

运行：`cd frontend; npm run test; npm run typecheck; npm run build; npx playwright test`

预期：单元测试、类型检查、生产构建和核心端到端检查全部通过。

- [ ] **步骤 5：提交**

```bash
git add frontend
git commit -m "feat: complete admin evaluation and trace UI"
```
