from pathlib import Path

import pytest

from gitcontext.discovery import DiscoveryLimits, discover_repository


def write(root: Path, path: str, text: str = "pass\n") -> Path:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


def test_selects_source_without_executing_and_reports_exclusions(tmp_path):
    write(tmp_path, "app.py", 'raise RuntimeError("must not execute")\n')
    write(tmp_path, "README.md")
    write(tmp_path, ".venv/dependency.py")
    write(tmp_path, ".git/internal.py")
    write(tmp_path, "models/weights.py")
    write(tmp_path, ".env.md")
    write(tmp_path, "secrets.py")
    write(tmp_path, "data.sqlite")
    report = discover_repository(tmp_path)
    assert [item.path for item in report.files] == ["README.md", "app.py"]
    assert not report.partial
    reasons = {item.path: item.reason for item in report.issues}
    assert reasons[".venv"] == "excluded_directory"
    assert reasons[".env.md"] == "excluded_filename"
    assert reasons["secrets.py"] == "excluded_filename"
    assert reasons["data.sqlite"] == "unsupported_extension"
    assert report.entries_examined == 8


def test_skips_file_directory_and_broken_symlinks(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = write(tmp_path, "outside/private.py")
    (repo / "link.py").symlink_to(outside)
    (repo / "folder").symlink_to(outside.parent, target_is_directory=True)
    (repo / "broken.py").symlink_to(tmp_path / "missing")
    report = discover_repository(repo)
    assert not report.files
    assert len(report.issues) == 3
    assert {item.reason for item in report.issues} == {"symlink"}
    assert not report.partial


@pytest.mark.parametrize("limit", ["max_entries", "max_files"])
def test_scan_limits_report_partial(tmp_path, limit):
    for index in range(3):
        write(tmp_path, f"file{index}.py")
    report = discover_repository(tmp_path, DiscoveryLimits(**{limit: 1}))
    assert report.partial
    assert len(report.files) <= 1
    assert any(
        item.reason == {"max_entries": "entry_limit", "max_files": "file_limit"}[limit]
        for item in report.issues
    )


def test_size_and_depth_limits(tmp_path):
    write(tmp_path, "large.py", "x" * 11)
    write(tmp_path, "nested/deeper/hidden.py")
    report = discover_repository(
        tmp_path, DiscoveryLimits(max_file_bytes=10, max_depth=1)
    )
    assert not report.files
    assert report.partial
    assert {item.reason for item in report.issues} == {"file_size_limit", "depth_limit"}


def test_exact_limits_do_not_falsely_report_partial(tmp_path):
    write(tmp_path, "app.py", "pass")
    report = discover_repository(
        tmp_path, DiscoveryLimits(max_entries=1, max_files=1, max_file_bytes=4)
    )
    assert len(report.files) == 1
    assert not report.partial


def test_directory_access_error_is_visible(tmp_path, monkeypatch):
    def denied(_path):
        raise PermissionError("access denied")

    monkeypatch.setattr("gitcontext.discovery.os.scandir", denied)
    report = discover_repository(tmp_path)
    assert report.partial
    assert report.issues[0].reason == "directory_error"
    assert "access denied" in report.issues[0].detail


def test_invalid_roots(tmp_path):
    with pytest.raises(FileNotFoundError):
        discover_repository(tmp_path / "missing")
    file = write(tmp_path, "app.py")
    with pytest.raises(ValueError, match="directory"):
        discover_repository(file)
    link = tmp_path / "linked"
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        discover_repository(link)


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_limits(value):
    with pytest.raises(ValueError, match="positive integer"):
        DiscoveryLimits(max_entries=value)
