from pathlib import Path

import fitz
from docx import Document as DocxDocument


class UnsupportedDocumentError(ValueError):
    pass


def parse_document(
    path: Path,
) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix in {".txt", ".md"}:
        return parse_text(path)
    raise UnsupportedDocumentError(f"unsupported document type: {suffix}")


def parse_pdf(
    path: Path,
) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    with fitz.open(str(path)) as document:
        for index, page in enumerate(
            document,
            start=1,
        ):
            text = page.get_text("text").strip()
            if text:
                pages.append((index, text))
    return pages


def parse_docx(
    path: Path,
) -> list[tuple[int, str]]:
    document = DocxDocument(str(path))
    paragraphs = [
        paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()
    ]
    text = "\n".join(paragraphs)
    return [(1, text)] if text else []


def parse_text(
    path: Path,
) -> list[tuple[int, str]]:
    text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    ).strip()
    return [(1, text)] if text else []
