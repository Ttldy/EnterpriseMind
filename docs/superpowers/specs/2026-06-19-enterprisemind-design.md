# EnterpriseMind 企业内部知识助手设计规格

## 1. 项目定位

EnterpriseMind 是一个用于校招作品集的单企业私有化知识助手。项目从零复刻 EchoMind 的核心 Agent 思想，并将其收敛为一个可以在 4–6 周内亲手完成、稳定演示、自动测试且能够深入讲解的企业级 Agent 项目。

项目面向企业内部员工，业务领域覆盖：

- 人事制度与员工服务；
- IT 运维与故障处理；
- 财务制度与报销流程；
- 授权范围内的企业数据库统计查询。

项目核心目的不是复刻完整企业平台，而是通过最小完整闭环证明开发者理解并实现了企业 Agent 的关键工程问题：

- 多领域 Agent 路由；
- 权限感知 RAG；
- 带来源引用的可靠回答；
- 敏感数据的混合模型路由；
- 安全的只读 Text-to-SQL；
- Prompt 版本、评测与回归；
- 可追踪、可测试、可部署的工程体系。

原始 `EchoMind/` 只作为只读参考。所有新代码、测试和文档均放入独立的 `EnterpriseMind/` 目录。

## 2. 项目范围

### 2.1 必须实现

- Vue 3 员工问答端和精简管理后台；
- FastAPI 模块化单体后端；
- 自建账号、部门、角色和 JWT 认证；
- HR、IT、Finance、DataAnalyst 四类 Agent；
- 规则优先、LLM 结构化分类兜底的路由器；
- PDF、DOCX、Markdown、TXT 文档入库；
- Qdrant 权限过滤向量检索；
- 文档名、页码、章节和原文片段引用；
- 无证据拒答；
- Ollama 与外部模型的统一模型网关；
- PUBLIC、INTERNAL、SENSITIVE 三级敏感度；
- PostgreSQL 安全视图上的只读 Text-to-SQL；
- SQL AST、表字段白名单、LIMIT、超时和只读账号防线；
- Prompt 候选版本、评测、启用和回滚；
- `trace_id` 与关键执行步骤追踪；
- Pytest、Vitest 和关键端到端测试；
- Docker Compose 私有化部署；
- 面试讲解和演示材料。

### 2.2 明确不实现

- 微服务拆分、Kubernetes、Helm；
- 多租户 SaaS；
- AD、LDAP、OIDC、MFA；
- OCR、扫描件、PPT、复杂 Excel 入库；
- MinIO/S3 对象存储；
- Agent 多实例池、动态性能路由、多 Agent 并行合并；
- GraphRAG、知识图谱、多路 Embedding、复杂混合检索；
- 完整 DLP、自动脱敏后外发；
- 完整文档审批、多版本发布工作流；
- 可视化数据源设计器和路由规则拖拽平台；
- OpenTelemetry、ELK、完整告警和灾备平台；
- 长期用户画像与跨会话语义记忆。

这些能力只在扩展设计中说明，不作为已实现功能宣传。

## 3. 技术路线与架构

### 3.1 架构选择

项目采用模块化单体，而不是微服务。

选择原因：

- 4–6 周内能够完成完整业务闭环；
- 本地调试、测试和部署成本更低；
- 模块边界清晰，未来仍可按模块拆分；
- 避免为了架构形式牺牲核心功能深度。

### 3.2 总体架构

```text
Vue 3 员工端 + 管理后台
              │
          FastAPI API
              │
      Auth / RBAC 权限层
              │
       AgentOrchestrator
       ┌──────┼─────────────┐
       │      │             │
   HR/IT/Finance Agent   DataAnalystAgent
       │                      │
   权限感知 RAG            只读 SQL 工具
       │                      │
     Qdrant           PostgreSQL 安全视图
       └──────────┬───────────┘
              ModelGateway
          ┌───────┴────────┐
       Ollama          外部模型 API
```

辅助组件：

