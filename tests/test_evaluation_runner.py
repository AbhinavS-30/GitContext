import json
from dataclasses import replace

import pytest

from gitcontext.evaluation_runner import load_evaluation_input, run_evaluation
from gitcontext.lexical import LexicalMatch, LexicalReport
from gitcontext.persistence import save_snapshot
from gitcontext.snapshots import build_snapshot


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "fixture.py").write_text("pass\n")
    snapshot = build_snapshot(root)
    saved = tmp_path / "snapshot.json"
    save_snapshot(snapshot, saved)
    dataset = tmp_path / "synthetic-input.json"
    data = {
        "schema_version": "evaluation-input-v1",
        "dataset_id": "synthetic-test-only",
        "dataset_version": "test-v1",
        "snapshot_id": snapshot.snapshot_id,
        "labeling_rules": "Synthetic runner checks, not relevance judgments",
        "limitations": ["Unit fixture, not benchmark data"],
        "cases": [
            {
                "case_id": "synthetic-1",
                "question": "pass",
                "split": "development",
                "expected_behavior": "supported",
                "label_status": "labelled",
                "relevant_chunk_ids": [snapshot.chunks[0].chunk_id],
                "label_author": "test-author",
                "review_status": "not_reviewed",
                "reviewer": None,
            }
        ],
    }
    dataset.write_text(json.dumps(data))
    return root, snapshot, saved, dataset, data


def test_current_run_records_provenance_metrics_timings_and_citations(fixture):
    root, snapshot, saved, dataset, _ = fixture
    before = saved.read_bytes(), dataset.read_bytes()
    run = run_evaluation(saved, dataset, root, split="development")
    assert run.dataset.snapshot_id == snapshot.snapshot_id
    assert run.manifest == snapshot.manifest
    assert run.root == root.resolve()
    assert run.dataset.cases[0].review_status == "not_reviewed"
    assert run.chunk_count == run.file_count == 1
    observation = run.observations[0]
    assert observation.status == "current" and observation.metrics.hit_at_k is True
    assert observation.metrics.recall_at_k == 1.0
    assert observation.citation_valid is True and observation.citations_checked == 1
    assert 0 <= observation.ranking_seconds <= observation.total_seconds
    assert run.setup_seconds >= 0
    assert run.ranking_version and run.tokenization_version
    assert (saved.read_bytes(), dataset.read_bytes()) == before


@pytest.mark.parametrize("state", ["stale", "unknown"])
def test_blocked_observations_are_preserved_and_never_rank(fixture, monkeypatch, state):
    root, _, saved, dataset, _ = fixture
    (root / "fixture.py").write_bytes(b"x = 1\n" if state == "stale" else b"\xff")

    def forbidden(*args, **kwargs):
        raise AssertionError("Must not rank blocked source")

    monkeypatch.setattr("gitcontext.evaluation_runner.rank_chunks", forbidden)
    observation = run_evaluation(
        saved, dataset, root, split="development"
    ).observations[0]
    assert observation.status == state and observation.matches == ()
    assert observation.metrics.hit_at_k is None
    assert observation.ranking_seconds is None and observation.citation_valid is None
    assert observation.freshness.status == state


def test_wrong_snapshot_fails_before_retrieval(fixture, monkeypatch):
    root, _, saved, dataset, data = fixture
    data["snapshot_id"] = "wrong-snapshot"
    dataset.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="different snapshot"):
        run_evaluation(saved, dataset, root, split="development")


def test_split_is_explicit_and_other_split_is_not_executed(fixture):
    root, _, saved, dataset, data = fixture
    other = dict(data["cases"][0], case_id="synthetic-held-out", split="held_out")
    data["cases"].append(other)
    dataset.write_text(json.dumps(data))
    run = run_evaluation(saved, dataset, root, split="held_out")
    assert [o.case.case_id for o in run.observations] == ["synthetic-held-out"]
    assert len(run.dataset.cases) == 1
    assert run.dataset_case_count == 2
    assert run.dataset.cases[0].split == "held_out"
    with pytest.raises(ValueError, match="explicitly"):
        run_evaluation(saved, dataset, root, split="all")


