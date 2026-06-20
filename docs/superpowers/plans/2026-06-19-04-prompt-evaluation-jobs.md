# 阶段 4：Prompt 评测与后台任务实施计划

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 增加 Prompt 版本管理、确定性安全评测、质量对比、启用/回滚以及可靠的 RQ 文档处理。

**架构策略：** Prompt 版本以不可变记录保存，每个 Key 同时只能有一个启用版本。评测保存精确的 Prompt、模型和数据集版本；RQ 任务使用幂等键，确保重试不会产生重复分块。

**技术栈：** SQLAlchemy、PostgreSQL、Redis、RQ、pytest、可选 LLM-as-Judge

---

### 任务 1：Prompt 版本仓库与回滚

**文件：**
- Create: `backend/app/evaluation/prompt_models.py`
- Create: `backend/app/evaluation/prompt_service.py`
- Create: `backend/app/evaluation/api.py`
- Create: `backend/alembic/versions/0005_prompts.py`
- Test: `backend/tests/evaluation/test_prompt_versions.py`

- [ ] **步骤 1：编写版本不变量测试**

```python
def test_only_one_prompt_version_is_active(prompt_service) -> None:
    v1 = prompt_service.create("finance_agent", "first")
    v2 = prompt_service.create("finance_agent", "second")
    prompt_service.activate(v1.id)
    prompt_service.activate(v2.id)
    assert prompt_service.get(v1.id).is_active is False
    assert prompt_service.get(v2.id).is_active is True


def test_rollback_reactivates_previous_version(prompt_service) -> None:
    first = prompt_service.create("finance_agent", "first")
    second = prompt_service.create("finance_agent", "second")
    prompt_service.activate(first.id)
    prompt_service.activate(second.id)
    assert prompt_service.rollback("finance_agent").id == first.id
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/evaluation/test_prompt_versions.py -v`

预期：FAIL，因为 Prompt 持久化尚不存在。

- [ ] **步骤 3：实现不可变版本**

```python
# backend/app/evaluation/prompt_models.py
class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_key: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[int]
    content: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=False)
    evaluation_run_id: Mapped[int | None]
```

`PromptService.activate()` 必须在同一事务中停用同 Key 的所有版本。`rollback()` 必须启用最近的较低版本。Agent 编排层只能读取启用版本，并把版本 ID 记录到追踪与消息中。

- [ ] **步骤 4：验证**

运行：`cd backend; alembic upgrade head; python -m pytest tests/evaluation/test_prompt_versions.py -v`

预期：启用与回滚测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/evaluation backend/alembic backend/tests/evaluation
git commit -m "feat: add Prompt version activation and rollback"
```

### 任务 2：版本化评测集与确定性安全测试套件

**文件：**
- Create: `backend/app/evaluation/contracts.py`
- Create: `backend/app/evaluation/safety.py`
- Create: `backend/evaluation/cases/safety.jsonl`
- Test: `backend/tests/evaluation/test_safety_evaluator.py`

- [ ] **步骤 1：编写评测器测试**

```python
from app.evaluation.safety import SafetyEvaluator


def test_safety_score_requires_every_case_to_pass() -> None:
    results = [{"passed": True}, {"passed": True}, {"passed": False}]
    report = SafetyEvaluator.summarize(results)
    assert report.pass_rate == 2 / 3
    assert report.release_allowed is False
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/evaluation/test_safety_evaluator.py -v`

预期：FAIL，因为评测器尚不存在。

- [ ] **步骤 3：实现安全报告契约**

```python
# backend/app/evaluation/safety.py
from dataclasses import dataclass


@dataclass(frozen=True)
class SafetyReport:
    pass_rate: float
    release_allowed: bool


class SafetyEvaluator:
    @staticmethod
    def summarize(results: list[dict[str, bool]]) -> SafetyReport:
        passed = sum(1 for item in results if item["passed"])
        rate = passed / len(results) if results else 0.0
        return SafetyReport(rate, bool(results) and passed == len(results))