- PostgreSQL：账号、权限、知识元数据、会话、Prompt、追踪和演示业务数据；
- Redis：最近会话缓存和 RQ 任务队列；
- RQ Worker：异步文档解析、分块和索引；
- 本地挂载目录：保存上传的原始文件；
- Nginx：前后端统一入口；
- Docker Compose：本地私有化部署。

### 3.3 建议目录

```text
EnterpriseMind/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── agents/
│   │   ├── knowledge/
│   │   ├── database_agent/
│   │   ├── model_gateway/
│   │   ├── conversations/
│   │   ├── evaluation/
│   │   ├── audit/
│   │   └── shared/
│   └── tests/
├── frontend/
│   └── src/modules/
│       ├── auth/
│       ├── chat/
│       ├── admin/
│       ├── evaluation/
│       └── traces/
├── deploy/
├── docs/
├── scripts/
├── docker-compose.yml
└── README.md
```

### 3.4 技术栈

- 后端：Python 3.12、FastAPI、Pydantic、SQLAlchemy、Alembic；
- 数据库：PostgreSQL；
- 向量数据库：Qdrant；
- 缓存与任务：Redis、RQ；
- 文档解析：PyMuPDF、python-docx；
- SQL 安全分析：SQLGlot；
- 本地模型：Ollama 与一款可在普通电脑演示的轻量开源模型；
- 外部模型：通过可替换 Provider 接入兼容 API；
- 前端：Vue 3、TypeScript、Vite、Element Plus、Pinia；
- 前端通信：REST API 与 SSE 流式响应；
- 测试：Pytest、Vitest、Playwright；
- 部署：Docker Compose、Nginx。

## 4. Agent 与路由设计

### 4.1 Agent 类型

- `HRAgent`：年假、考勤、福利、人事制度；
- `ITAgent`：VPN、账号、设备、系统故障；
- `FinanceAgent`：报销、发票、差旅和财务制度；
- `DataAnalystAgent`：授权数据集的统计查询。

通用拒答、澄清和异常降级由 `AgentOrchestrator` 处理，不单独创建 GeneralAgent 或 FallbackAgent。

每个问题只选择一个主 Agent。首期不实现多 Agent 并行协作。

### 4.2 路由流程

```text
确定性关键词规则
→ 未确定时调用 LLM 结构化分类
→ 检查最低置信度
→ 选择领域 Agent 或要求澄清
```

统一结果：

```json
{
  "domain": "finance",
  "intent": "knowledge_query",
  "requires_sql": false,
  "sensitivity": "internal",
  "confidence": 0.93,
  "agent": "finance"
}
```

领域与 Agent 映射由代码维护。领域关键词、最低置信度、默认 Top-K 和重排开关可由 YAML 或简单数据库配置维护。

## 5. 员工问答主链路

```text
用户登录
→ 提交问题
→ 后端生成 AccessContext
→ 路由器识别领域、意图和 SQL 需求
→ 选择领域 Agent
→ 执行权限感知 RAG 或只读 SQL
→ 合并问题、证据和数据集敏感等级
→ ModelGateway 选择 Ollama 或外部模型
→ 生成带引用回答
→ 保存会话、引用和 trace
→ 流式返回前端
```

关键约束：

- 身份、角色和部门只能由后端从登录用户生成；
- 权限在检索或数据集选择之前执行；
- 制度回答必须有知识库证据；
- 无可靠证据时明确拒答；
- 敏感内容不得发送给外部模型；
- 低置信度路由要求用户补充信息；
- 每个请求生成唯一 `trace_id`。

## 6. 文档入库与权限感知 RAG

### 6.1 文档入库

支持格式：

- PDF；
- DOCX；
- Markdown；
- TXT。

流程：

```text
管理员上传
→ 校验格式、大小和 SHA-256
→ 保存原文件
→ 创建 RQ 任务
→ 提取文本、标题和页码
→ 分块
→ Embedding
→ 写入 Qdrant
→ READY
```

状态只保留：

- `PROCESSING`；
- `READY`；
- `FAILED`。

必须支持：

