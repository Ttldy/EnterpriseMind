from app.conversations.models import CitationRecord


def test_citation_document_reference_survives_document_delete() -> None:
    column = CitationRecord.__table__.c.document_id
    foreign_key = next(iter(column.foreign_keys))

    assert column.nullable is True
    assert foreign_key.ondelete == "SET NULL"

