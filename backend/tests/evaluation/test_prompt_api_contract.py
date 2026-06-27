from datetime import UTC, datetime

from app.evaluation.api import prompt_dict
from app.evaluation.models import PromptVersion


def test_prompt_response_exposes_candidate_status() -> None:
    prompt = PromptVersion(
        id=9,
        prompt_key="it_agent",
        version=2,
        content="candidate prompt content",
        content_sha256="0" * 64,
        is_active=False,
        created_by=1,
        created_at=datetime.now(UTC),
    )

    assert prompt_dict(prompt)["status"] == "candidate"