- 文件哈希去重；
- 失败原因和手动重试；
- 分块预览；
- 删除文件并同步删除向量；
- 为知识库配置部门和角色权限；
- 保存文件名、页码、章节和敏感等级元数据。

文档更新采用删除旧文档后重新上传，不实现审批和多版本发布。

### 6.2 Qdrant 元数据

每个片段至少包含：

```json
{
  "knowledge_base_id": "it_internal",
  "allowed_departments": ["it"],
  "allowed_roles": ["it_staff"],
  "document_id": "doc_001",
  "filename": "VPN故障处理手册.pdf",
  "page": 8,
  "section": "连接失败",
  "sensitivity": "internal"
}
```

### 6.3 检索流程

```text
问题标准化
→ 计算用户可访问知识库
→ 构造 Qdrant Filter
→ Top-K 向量检索
→ 可选重排
→ 证据阈值判断
→ 构建引用上下文
→ Agent 生成回答
```

首期不实现多 Query 改写、BM25 混合检索和自适应 Top-K。重排器保留接口和开关，用评测比较启用前后的效果。

### 6.4 RAG 安全要求

- 普通员工不能检索受限片段；
- 权限过滤必须发生在 Qdrant 召回阶段；
- 引用详情和原文件下载再次鉴权；
- 缓存键必须包含用户权限范围；
- 无结果或相关度不足时拒答；
- 权限不足不能泄露文档名称。

## 7. 混合模型网关

### 7.1 Provider

- `OllamaProvider`；
- `ExternalModelProvider`。

Agent 只能依赖统一 `ModelGateway`，不得直接调用具体模型 SDK。

### 7.2 敏感等级

```text
PUBLIC
INTERNAL
SENSITIVE
```

最终等级取以下输入中的最高等级：

- 用户问题规则检测结果；
- 检索片段敏感等级；
- SQL 数据集敏感等级。

判断失败时按 `SENSITIVE` 处理。Prompt 和 Agent 不能降低已确定的等级。

### 7.3 路由规则

```text
PUBLIC → 外部模型
INTERNAL → 默认 Ollama，可配置为允许外部模型
SENSITIVE → Ollama
无法判断 → Ollama
外部模型失败 → Ollama
敏感请求且 Ollama 失败 → 拒答
```

每次调用记录：

- 最终敏感等级；
- Provider 和模型；
- 路由原因；
- 是否向外部服务发送数据；
- Prompt 版本；
- 请求耗时和结果状态。

首期不实现复杂 DLP、自动脱敏后外发、多模型负载均衡或成本优化器。

## 8. 安全只读数据库 Agent

### 8.1 数据来源

仅连接 PostgreSQL 演示数据库，并暴露以下安全视图：

- `employee_directory_view`；
- `leave_statistics_view`；
- `expense_summary_view`；
- `it_ticket_statistics_view`。

### 8.2 查询流程

```text
requires_sql=true
→ 检查 DATASET_QUERY 能力
→ 选择用户有权访问的数据集
→ 将授权 Schema 交给 LLM
→ 生成一条 SQL
→ SQLGlot AST 校验
→ 表与字段白名单校验
→ 添加最大 LIMIT
→ 只读事务执行
→ Agent 解释结果
→ 保存 SQL 和 trace
```

### 8.3 安全防线

- 仅允许单条 `SELECT` 或 `WITH ... SELECT`；
- 禁止 INSERT、UPDATE、DELETE、DDL；
- 禁止注释、多语句和系统表；
- 仅允许授权安全视图和字段；
- 最大返回 200 行；
- 查询超时 5 秒；
- 数据库账号只拥有安全视图 `SELECT` 权限；
- 前端可折叠展示生成的 SQL；
- 审计不保存完整敏感结果。

首期不实现 EXPLAIN 成本分析、多数据库适配、图表推荐或复杂行列级脱敏。

## 9. 用户、角色与权限

### 9.1 固定角色

- `employee`；
- `hr_staff`；
- `it_staff`；
- `finance_staff`；
- `admin`。

### 9.2 功能能力

