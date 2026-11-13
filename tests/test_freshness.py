from dataclasses import replace

import pytest

from gitcontext.discovery import DiscoveryLimits
from gitcontext.freshness import check_freshness
from gitcontext.snapshots import build_snapshot


@pytest.fixture
def baseline(tmp_path):
    (tmp_path / "app.py").write_text("def answer():\n    return True\n")
    (tmp_path / "README.md").write_text("# Setup\nInstall\n")
    return build_snapshot(tmp_path), tmp_path


def test_unchanged_is_current_without_rebuilding_or_mutating(baseline, monkeypatch):
    snapshot, root = baseline

    def forbidden(*args, **kwargs):
        raise AssertionError("Freshness must not build snapshots or call Git")

    monkeypatch.setattr("gitcontext.snapshots.build_snapshot", forbidden)
    monkeypatch.setattr("gitcontext.git_metadata.inspect_git", forbidden)
    report = check_freshness(snapshot, root)
    assert report.status == "current"
    assert not report.added and not report.modified and not report.removed
    assert check_freshness(snapshot, root) == report


@pytest.mark.parametrize("change", ["add", "modify", "delete", "rename"])
def test_supported_source_changes_are_stale(baseline, change):
    snapshot, root = baseline
    if change == "add":
        (root / "new.py").write_text("pass")
    elif change == "modify":
        (root / "app.py").write_text("def answer():\n    return None\n")
    elif change == "delete":
        (root / "app.py").unlink()
    else:
        (root / "app.py").rename(root / "moved.py")
    report = check_freshness(snapshot, root)
    assert report.status == "stale"
    assert report.added == (
        {"add": ("new.py",), "rename": ("moved.py",)}.get(change, ())
    )
    assert report.modified == (("app.py",) if change == "modify" else ())
    assert report.removed == (("app.py",) if change in ("delete", "rename") else ())


def test_expected_exclusions_and_git_context_do_not_define_freshness(baseline):
    snapshot, root = baseline
    (root / "notes.txt").write_text("unsupported")
    (root / ".gitcontext").mkdir()
    (root / ".gitcontext/snapshot.json").write_text("generated")
    git = replace(snapshot.manifest.git, commit="a" * 40, dirty=True)
    snapshot = replace(snapshot, manifest=replace(snapshot.manifest, git=git))
    assert check_freshness(snapshot, root).status == "current"


def test_permission_failure_is_unknown_not_deleted(baseline, monkeypatch):
    snapshot, root = baseline
    from gitcontext import reading

    original = reading._open_source

    def denied(fd, path):
        if path == "app.py":
            raise PermissionError("denied")
        return original(fd, path)

    monkeypatch.setattr(reading, "_open_source", denied)
    report = check_freshness(snapshot, root)
    assert report.status == "unknown"
    assert not report.removed
    assert any(issue.reason == "read_error" for issue in report.issues)


def test_known_changes_remain_visible_when_another_file_is_unreadable(baseline):
    snapshot, root = baseline
    (root / "app.py").write_text("def answer():\n    return None\n")
    (root / "README.md").write_bytes(b"\xff")
    report = check_freshness(snapshot, root)
    assert report.status == "unknown"
    assert report.modified == ("app.py",)
    assert "current_inspection_partial" in report.limitations


@pytest.mark.parametrize(
    "override",
    [
        {"max_lines": 100},
        {"max_total_bytes": 20_000_000},
        {"discovery_limits": DiscoveryLimits(max_files=500)},
    ],
)
def test_config_changes_are_stale(baseline, override):
    snapshot, root = baseline
    report = check_freshness(snapshot, root, **override)
    assert report.status == "stale"
    assert tuple(override) == report.config_changes


def test_policy_change_is_stale(baseline):
    snapshot, root = baseline
    config = replace(snapshot.manifest.config, reading_policy="older-reading-policy")
    snapshot = replace(snapshot, manifest=replace(snapshot.manifest, config=config))
    assert "reading_policy" in check_freshness(snapshot, root).config_changes


def test_saved_partial_cannot_become_current_just_because_error_disappeared(tmp_path):
    (tmp_path / "bad.py").write_bytes(b"\xff")
    snapshot = build_snapshot(tmp_path)
    (tmp_path / "bad.py").write_text("pass")
    report = check_freshness(snapshot, tmp_path)
    assert report.status == "unknown"
    assert "saved_snapshot_partial" in report.limitations


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_total_bytes": 1},
        {"discovery_limits": DiscoveryLimits(max_entries=1)},
        {"discovery_limits": DiscoveryLimits(max_file_bytes=1)},
    ],
)
def test_limit_failures_are_unknown_and_do_not_invent_deletions(baseline, kwargs):
    snapshot, root = baseline
    report = check_freshness(snapshot, root, **kwargs)
    assert report.status == "unknown"
    assert not report.removed


def test_syntax_fallback_can_be_current_while_still_degraded(tmp_path):
    (tmp_path / "broken.py").write_text("def broken(:\n")
    snapshot = build_snapshot(tmp_path)
    assert snapshot.manifest.degraded
    assert check_freshness(snapshot, tmp_path).status == "current"
    assert snapshot.manifest.degraded


def test_missing_or_different_root_is_unknown(baseline, tmp_path):
    snapshot, root = baseline
    other = root / "other"
    other.mkdir()
    assert check_freshness(snapshot, other).limitations == ("repository_root_mismatch",)
    assert check_freshness(snapshot, root / "missing").status == "unknown"


def test_file_replaced_with_symlink_is_removed_from_supported_scope(baseline):
    snapshot, root = baseline
    (root / "app.py").unlink()
    (root / "app.py").symlink_to(root / "README.md")
    report = check_freshness(snapshot, root)
    assert report.status == "stale"
    assert report.removed == ("app.py",)


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_config_is_caller_error(baseline, value):
    snapshot, root = baseline
    with pytest.raises(ValueError):
        check_freshness(snapshot, root, max_lines=value)
