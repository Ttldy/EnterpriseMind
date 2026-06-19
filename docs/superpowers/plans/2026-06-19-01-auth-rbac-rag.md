# 阶段 1：认证、RBAC 与权限感知 RAG 实施计划

> **供执行 Agent 使用：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，逐任务执行本计划。使用复选框（`- [ ]`）跟踪进度。

**目标：** 增加 PostgreSQL 身份数据、JWT 认证、后端生成的访问上下文、文档入库、Qdrant 权限过滤、引用以及基于证据的拒答。

**架构策略：** PostgreSQL 是身份与授权元数据的唯一可信来源。Qdrant 保存带授权载荷的知识片段；检索服务只能接收后端创建的 `AccessContext`，不能使用客户端提交的角色。

**技术栈：** FastAPI、SQLAlchemy 2、Alembic、PostgreSQL、pwdlib/Argon2、PyJWT、PyMuPDF、python-docx、Qdrant、pytest

---

## 文件结构

```text
backend/app/
├── shared/database.py
├── auth/models.py
├── auth/schemas.py
├── auth/security.py
├── auth/service.py
├── auth/dependencies.py
├── auth/api.py
├── knowledge/models.py
├── knowledge/access.py
├── knowledge/parsers.py
├── knowledge/chunking.py
├── knowledge/vector_store.py
├── knowledge/retrieval.py
└── knowledge/api.py
```

### 任务 1：数据库模型、迁移与演示身份

**文件：**
- Create: `backend/app/shared/database.py`
- Create: `backend/app/auth/models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_identity.py`
- Test: `backend/tests/auth/test_models.py`

- [ ] **步骤 1：编写数据库模型测试**

```python
from app.auth.models import Department, Role, User


def test_user_has_department_and_roles(db_session) -> None:
    department = Department(name="IT")
    role = Role(name="it_staff")
    user = User(username="it01", password_hash="hash", department=department, roles=[role])
    db_session.add(user)
    db_session.commit()
    assert user.department.name == "IT"
    assert {item.name for item in user.roles} == {"it_staff"}
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/auth/test_models.py -v`

预期：FAIL，因为模型尚不存在。

- [ ] **步骤 3：实现 SQLAlchemy 模型**

```python
# backend/app/auth/models.py
from sqlalchemy import Boolean, ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.database import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    department: Mapped[Department] = relationship()
    roles: Mapped[list[Role]] = relationship(secondary=user_roles)
```

- [ ] **步骤 4：添加迁移并验证**

运行：`cd backend; alembic upgrade head; python -m pytest tests/auth/test_models.py -v`

预期：迁移成功，测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/shared backend/app/auth backend/alembic*
git commit -m "feat: add identity database models"
```

### 任务 2：登录、JWT 与后端生成的 AccessContext

**文件：**
- Create: `backend/app/auth/security.py`
- Create: `backend/app/auth/schemas.py`
- Create: `backend/app/auth/service.py`
- Create: `backend/app/auth/dependencies.py`
- Create: `backend/app/auth/api.py`
- Create: `backend/app/knowledge/access.py`
- Test: `backend/tests/auth/test_login.py`
- Test: `backend/tests/knowledge/test_access.py`

- [ ] **步骤 1：编写认证与防伪造测试**

```python
def test_login_returns_access_token(client, seeded_users) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "it01", "password": "Passw0rd!"})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_access_context_ignores_client_roles(client, it_token) -> None:
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {it_token}"},
        json={"message": "VPN 无法连接", "roles": ["admin"]},
    )
    assert response.status_code == 200
    assert response.json()["access"]["roles"] == ["employee", "it_staff"]
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/auth/test_login.py tests/knowledge/test_access.py -v`

预期：FAIL，因为登录能力与 `AccessContext` 尚不存在。

- [ ] **步骤 3：实现安全契约**

```python
# backend/app/knowledge/access.py
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessContext:
    user_id: int
    department: str
    roles: frozenset[str]
    knowledge_base_ids: frozenset[int]
    dataset_ids: frozenset[int]
```

```python
# backend/app/auth/security.py
from datetime import UTC, datetime, timedelta
import jwt
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def create_access_token(user_id: int, secret: str) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(UTC) + timedelta(minutes=15)}
    return jwt.encode(payload, secret, algorithm="HS256")
