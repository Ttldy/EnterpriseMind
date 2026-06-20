from dataclasses import dataclass


@dataclass(frozen=True)
class Citation:
    document_id: int
    filename: str
    page: int
    text: str
    score: float
    sensitivity: str
