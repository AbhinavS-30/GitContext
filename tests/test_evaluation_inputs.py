import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from gitcontext.evaluation_inputs import validate_evaluation_input
from gitcontext.snapshots import build_snapshot, snapshot_id


@pytest.fixture
def baseline(tmp_path):
    (tmp_path / "fixture.py").write_text("pass\n")
    return build_snapshot(tmp_path)


def payload(snapshot):
    return {
        "schema_version": "evaluation-input-v1",
        "dataset_id": "synthetic-test-only",
        "dataset_version": "test-v1",
        "snapshot_id": snapshot.snapshot_id,
        "labeling_rules": "Synthetic schema fixture; not relevance judgments",
        "limitations": ["Unit tests only; no formal questions or quality claims"],
        "cases": [
            {
                "case_id": "synthetic-case",
                "question": "Synthetic test input",
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


def test_matching_input_preserves_provenance_without_promoting_review(baseline):
    result = validate_evaluation_input(json.dumps(payload(baseline)), baseline)
    assert result.dataset_id == "synthetic-test-only"
    assert result.cases[0].relevant_chunk_ids == (baseline.chunks[0].chunk_id,)
    assert result.cases[0].review_status == "not_reviewed"
    assert result.cases[0].reviewer is None
    with pytest.raises(ValidationError):
        result.dataset_version = "changed"


def test_snapshot_mismatch_is_rejected_even_when_chunk_exists(baseline):
    data = payload(baseline)
    data["snapshot_id"] = "snapshot-v2:different"
    with pytest.raises(ValueError, match="different snapshot"):
        validate_evaluation_input(json.dumps(data), baseline)


def test_unknown_or_duplicate_chunk_references_are_rejected(baseline):
    data = payload(baseline)
    data["cases"][0]["relevant_chunk_ids"] = ["not-in-snapshot"]
    with pytest.raises(ValueError, match="Unknown relevant"):
        validate_evaluation_input(json.dumps(data), baseline)
    data = payload(baseline)
    data["cases"][0]["relevant_chunk_ids"] *= 2
    with pytest.raises(ValueError, match="Duplicate relevant"):
        validate_evaluation_input(json.dumps(data), baseline)


def test_duplicate_cases_and_empty_datasets_are_rejected(baseline):
    data = payload(baseline)
    data["cases"] *= 2
    with pytest.raises(ValueError, match="Duplicate evaluation"):
        validate_evaluation_input(json.dumps(data), baseline)
    data["cases"] = []
    with pytest.raises(ValueError):
        validate_evaluation_input(json.dumps(data), baseline)


@pytest.mark.parametrize(
    "change",
    [
        {"relevant_chunk_ids": []},
        {"label_author": None},
        {"expected_behavior": "undetermined"},
        {"expected_behavior": "unsupported"},
        {"review_status": "human_reviewed"},
        {"review_status": "codex_reviewed"},
        {"reviewer": "test-reviewer"},
    ],
)
def test_inconsistent_label_or_review_states_are_rejected(baseline, change):
    data = payload(baseline)
    data["cases"][0].update(change)
    with pytest.raises(ValueError):
        validate_evaluation_input(json.dumps(data), baseline)


def test_unlabelled_and_explicit_unsupported_cases_are_distinct(baseline):
    data = payload(baseline)
    case = data["cases"][0]
    case.update(expected_behavior="unsupported", relevant_chunk_ids=[])
    unsupported = validate_evaluation_input(json.dumps(data), baseline).cases[0]
    assert unsupported.label_status == "labelled" and unsupported.label_author
    case.update(
        label_status="unlabelled", expected_behavior="undetermined", label_author=None
    )
    unlabelled = validate_evaluation_input(json.dumps(data), baseline).cases[0]
    assert unlabelled.label_status == "unlabelled"
    case["expected_behavior"] = "unsupported"
    with pytest.raises(ValueError):
        validate_evaluation_input(json.dumps(data), baseline)


@pytest.mark.parametrize("review", ["codex_reviewed", "human_reviewed"])
def test_review_declarations_are_explicit_caller_metadata(baseline, review):
    data = payload(baseline)
    data["cases"][0].update(review_status=review, reviewer="declared-test-reviewer")
    # This verifies schema preservation, not that a human review occurred.
    result = validate_evaluation_input(json.dumps(data), baseline)
    assert result.cases[0].review_status == review


@pytest.mark.parametrize(
    "field,value",
    [
        ("question", "   "),
        ("question", "x" * 2001),
        ("case_id", ""),
        ("case_id", 42),
        ("split", "test"),
        ("unexpected", True),
    ],
)
def test_strict_case_fields(baseline, field, value):
    data = payload(baseline)
    data["cases"][0][field] = value
    with pytest.raises(ValueError):
        validate_evaluation_input(json.dumps(data), baseline)


def test_extra_dataset_fields_and_wrong_schema_are_rejected(baseline):
    data = payload(baseline)
    data["invented_quality_score"] = 1.0
    with pytest.raises(ValueError):
        validate_evaluation_input(json.dumps(data), baseline)
    data = payload(baseline)
    data["schema_version"] = "future-v99"
    with pytest.raises(ValueError):
        validate_evaluation_input(json.dumps(data), baseline)


def test_partial_baseline_is_rejected_and_degraded_is_retained(baseline):
    manifest = replace(baseline.manifest, partial=True)
    partial = replace(baseline, manifest=manifest, snapshot_id=snapshot_id(manifest))
    with pytest.raises(ValueError, match="complete source"):
        validate_evaluation_input(json.dumps(payload(partial)), partial)
    manifest = replace(baseline.manifest, degraded=True)
    degraded = replace(baseline, manifest=manifest, snapshot_id=snapshot_id(manifest))
    assert validate_evaluation_input(json.dumps(payload(degraded)), degraded)
    assert degraded.manifest.degraded


def test_held_out_declaration_is_preserved_and_malformed_json_rejected(baseline):
    data = payload(baseline)
    data["cases"][0]["split"] = "held_out"
    assert (
        validate_evaluation_input(json.dumps(data), baseline).cases[0].split
        == "held_out"
    )
    with pytest.raises(ValueError):
        validate_evaluation_input('{"unfinished":', baseline)