```

根据 JWT 实现 `get_current_user()`，并根据持久化角色和授权实现 `build_access_context(user, session)`。问答请求模型不得接收角色、部门、知识库 ID 或数据集 ID。

- [ ] **步骤 4：确认 GREEN**

运行：`cd backend; python -m pytest tests/auth tests/knowledge/test_access.py -v`

预期：登录成功，客户端伪造的角色被忽略。

- [ ] **步骤 5：提交**

```bash
git add backend/app/auth backend/app/knowledge/access.py backend/tests/auth backend/tests/knowledge/test_access.py
git commit -m "feat: add JWT authentication and access context"
```

### 任务 3：知识元数据、解析器、分块与 Qdrant 载荷

**文件：**
- Create: `backend/app/knowledge/models.py`
- Create: `backend/app/knowledge/parsers.py`
- Create: `backend/app/knowledge/chunking.py`
- Create: `backend/app/knowledge/vector_store.py`
- Create: `backend/alembic/versions/0002_knowledge.py`
- Test: `backend/tests/knowledge/test_ingestion.py`

- [ ] **步骤 1：编写解析器与载荷测试**

```python
from app.knowledge.chunking import chunk_pages


def test_chunk_preserves_page_and_permissions() -> None:
    chunks = chunk_pages(
        pages=[(3, "VPN 连接失败时先检查网络。")],
        document_id=7,
        knowledge_base_id=2,
        filename="vpn.pdf",
        roles={"it_staff"},
        departments={"IT"},
        sensitivity="internal",
    )
    assert chunks[0].payload["page"] == 3
    assert chunks[0].payload["allowed_roles"] == ["it_staff"]
    assert chunks[0].payload["knowledge_base_id"] == 2
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/knowledge/test_ingestion.py -v`

预期：FAIL，因为分块功能尚不存在。

- [ ] **步骤 3：实现职责单一的解析器与分块模型**

```python
# backend/app/knowledge/chunking.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    payload: dict[str, object]


def chunk_pages(
    pages: list[tuple[int, str]],
    document_id: int,
    knowledge_base_id: int,
    filename: str,
    roles: set[str],
    departments: set[str],
    sensitivity: str,
    size: int = 600,
) -> list[Chunk]:
    result: list[Chunk] = []
    for page, text in pages:
        for start in range(0, len(text), size):
            content = text[start : start + size].strip()
            if content:
                result.append(
                    Chunk(
                        content,
                        {
                            "document_id": document_id,
                            "knowledge_base_id": knowledge_base_id,
                            "filename": filename,
                            "page": page,
                            "allowed_roles": sorted(roles),
                            "allowed_departments": sorted(departments),
                            "sensitivity": sensitivity,
                        },
                    )
                )
    return result
```

实现返回类型为 `list[tuple[int, str]]` 的 `parse_pdf`、`parse_docx` 和 `parse_text`。在可被测试 Fake 替换的类中实现 `QdrantVectorStore.upsert(chunks)` 与 `delete_document(document_id)`。迁移 `0002_knowledge.py` 创建 `knowledge_bases`、`knowledge_permissions`、`documents`，并为每个知识库设置 SHA-256 唯一约束。

- [ ] **步骤 4：确认 GREEN**

运行：`cd backend; python -m pytest tests/knowledge/test_ingestion.py -v`

预期：解析器夹具与载荷测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/knowledge backend/tests/knowledge
git commit -m "feat: add permission-aware document ingestion"
```

### 任务 4：权限过滤检索、引用与拒答

**文件：**
- Create: `backend/app/knowledge/retrieval.py`
- Create: `backend/app/knowledge/schemas.py`
- Modify: `backend/app/agents/orchestrator.py`
- Test: `backend/tests/knowledge/test_retrieval.py`
- Test: `backend/tests/api/test_rag_chat.py`

- [ ] **步骤 1：编写授权与拒答测试**

```python
import pytest
from app.knowledge.access import AccessContext
from app.knowledge.retrieval import RetrievalService


@pytest.mark.asyncio
async def test_retrieval_builds_permission_filter(fake_vector_store) -> None:
    access = AccessContext(1, "IT", frozenset({"employee", "it_staff"}), frozenset({2}), frozenset())
    await RetrievalService(fake_vector_store).search("VPN", access)
    assert fake_vector_store.last_filter["knowledge_base_id"] == [2]
    assert fake_vector_store.last_filter["roles"] == ["employee", "it_staff"]


@pytest.mark.asyncio
async def test_orchestrator_refuses_without_evidence(orchestrator_without_hits) -> None:
    result = await orchestrator_without_hits.run("公司的年假制度是什么？")
    assert result.refused is True
    assert "知识库无法确认" in result.answer
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/knowledge/test_retrieval.py tests/api/test_rag_chat.py -v`

