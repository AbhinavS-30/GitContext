import json
import subprocess
import sys
from dataclasses import replace

import pytest

from gitcontext.cli import main
from gitcontext.persistence import load_snapshot, save_snapshot
from gitcontext.snapshots import snapshot_id


def invoke(capsys, *arguments):
    code = main([str(arg) for arg in arguments])
    captured = capsys.readouterr()
    return code, json.loads(captured.out or captured.err)


@pytest.fixture
def indexed(tmp_path, capsys):
    (tmp_path / "app.py").write_text("def save_record():\n    return True\n")
    (tmp_path / "README.md").write_text("# Persistence\nSave records locally.\n")
    assert invoke(capsys, "index", tmp_path)[0] == 0
    return tmp_path


def test_current_search_returns_ranked_traceable_evidence_without_writes(
    indexed, capsys
):
    path = indexed / ".gitcontext/snapshot.json"
    old = path.read_bytes()
    code, output = invoke(capsys, "search", indexed, "save record", "--top-k", 1)
    assert code == 0
    assert output["freshness"]["status"] == "current"
    assert output["evidence_state"] == "source_freshness_checked"
    assert output["score_kind"] == "distinct_normalized_query_term_count"
    assert output["query_terms"] == ["record", "save"]
    assert len(output["matches"]) == 1
    match = output["matches"][0]
    assert match["score"] == 2
    assert match["matched_terms"] == ["record", "save"]
    assert match["source"]["path"] == "app.py"
    assert match["source"]["text"] == (indexed / "app.py").read_text()
    snapshot = load_snapshot(path)
    assert output["snapshot_id"] == snapshot.snapshot_id
    assert match["chunk_id"] == snapshot.manifest.files[1].chunk_ids[0]
    assert output["tokenization_version"] == "code-words-v1"
    assert output["ranking_version"] == "distinct-term-overlap-v1"
    assert path.read_bytes() == old


@pytest.mark.parametrize("change,exit_code", [("stale", 3), ("unreadable", 4)])
def test_stale_or_unknown_blocks_ranking_and_never_refreshes(
    indexed, capsys, monkeypatch, change, exit_code
):
    path = indexed / ".gitcontext/snapshot.json"
    old = path.read_bytes()
    (indexed / "app.py").write_bytes(
        b"def save_record():\n    return None\n" if change == "stale" else b"\xff"
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Blocked search must not rank, rebuild, or write")

    monkeypatch.setattr("gitcontext.cli.rank_chunks", forbidden)
    monkeypatch.setattr("gitcontext.cli.build_snapshot", forbidden)
    monkeypatch.setattr("gitcontext.cli.save_snapshot", forbidden)
    code, output = invoke(capsys, "search", indexed, "save")
    assert code == exit_code
    assert output["matches"] == []
    assert output["evidence_state"] in ("blocked_stale", "blocked_unknown")
    assert "refresh" in output["next_action"]
    assert path.read_bytes() == old


def test_explicit_refresh_enables_search_after_edit(indexed, capsys):
    (indexed / "app.py").write_text("def update_record():\n    pass\n")
    assert invoke(capsys, "search", indexed, "update_record")[0] == 3
    assert invoke(capsys, "refresh", indexed)[0] == 0
    code, output = invoke(capsys, "search", indexed, "update_record")
    assert code == 0
    assert "update_record" in output["matches"][0]["matched_terms"]


@pytest.mark.parametrize("query", ["", "!!! ___", "unfindable"])
def test_no_match_is_successful_empty_result(indexed, capsys, query):
    code, output = invoke(capsys, "search", indexed, query)
    assert code == 0
    assert output["matches"] == []
    assert output["freshness"]["status"] == "current"


def test_degraded_current_source_keeps_fallback_warning(indexed, capsys):
    (indexed / "app.py").write_text("def broken(:\n")
    assert invoke(capsys, "refresh", indexed)[0] == 0
    code, output = invoke(capsys, "search", indexed, "broken")
    assert code == 0 and output["saved_degraded"]
    assert output["matches"][0]["source"]["symbol_type"] == "fallback"
    assert any(issue["reason"] == "syntax_error" for issue in output["snapshot_issues"])


def test_saved_partial_snapshot_cannot_produce_search_results(indexed, capsys):
    path = indexed / ".gitcontext/snapshot.json"
    snapshot = load_snapshot(path)
    manifest = replace(snapshot.manifest, partial=True)
    save_snapshot(
        replace(snapshot, manifest=manifest, snapshot_id=snapshot_id(manifest)), path
    )
    code, output = invoke(capsys, "search", indexed, "save")
    assert code == 4 and not output["matches"]
    assert "saved_snapshot_partial" in output["freshness"]["limitations"]


def test_corrupted_snapshot_is_an_error_not_evidence(indexed, capsys):
    (indexed / ".gitcontext/snapshot.json").write_text("not JSON")
    code, output = invoke(capsys, "search", indexed, "save")
    assert code == 1 and "error" in output
    assert "matches" not in output


@pytest.mark.parametrize(
    "options", [["--top-k", "0"], ["--top-k", "101"], ["--top-k", "1.5"]]
)
def test_bad_top_k_is_argument_error(indexed, options):
    result = subprocess.run(
        [sys.executable, "-m", "gitcontext", "search", str(indexed), "save", *options],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_query_size_limit_is_argument_error(indexed):
    result = subprocess.run(
        [sys.executable, "-m", "gitcontext", "search", str(indexed), "x" * 2001],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_search_before_index_is_an_error(tmp_path, capsys):
    code, output = invoke(capsys, "search", tmp_path, "save")
    assert code == 1 and "error" in output