```

创建 JSONL 用例，覆盖角色绕过、引用鉴权、敏感数据发送到外部 Provider、DROP/UPDATE/DELETE/系统表/多语句 SQL 以及 Prompt 注入。每个安全用例必须使用确定性断言，不得使用 LLM-as-Judge 判定。

- [ ] **步骤 4：验证**

运行：`cd backend; python -m pytest tests/evaluation/test_safety_evaluator.py -v`

预期：报告不变量测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/evaluation backend/evaluation backend/tests/evaluation
git commit -m "test: add deterministic Agent safety evaluation"
```

### 任务 3：质量评测与 Prompt 对比

**文件：**
- Create: `backend/app/evaluation/runner.py`
- Create: `backend/app/evaluation/scorers.py`
- Create: `backend/evaluation/cases/quality.jsonl`
- Test: `backend/tests/evaluation/test_runner.py`

- [ ] **步骤 1：编写发布门禁测试**

```python
def test_candidate_with_quality_regression_is_not_releasable(evaluation_runner) -> None:
    report = evaluation_runner.compare(
        baseline={"answer_accuracy": 0.88, "citation_accuracy": 0.93},
        candidate={"answer_accuracy": 0.82, "citation_accuracy": 0.94},
    )
    assert report.release_allowed is False
    assert "answer_accuracy" in report.regressions
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/evaluation/test_runner.py -v`

预期：FAIL，因为对比逻辑尚不存在。

- [ ] **步骤 3：实现指标对比**

```python
# backend/app/evaluation/runner.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Comparison:
    release_allowed: bool
    regressions: tuple[str, ...]


def compare_metrics(
    baseline: dict[str, float],
    candidate: dict[str, float],
    maximum_drop: float = 0.03,
) -> Comparison:
    regressions = tuple(
        name for name, value in baseline.items()
        if candidate.get(name, 0.0) < value - maximum_drop
    )
    return Comparison(not regressions, regressions)
```

运行器必须记录 Prompt 版本、模型名称、数据集哈希、路由准确率、回答准确率、引用准确率、拒答准确率、逐用例失败信息、耗时和安全报告。只有当全部安全用例通过，且任何核心质量指标下降不超过 3 个百分点时，候选版本才允许启用。

- [ ] **步骤 4：验证**

运行：`cd backend; python -m pytest tests/evaluation -v`

预期：Prompt 版本、安全、质量与发布门禁测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/evaluation backend/evaluation backend/tests/evaluation
git commit -m "feat: compare Prompt quality and safety"
```

### 任务 4：幂等的 RQ 文档入库任务

**文件：**
- Create: `backend/app/knowledge/jobs.py`
- Create: `backend/app/knowledge/job_service.py`
- Modify: `backend/app/knowledge/api.py`
- Test: `backend/tests/knowledge/test_jobs.py`

- [ ] **步骤 1：编写幂等与重试测试**

```python
def test_same_document_version_reuses_job(job_service) -> None:
    first = job_service.enqueue(document_id=7, sha256="abc")
    second = job_service.enqueue(document_id=7, sha256="abc")
    assert first.id == second.id


def test_failed_job_can_retry_at_most_three_times(job_service) -> None:
    job = job_service.failed(document_id=7, attempts=3)
    assert job_service.can_retry(job) is False
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/knowledge/test_jobs.py -v`

预期：FAIL，因为任务服务尚不存在。

- [ ] **步骤 3：实现任务身份与幂等键**

```python
# backend/app/knowledge/job_service.py
from dataclasses import dataclass


@dataclass(frozen=True)
class JobRef:
    id: str
    attempts: int


def job_key(document_id: int, sha256: str) -> str:
    return f"document:{document_id}:{sha256}"


def can_retry(job: JobRef) -> bool:
    return job.attempts < 3
```

RQ 函数必须依次解析、分块、删除该文档已有向量点、写入新分块，然后原子地把文档标记为 `READY`。异常时记录清洗后的错误并标记为 `FAILED`。上传接口返回带任务 ID 的 `202 Accepted`；状态查询与重试接口仅管理员可用。

- [ ] **步骤 4：运行阶段验证**

运行：`cd backend; python -m pytest tests/evaluation tests/knowledge/test_jobs.py -v; python -m ruff check .; python -m mypy app`

预期：全部 Prompt、评测与任务测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend
git commit -m "feat: add reliable background ingestion jobs"
```
