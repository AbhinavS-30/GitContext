import json
import subprocess
import sys

import pytest

from gitcontext.cli import main
from gitcontext.evaluation_runner import run_evaluation
from gitcontext.persistence import load_snapshot


def invoke(capsys, *args):
    code = main([str(arg) for arg in args])
    captured = capsys.readouterr()
    return code, json.loads(captured.out or captured.err)


@pytest.fixture
def fixture(tmp_path, capsys):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def record_id():\n    pass\n")
    assert invoke(capsys, "index", root)[0] == 0
    snapshot = load_snapshot(root / ".gitcontext/snapshot.json")
    dataset = tmp_path / "synthetic-input.json"
    dataset.write_text(
        json.dumps(
            {
                "schema_version": "evaluation-input-v1",
                "dataset_id": "synthetic-bm25-cli",
                "dataset_version": "test-v1",
                "snapshot_id": snapshot.snapshot_id,
                "labeling_rules": "Synthetic checks, not relevance judgments",
                "limitations": ["Not a benchmark"],
                "cases": [
                    {
                        "case_id": "synthetic-1",
                        "question": "record_id",
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
        )
    )
    return root, dataset


def test_overlap_remains_default_and_bm25_is_explicit(fixture, capsys):
    root, _ = fixture
    code, default = invoke(capsys, "search", root, "record_id")
    assert code == 0 and default["score_kind"] == "distinct_normalized_query_term_count"
    assert default["matches"][0]["score"] == 3
    assert (
        invoke(capsys, "search", root, "record_id", "--ranking", "overlap")[1]
        == default
    )
    code, candidate = invoke(capsys, "search", root, "record_id", "--ranking", "bm25")
    assert code == 0 and candidate["score_kind"] == "bm25_positive_idf_weight"
    assert candidate["ranking_version"] == "bm25-positive-idf-v1"
    assert candidate["ranking_parameters"] == [["k1", 1.2], ["b", 0.75]]
    assert candidate["document_count"] == 1
    assert candidate["evidence_state"] == "source_freshness_checked"
    assert candidate["matches"][0]["source"] == default["matches"][0]["source"]


def test_evaluation_records_method_and_parameters_without_changing_snapshot(
    fixture, capsys
):
    root, dataset = fixture
    path = root / ".gitcontext/snapshot.json"
    old = path.read_bytes()
    code, output = invoke(
        capsys,
        "evaluate",
        root,
        "--dataset",
        dataset,
        "--split",
        "development",
        "--ranking",
        "bm25",
    )
    assert code == 0
    assert (
        output["run"]["lexical_method"] == output["summary"]["lexical_method"] == "bm25"
    )
    assert (
        output["run"]["ranking_version"]
        == output["summary"]["ranking_version"]
        == "bm25-positive-idf-v1"
    )
    assert (
        output["run"]["ranking_parameters"]
        == output["summary"]["ranking_parameters"]
        == [["k1", 1.2], ["b", 0.75]]
    )
    assert output["summary"]["hit_count"] == 1
    assert path.read_bytes() == old


@pytest.mark.parametrize(
    "change,code", [(b"def other():\n    pass\n", 3), (b"\xff", 4)]
)
def test_candidate_search_and_evaluation_keep_freshness_gate(
    fixture, capsys, monkeypatch, change, code
):
    root, dataset = fixture
    (root / "app.py").write_bytes(change)

    def forbidden(*args, **kwargs):
        raise AssertionError("Blocked source must not call BM25")

    monkeypatch.setattr("gitcontext.cli.rank_bm25", forbidden)
    monkeypatch.setattr("gitcontext.evaluation_runner.rank_bm25", forbidden)
    result, search = invoke(capsys, "search", root, "record_id", "--ranking", "bm25")
    assert result == code and search["matches"] == []
    result, report = invoke(
        capsys,
        "evaluate",
        root,
        "--dataset",
        dataset,
        "--split",
        "development",
        "--ranking",
        "bm25",
    )
    assert result == code and report["summary"]["eligible"] == 0
    assert report["run"]["ranking_version"] == "bm25-positive-idf-v1"


def test_candidate_empty_match_is_not_invented_success(fixture, capsys):
    root, _ = fixture
    code, output = invoke(capsys, "search", root, "absent", "--ranking", "bm25")
    assert code == 0 and output["matches"] == []


def test_invalid_method_is_rejected(fixture):
    root, dataset = fixture
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "gitcontext",
            "search",
            str(root),
            "record_id",
            "--ranking",
            "invented",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    with pytest.raises(ValueError, match="ranking"):
        run_evaluation(
            root / ".gitcontext/snapshot.json",
            dataset,
            root,
            split="development",
            ranking="invented",
        )