def test_per_case_errors_remain_visible_and_later_cases_run(fixture, monkeypatch):
    root, _, saved, dataset, data = fixture
    data["cases"].append(dict(data["cases"][0], case_id="synthetic-2"))
    dataset.write_text(json.dumps(data))
    from gitcontext import evaluation_runner

    original = evaluation_runner.rank_chunks
    count = 0

    def fail_once(*args, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            raise RuntimeError("synthetic failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(evaluation_runner, "rank_chunks", fail_once)
    observations = run_evaluation(
        saved, dataset, root, split="development"
    ).observations
    assert [o.status for o in observations] == ["error", "current"]
    assert observations[0].metrics.hit_at_k is None
    assert "synthetic failure" in observations[0].error


def test_invalid_returned_source_fails_reference_check(fixture, monkeypatch):
    root, snapshot, saved, dataset, _ = fixture
    item = snapshot.chunks[0]
    altered = replace(item.source, text="altered")
    report = LexicalReport(
        ("pass",), (LexicalMatch(item.chunk_id, 1, ("pass",), altered),)
    )
    monkeypatch.setattr(
        "gitcontext.evaluation_runner.rank_chunks", lambda *a, **k: report
    )
    observation = run_evaluation(
        saved, dataset, root, split="development"
    ).observations[0]
    assert observation.status == "error" and observation.citation_valid is False
    assert observation.matches == () and observation.metrics.hit_at_k is None


@pytest.mark.parametrize("expectation", ["supported", "unsupported", "undetermined"])
def test_empty_results_and_label_status_do_not_become_invented_success(
    fixture, expectation
):
    root, _, saved, dataset, data = fixture
    case = data["cases"][0]
    case["question"] = "synthetic-unmatchable"
    if expectation != "supported":
        case.update(expected_behavior=expectation, relevant_chunk_ids=[])
    if expectation == "undetermined":
        case.update(label_status="unlabelled", label_author=None)
    dataset.write_text(json.dumps(data))
    observation = run_evaluation(
        saved, dataset, root, split="development"
    ).observations[0]
    assert observation.status == "current" and observation.matches == ()
    assert observation.citation_valid is None
    if expectation == "supported":
        assert (
            observation.metrics.hit_at_k is False
            and observation.metrics.recall_at_k == 0
        )
    else:
        assert observation.metrics.hit_at_k is None


def test_loader_bounds_regular_file_bytes_and_case_count(fixture, monkeypatch):
    _, snapshot, _, dataset, data = fixture
    monkeypatch.setattr("gitcontext.evaluation_runner.MAX_EVALUATION_BYTES", 10)
    with pytest.raises(ValueError, match="byte limit"):
        load_evaluation_input(dataset, snapshot)
    monkeypatch.setattr("gitcontext.evaluation_runner.MAX_EVALUATION_BYTES", 1_000_000)
    monkeypatch.setattr("gitcontext.evaluation_runner.MAX_EVALUATION_CASES", 1)
    data["cases"].append(dict(data["cases"][0], case_id="synthetic-2"))
    dataset.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="case limit"):
        load_evaluation_input(dataset, snapshot)


def test_loader_refuses_symlink_and_no_cases_in_split(fixture):
    root, snapshot, saved, dataset, _ = fixture
    link = dataset.parent / "linked.json"
    link.symlink_to(dataset)
    with pytest.raises(OSError):
        load_evaluation_input(link, snapshot)
    with pytest.raises(ValueError, match="No cases"):
        run_evaluation(saved, dataset, root, split="held_out")


@pytest.mark.parametrize("k", [0, True, 101])
def test_invalid_k(fixture, k):
    root, _, saved, dataset, _ = fixture
    with pytest.raises(ValueError):
        run_evaluation(saved, dataset, root, split="development", k=k)


def test_unsupported_case_can_still_have_lexical_matches(fixture):
    root, _, saved, dataset, data = fixture
    data["cases"][0].update(expected_behavior="unsupported", relevant_chunk_ids=[])
    dataset.write_text(json.dumps(data))
    observation = run_evaluation(
        saved, dataset, root, split="development"
    ).observations[0]
    assert observation.status == "current" and observation.unsupported_case_has_matches
    assert observation.metrics.hit_at_k is None


def test_snapshot_replacement_during_run_is_an_error(fixture, monkeypatch):
    root, snapshot, saved, dataset, _ = fixture
    from gitcontext import evaluation_runner

    original = evaluation_runner.load_snapshot
    calls = 0

    def changed(path):
        nonlocal calls
        calls += 1
        return (
            original(path) if calls == 1 else replace(snapshot, snapshot_id="different")
        )

    monkeypatch.setattr(evaluation_runner, "load_snapshot", changed)
    observation = run_evaluation(
        saved, dataset, root, split="development"
    ).observations[0]
    assert observation.status == "error" and observation.metrics.hit_at_k is None
    assert "changed during evaluation" in observation.error
