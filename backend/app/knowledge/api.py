from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import (
    get_access_context,
    require_role,
)
from app.auth.models import User
from app.knowledge.access import AccessContext
from app.knowledge.models import (
    Document,
    KnowledgeBase,
    KnowledgePermission,
)
from app.knowledge.service import (
    DuplicateDocumentError,
    InvalidUploadError,
    save_and_index_document,
)
from app.shared.config import get_settings
from app.shared.database import get_session

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
)


class KnowledgeBaseCreate(BaseModel):
    name: str
    domain: str
    sensitivity: str = "internal"
    is_public: bool = False


class PermissionCreate(BaseModel):
    subject_type: str
    subject_value: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    sensitivity: str
    error_message: str | None


@router.post("/bases")
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    knowledge_base = KnowledgeBase(
        name=body.name,
        domain=body.domain,
        sensitivity=body.sensitivity,
        is_public=body.is_public,
    )
    session.add(knowledge_base)
    await session.commit()
    await session.refresh(knowledge_base)
    return {
        "id": knowledge_base.id,
        "name": knowledge_base.name,
    }


@router.post("/bases/{knowledge_base_id}/permissions")
async def add_permission(
    knowledge_base_id: int,
    body: PermissionCreate,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    subject_type = body.subject_type.upper()
    if subject_type not in {"ROLE", "DEPARTMENT"}:
        raise HTTPException(
            status_code=422,
            detail="subject_type must be ROLE or DEPARTMENT",
        )

    permission = KnowledgePermission(
        knowledge_base_id=knowledge_base_id,
        subject_type=subject_type,
        subject_value=body.subject_value,
    )
    session.add(permission)
    await session.commit()
    await session.refresh(permission)
    return {"id": permission.id}


@router.post(
    "/bases/{knowledge_base_id}/documents",
    response_model=DocumentResponse,
)
async def upload_document(
    knowledge_base_id: int,
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> Document:
    try:
        return await save_and_index_document(
            session=session,
            vector_store=request.app.state.vector_store,
            settings=get_settings(),
            knowledge_base_id=knowledge_base_id,
            upload=file,
        )
    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except InvalidUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/documents/{document_id}/source")
async def download_document(
    document_id: int,
    access: AccessContext = Depends(get_access_context),
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    document = await session.scalar(select(Document).where(Document.id == document_id))
    if document is None or document.knowledge_base_id not in access.knowledge_base_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="resource not found",
        )

    path = Path(document.storage_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="resource not found",
        )
    return FileResponse(
        path,
        filename=document.filename,
    )

@router.get("/bases")
async def list_knowledge_bases(
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    bases = (
        await session.scalars(
            select(KnowledgeBase)
            .options(
                selectinload(
                    KnowledgeBase.permissions
                ),
                selectinload(
                    KnowledgeBase.documents
                ),
            )
            .order_by(KnowledgeBase.id)
        )
    ).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "domain": item.domain,
            "sensitivity": item.sensitivity,
            "is_public": item.is_public,
            "permissions": [
                {
                    "id": permission.id,
                    "subject_type": (
                        permission.subject_type
                    ),
                    "subject_value": (
                        permission.subject_value
                    ),
                }
                for permission in item.permissions
            ],
            "document_count": len(item.documents),
        }
        for item in bases
    ]


@router.get("/bases/{knowledge_base_id}/documents")
async def list_documents(
    knowledge_base_id: int,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, object]]:
    documents = (
        await session.scalars(
            select(Document)
            .where(
                Document.knowledge_base_id
                == knowledge_base_id
            )
            .order_by(Document.id.desc())
        )
    ).all()
    return [
        {
            "id": item.id,
            "filename": item.filename,
            "status": item.status,
            "sensitivity": item.sensitivity,
            "error_message": item.error_message,
            "created_at": item.created_at,
        }
        for item in documents
    ]


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: int,
    request: Request,
    _: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
) -> None:
    document = await session.get(
        Document,
        document_id,
    )
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="document not found",
        )

    await request.app.state.vector_store.delete_document(
        document.id
    )
    path = Path(document.storage_path)
    await session.execute(
        delete(Document).where(
            Document.id == document_id
        )
    )
    await session.commit()

    if path.exists():
        path.unlink()