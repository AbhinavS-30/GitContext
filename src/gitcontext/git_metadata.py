"""Bounded, read-only Git observations; never execute repository helpers."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class GitMetadata:
    status: Literal["available", "not_repository", "unavailable"]
    commit: str | None
    dirty: bool | None
    issue: str | None = None


def _run_git(executable: str, root: Path, *arguments: str) -> tuple[int, bytes]:
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
        }
    )
    command = [
        executable,
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-C",
        str(root),
        *arguments,
    ]
    # Spool stdout rather than capture unbounded status output into memory.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run(
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        output.seek(0)
        data = output.read(65_537)
    if len(data) > 65_536:
        raise ValueError("git_output_limit")
    return result.returncode, data


def inspect_git(root: Path) -> GitMetadata:
    """Observe an exact working-tree root, including staged/untracked changes.

    No ancestor-repository attribution; no remote access. Ignored files and
    unstaged changes inside submodule worktrees are outside the dirty policy.
    An unavailable HEAD is recorded explicitly (including repositories with no
    commits). This observation does not bind the read source to a Git commit.
    """
    executable = shutil.which("git")
    if executable is None:
        return GitMetadata("unavailable", None, None, "git_not_installed")
    try:
        root = Path(root).resolve(strict=True)
        code, output = _run_git(executable, root, "rev-parse", "--show-toplevel")
        if code:
            status = "unavailable" if (root / ".git").exists() else "not_repository"
            return GitMetadata(status, None, None, "repository_unresolved")
        if Path(os.fsdecode(output).rstrip("\r\n")).resolve() != root:
            return GitMetadata("not_repository", None, None, "root_is_subdirectory")
        code, output = _run_git(
            executable, root, "rev-parse", "--verify", "--quiet", "HEAD^{commit}"
        )
        commit = output.decode("ascii").strip() if code == 0 else None
        if commit is not None and (
            len(commit) not in (40, 64)
            or any(c not in "0123456789abcdef" for c in commit)
        ):
            return GitMetadata("unavailable", None, None, "invalid_commit_output")
        code, output = _run_git(
            executable,
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=normal",
            "--ignore-submodules=all",
        )
        if code:
            return GitMetadata("unavailable", commit, None, "status_failed")
        return GitMetadata(
            "available", commit, bool(output), None if commit else "head_unavailable"
        )
    except subprocess.TimeoutExpired:
        return GitMetadata("unavailable", None, None, "git_timeout")
    except (OSError, ValueError) as exc:
        issue = (
            "git_output_limit"
            if str(exc) == "git_output_limit"
            else "git_inspection_failed"
        )
        return GitMetadata("unavailable", None, None, issue)
