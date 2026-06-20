# 阶段 0：项目基础与 Agent 主链实施计划

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 建立独立的 EnterpriseMind 仓库，完成 FastAPI 健康检查与问答主链、强类型 Agent 契约、规则优先路由器和可替换的外部模型 Provider。

**架构策略：** 先实现内存版模块化单体，在引入数据库和 RAG 前打通 HTTP、编排、路由、Agent 与模型 Provider 的边界。所有外部依赖都置于协议接口之后，并可在测试中替换为 Fake。

**技术栈：** Python 3.12、FastAPI、Pydantic 2、httpx、pytest、pytest-asyncio、Ruff、MyPy

---

## 文件结构

```text
backend/
├── pyproject.toml
├── app/
│   ├── main.py                 # FastAPI application factory
│   ├── api/health.py           # health endpoint
│   ├── api/chat.py             # HTTP chat boundary
│   ├── agents/contracts.py     # typed orchestration contracts
│   ├── agents/router.py        # deterministic-first routing
│   ├── agents/domain_agents.py # HR/IT/Finance/Data Agent prompts
│   ├── agents/orchestrator.py  # main application use case
│   ├── model_gateway/contracts.py
│   ├── model_gateway/external.py
│   └── shared/config.py
└── tests/
    ├── test_health.py
    ├── agents/test_router.py
    ├── agents/test_orchestrator.py
    └── api/test_chat.py
```

### 任务 1：后端质量基线与健康检查接口

**文件：**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/health.py`
- Create: `backend/tests/test_health.py`

- [ ] **步骤 1：创建依赖与质量工具配置**

```toml
[project]
name = "enterprisemind-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["fastapi==0.115.5", "uvicorn[standard]==0.32.1", "pydantic-settings==2.7.0", "httpx==0.28.1"]

