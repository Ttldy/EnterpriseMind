from dataclasses import dataclass

from redis import Redis
from rq import Queue, Retry
from rq.job import Job

from app.shared.config import Settings


@dataclass(frozen=True)
class JobRef:
    id: str
    status: str
    attempts: int


def job_key(
    document_id: int,
    sha256: str,
) -> str:
    return f"document-{document_id}-{sha256}"


def can_retry(attempts: int) -> bool:
    return attempts < 3


class DocumentJobService:
    def __init__(
        self,
        redis: Redis,
        settings: Settings,
    ) -> None:
        self._redis = redis
        self._settings = settings
        self._queue = Queue(
            settings.rq_document_queue,
            connection=redis,
            default_timeout=(
                settings.rq_job_timeout_seconds
            ),
        )

    def enqueue(
        self,
        document_id: int,
        sha256: str,
    ) -> JobRef:
        key = job_key(document_id, sha256)
        existing = Job.fetch(
            key,
            connection=self._redis,
        ) if self._exists(key) else None

        if existing is not None:
            return JobRef(
                id=existing.id,
                status=existing.get_status(
                    refresh=True
                ).value,
                attempts=int(
                    existing.meta.get(
                        "attempts",
                        0,
                    )
                ),
            )

        job = self._queue.enqueue(
            "app.knowledge.jobs.process_document_job",
            document_id,
            job_id=key,
            retry=Retry(
                max=3,
                interval=[10, 30, 60],
            ),
            result_ttl=(
                self._settings.rq_result_ttl_seconds
            ),
            failure_ttl=(
                self._settings.rq_result_ttl_seconds
            ),
            meta={"attempts": 0},
        )
        return JobRef(
            id=job.id,
            status="queued",
            attempts=0,
        )

    def status(self, job_id: str) -> JobRef:
        job = Job.fetch(
            job_id,
            connection=self._redis,
        )
        return JobRef(
            id=job.id,
            status=job.get_status(
                refresh=True
            ).value,
            attempts=int(
                job.meta.get("attempts", 0)
            ),
        )

    def retry(
        self,
        job_id: str,
    ) -> JobRef:
        job = Job.fetch(
            job_id,
            connection=self._redis,
        )
        attempts = int(
            job.meta.get("attempts", 0)
        )
        if not can_retry(attempts):
            raise ValueError(
                "maximum retry attempts reached"
            )
        job.requeue()
        return self.status(job.id)

    def _exists(self, job_id: str) -> bool:
        return bool(
            self._redis.exists(
                f"rq:job:{job_id}"
            )
        )
