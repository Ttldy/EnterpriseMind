# 阶段 5：部署、验证与面试交付实施计划

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 将 EnterpriseMind 打包为可重复执行的私有化部署，验证完整验收套件，并产出如实描述项目能力的作品集与面试文档。

**架构策略：** Docker Compose 提供可复现的本地环境。通过健康检查、数据库迁移、演示数据、结构化日志和脚本化验证，使项目可恢复、可独立运行。

**技术栈：** Docker Compose、Nginx、PostgreSQL、Redis、Qdrant、Ollama、FastAPI、Vue、pytest、Vitest、Playwright

---

### 任务 1：结构化追踪、健康检查与指标

**文件：**
- Create: `backend/app/audit/models.py`
- Create: `backend/app/audit/service.py`
- Create: `backend/app/audit/api.py`
- Create: `backend/app/shared/logging.py`
- Modify: `backend/app/api/health.py`
- Create: `backend/app/api/metrics.py`
- Test: `backend/tests/audit/test_trace.py`

- [ ] **步骤 1：编写追踪完整性测试**

```python
def test_trace_contains_required_decision_steps(trace_service) -> None:
    trace = trace_service.create(user_id=1, question="VPN 无法连接")
    for step in ("AUTH", "ROUTE", "RETRIEVAL", "MODEL_ROUTE", "GENERATION", "RESPONSE"):
        trace_service.add_step(trace.id, step, {"status": "ok"}, duration_ms=1)
    assert [item.step_type for item in trace_service.get(trace.id).steps] == [
        "AUTH", "ROUTE", "RETRIEVAL", "MODEL_ROUTE", "GENERATION", "RESPONSE"
    ]
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/audit/test_trace.py -v`

预期：FAIL，因为持久化追踪模型尚不存在。

- [ ] **步骤 3：实现清洗后的追踪持久化**

创建 `Trace` 与 `TraceStep` SQLAlchemy 模型。`TraceService.add_step()` 只接受可 JSON 序列化的元数据，并移除匹配 `password`、`token`、`api_key`、`secret` 的键。`/api/v1/traces/{trace_id}` 要求管理员角色。`/health` 检查已配置依赖；`/metrics` 暴露请求数、延迟、模型路由次数、空检索次数和 SQL 拒绝次数。

- [ ] **步骤 4：验证**

运行：`cd backend; python -m pytest tests/audit/test_trace.py -v`

预期：追踪顺序与敏感字段清洗测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/audit backend/app/shared backend/app/api backend/tests/audit
git commit -m "feat: persist sanitized Agent traces"
```

### 任务 2：Docker 镜像与 Compose 环境

**文件：**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `deploy/nginx.conf`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `scripts/start.ps1`
- Create: `scripts/healthcheck.ps1`

- [ ] **步骤 1：定义预期服务图检查**

创建 `scripts/healthcheck.ps1`，只要以下任一检查失败就返回非零退出码：

```powershell
$services = @(
  "http://localhost/api/v1/health",
  "http://localhost/"
)
foreach ($url in $services) {
  $response = Invoke-WebRequest -UseBasicParsing -Uri $url
  if ($response.StatusCode -ne 200) { exit 1 }
}
exit 0
```

- [ ] **步骤 2：确认 RED**

运行：`powershell -ExecutionPolicy Bypass -File scripts/healthcheck.ps1`

预期：FAIL，因为服务栈尚未运行。

- [ ] **步骤 3：实现 Compose 服务**

`docker-compose.yml` 必须定义 `frontend`、`backend`、`worker`、`postgres`、`redis`、`qdrant`、`ollama` 和 `nginx`，并增加命名卷、健康检查、重启策略和依赖条件。后端入口在启动 Uvicorn 前运行 `alembic upgrade head`。`.env.example` 为全部必需变量提供非敏感占位值。支持的容器使用非 root 用户运行。

- [ ] **步骤 4：构建并验证**

运行：`docker compose build; docker compose up -d; powershell -ExecutionPolicy Bypass -File scripts/healthcheck.ps1`

预期：镜像构建成功，所有核心服务变为健康，脚本退出码为 0。

- [ ] **步骤 5：提交**

```bash
git add backend/Dockerfile frontend/Dockerfile deploy docker-compose.yml .env.example scripts
git commit -m "build: add private Docker Compose deployment"
```

### 任务 3：一键验证与验收套件

**文件：**
- Create: `scripts/test.ps1`
- Create: `scripts/evaluate.ps1`
- Create: `scripts/demo-check.ps1`
- Create: `.github/workflows/ci.yml`

- [ ] **步骤 1：编写验证流水线脚本**

```powershell
# scripts/test.ps1
$ErrorActionPreference = "Stop"
Push-Location backend
python -m ruff check .
python -m mypy app
python -m pytest -q
Pop-Location
Push-Location frontend
npm ci
npm run test -- --run
npm run typecheck
npm run build
Pop-Location
```

- [ ] **步骤 2：运行并观察首次失败**

运行：`powershell -ExecutionPolicy Bypass -File scripts/test.ps1`

预期：脚本在第一个未配置或失败的质量门禁处停止。

- [ ] **步骤 3：增加 CI 与验收检查**

CI 必须运行后端静态检查与测试、前端单元/类型/构建检查、Docker 构建和确定性安全评测。`demo-check.ps1` 使用演示账号登录并验证：HR/IT/财务问题路由、带引用 RAG 回答、权限拒绝、敏感请求 Ollama 路由、安全 SQL 成功、不安全 SQL 拒绝以及追踪查询。

- [ ] **步骤 4：运行最终验证**

运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test.ps1
powershell -ExecutionPolicy Bypass -File scripts/evaluate.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo-check.ps1
```

预期：所有命令退出码为 0；安全评测 100% 通过；质量指标达到设计门槛。

- [ ] **步骤 5：提交**

```bash
git add scripts .github
git commit -m "ci: add complete quality and demo verification"
```

### 任务 4：作品集文档与面试材料

**文件：**
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/request-flow.md`
- Create: `docs/rbac-rag.md`
- Create: `docs/model-routing.md`
- Create: `docs/safe-text-to-sql.md`
- Create: `docs/evaluation.md`
- Create: `docs/deployment.md`
- Create: `docs/interview-guide.md`

- [ ] **步骤 1：编写 README 验收清单**

README 必须包含以下可直接运行的命令：

```powershell
Copy-Item .env.example .env
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts/healthcheck.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo-check.ps1
```

- [ ] **步骤 2：验证文档命令**

在全新检出或新 worktree 中运行 README 中的每一条命令。

预期：除了提供外部模型 Key 和拉取文档指定的 Ollama 模型外，不需要任何未写入文档的手工配置。

- [ ] **步骤 3：完成如实的技术文档**

文档必须包含架构图和请求流程图、Qdrant 授权过滤、模型防泄漏规则、SQL 防线、评测门槛、准确的演示账号、已实现/未实现能力矩阵、已知限制和生产演进路径。`interview-guide.md` 包含 3 分钟项目介绍、10 分钟技术讲解、5 分钟演示，以及设计规格中 9 个问题的回答。

- [ ] **步骤 4：最终仓库验证**

运行：`git status --short; powershell -ExecutionPolicy Bypass -File scripts/test.ps1; powershell -ExecutionPolicy Bypass -File scripts/evaluate.ps1`

预期：提交前只有预期文档变更；测试与评测通过。

- [ ] **步骤 5：提交**

```bash
git add README.md docs
git commit -m "docs: complete EnterpriseMind portfolio handoff"
```
