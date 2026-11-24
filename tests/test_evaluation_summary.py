import json
from dataclasses import replace

import pytest

from gitcontext.evaluation import metrics_at_k
from gitcontext.evaluation_runner import run_evaluation
from gitcontext.evaluation_summary import summarize_run
from gitcontext.freshness import FreshnessReport
from gitcontext.persistence import save_snapshot
from gitcontext.snapshots import build_snapshot


@pytest.fixture
def run(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "fixture.py").write_text("pass\n")
    (root / "other.py").write_text("x = 1\n")
    snapshot = build_snapshot(root)
    saved = tmp_path / "snapshot.json"
    save_snapshot(snapshot, saved)
    cases = []
    for index in range(5):
        cases.append(
            {
                "case_id": f"synthetic-{index}",
                "question": "pass",
                "split": "development",
                "expected_behavior": "supported",
                "label_status": "labelled",
                "relevant_chunk_ids": [snapshot.chunks[0].chunk_id],
                "label_author": "test-author",
                "review_status": "not_reviewed",
                "reviewer": None,
            }
        )
    cases[0]["relevant_chunk_ids"] = [item.chunk_id for item in snapshot.chunks]
    cases[1]["question"] = "synthetic-missing-term"
    cases[1]["relevant_chunk_ids"] = [item.chunk_id for item in snapshot.chunks]
    cases[2].update(expected_behavior="unsupported", relevant_chunk_ids=[])
    cases[3].update(
        expected_behavior="undetermined",
        label_status="unlabelled",
        relevant_chunk_ids=[],
        label_author=None,
    )
    path = tmp_path / "synthetic-input.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "evaluation-input-v1",
                "dataset_id": "synthetic-summary-only",
                "dataset_version": "test-v1",
                "snapshot_id": snapshot.snapshot_id,
                "labeling_rules": "Synthetic arithmetic tests, not relevance labels",
                "limitations": ["Not a benchmark or quality measurement"],
                "cases": cases,
            }
        )
    )
    result = run_evaluation(saved, path, root, split="development")
    rows = tuple(
        replace(item, ranking_seconds=0.1, total_seconds=float(index + 1))
        for index, item in enumerate(result.observations)
    )
    return replace(result, observations=rows, setup_seconds=0.5)


def blocked(item, status="unknown"):
    return replace(
        item,
        status=status,
        matches=(),
        metrics=metrics_at_k(
            [], item.case.relevant_chunk_ids, k=item.metrics.k, status=status
        ),
        freshness=FreshnessReport(status) if status != "error" else None,
        ranking_seconds=None,
        citations_checked=0,
        citation_valid=None,
        unsupported_case_has_matches=None,
        error="synthetic failure" if status == "error" else None,
    )


def test_mixed_outcomes_keep_attempted_count_and_explicit_denominator(run):
    run = replace(
        run, observations=(*run.observations[:4], blocked(run.observations[4]))
    )
    result = summarize_run(run)
    assert result.snapshot_id == run.dataset.snapshot_id
    assert result.dataset_id == "synthetic-summary-only"
    assert result.dataset_case_count == 5
    assert result.attempted == 5
    assert result.current == 4 and result.unknown == 1
    assert result.supported_labelled == 3
    assert result.unsupported_labelled == result.unlabelled == 1
    assert result.eligible == 2 and result.hit_count == 1
    assert result.hit_rate_at_k == 0.5
    assert result.macro_recall_at_k == 0.25
    assert (
        result.current_unsupported_cases == result.unsupported_cases_with_matches == 1
    )
    assert (
        result.citation_checked_observations == result.citation_valid_observations == 3
    )
    assert result.citation_observation_validity_rate == 1.0
    assert result.timings[0].total_seconds.count == 4
    assert result.timings[2].total_seconds.count == 1
    assert result.timings[2].ranking_seconds.count == 0


def test_macro_recall_averages_cases_not_pooled_relevance_counts(run):
    result = summarize_run(run)
    assert result.eligible == 3
    assert result.hit_rate_at_k == pytest.approx(2 / 3)
    assert result.macro_recall_at_k == 0.5  # mean of 1/2, 0/2, 1/1; not pooled 2/5.


@pytest.mark.parametrize("status", ["stale", "unknown", "error"])
def test_all_blocked_or_failed_is_undefined_not_zero_or_success(run, status):
    result = summarize_run(
        replace(
            run, observations=tuple(blocked(item, status) for item in run.observations)
        )
    )
    assert result.attempted == 5 and result.eligible == 0
    assert result.hit_rate_at_k is None and result.macro_recall_at_k is None
    assert result.citation_observation_validity_rate is None
    assert result.citations_checked == 0


def test_no_positive_label_population_remains_undefined(run):
    cases = run.dataset.cases[2:4]
    selected = replace(
        run,
        dataset=run.dataset.model_copy(update={"cases": cases}),
        observations=run.observations[2:4],
    )
    result = summarize_run(selected)
    assert result.attempted == 2 and result.eligible == 0
    assert result.hit_rate_at_k is None and result.macro_recall_at_k is None


def test_citation_failure_is_not_hidden_by_error_status(run):
    failed = replace(
        blocked(run.observations[4], "error"),
        citations_checked=1,
        citation_valid=False,
        ranking_seconds=0.1,
    )
    result = summarize_run(replace(run, observations=(*run.observations[:4], failed)))
    assert result.errors == 1
    assert result.citation_invalid_observations == 1
    assert result.citation_checked_observations == 4
    assert result.citation_observation_validity_rate == 0.75
    assert result.timings[3].ranking_seconds.count == 1


def test_timing_summaries_separate_populations_and_are_repeatable(run):
    result = summarize_run(run)
    assert result == summarize_run(run)
    current = result.timings[0]
    assert current.total_seconds.count == 5
    assert current.total_seconds.minimum == 1.0
    assert current.total_seconds.mean == current.total_seconds.median == 3.0
    assert current.total_seconds.maximum == 5.0
    assert current.ranking_seconds.mean == 0.1
    assert result.timings[1].total_seconds.count == 0
    assert result.timings[1].total_seconds.mean is None
    assert run.setup_seconds == 0.5  # Not added to each per-case timing.


@pytest.mark.parametrize("kind", ["missing", "duplicate", "metrics", "case"])
def test_incomplete_or_inconsistent_runs_are_rejected(run, kind):
    if kind == "missing":
        run = replace(run, observations=run.observations[:-1])
    elif kind == "duplicate":
        run = replace(run, observations=(*run.observations[:-1], run.observations[0]))
    elif kind == "metrics":
        bad = replace(
            run.observations[0],
            metrics=replace(run.observations[0].metrics, hit_at_k=False),
        )
        run = replace(run, observations=(bad, *run.observations[1:]))
    else:
        bad = replace(
            run.observations[0],
            case=run.observations[0].case.model_copy(update={"question": "different"}),
        )
        run = replace(run, observations=(bad, *run.observations[1:]))
    with pytest.raises(ValueError):
        summarize_run(run)


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_invalid_times_are_rejected(run, value):
    bad = replace(run.observations[0], total_seconds=value)
    with pytest.raises(ValueError):
        summarize_run(replace(run, observations=(bad, *run.observations[1:])))


def test_inconsistent_citation_population_is_rejected(run):
    bad = replace(run.observations[0], citations_checked=0, citation_valid=True)
    with pytest.raises(ValueError, match="Citation validity"):
        summarize_run(replace(run, observations=(bad, *run.observations[1:])))