```python
class Permission(str, Enum):
    CHAT_USE = "chat:use"
    KNOWLEDGE_MANAGE = "knowledge:manage"
    DATASET_QUERY = "dataset:query"
    PROMPT_MANAGE = "prompt:manage"
    TRACE_READ = "trace:read"
    USER_MANAGE = "user:manage"
```

角色到功能能力的映射由代码或简单配置维护。

知识库与数据集的具体授权存入 PostgreSQL。

### 9.3 AccessContext

```python
@dataclass
class AccessContext:
    user_id: str
    department: str
    roles: set[str]
    knowledge_base_ids: set[str]
    dataset_ids: set[str]
```

该对象由后端生成并贯穿 API 鉴权、Agent 路由、Qdrant Filter、引用查看和数据集选择。

### 9.4 权限防线

1. API 层检查登录和功能能力；
2. 应用层检查知识库或数据集授权；
3. Qdrant 在召回阶段应用权限过滤；
4. 引用和文件下载再次鉴权；
5. SQL Agent 使用数据集授权、安全视图、白名单和只读账号。

权限不完整、权限计算异常或知识库没有授权记录时默认拒绝。

## 10. 认证设计

校招版本实现：

- 用户名与密码登录；
- Argon2id 密码哈希；
- JWT Access Token；
- 简单 Refresh Token；
- Refresh Token 使用 HttpOnly Cookie；
- 用户禁用后禁止登录；
- 登录接口基础限流；
- 后台接口角色鉴权。

首期不实现 MFA、企业 SSO、多设备会话中心、Token 复用检测、验证码和密码找回邮件。

## 11. 会话与记忆

- PostgreSQL 持久化会话和消息；
- Redis 缓存最近 5–8 轮；
- 支持创建、查询和删除自己的会话；
- 最近消息加入模型上下文；
- 超长会话可以生成一次简短摘要。

不实现跨会话向量记忆、用户画像、长期偏好和重要性评分。

## 12. Prompt 版本与评测

### 12.1 Prompt 类型

- `router`；
- `hr_agent`；
- `it_agent`；
- `finance_agent`；
- `data_analyst_agent`；
- `answer_generator`。

### 12.2 版本能力

每个版本保存：

- Prompt Key；
- 版本号；
- 内容；
- 是否启用；
- 创建人和时间；
- 对应评测运行 ID。

只实现：

```text
创建候选版本
→ 运行评测
→ 启用或回滚
```

运行时将 Prompt Key 和版本记录到消息与 trace。

### 12.3 评测集

准备 50–100 条版本化用例：

- HR、IT、财务问答；
- Agent 路由；
- 多轮追问；
- 无答案拒答；
- 引用准确性；
- 权限越权；
- 敏感数据外发；
- SQL 攻击；
- Prompt 注入。

核心目标：

| 指标 | 门槛 |
|---|---:|
| Agent 路由准确率 | ≥ 90% |
| 有答案问题正确率 | ≥ 85% |
| 引用准确率 | ≥ 90% |
| 无答案拒答准确率 | ≥ 90% |
| 越权阻断率 | 100% |
| 敏感数据外发率 | 0% |
| 危险 SQL 阻断率 | 100% |

安全指标采用确定性断言。回答质量使用关键词、语义匹配和可选 LLM-as-Judge，不允许只依赖 Judge 判断安全性。

## 13. 数据模型

核心实体：

```text
User ──< UserRole >── Role
  │
  └── Department

KnowledgeBase ──< KnowledgePermission
      │
      └──< Document

Conversation ──< Message ──< Citation

Prompt ──< PromptVersion

Dataset ──< DatasetPermission

Trace ──< TraceStep

EvaluationRun
Feedback
```

核心表：

- `users`；
- `departments`；
- `roles`；
- `user_roles`；
- `knowledge_bases`；
- `knowledge_permissions`；
- `documents`；
- `conversations`；
- `messages`；
- `citations`；
- `prompts`；
- `prompt_versions`；
- `datasets`；
- `dataset_permissions`；
- `traces`；
- `trace_steps`；
- `evaluation_runs`；
- `feedback`。

不设计租户表、复杂权限点表、文档审批表、路由版本表和审计归档任务。

