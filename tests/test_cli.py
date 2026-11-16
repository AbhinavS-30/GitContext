import json
import subprocess
import sys

import pytest

from gitcontext.cli import main
from gitcontext.persistence import load_snapshot


def invoke(capsys, command, root, *options):
    code = main([command, str(root), *options])
    output = capsys.readouterr()
    return code, json.loads(output.out or output.err)


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text("def answer():\n    return True\n")
    return tmp_path


def test_full_command_flow_and_inspection_of_saved_evidence(repo, capsys):
    code, initial = invoke(capsys, "index", repo)
    assert code == 0 and initial["saved"]
    path = repo / ".gitcontext/snapshot.json"
    old = path.read_bytes()
    assert invoke(capsys, "status", repo)[0] == 0
    code, inspected = invoke(capsys, "inspect", repo)
    assert code == 0
    assert inspected["evidence_state"] == "saved_snapshot_not_freshness_checked"
    reference = inspected["files"][0]["chunk_ids"][0]
    code, chunk = invoke(capsys, "inspect", repo, "--chunk", reference)
    assert code == 0 and "return True" in chunk["chunk"]["source"]["text"]
    (repo / "app.py").write_text("def answer():\n    return None\n")
    code, stale = invoke(capsys, "status", repo)
    assert code == 3 and stale["modified"] == ["app.py"]
    assert path.read_bytes() == old
    code, refreshed = invoke(capsys, "refresh", repo)
    assert code == 0 and refreshed["saved"]
    assert refreshed["snapshot_id"] != initial["snapshot_id"]
    assert invoke(capsys, "status", repo)[0] == 0


def test_index_never_silently_replaces_existing_snapshot(repo, capsys):
    invoke(capsys, "index", repo)
    path = repo / ".gitcontext/snapshot.json"
    before = path.read_bytes()
    code, output = invoke(capsys, "index", repo)
    assert code == 1 and "refresh" in output["error"]
    assert path.read_bytes() == before


def test_partial_refresh_keeps_old_and_unknown_status_is_visible(repo, capsys):
    invoke(capsys, "index", repo)
    path = repo / ".gitcontext/snapshot.json"
    before = path.read_bytes()
    (repo / "app.py").write_bytes(b"\xff")
    assert invoke(capsys, "status", repo)[0] == 4
    code, output = invoke(capsys, "refresh", repo)
    assert code == 4 and not output["saved"] and output["partial"]
    assert path.read_bytes() == before


def test_partial_initial_index_does_not_publish(repo, capsys):
    (repo / "bad.md").write_bytes(b"\xff")
    code, output = invoke(capsys, "index", repo)
    assert code == 4 and not output["saved"]
    assert not (repo / ".gitcontext/snapshot.json").exists()


def test_degraded_complete_snapshot_is_saved_with_visible_warning(repo, capsys):
    (repo / "app.py").write_text("def broken(:\n")
    code, output = invoke(capsys, "index", repo)
    assert code == 0 and output["degraded"]
    assert output["issues"][0]["reason"] == "syntax_error"


def test_refresh_retains_limits_and_allows_explicit_override(repo, capsys):
    invoke(capsys, "index", repo, "--max-lines", "2", "--max-files", "10")
    invoke(capsys, "refresh", repo)
    path = repo / ".gitcontext/snapshot.json"
    assert load_snapshot(path).manifest.config.max_lines == 2
    assert load_snapshot(path).manifest.config.discovery_limits.max_files == 10
    invoke(capsys, "refresh", repo, "--max-lines", "5")
    assert load_snapshot(path).manifest.config.max_lines == 5


def test_corrupt_saved_data_and_missing_chunk_fail_clearly(repo, capsys):
    invoke(capsys, "index", repo)
    assert invoke(capsys, "inspect", repo, "--chunk", "fabricated")[0] == 1
    (repo / ".gitcontext/snapshot.json").write_text("not JSON")
    assert invoke(capsys, "inspect", repo)[0] == 1


@pytest.mark.parametrize("command", ["inspect", "status", "refresh"])
def test_missing_saved_snapshot_is_an_error(repo, capsys, command):
    assert invoke(capsys, command, repo)[0] == 1


def test_symlink_storage_cannot_redirect_writes(repo, capsys, tmp_path):
    outside = repo / "other"
    outside.mkdir()
    (repo / ".gitcontext").symlink_to(outside, target_is_directory=True)
    assert invoke(capsys, "index", repo)[0] == 1
    assert not (outside / "snapshot.json").exists()


def test_failed_replace_through_cli_preserves_old(repo, capsys, monkeypatch):
    invoke(capsys, "index", repo)
    path = repo / ".gitcontext/snapshot.json"
    before = path.read_bytes()
    (repo / "app.py").write_text("pass")

    def fail(*args):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr("gitcontext.persistence.os.replace", fail)
    assert invoke(capsys, "refresh", repo)[0] == 1
    assert path.read_bytes() == before


def test_module_entrypoint_and_bad_arguments(repo):
    result = subprocess.run(
        [sys.executable, "-m", "gitcontext", "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0 and "refresh" in result.stdout
    invalid = subprocess.run(
        [sys.executable, "-m", "gitcontext", "index", str(repo), "--max-lines", "0"],
        capture_output=True,
        text=True,
    )
    assert invalid.returncode == 2
    assert not (repo / ".gitcontext").exists()
