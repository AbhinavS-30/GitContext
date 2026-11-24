import json
import subprocess
import sys

import pytest

from gitcontext.cli import main
from gitcontext.persistence import load_snapshot


def invoke(capsys, *arguments):
    code = main([str(arg) for arg in arguments])
    output = capsys.readouterr()
    return code, json.loads(output.out or output.err)


@pytest.fixture
def fixture(tmp_path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "fixture.py").write_text("pass\n")
    assert invoke(capsys, "index", root)[0] == 0
    snapshot = load_snapshot(root / ".gitcontext/snapshot.json")
    data = {
        "schema_version": "evaluation-input-v1",
        "dataset_id": "synthetic-cli-only",
        "dataset_version": "test-v1",
        "snapshot_id": snapshot.snapshot_id,
        "labeling_rules": "Synthetic CLI checks, not relevance judgments",
        "limitations": ["Not a formal dataset or quality measurement"],
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
    path = tmp_path / "synthetic-input.json"
    path.write_text(json.dumps(data))
    return root, path, data


def evaluate(capsys, root, dataset, split="development"):
    return invoke(capsys, "evaluate", root, "--dataset", dataset, "--split", split)


def test_cli_emits_complete_versioned_report_without_writes(fixture, capsys):
    root, path, _ = fixture
    saved = root / ".gitcontext/snapshot.json"
    before = path.read_bytes(), saved.read_bytes()
    code, report = evaluate(capsys, root, path)
    assert code == 0 and report["report_version"] == "evaluation-report-v1"
    assert report["summary"]["attempted"] == report["summary"]["eligible"] == 1
    assert report["run"]["dataset"]["dataset_id"] == "synthetic-cli-only"
    observation = report["run"]["observations"][0]
    assert observation["citation_valid"] is True
    assert observation["case"]["review_status"] == "not_reviewed"
    assert observation["ranking_seconds"] <= observation["total_seconds"]
    assert (path.read_bytes(), saved.read_bytes()) == before


@pytest.mark.parametrize("state,code", [("stale", 3), ("unknown", 4)])
def test_blocked_cases_return_full_report_and_nonzero_exit(
    fixture, capsys, state, code
):
    root, path, _ = fixture
    (root / "fixture.py").write_bytes(b"x = 1\n" if state == "stale" else b"\xff")
    result, report = evaluate(capsys, root, path)
    assert result == code
    assert report["summary"]["attempted"] == 1 and report["summary"]["eligible"] == 0
    assert report["summary"]["hit_rate_at_k"] is None
    assert report["run"]["observations"][0]["status"] == state
    assert report["run"]["observations"][0]["matches"] == []


def test_current_miss_is_execution_success_not_quality_failure(fixture, capsys):
    root, path, data = fixture
    data["cases"][0]["question"] = "synthetic-no-match"
    path.write_text(json.dumps(data))
    code, report = evaluate(capsys, root, path)
    assert code == 0
    assert report["summary"]["hit_rate_at_k"] == 0.0
    assert report["summary"]["macro_recall_at_k"] == 0.0


def test_wrong_snapshot_is_setup_error_not_a_scored_report(fixture, capsys):
    root, path, data = fixture
    data["snapshot_id"] = "wrong-snapshot"
    path.write_text(json.dumps(data))
    code, output = evaluate(capsys, root, path)
    assert code == 1 and "different snapshot" in output["error"]
    assert "summary" not in output


def test_selected_split_only_appears_in_report(fixture, capsys):
    root, path, data = fixture
    data["cases"].append(
        dict(data["cases"][0], case_id="synthetic-held", split="held_out")
    )
    path.write_text(json.dumps(data))
    code, report = evaluate(capsys, root, path, "held_out")
    assert code == 0 and report["summary"]["dataset_case_count"] == 2
    assert report["summary"]["attempted"] == 1
    assert [case["case_id"] for case in report["run"]["dataset"]["cases"]] == [
        "synthetic-held"
    ]


def test_per_case_error_keeps_report_and_exit_one(fixture, capsys, monkeypatch):
    root, path, _ = fixture

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr("gitcontext.evaluation_runner.rank_chunks", fail)
    code, report = evaluate(capsys, root, path)
    assert code == 1
    assert report["summary"]["errors"] == report["summary"]["attempted"] == 1
    assert "synthetic failure" in report["run"]["observations"][0]["error"]


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--dataset", "absent.json"],
        ["--split", "all"],
        ["--dataset", "absent.json", "--split", "development", "--top-k", "101"],
    ],
)
def test_required_and_invalid_options_are_argument_errors(fixture, extra):
    root, _, _ = fixture
    result = subprocess.run(
        [sys.executable, "-m", "gitcontext", "evaluate", str(root), *extra],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_dataset_symlink_is_refused(fixture, capsys):
    root, path, _ = fixture
    link = path.parent / "linked-input.json"
    link.symlink_to(path)
    code, output = evaluate(capsys, root, link)
    assert code == 1 and "error" in output