## 14. 请求追踪与日志

每次请求创建一个 trace：

```text
AUTH
→ ROUTE
→ RETRIEVAL 或 SQL
→ MODEL_ROUTE
→ GENERATION
→ RESPONSE
```

`traces` 保存：

- `trace_id`；
- 用户；
- 问题；
- Agent；
- 状态；
- 总耗时；
- 创建时间。

`trace_steps` 保存：

- 步骤类型；
- 输入输出摘要；
- 决策；
- 耗时；
- 结构化元数据。

关键元数据包括：

- 用户角色与部门；
- 路由结果与置信度；
- 检索知识库、片段 ID 和相关度；
- SQL 和校验结果；
- 敏感等级；
- 模型与路由原因；
- Prompt 版本；
- 错误码和耗时。

日志使用结构化 JSON，并禁止记录密码、Token、API Key、数据库密码、完整敏感文档和完整个人隐私数据。

## 15. 前端范围

### 15.1 员工端

- 登录；
- SSE 流式问答；
- 会话历史；
- Agent 类型；
- 模型路由标识；
- 引用卡片；
- SQL 折叠查看；
- 点赞、点踩；
- 无权限、拒答和异常状态。

### 15.2 管理后台

只保留四个页面：

1. 用户与权限；
2. 知识库与文档；
3. Prompt 与评测；
4. 请求追踪。

不实现完整模型配置中心、数据源设计器、路由规则编辑器、监控大屏和告警平台。

## 16. 错误与降级

- 无权限：拒绝且不暴露资源名称；
- 无检索证据：拒答，不允许自由编造制度；
- Qdrant 异常：停止制度回答；
- 外部模型异常：降级到 Ollama；
- 敏感请求且 Ollama 异常：拒答，禁止外发；
- SQL 校验失败：返回安全提示并记录原因；
- 文档解析失败：标记 `FAILED`，允许重试；
- 路由低置信度：要求用户补充信息；
- 权限服务异常：默认拒绝；
- 流式回答失败：保留 trace 和可重试错误码。

## 17. 测试策略

### 17.1 单元测试

- 路由器；
- 权限决策；
- Qdrant Filter 构造；
- 敏感等级合并；
- 模型网关路由；
- SQL AST 和白名单校验；
- 引用与拒答；
- Prompt 版本选择；
- 缓存权限隔离。

### 17.2 集成测试

- PostgreSQL 用户与权限；
- 文档解析、分块和 Qdrant 索引；
- Qdrant 权限检索；
- Ollama 与外部模型 Provider；
- 只读 SQL 执行；
- Redis 与 RQ 任务。

### 17.3 端到端测试

- 登录后完成带引用问答；
- 不同角色获得不同检索结果；
- 敏感问题只走 Ollama；
- 越权请求和危险 SQL 被拦截；
- 管理员上传文档后员工可以检索；
- Prompt 候选版本评测、启用和回滚。

## 18. 工程质量与部署

核心工具：

- Ruff；
- MyPy；
- Pytest；
- ESLint；
- Vitest；
- Playwright；
- Alembic；
- Docker Compose。

Docker Compose 服务：

```text
frontend
backend
worker
postgres
redis
qdrant
ollama
nginx
```

必须提供：

- `.env.example`；
- 数据库迁移；
- 演示数据初始化；
- 健康检查；
- 持久化目录；
- 一键启动脚本；
- 一键测试脚本；
- 一键评测命令。

必须实现 `/health` 和基础 `/metrics`。Prometheus、Grafana、OpenTelemetry 和完整日志平台不是核心完成条件。

## 19. 最终验收场景