预期：FAIL，因为检索与拒答逻辑尚不存在。

- [ ] **步骤 3：实现检索契约**

```python
# backend/app/knowledge/schemas.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    document_id: int
    filename: str
    page: int
    text: str
    score: float
```

```python
# backend/app/knowledge/retrieval.py
from app.knowledge.access import AccessContext
from app.knowledge.schemas import Citation


class RetrievalService:
    def __init__(self, store, minimum_score: float = 0.55) -> None:
        self.store = store
        self.minimum_score = minimum_score

    async def search(self, query: str, access: AccessContext) -> list[Citation]:
        permission_filter = {
            "knowledge_base_id": sorted(access.knowledge_base_ids),
            "roles": sorted(access.roles),
            "departments": [access.department],
        }
        hits = await self.store.search(query, permission_filter, limit=5)
        return [
            Citation(hit.document_id, hit.filename, hit.page, hit.text, hit.score)
            for hit in hits
            if hit.score >= self.minimum_score
        ]
```

修改编排器：知识类 Agent 必须先检索；引用列表为空时拒答；只允许将引用文本传给模型。API 响应中返回引用。

- [ ] **步骤 4：运行阶段验证**

运行：`cd backend; python -m pytest tests/auth tests/knowledge tests/api/test_rag_chat.py -v; python -m ruff check .; python -m mypy app`

预期：认证、权限、入库、检索、引用与拒答测试全部通过。

- [ ] **步骤 5：提交**

```bash
git add backend
git commit -m "feat: add permission-aware RAG with citations"
```

### 任务 5：会话持久化、最近消息缓存与反馈

**文件：**
- Create: `backend/app/conversations/models.py`
- Create: `backend/app/conversations/service.py`
- Create: `backend/app/conversations/api.py`
- Create: `backend/alembic/versions/0003_conversations.py`
- Test: `backend/tests/conversations/test_service.py`
- Test: `backend/tests/api/test_conversations.py`

- [ ] **步骤 1：编写所有权与缓存测试**

```python
import pytest


@pytest.mark.asyncio
async def test_user_cannot_read_another_users_conversation(conversation_service) -> None:
    conversation = await conversation_service.create(user_id=1, title="VPN")
    with pytest.raises(PermissionError):
        await conversation_service.get(conversation.id, user_id=2)


@pytest.mark.asyncio
async def test_recent_context_is_limited_to_eight_messages(conversation_service) -> None:
    conversation = await conversation_service.create(user_id=1, title="制度")
    for index in range(12):
        await conversation_service.add_message(conversation.id, "user", str(index))
    recent = await conversation_service.recent_context(conversation.id, limit=8)
    assert [item.content for item in recent] == [str(index) for index in range(4, 12)]
```

- [ ] **步骤 2：确认 RED**

运行：`cd backend; python -m pytest tests/conversations tests/api/test_conversations.py -v`

预期：FAIL，因为会话持久化尚不存在。

- [ ] **步骤 3：实现所有权优先的会话服务**

```python
# backend/app/conversations/models.py
class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str]
    agent: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version_id: Mapped[int | None]
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rating: Mapped[int]
    comment: Mapped[str | None]
```

`ConversationService.get/list/delete` 必须按 `user_id` 过滤。`add_message()` 先写 PostgreSQL，再更新 Redis 列表 `conversation:{id}:recent`，并裁剪为 8 条。Redis 为空时，`recent_context()` 回退到 PostgreSQL。反馈只接受 `-1` 或 `1`，且只能由对应消息的所有者提交。

- [ ] **步骤 4：确认 GREEN 并验证迁移**

运行：`cd backend; alembic upgrade head; python -m pytest tests/conversations tests/api/test_conversations.py -v`

预期：所有权、8 条消息缓存、删除与反馈测试通过。

- [ ] **步骤 5：提交**

```bash
git add backend/app/conversations backend/alembic backend/tests/conversations backend/tests/api/test_conversations.py
git commit -m "feat: persist conversations and employee feedback"
```
