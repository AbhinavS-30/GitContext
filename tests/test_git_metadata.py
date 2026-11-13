import os
import subprocess

import pytest

from gitcontext.git_metadata import inspect_git
from gitcontext.snapshots import build_snapshot


def git(root, *arguments):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    (tmp_path / "app.py").write_text("pass\n")
    git(tmp_path, "add", "app.py")
    git(
        tmp_path,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Fixture",
    )
    return tmp_path


def test_clean_metadata_and_snapshot_integration(repository):
    before_index = (repository / ".git/index").read_bytes()
    metadata = inspect_git(repository)
    assert metadata.status == "available"
    assert metadata.commit == git(repository, "rev-parse", "HEAD")
    assert metadata.dirty is False
    assert metadata.issue is None
    assert build_snapshot(repository).manifest.git == metadata
    assert (repository / ".git/index").read_bytes() == before_index


@pytest.mark.parametrize("change", ["modified", "staged", "untracked", "deleted"])
def test_dirty_changes_preserve_commit(repository, change):
    commit = git(repository, "rev-parse", "HEAD")
    if change == "untracked":
        (repository / "new.md").write_text("new")
    elif change == "deleted":
        (repository / "app.py").unlink()
    else:
        (repository / "app.py").write_text("x = 1\n")
        if change == "staged":
            git(repository, "add", "app.py")
    metadata = inspect_git(repository)
    assert metadata.commit == commit
    assert metadata.dirty is True


def test_ignored_files_do_not_make_dirty(repository):
    (repository / ".git/info/exclude").write_text("ignored.py\n")
    (repository / "ignored.py").write_text("pass")
    assert inspect_git(repository).dirty is False


def test_non_git_folder_and_ancestor_repository_are_not_attributed(tmp_path):
    metadata = inspect_git(tmp_path)
    assert metadata.status == "not_repository"
    assert metadata.dirty is None
    git(tmp_path, "init", "-b", "main")
    child = tmp_path / "child"
    child.mkdir()
    metadata = inspect_git(child)
    assert metadata.status == "not_repository"
    assert metadata.issue == "root_is_subdirectory"


def test_unborn_repository_has_no_invented_commit(tmp_path):
    git(tmp_path, "init", "-b", "main")
    metadata = inspect_git(tmp_path)
    assert metadata.status == "available"
    assert metadata.commit is None
    assert metadata.issue == "head_unavailable"
    assert metadata.dirty is False


def test_inherited_git_directory_does_not_redirect_inspection(
    repository, tmp_path, monkeypatch
):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("GIT_DIR", str(repository / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(repository))
    assert inspect_git(other).status == "not_repository"


def test_fsmonitor_helper_is_not_executed(repository):
    helper = repository / ".git/helper.sh"
    helper.write_text('#!/bin/sh\nprintf invoked > "$(dirname "$0")/invoked"\n')
    helper.chmod(0o755)
    git(repository, "config", "core.fsmonitor", str(helper))
    assert inspect_git(repository).dirty is False
    assert not (repository / ".git/invoked").exists()


def test_git_missing_is_explicit(repository, monkeypatch):
    monkeypatch.setattr("gitcontext.git_metadata.shutil.which", lambda _: None)
    metadata = inspect_git(repository)
    assert metadata.status == "unavailable"
    assert metadata.dirty is None
    assert metadata.issue == "git_not_installed"


def test_timeout_is_not_clean(repository, monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 5)

    monkeypatch.setattr("gitcontext.git_metadata.subprocess.run", timeout)
    metadata = inspect_git(repository)
    assert metadata.dirty is None
    assert metadata.issue == "git_timeout"


def test_output_limit_is_explicit(repository, monkeypatch):
    def excessive(*args, **kwargs):
        kwargs["stdout"].write(b"x" * 65_537)
        return subprocess.CompletedProcess([], 0)

    monkeypatch.setattr("gitcontext.git_metadata.subprocess.run", excessive)
    metadata = inspect_git(repository)
    assert metadata.dirty is None
    assert metadata.issue == "git_output_limit"


def test_status_failure_preserves_commit_but_not_clean_claim(repository, monkeypatch):
    commit = "a" * 40
    results = iter(
        [(0, os.fsencode(str(repository)) + b"\n"), (0, commit.encode()), (1, b"")]
    )
    monkeypatch.setattr("gitcontext.git_metadata._run_git", lambda *args: next(results))
    metadata = inspect_git(repository)
    assert metadata.commit == commit
    assert metadata.status == "unavailable"
    assert metadata.dirty is None
    assert metadata.issue == "status_failed"


def test_same_source_new_git_context_changes_snapshot_identity(repository):
    before = build_snapshot(repository)
    git(
        repository,
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--allow-empty",
        "-m",
        "Fixture context change",
    )
    after = build_snapshot(repository)
    assert before.manifest.files == after.manifest.files
    assert before.manifest.git.commit != after.manifest.git.commit
    assert before.snapshot_id != after.snapshot_id
