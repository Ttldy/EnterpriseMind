# EnterpriseMind 总体交付路线图

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 通过六个可独立测试、独立验收的阶段，完整落实已经确认的 EnterpriseMind 设计规格。

**架构策略：** 每个阶段结束时都必须得到可运行的软件，并且只依赖前序阶段已经建立和验证的公开接口。计划必须按编号顺序执行；相关后端 API 未验证前，不得开始前端集成。

**技术栈：** FastAPI、PostgreSQL、Qdrant、Redis/RQ、Ollama、Vue 3、TypeScript、Docker Compose

---

## 阶段执行顺序

- [ ] **阶段 0——项目基础与 Agent 主链**

计划文件：`docs/superpowers/plans/2026-06-19-00-foundation-agent-main-path.md`

退出标准：`/health` 与带追踪信息的 `/chat` 可以运行；HR、IT、财务、数据查询路由已经过测试。

- [ ] **阶段 1——认证、RBAC 与权限感知 RAG**

计划文件：`docs/superpowers/plans/2026-06-19-01-auth-rbac-rag.md`

退出标准：登录用户只能获得有权访问的知识片段和引用回答；缺少证据时系统会拒答。

- [ ] **阶段 2——混合模型网关与安全 SQL**

计划文件：`docs/superpowers/plans/2026-06-19-02-model-gateway-safe-sql.md`

退出标准：敏感上下文绝不会进入外部模型 Provider；授权只读 SQL 可以执行，攻击 SQL 全部被阻断。

- [ ] **阶段 3——员工端与管理后台**

计划文件：`docs/superpowers/plans/2026-06-19-03-frontend-admin.md`

退出标准：员工可以问答并查看引用；管理员可以管理用户、知识、Prompt 评测和请求追踪。

- [ ] **阶段 4——Prompt 评测与后台任务**

计划文件：`docs/superpowers/plans/2026-06-19-04-prompt-evaluation-jobs.md`

退出标准：候选 Prompt 必须经过评测才能启用；回滚有效；文档任务具备幂等性并支持重试。

- [ ] **阶段 5——部署与面试交付**

计划文件：`docs/superpowers/plans/2026-06-19-05-deployment-interview.md`

退出标准：全新检出后可以通过 Docker Compose 启动，通过测试、评测和演示检查，并包含如实描述能力边界的作品集文档。

## 全局执行规则

1. 每项行为都遵循 RED → GREEN → REFACTOR。
2. 宣布阶段完成前，必须运行该阶段的验证命令。
3. 每个任务完成后提交一次；不相关任务不得合并到同一提交。
4. 严格遵守设计规格中已经确认的非目标。
5. 不得修改同级目录中的原始 `EchoMind/` 项目。
6. 外部 Provider 必须可被 Fake 替换；自动测试不得依赖付费 API。
7. 安全门禁采用确定性断言，要求 100% 通过。
8. 每个阶段结束后，更新 `docs/interview-guide.md`，记录真实实现的调用链和技术取舍。
