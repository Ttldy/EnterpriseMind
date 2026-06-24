from app.knowledge.models import Document


def test_document_tracks_ingestion_job_fields() -> None:
    columns = Document.__table__.columns

    assert "job_id" in columns
    assert "attempts" in columns
    assert "updated_at" in columns
    assert columns["job_id"].index is True
    assert columns["attempts"].default is not None
    assert columns["attempts"].server_default is not None
    assert columns["updated_at"].server_default is not None
    assert columns["updated_at"].onupdate is not None
