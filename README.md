# EnterpriseMind（企业内部知识与数据问答 Agent）

EnterpriseMind 是一个面向企业内部员工的知识与数据问答平台，覆盖 HR 制度、IT 运维、财务报销与只读数据统计等场景。系统强调企业场景的可控性：账号与权限隔离、敏感内容本地推理、证据驱动回答、可观测与可评测。

本仓库包含：
- `backend/`：FastAPI 后端（RAG / SQL Agent / 权限 / 记忆 / 工具 / 监控 / 评测）
- `frontend/`：Vue3 前端（聊天、知识库管理、用户管理、监控、评测、Trace）
- `scripts/`：Windows PowerShell 一键启动/停止/检查/测试脚本
- `compose.dev.yml`：本地开发依赖（PostgreSQL / Redis / Qdrant）

## 核心能力

- 权限与隔离：自建账号、角色与部门；知识库权限、数据集权限统一由 `AccessContext` 驱动，检索与查询在数据访问层完成过滤
- 企业增强 RAG：Query Normalize / Query Rewrite、多路召回、Fusion、敏感感知精排（rerank）、Evidence Gate、引用溯源与证据不足拒答
- 数据问答（只读 SQL）：数据集授权、SQL 生成、AST/白名单校验、只读连接执行、结果解释
- 混合模型路由：根据问题/证据敏感度动态选择外部 API 或本地模型，敏感内容强制本地推理
- 多层记忆：PostgreSQL 保留会话事实，Redis 缓存当前会话最近消息，Qdrant 存储长期摘要记忆并按用户私有检索
- 工具调用框架：类 MCP 风格的工具治理（schema 校验、TTL 缓存、超时、熔断、fallback、调用 metadata 记录）
- 复合多 Agent：对“先讲制度再做统计”等复合问题进行拆解与结果合成，支持 partial success
- 真实在线监控闭环：对 Agent/Tool/链路关键节点采集与归档运行事件，结合健康评分、告警与后台查询形成可观测闭环
- 端到端评测：真实调用编排器生成回复，结合 deterministic metrics 与 LLM-as-Judge 评估质量，支持回归与发布门禁

## 架构与业务流

```mermaid
flowchart LR
    A[登录/JWT] --> B[AccessContext]
    B --> C[意图识别与路由]
    C -->|知识问答| D[RAG 检索链路]
    C -->|数据统计| E[只读 SQL 链路]
    D --> F[模型路由]
    E --> F
    F --> G[返回回答 + 引用 + Trace]
    G --> H[会话事实(PostgreSQL)]
    G --> I[短期缓存(Redis)]
    G --> J[长期记忆(Qdrant)]
    G --> K[监控事件与健康评分]
```

## 快速开始

### 1) 前置依赖

- Docker Desktop
- Conda
- Node.js / npm
- Ollama
- Ollama 模型：
  - `bge-m3`：Embedding 与 Qdrant 检索
  - `qwen2.5:3b`：本地问答、敏感内容处理、SQL 生成、长期记忆摘要、LLM Judge

后端 Conda 环境建议使用项目根目录的 `environment.yml` 创建：

```powershell
cd EnterpriseMind
conda env create -f environment.yml
conda activate em
```

```powershell
ollama pull bge-m3
ollama pull qwen2.5:3b
```

### 2) 一键环境检查

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check-enterprisemind.ps1
```

### 3) 一键启动

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-enterprisemind.ps1
```

首次启动建议使用（自动执行 `npm install`）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-enterprisemind.ps1 -InstallFrontendDependencies
```

启动后访问：
- 后端 API：http://127.0.0.1:8000
- Swagger：http://127.0.0.1:8000/docs
- 前端：http://127.0.0.1:5173

说明：
- 脚本默认会启动 Docker compose、后端、前端与 Windows 兼容的 RQ Worker
- 脚本默认不会清库/不会删除 Docker volume/不会打印 `.env` 的真实 Key

### 4) 一键停止

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-enterprisemind.ps1
```

## 初始化与演示数据

首次数据库初始化通常需要执行迁移与 seed（脚本默认不会自动执行，避免误改已有数据）：

```powershell
cd backend
conda activate em
alembic upgrade head
python scripts\seed_stage1.py
python scripts\seed_stage2.py
python scripts\seed_stage4.py
```

默认演示账号来自 `backend/scripts/seed_stage1.py`：

| 账号 | 密码 | 用途 |
| --- | --- | --- |
| `admin` | `AdminPassw0rd!` | 管理后台 |
| `it01` | `ItPassw0rd!` | IT 问答 |
| `hr01` | `HrPassw0rd!` | HR 问答 |
| `finance01` | `FinancePassw0rd!` | 财务问答和数据统计 |
| `employee01` | `EmployeePassw0rd!` | 普通员工权限测试 |

## 文档入库（知识库索引）

上传文档后会异步入库（解析、切块、Embedding、写入 Qdrant）。如需本地演示入库，必须启动 worker：

```powershell
rq worker document_ingestion --url redis://127.0.0.1:6379/0 --worker-class rq.worker.SimpleWorker --with-scheduler
```

一键启动脚本默认会打开 worker 窗口；只有明确不需要文档入库时才使用 `-SkipWorker`。

## 监控（真实在线闭环）

系统会对关键链路产出监控事件与健康评分，支持后台查询与可视化展示，用于：
- 追踪 Agent/Tool 成功率、延迟、失败、超时与熔断
- 将监控信号写入请求结果 metadata，辅助评测与回归分析

前端提供监控管理页面，后端提供监控查询 API；若你只做面试演示，建议准备一条“超时/熔断”场景问句与一条正常问句对比展示。

## 测试与 Benchmark

### 一键测试

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test-enterprisemind.ps1
```

### Benchmark（对比报告）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\test-enterprisemind.ps1 -BackendOnly -Benchmark
```

输出位置：
- `backend/evaluation/reports/baseline.json`
- `backend/evaluation/reports/enhanced.json`
- `backend/evaluation/reports/compare.json`

## 目录结构（速览）

```text
backend/app/
  agents/            编排、意图识别、领域 Agent、复合任务
  auth/              登录认证、JWT、RBAC
  knowledge/          文档入库、向量检索、RAG 增强（Rewrite/Rerank/Gate）
  database_agent/     只读 SQL 数据问答
  conversations/      会话持久化、短期缓存、长期记忆
  tools/              工具框架与内置工具（含 knowledge_search）
  monitoring/         监控事件、健康评分、查询与 API
  evaluation/         端到端评测、benchmark、LLM-as-Judge
frontend/src/
  modules/            chat/admin/evaluation/traces/monitoring 等页面
scripts/              PowerShell 一键脚本
compose.dev.yml       Postgres/Redis/Qdrant
```
