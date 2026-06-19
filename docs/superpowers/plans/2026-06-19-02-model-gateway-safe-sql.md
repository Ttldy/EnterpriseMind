# 阶段 2：混合模型网关与安全 SQL 实施计划

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 确保敏感上下文只路由到 Ollama，并在 PostgreSQL 安全视图之上建立经过授权、AST 校验的只读 Text-to-SQL 链路。

**架构策略：** 模型调用前，根据问题、检索证据和数据集元数据计算敏感等级。Text-to-SQL 只能接收已授权 Schema，并且必须通过确定性校验后，才能交给只读执行器运行。

**技术栈：** Ollama HTTP API、外部模型 Provider、SQLGlot、SQLAlchemy、PostgreSQL、pytest

---

### 任务 1：敏感度策略与模型网关

**文件：**
- Create: `backend/app/model_gateway/sensitivity.py`
- Create: `backend/app/model_gateway/ollama.py`
- Create: `backend/app/model_gateway/gateway.py`
- Test: `backend/tests/model_gateway/test_gateway.py`

- [ ] **步骤 1：编写路由与防泄漏测试**

```python
import pytest
from app.agents.contracts import Sensitivity
from app.model_gateway.gateway import ModelGateway
from app.model_gateway.contracts import ModelRequest, ModelResponse


class SpyProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[ModelRequest] = []

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        return ModelResponse("ok", self.name)


@pytest.mark.asyncio
async def test_sensitive_context_never_calls_external_provider() -> None:
    local, external = SpyProvider("ollama"), SpyProvider("external")
    result = await ModelGateway(local, external).generate(
        ModelRequest("system", "查询工资"),
        Sensitivity.SENSITIVE,
    )
    assert result.model == "ollama"
    assert external.calls == []
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/model_gateway/test_gateway.py -v`

预期：FAIL，因为 `ModelGateway` 尚不存在。

- [ ] **步骤 3：实现确定性路由**

```python
# backend/app/model_gateway/gateway.py
from app.agents.contracts import Sensitivity
from app.model_gateway.contracts import ModelProvider, ModelRequest, ModelResponse


class SensitiveModelUnavailable(RuntimeError):
    pass


class ModelGateway:
    def __init__(self, local: ModelProvider, external: ModelProvider) -> None:
        self.local = local
        self.external = external

    async def generate(self, request: ModelRequest, sensitivity: Sensitivity) -> ModelResponse:
        if sensitivity is Sensitivity.PUBLIC:
            try:
                return await self.external.generate(request)
            except Exception:
                return await self.local.generate(request)
        try:
            return await self.local.generate(request)
        except Exception as exc:
            raise SensitiveModelUnavailable("敏感请求的本地模型不可用") from exc
```

使用枚举顺序实现 `highest_sensitivity(question_level, evidence_levels, dataset_level)`，并通过 `httpx.AsyncClient` 实现 `OllamaProvider.generate()`。

- [ ] **步骤 4：确认 GREEN**

运行：`cd backend; python -m pytest tests/model_gateway -v`

预期：公开请求降级与敏感请求防泄漏测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/model_gateway backend/tests/model_gateway
git commit -m "feat: add sensitivity-aware model gateway"
```

### 任务 2：演示业务数据、安全视图与数据集授权

**文件：**
- Create: `backend/app/database_agent/models.py`
- Create: `backend/alembic/versions/0004_business_views.py`
- Create: `backend/scripts/seed_demo_data.py`
- Test: `backend/tests/database_agent/test_dataset_access.py`

- [ ] **步骤 1：编写数据集授权测试**

```python
from app.database_agent.models import DatasetPolicy


def test_finance_dataset_requires_finance_role() -> None:
    policy = DatasetPolicy(
        name="expense_summary",
        view_name="expense_summary_view",
        allowed_columns=frozenset({"department", "month", "total_amount"}),
        allowed_roles=frozenset({"finance_staff", "admin"}),
        sensitivity="sensitive",
    )
    assert policy.allows(frozenset({"employee"})) is False
    assert policy.allows(frozenset({"employee", "finance_staff"})) is True
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/database_agent/test_dataset_access.py -v`

预期：FAIL，因为 `DatasetPolicy` 尚不存在。

- [ ] **步骤 3：实现策略与 SQL 迁移**

```python
# backend/app/database_agent/models.py
from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetPolicy:
    name: str
    view_name: str
    allowed_columns: frozenset[str]
    allowed_roles: frozenset[str]
    sensitivity: str

    def allows(self, roles: frozenset[str]) -> bool:
        return bool(self.allowed_roles & roles)
```

迁移必须创建演示源表以及设计中指定的四个视图。应用只读角色只能获得这些视图的 `SELECT` 权限。种子脚本至少写入 2 个部门、12 名员工、请假聚合、报销聚合和 IT 工单聚合数据。

- [ ] **步骤 4：验证迁移与测试**

运行：`cd backend; alembic upgrade head; python scripts/seed_demo_data.py; python -m pytest tests/database_agent/test_dataset_access.py -v`

预期：视图存在，种子脚本具备幂等性，授权测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/database_agent backend/alembic backend/scripts backend/tests/database_agent
git commit -m "feat: add authorized business datasets"
```

