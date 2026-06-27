from dataclasses import dataclass

from app.knowledge.vector_store import VectorHit


@dataclass(frozen=True)
class FusedHit:
    hit: VectorHit
    best_score: float
    hit_count: int
    fused_score: float
    source_queries: tuple[str, ...]
    relevance: float | None = None
    coverage: float | None = None
    rerank_reason: str = ""


def fuse_hits(
    query_hits: list[tuple[str, list[VectorHit]]],
    limit: int,
) -> list[FusedHit]:
    grouped: dict[tuple[int, int, str], FusedHit] = {}

    for query, hits in query_hits:
        for rank, hit in enumerate(
            hits,
            start=1,
        ):
            key = (
                hit.document_id,
                hit.page,
                hit.text,
            )
            rank_bonus = 1.0 / (rank + 10)
            existing = grouped.get(key)
            if existing is None:
                grouped[key] = FusedHit(
                    hit=hit,
                    best_score=hit.score,
                    hit_count=1,
                    fused_score=hit.score + rank_bonus,
                    source_queries=(query,),
                )
                continue

            best_hit = hit if hit.score > existing.best_score else existing.hit
            source_queries = (
                existing.source_queries
                if query in existing.source_queries
                else (*existing.source_queries, query)
            )
            grouped[key] = FusedHit(
                hit=best_hit,
                best_score=max(existing.best_score, hit.score),
                hit_count=existing.hit_count + 1,
                fused_score=existing.fused_score + hit.score + rank_bonus,
                source_queries=source_queries,
            )

    return sorted(
        grouped.values(),
        key=lambda item: (
            item.hit_count,
            item.best_score,
            item.fused_score,
        ),
        reverse=True,
    )[:limit]