1. 员工登录后，系统读取其部门和角色；
2. HR、IT、财务问题路由到对应 Agent；
3. 回答包含文档名、页码和原文引用；
4. 普通员工无法检索受限知识；
5. 引用详情和文件下载无法绕过权限；
6. 敏感问题使用 Ollama，普通公开问题使用外部模型；
7. 敏感请求在 Ollama 不可用时拒答而非外发；
8. 授权用户可以用自然语言查询统计数据；
9. 写操作、系统表、多语句和越权字段被 SQL 校验器阻断；
10. 管理员可以上传、查看和重试文档任务；
11. 管理员可以创建 Prompt 候选版本、运行评测、启用和回滚；
12. 根据 `trace_id` 可以查看权限、路由、RAG/SQL、模型和 Prompt 链路；
13. 自动化测试达到要求；
14. Docker Compose 可以从空环境启动系统并保留数据。

## 20. 4–6 周实施路线

### 第 0 阶段：项目基线，1–2 天

- 创建独立目录和 Git 仓库；
- 建立前后端、测试、文档和部署结构；
- 配置质量工具；
- 实现 `/health`；
- 验证前端可以访问后端；
- 写明项目范围和非目标。

### 第一周：Agent 主链

- FastAPI API、生命周期、异常和 `trace_id`；
- Agent 请求、响应和四个 Agent；
- 规则优先、LLM 兜底路由；
- 外部模型 Provider；
- `/chat` 主链；
- 路由与 API 测试；
- 主调用链文档。

### 第二周：认证、权限与 RAG

- PostgreSQL、SQLAlchemy、Alembic；
- 用户、部门、角色和 JWT；
- 知识库授权和 `AccessContext`；
- PDF、DOCX、Markdown、TXT 入库；
- Qdrant 权限过滤；
- 引用与拒答；
- 越权测试。

### 第三周：混合模型与安全 SQL

- OllamaProvider 和 ModelGateway；
- 敏感度分类与安全路由；
- 演示业务数据和安全视图；
- Text-to-SQL；
- SQLGlot AST、白名单、LIMIT、超时和只读账号；
- 敏感外发与 SQL 攻击测试。

### 第四周：前端与管理后台

- 登录和员工问答端；
- SSE、会话、引用和 SQL 展示；
- 用户权限页面；
- 知识库文档页面；
- 请求追踪页面；
- 关键前端测试和端到端演示。

第四周结束达到可投递 MVP。

### 第五周：Prompt、评测与异步任务

- Prompt 候选版本、启用和回滚；
- 50–100 条评测集；
- 路由、回答、引用、拒答和安全评测；
- 新旧 Prompt 对比；
- Redis 和 RQ 文档任务；
- 幂等、失败重试和状态查询。

### 第六周：部署与面试材料

- JSON 日志、错误码和基础指标；
- Docker Compose；
- 数据迁移、演示数据和健康检查；
- 全量测试和评测；
- README 与架构、安全、部署文档；
- 3 分钟简介、10 分钟讲解和 5 分钟演示脚本。

## 21. 每阶段完成门槛

每个阶段只有同时满足以下条件才算完成：

```text
代码可以运行
→ 自动测试通过
→ 存在真实演示场景
→ 对应文档已经更新
→ 开发者能够脱离代码讲清设计与取舍
```

禁止把测试、评测和文档全部推迟到项目最后。

## 22. 校招讲解重点

项目完成后应能独立回答：

- 为什么使用模块化单体而不是微服务；
- 权限如何进入 Qdrant 检索，而不是只停留在 API；
- 如何证明敏感数据没有发送给外部模型；
- Text-to-SQL 有哪些独立安全防线；
- 如何实现引用、证据不足拒答和权限隔离；
- 为什么简化 EchoMind 的三路意图融合和三级长期记忆；
- Prompt 修改后如何评测和回滚；
- `trace_id` 如何还原一次 Agent 请求；
- 校招版与真实生产系统还存在哪些差距。

## 23. 成功定义

EnterpriseMind 的成功不是拥有最多组件，而是形成以下可验证闭环：

- 身份真实决定知识和数据访问范围；
- RAG 返回可定位的证据并在无证据时拒答；
- 敏感等级真实决定模型路由；
- SQL 查询只能访问授权安全视图；
- Prompt 变化可以被评测、启用和回滚；
- 每次请求可追踪、可测试、可复现；
- 系统能够一键部署并完成稳定演示；
- 开发者能够解释每项设计的原因、实现和取舍。