### 任务 3：SQL AST 校验器

**文件：**
- Create: `backend/app/database_agent/validator.py`
- Test: `backend/tests/database_agent/test_validator.py`

- [ ] **步骤 1：编写攻击测试矩阵**

```python
import pytest
from app.database_agent.validator import SqlPolicy, UnsafeSqlError, validate_sql

POLICY = SqlPolicy(
    views={"expense_summary_view"},
    columns={"department", "month", "total_amount"},
    max_rows=200,
)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        "UPDATE expense_summary_view SET total_amount = 0",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT department FROM expense_summary_view; SELECT 1",
        "SELECT secret_column FROM expense_summary_view",
    ],
)
def test_rejects_unsafe_sql(sql: str) -> None:
    with pytest.raises(UnsafeSqlError):
        validate_sql(sql, POLICY)


def test_adds_limit_to_safe_select() -> None:
    sql = validate_sql("SELECT department, total_amount FROM expense_summary_view", POLICY)
    assert sql.endswith("LIMIT 200")
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/database_agent/test_validator.py -v`

预期：FAIL，因为校验器类型尚不存在。

- [ ] **步骤 3：实现 SQLGlot 校验**

```python
# backend/app/database_agent/validator.py
from dataclasses import dataclass
import sqlglot
from sqlglot import exp


class UnsafeSqlError(ValueError):
    pass


@dataclass(frozen=True)
class SqlPolicy:
    views: set[str]
    columns: set[str]
    max_rows: int


def validate_sql(sql: str, policy: SqlPolicy) -> str:
    statements = sqlglot.parse(sql, read="postgres")
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union)):
        raise UnsafeSqlError("only one read-only query is allowed")
    tree = statements[0]
    tables = {table.name for table in tree.find_all(exp.Table)}
    columns = {column.name for column in tree.find_all(exp.Column) if column.name != "*"}
    if not tables or not tables <= policy.views:
        raise UnsafeSqlError("query references a non-authorized view")
    if not columns <= policy.columns:
        raise UnsafeSqlError("query references a non-authorized column")
    if any(tree.find(node) for node in (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Command)):
        raise UnsafeSqlError("write statements are forbidden")
    if tree.args.get("limit") is None:
        tree.set("limit", exp.Limit(expression=exp.Literal.number(policy.max_rows)))
    return tree.sql(dialect="postgres")
```

- [ ] **步骤 4：确认 GREEN**

运行：`cd backend; python -m pytest tests/database_agent/test_validator.py -v`

预期：所有攻击用例均被拒绝，安全 SQL 自动获得行数限制。

- [ ] **步骤 5：提交**

```bash
git add backend/app/database_agent/validator.py backend/tests/database_agent/test_validator.py
git commit -m "feat: validate generated SQL with AST policy"
```

### 任务 4：授权 Text-to-SQL 编排

**文件：**
- Create: `backend/app/database_agent/service.py`
- Create: `backend/app/database_agent/executor.py`
- Modify: `backend/app/agents/orchestrator.py`
- Test: `backend/tests/database_agent/test_service.py`
- Test: `backend/tests/api/test_data_chat.py`

- [ ] **步骤 1：编写端到端服务测试**

```python
import pytest


@pytest.mark.asyncio
async def test_finance_user_can_run_safe_aggregate(data_service, finance_access) -> None:
    result = await data_service.answer("统计本月各部门报销金额", finance_access)
    assert result.sql.startswith("SELECT")
    assert result.row_count > 0


@pytest.mark.asyncio
async def test_employee_cannot_query_finance_dataset(data_service, employee_access) -> None:
    with pytest.raises(PermissionError):
        await data_service.answer("统计本月各部门报销金额", employee_access)
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/database_agent/test_service.py tests/api/test_data_chat.py -v`

预期：FAIL，因为服务与执行器尚不存在。

- [ ] **步骤 3：实现安全执行边界**

```python
# backend/app/database_agent/executor.py
from sqlalchemy import text


class ReadOnlyExecutor:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    async def execute(self, sql: str) -> list[dict[str, object]]:
        async with self.session_factory() as session:
            await session.execute(text("SET LOCAL statement_timeout = '5s'"))
            result = await session.execute(text(sql))
            return [dict(row._mapping) for row in result.fetchall()]
```

`DataQueryService.answer()` 只能选择 ID 存在于 `AccessContext.dataset_ids` 中的策略；只向模型提供该数据集的 Schema；依次完成 SQL 生成、校验、执行，并把受限行数的结果交给 `DataAnalystAgent` 解释。API 响应包含 SQL、返回行数、模型路由和 trace ID。

- [ ] **步骤 4：运行阶段验证**

运行：`cd backend; python -m pytest tests/model_gateway tests/database_agent tests/api/test_data_chat.py -v; python -m ruff check .; python -m mypy app`

预期：敏感防泄漏、数据集授权、SQL 攻击、执行与 API 测试全部通过。

- [ ] **步骤 5：提交**

```bash
git add backend
git commit -m "feat: add authorized read-only data Agent"
```
