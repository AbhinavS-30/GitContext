"""Per-observation retrieval arithmetic; no dataset or quality claims."""

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Literal

ObservationStatus = Literal["current", "stale", "unknown", "error"]


@dataclass(frozen=True)
class RetrievalMetrics:
    k: int
    status: ObservationStatus
    relevant_count: int
    retrieved_count: int
    matched_relevant_count: int | None
    hit_at_k: bool | None
    recall_at_k: float | None


def _check_ids(values: Collection[str]) -> None:
    if isinstance(values, str | bytes):
        raise ValueError("Expected a collection of chunk IDs, not a string")
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError("Chunk IDs must be nonempty strings")
    if len(set(values)) != len(values):
        raise ValueError("Duplicate chunk IDs are not allowed")


def metrics_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: Collection[str],
    *,
    k: int,
    status: ObservationStatus,
) -> RetrievalMetrics:
    """Compute hit/recall for current, positively labeled observations only.

    Ordering is supplied by retrieval; cutoff is applied before matching. Empty
    labels mean metrics are undefined, not perfect recall. Stale/unknown/error
    states remain explicit and cannot receive scores or contain returned evidence.
    IDs and their labels must be validated against a snapshot by a future runner.
    """
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    if status not in ("current", "stale", "unknown", "error"):
        raise ValueError("Unsupported observation status")
    _check_ids(retrieved_ids)
    _check_ids(relevant_ids)
    if status != "current":
        if retrieved_ids:
            raise ValueError("Blocked/failed observations cannot contain evidence")
        return RetrievalMetrics(k, status, len(relevant_ids), 0, None, None, None)
    top = retrieved_ids[:k]
    matched = len(set(top).intersection(relevant_ids))
    if not relevant_ids:
        return RetrievalMetrics(k, status, 0, len(top), matched, None, None)
    return RetrievalMetrics(
        k,
        status,
        len(relevant_ids),
        len(top),
        matched,
        matched > 0,
        matched / len(relevant_ids),
    )
