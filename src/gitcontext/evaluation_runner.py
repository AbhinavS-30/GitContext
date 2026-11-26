"""Bounded input loading and an in-memory lexical evaluation runner."""

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Literal

from gitcontext.bm25 import BM25_PARAMETERS, BM25_VERSION, rank_bm25
from gitcontext.evaluation import ObservationStatus, RetrievalMetrics, metrics_at_k
from gitcontext.evaluation_inputs import (
    EvaluationCase,
    EvaluationDataset,
    validate_evaluation_input,
)
from gitcontext.freshness import FreshnessReport, check_freshness
from gitcontext.lexical import (
    LEXICAL_RANKING_VERSION,
    MAX_TOP_K,
    LexicalMatch,
    rank_chunks,
)
from gitcontext.persistence import load_snapshot
from gitcontext.snapshots import Snapshot, SnapshotManifest
from gitcontext.tokenization import TOKENIZATION_VERSION

MAX_EVALUATION_BYTES = 1_000_000
MAX_EVALUATION_CASES = 1_000


@dataclass(frozen=True)
class EvaluationObservation:
    case: EvaluationCase
    status: ObservationStatus
    metrics: RetrievalMetrics
    matches: tuple[LexicalMatch, ...]
    freshness: FreshnessReport | None
    ranking_seconds: float | None
    total_seconds: float
    citations_checked: int
    citation_valid: bool | None
    unsupported_case_has_matches: bool | None
    error: str | None


@dataclass(frozen=True)
class EvaluationRun:
    dataset: EvaluationDataset
    manifest: SnapshotManifest
    root: Path
    split: Literal["development", "held_out"]
    k: int
    setup_seconds: float
    observations: tuple[EvaluationObservation, ...]
    saved_degraded: bool
    file_count: int
    chunk_count: int
    dataset_case_count: int
    ranking_version: str = LEXICAL_RANKING_VERSION
    tokenization_version: str = TOKENIZATION_VERSION
    retrieval_mode: str = "lexical"
    python_runtime: str = sys.version.split()[0]
    platform: str = sys.platform
    evaluation_version: str = "lexical-evaluation-v2"
    lexical_method: str = "overlap"
    ranking_parameters: tuple[tuple[str, float], ...] = ()


def load_evaluation_input(path: Path, snapshot: Snapshot) -> EvaluationDataset:
    """Read bounded regular-file JSON and bind it to the supplied snapshot."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb", buffering=0) as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Evaluation input must be a regular file")
        raw = stream.read(MAX_EVALUATION_BYTES + 1)
    if len(raw) > MAX_EVALUATION_BYTES:
        raise ValueError("Evaluation input exceeds byte limit")
    dataset = validate_evaluation_input(raw, snapshot)
    if len(dataset.cases) > MAX_EVALUATION_CASES:
        raise ValueError("Evaluation input exceeds case limit")
    return dataset


def run_evaluation(
    snapshot_path: Path,
    dataset_path: Path,
    root: Path,
    *,
    split: Literal["development", "held_out"],
    k: int = 5,
    ranking: Literal["overlap", "bm25"] = "overlap",
) -> EvaluationRun:
    """Run supplied cases; do not author data, tune settings, save, or refresh.

    Setup/invalid-input failures raise before queries. Per-case failures remain
    error observations. Total case time includes snapshot reload/validation,
    freshness, ranking, reference checks, and metric calculation. Ranking time is
    measured separately. These observations are not independent human validation.
    """
    if split not in ("development", "held_out"):
        raise ValueError("Choose development or held_out explicitly")
    if type(k) is not int or not 1 <= k <= MAX_TOP_K:
        raise ValueError(f"k must be an integer between 1 and {MAX_TOP_K}")
    if ranking not in ("overlap", "bm25"):
        raise ValueError("Choose overlap or bm25 ranking")
    setup_start = perf_counter()
    initial = load_snapshot(snapshot_path)
    dataset = load_evaluation_input(dataset_path, initial)
    cases = tuple(case for case in dataset.cases if case.split == split)
    if not cases:
        raise ValueError("No cases in requested split")
    setup_seconds = perf_counter() - setup_start
    observations = []
    for case in cases:
        start = perf_counter()
        status: ObservationStatus = "error"
        matches: tuple[LexicalMatch, ...] = ()
        freshness = None
        ranking_seconds = None
        citations_checked = 0
        citation_valid = None
        error = None
        try:
            snapshot = load_snapshot(snapshot_path)
            if snapshot.snapshot_id != dataset.snapshot_id:
                raise ValueError("Snapshot changed during evaluation")
            freshness = check_freshness(snapshot, root)
            status = freshness.status
            if status == "current":
                rank_start = perf_counter()
                ranker = rank_chunks if ranking == "overlap" else rank_bm25
                ranked = ranker(snapshot.chunks, case.question, top_k=k)
                ranking_seconds = perf_counter() - rank_start
                matches = ranked.matches
                citations_checked = len(matches)
                if matches:
                    known = {item.chunk_id: item.source for item in snapshot.chunks}
                    ids = [match.chunk_id for match in matches]
                    citation_valid = len(ids) == len(set(ids)) and all(
                        known.get(match.chunk_id) == match.source for match in matches
                    )
                    if not citation_valid:
                        raise ValueError(
                            "Invalid returned citation reference or source"
                        )
        except Exception as exc:
            # Failed observations remain visible and unscored; do not stop the
            # dataset at one case or silently omit it. Interrupts still propagate.
            status = "error"
            matches = ()
            error = f"{type(exc).__name__}: {exc}"
        metrics = metrics_at_k(
            [match.chunk_id for match in matches],
            case.relevant_chunk_ids,
            k=k,
            status=status,
        )
        unsupported = (
            bool(matches)
            if status == "current" and case.expected_behavior == "unsupported"
            else None
        )
        observations.append(
            EvaluationObservation(
                case,
                status,
                metrics,
                matches,
                freshness,
                ranking_seconds,
                perf_counter() - start,
                citations_checked,
                citation_valid,
                unsupported,
                error,
            )
        )
    return EvaluationRun(
        dataset=dataset.model_copy(update={"cases": cases}),
        manifest=initial.manifest,
        root=Path(root).resolve(),
        split=split,
        k=k,
        setup_seconds=setup_seconds,
        observations=tuple(observations),
        saved_degraded=initial.manifest.degraded,
        file_count=len(initial.manifest.files),
        chunk_count=len(initial.chunks),
        dataset_case_count=len(dataset.cases),
        lexical_method=ranking,
        ranking_version=LEXICAL_RANKING_VERSION
        if ranking == "overlap"
        else BM25_VERSION,
        ranking_parameters=() if ranking == "overlap" else BM25_PARAMETERS,
    )