[project.optional-dependencies]
dev = ["pytest==8.3.4", "pytest-asyncio==0.24.0", "ruff==0.8.4", "mypy==1.13.0"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
```

- [ ] **步骤 2：编写失败的健康检查测试**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_health_returns_service_status() -> None:
    response = TestClient(create_app()).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "enterprisemind"}
```

- [ ] **步骤 3：运行测试并确认 RED**

运行：`cd backend; python -m pytest tests/test_health.py -v`

预期：FAIL，因为 `app.main` 尚未提供 `create_app`。

- [ ] **步骤 4：实现最小应用**

```python
# backend/app/api/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "enterprisemind"}
```

```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="EnterpriseMind", version="0.1.0")
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()
```

- [ ] **步骤 5：验证并提交**

运行：`cd backend; python -m pytest tests/test_health.py -v; python -m ruff check .; python -m mypy app`

预期：1 个测试通过，Ruff 与 MyPy 检查无错误。

```bash
git add backend
git commit -m "build: bootstrap FastAPI backend"
```

### 任务 2：强类型 Agent 契约与确定性路由器

**文件：**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/contracts.py`
- Create: `backend/app/agents/router.py`
- Test: `backend/tests/agents/test_router.py`

- [ ] **步骤 1：编写路由测试**

```python
from app.agents.contracts import AgentType, IntentType
from app.agents.router import RuleRouter


def test_routes_vpn_problem_to_it() -> None:
    result = RuleRouter().route("公司 VPN 无法连接")
    assert result.agent is AgentType.IT
    assert result.intent is IntentType.KNOWLEDGE_QUERY
    assert result.requires_sql is False


def test_routes_statistics_question_to_data_agent() -> None:
    result = RuleRouter().route("统计本月各部门报销金额")
    assert result.agent is AgentType.DATA_ANALYST
    assert result.requires_sql is True


def test_unknown_question_requires_clarification() -> None:
    result = RuleRouter().route("帮我看看这个")
    assert result.agent is AgentType.CLARIFICATION
    assert result.confidence < 0.6
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/agents/test_router.py -v`

预期：FAIL，因为 Agent 契约与 `RuleRouter` 尚不存在。

- [ ] **步骤 3：实现契约与规则**

```python
# backend/app/agents/contracts.py
from dataclasses import dataclass
from enum import StrEnum


class AgentType(StrEnum):
    HR = "hr"
    IT = "it"
    FINANCE = "finance"
    DATA_ANALYST = "data_analyst"
    CLARIFICATION = "clarification"


class IntentType(StrEnum):
    KNOWLEDGE_QUERY = "knowledge_query"
    DATA_QUERY = "data_query"
    UNKNOWN = "unknown"


class Sensitivity(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"


@dataclass(frozen=True)
class RouteResult:
    agent: AgentType
    intent: IntentType
    requires_sql: bool
    sensitivity: Sensitivity
    confidence: float
```

```python
# backend/app/agents/router.py
from app.agents.contracts import AgentType, IntentType, RouteResult, Sensitivity


class RuleRouter:
    _rules = {
        AgentType.HR: ("年假", "请假", "考勤", "福利"),
        AgentType.IT: ("vpn", "登录", "报错", "设备", "网络"),
        AgentType.FINANCE: ("报销", "发票", "差旅", "付款"),
    }

    def route(self, message: str) -> RouteResult:
        text = message.lower()
        requires_sql = any(word in text for word in ("统计", "多少", "趋势", "汇总"))
        if requires_sql:
            return RouteResult(
                AgentType.DATA_ANALYST,
                IntentType.DATA_QUERY,
                True,
                Sensitivity.SENSITIVE,
                0.95,
            )
        for agent, words in self._rules.items():
            if any(word in text for word in words):
                return RouteResult(agent, IntentType.KNOWLEDGE_QUERY, False, Sensitivity.INTERNAL, 0.9)
        return RouteResult(
            AgentType.CLARIFICATION,
            IntentType.UNKNOWN,
            False,
            Sensitivity.INTERNAL,
            0.2,
        )
```

- [ ] **步骤 4：确认 GREEN**

运行：`cd backend; python -m pytest tests/agents/test_router.py -v`

预期：3 个测试全部通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/agents backend/tests/agents
git commit -m "feat: add typed Agent routing contracts"
```

### 任务 3：模型 Provider 与领域 Agent 编排

**文件：**
- Create: `backend/app/model_gateway/__init__.py`
- Create: `backend/app/model_gateway/contracts.py`
- Create: `backend/app/model_gateway/external.py`
- Create: `backend/app/agents/domain_agents.py`
- Create: `backend/app/agents/orchestrator.py`
- Test: `backend/tests/agents/test_orchestrator.py`

- [ ] **步骤 1：使用 Fake Provider 编写编排测试**

```python
import pytest
from app.agents.orchestrator import AgentOrchestrator
from app.agents.router import RuleRouter
from app.model_gateway.contracts import ModelRequest, ModelResponse


class FakeProvider:
    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(text=f"{request.system_prompt}|{request.user_message}", model="fake")


@pytest.mark.asyncio
async def test_orchestrator_selects_hr_prompt() -> None:
    result = await AgentOrchestrator(RuleRouter(), FakeProvider()).run("年假有几天？")
    assert result.agent == "hr"
    assert "人事制度助手" in result.answer
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/agents/test_orchestrator.py -v`

预期：FAIL，因为模型与编排器契约尚不存在。

- [ ] **步骤 3：实现 Provider 与编排器契约**

```python
# backend/app/model_gateway/contracts.py
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelRequest:
    system_prompt: str
    user_message: str


@dataclass(frozen=True)
class ModelResponse:
    text: str
    model: str


class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
```

```python
# backend/app/agents/domain_agents.py
from app.agents.contracts import AgentType

PROMPTS = {
    AgentType.HR: "你是企业人事制度助手，只根据提供的企业证据回答。",
    AgentType.IT: "你是企业 IT 运维助手，提供可执行的排障步骤。",
    AgentType.FINANCE: "你是企业财务制度助手，准确解释报销和发票制度。",
    AgentType.DATA_ANALYST: "你是只读数据分析助手，只解释已验证 SQL 的结果。",
}
```

```python
# backend/app/agents/orchestrator.py
from dataclasses import dataclass
from app.agents.contracts import AgentType
from app.agents.domain_agents import PROMPTS
from app.agents.router import RuleRouter
from app.model_gateway.contracts import ModelProvider, ModelRequest


@dataclass(frozen=True)
class OrchestratorResult:
    answer: str
    agent: str
    model: str


class AgentOrchestrator:
    def __init__(self, router: RuleRouter, provider: ModelProvider) -> None:
        self.router = router
        self.provider = provider

    async def run(self, message: str) -> OrchestratorResult:
        route = self.router.route(message)
        if route.agent is AgentType.CLARIFICATION:
            return OrchestratorResult("请补充问题所属领域和具体需求。", route.agent.value, "none")
        response = await self.provider.generate(ModelRequest(PROMPTS[route.agent], message))
        return OrchestratorResult(response.text, route.agent.value, response.model)
```

- [ ] **步骤 4：确认 GREEN**

运行：`cd backend; python -m pytest tests/agents/test_orchestrator.py -v`

预期：1 个测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/model_gateway backend/app/agents backend/tests/agents
git commit -m "feat: add domain Agent orchestration"
```

### 任务 4：HTTP 问答接口与 trace ID

**文件：**
- Create: `backend/app/api/chat.py`
- Create: `backend/app/shared/trace.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_chat.py`

- [ ] **步骤 1：编写 API 测试**

```python
from fastapi.testclient import TestClient
from app.main import create_app


def test_chat_returns_agent_and_trace_id() -> None:
    response = TestClient(create_app(testing=True)).post(
        "/api/v1/chat",
        json={"message": "VPN 无法连接"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["agent"] == "it"
    assert body["trace_id"]
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/api/test_chat.py -v`

预期：`/api/v1/chat` 返回 404，测试失败。

- [ ] **步骤 3：实现 HTTP 边界**

```python
# backend/app/api/chat.py
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    agent: str
    model: str
    trace_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    result = await request.app.state.orchestrator.run(body.message)
    return ChatResponse(
        answer=result.answer,
        agent=result.agent,
        model=result.model,
        trace_id=request.state.trace_id,
    )
```

```python
# backend/app/shared/trace.py
from uuid import uuid4
from fastapi import Request


async def trace_middleware(request: Request, call_next):
    request.state.trace_id = uuid4().hex
    response = await call_next(request)
    response.headers["X-Trace-ID"] = request.state.trace_id
    return response
```

更新 `create_app(testing=True)`：注册中间件、问答路由，并在测试模式下注入 Fake Provider。

- [ ] **步骤 4：运行本阶段全部检查**

运行：`cd backend; python -m pytest -v; python -m ruff check .; python -m mypy app`

预期：全部测试通过，静态检查无错误。

- [ ] **步骤 5：提交**

```bash
git add backend
git commit -m "feat: expose traced chat API"
```
