from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
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
    overlap: int = 100,
) -> list[Chunk]:
    if size <= 0:
        raise ValueError("size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be between 0 and size")

    result: list[Chunk] = []
    chunk_index = 0
    step = size - overlap

    for page, text in pages:
        normalized = " ".join(text.split())
        for start in range(0, len(normalized), step):
            content = normalized[start : start + size].strip()
            if not content:
                continue

            result.append(
                Chunk(
                    chunk_index=chunk_index,
                    text=content,
                    payload={
                        "document_id": document_id,
                        "knowledge_base_id": knowledge_base_id,
                        "filename": filename,
                        "page": page,
                        "chunk_index": chunk_index,
                        "allowed_roles": sorted(roles),
                        "allowed_departments": sorted(departments),
                        "sensitivity": sensitivity,
                    },
                )
            )
            chunk_index += 1

    return result
