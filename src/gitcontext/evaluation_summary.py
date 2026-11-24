"""Aggregate one evaluation run with explicit populations and denominators."""

import math
from dataclasses import dataclass
from statistics import mean, median

from gitcontext.evaluation import ObservationStatus, metrics_at_k
from gitcontext.evaluation_runner import EvaluationRun


@dataclass(frozen=True)
class TimingSummary:
    count: int
    minimum: float | None
    mean: float | None
    median: float | None
    maximum: float | None


@dataclass(frozen=True)
class StatusTiming:
    status: ObservationStatus
    total_seconds: TimingSummary
    ranking_seconds: TimingSummary


@dataclass(frozen=True)
class EvaluationSummary:
    dataset_id: str
    dataset_version: str
    snapshot_id: str
    split: str
    dataset_case_count: int
    saved_degraded: bool
    ranking_version: str
    tokenization_version: str
    k: int
    attempted: int
    current: int
    stale: int
    unknown: int
    errors: int
    supported_labelled: int
    unsupported_labelled: int
    unlabelled: int
    eligible: int
    hit_count: int
    hit_rate_at_k: float | None
    macro_recall_at_k: float | None
    current_unsupported_cases: int
    unsupported_cases_with_matches: int
    citation_checked_observations: int
    citation_valid_observations: int
    citation_invalid_observations: int
    citations_checked: int
    citation_observation_validity_rate: float | None
    timings: tuple[StatusTiming, ...]
    summary_version: str = "evaluation-summary-v1"


def _valid_time(value: float) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _timing(values: list[float]) -> TimingSummary:
    if not values:
        return TimingSummary(0, None, None, None, None)
    return TimingSummary(
        len(values), min(values), mean(values), median(values), max(values)
    )


def summarize_run(run: EvaluationRun) -> EvaluationSummary:
    """Score only current positive-label cases; retain every attempted outcome.

    This assumes runner-created data, verifies complete/unique case coverage and
    stored metric consistency, and performs no I/O, relevance labeling, or tuning.
    Citation validity is observation-level, not a per-reference percentage.
    """
    expected = {case.case_id: case for case in run.dataset.cases}
    observed = [item.case.case_id for item in run.observations]
    if (
        not expected
        or len(observed) != len(set(observed))
        or set(observed) != set(expected)
    ):
        raise ValueError("Summary requires exactly one observation per selected case")
    if run.dataset_case_count < len(expected) or not _valid_time(run.setup_seconds):
        raise ValueError("Invalid run metadata")
    for item in run.observations:
        if item.case != expected[item.case.case_id] or item.case.split != run.split:
            raise ValueError("Observation does not match selected dataset case")
        calculated = metrics_at_k(
            [match.chunk_id for match in item.matches],
            item.case.relevant_chunk_ids,
            k=run.k,
            status=item.status,
        )
        if calculated != item.metrics:
            raise ValueError("Stored metrics do not match observation")
        if not _valid_time(item.total_seconds) or (
            item.ranking_seconds is not None
            and (
                not _valid_time(item.ranking_seconds)
                or item.ranking_seconds > item.total_seconds
            )
        ):
            raise ValueError("Invalid observation timing")
        if type(item.citations_checked) is not int or item.citations_checked < 0:
            raise ValueError("Invalid citation count")
        if (item.citation_valid is None) != (item.citations_checked == 0):
            raise ValueError("Citation validity requires a nonempty checked population")
    rows = run.observations
    eligible = [
        item
        for item in rows
        if item.status == "current" and item.metrics.hit_at_k is not None
    ]
    hits = sum(item.metrics.hit_at_k is True for item in eligible)
    checked = [item for item in rows if item.citation_valid is not None]
    valid = sum(item.citation_valid is True for item in checked)
    unsupported = [
        item
        for item in rows
        if item.status == "current" and item.case.expected_behavior == "unsupported"
    ]
    statuses: tuple[ObservationStatus, ...] = ("current", "stale", "unknown", "error")
    return EvaluationSummary(
        dataset_id=run.dataset.dataset_id,
        dataset_version=run.dataset.dataset_version,
        snapshot_id=run.dataset.snapshot_id,
        split=run.split,
        dataset_case_count=run.dataset_case_count,
        saved_degraded=run.saved_degraded,
        ranking_version=run.ranking_version,
        tokenization_version=run.tokenization_version,
        k=run.k,
        attempted=len(rows),
        current=sum(item.status == "current" for item in rows),
        stale=sum(item.status == "stale" for item in rows),
        unknown=sum(item.status == "unknown" for item in rows),
        errors=sum(item.status == "error" for item in rows),
        supported_labelled=sum(
            item.case.expected_behavior == "supported" for item in rows
        ),
        unsupported_labelled=sum(
            item.case.expected_behavior == "unsupported" for item in rows
        ),
        unlabelled=sum(item.case.label_status == "unlabelled" for item in rows),
        eligible=len(eligible),
        hit_count=hits,
        hit_rate_at_k=hits / len(eligible) if eligible else None,
        macro_recall_at_k=mean(item.metrics.recall_at_k for item in eligible)
        if eligible
        else None,
        current_unsupported_cases=len(unsupported),
        unsupported_cases_with_matches=sum(bool(item.matches) for item in unsupported),
        citation_checked_observations=len(checked),
        citation_valid_observations=valid,
        citation_invalid_observations=len(checked) - valid,
        citations_checked=sum(item.citations_checked for item in rows),
        citation_observation_validity_rate=valid / len(checked) if checked else None,
        timings=tuple(
            StatusTiming(
                status,
                _timing([item.total_seconds for item in rows if item.status == status]),
                _timing(
                    [
                        item.ranking_seconds
                        for item in rows
                        if item.status == status and item.ranking_seconds is not None
                    ]
                ),
            )
            for status in statuses
        ),
    )
