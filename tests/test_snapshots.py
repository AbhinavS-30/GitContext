from dataclasses import asdict

import pytest

from gitcontext.discovery import DiscoveryLimits
from gitcontext.snapshots import build_snapshot


def write(root, path, text):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text)


def test_build_connects_inventory_to_exact_source_and_chunk_references(tmp_path):
    write(tmp_path, "app.py", "@guard\ndef save():\n    return True\n")
    write(tmp_path, "README.md", "# Setup\nInstall it\n")
    write(tmp_path, "empty.py", "")
    snapshot = build_snapshot(tmp_path)
    assert not snapshot.manifest.partial
    assert not snapshot.manifest.degraded
    assert snapshot.manifest.selected_paths == ("README.md", "app.py", "empty.py")
    assert len(snapshot.manifest.files) == 3
    references = {item.chunk_id: item.source for item in snapshot.chunks}
    for file in snapshot.manifest.files:
        text = "".join(references[ref].text for ref in file.chunk_ids)
        assert text == (tmp_path / file.path).read_text()
        assert all(
            references[ref].content_sha256 == file.content_sha256
            for ref in file.chunk_ids
        )
    assert snapshot.manifest.files[-1].chunk_ids == ()
    assert snapshot.manifest.config.max_lines == 80
    assert asdict(snapshot.manifest)["schema_version"] == "snapshot-v2"


def test_repeatable_across_roots_and_creation_order(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    for root, paths in ((first, ["a.py", "b.py"]), (second, ["b.py", "a.py"])):
        for path in paths:
            write(root, path, "pass\n")
    a = build_snapshot(first)
    assert a.snapshot_id == build_snapshot(first).snapshot_id
    assert a.snapshot_id == build_snapshot(second).snapshot_id
    assert a.root != build_snapshot(second).root


@pytest.mark.parametrize("change", ["edit", "add", "delete", "rename"])
def test_inventory_changes_change_identity_without_git(tmp_path, change):
    write(tmp_path, "app.py", "return True")
    original = build_snapshot(tmp_path)
    if change == "edit":
        write(tmp_path, "app.py", "return None")
    elif change == "add":
        write(tmp_path, "new.md", "# New")
    elif change == "delete":
        (tmp_path / "app.py").unlink()
    else:
        (tmp_path / "app.py").rename(tmp_path / "moved.py")
    assert original.snapshot_id != build_snapshot(tmp_path).snapshot_id


def test_configuration_changes_identity_even_for_empty_repo(tmp_path):
    original = build_snapshot(tmp_path)
    assert original.snapshot_id != build_snapshot(tmp_path, max_lines=100).snapshot_id
    assert (
        original.snapshot_id != build_snapshot(tmp_path, max_total_bytes=5).snapshot_id
    )
    assert (
        original.snapshot_id
        != build_snapshot(
            tmp_path, discovery_limits=DiscoveryLimits(max_files=5)
        ).snapshot_id
    )


def test_partial_inventory_preserves_selected_but_unreadable_files(tmp_path):
    write(tmp_path, "good.py", "pass")
    (tmp_path / "bad.py").write_bytes(b"\xff")
    report = build_snapshot(tmp_path)
    assert report.manifest.partial
    assert not report.manifest.degraded
    assert report.manifest.selected_paths == ("bad.py", "good.py")
    assert [file.path for file in report.manifest.files] == ["good.py"]
    assert report.manifest.issues[0].reason == "invalid_utf8"


def test_degraded_fallback_is_distinct_from_missing_source(tmp_path):
    write(tmp_path, "bad.py", "def broken(:\n")
    write(tmp_path, "README.md", "# Example\n```python\n# code\n")
    report = build_snapshot(tmp_path)
    assert report.manifest.degraded
    assert not report.manifest.partial
    assert {issue.reason for issue in report.manifest.issues} == {
        "syntax_error",
        "unclosed_fence",
    }
    assert len(report.manifest.files) == 2


def test_discovery_and_total_byte_limits_stay_visible(tmp_path):
    write(tmp_path, "a.py", "pass")
    write(tmp_path, "b.py", "pass")
    limited = build_snapshot(tmp_path, discovery_limits=DiscoveryLimits(max_files=1))
    assert limited.manifest.partial
    assert any(issue.reason == "file_limit" for issue in limited.manifest.issues)
    budget = build_snapshot(tmp_path, max_total_bytes=2)
    assert budget.manifest.partial
    assert not budget.manifest.files
    assert budget.manifest.issues[0].reason == "total_byte_limit"


@pytest.mark.parametrize("name", ["max_lines", "max_total_bytes"])
@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_config_is_rejected_even_for_empty_repo(tmp_path, name, value):
    with pytest.raises(ValueError):
        build_snapshot(tmp_path, **{name: value})
