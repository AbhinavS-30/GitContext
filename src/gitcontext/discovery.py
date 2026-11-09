"""Bounded discovery of source paths; never import or read target source."""

import os
import stat
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = frozenset({".py", ".md"})
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        "vendor",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        ".nox",
        "build",
        "dist",
        "site-packages",
        "htmlcov",
        ".gitcontext",
        "models",
        ".aws",
        ".ssh",
    }
)


@dataclass(frozen=True)
class DiscoveryLimits:
    """Defaults for small repositories; root entries have depth zero."""

    max_entries: int = 10_000
    max_files: int = 1_000
    max_file_bytes: int = 1_000_000
    max_depth: int = 20

    def __post_init__(self) -> None:
        for name in ("max_entries", "max_files", "max_file_bytes", "max_depth"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class DiscoveredFile:
    path: str
    size_bytes: int


@dataclass(frozen=True)
class DiscoveryIssue:
    path: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class DiscoveryReport:
    root: Path
    files: tuple[DiscoveredFile, ...]
    issues: tuple[DiscoveryIssue, ...]
    entries_examined: int
    partial: bool
    limits: DiscoveryLimits


def discover_repository(
    root: Path, limits: DiscoveryLimits | None = None
) -> DiscoveryReport:
    """Discover paths under an explicit directory, without following symlinks.

    Invalid roots raise ValueError/OSError. Child inspection failures are reported
    as partial results. Excluded directories are reported once, not traversed.
    Traversal order follows the filesystem; returned records are sorted by path.
    A limited scan may therefore select different subsets on different systems.
    """
    limits = limits or DiscoveryLimits()
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Repository root must not be a symlink")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Repository root must be a directory")

    files: list[DiscoveredFile] = []
    issues: list[DiscoveryIssue] = []
    examined = 0
    partial = False
    stopped = False

    def issue(path: str, reason: str, detail: str = "", *, incomplete=False):
        nonlocal partial
        issues.append(DiscoveryIssue(path, reason, detail))
        partial = partial or incomplete

    def visit(directory: Path, depth: int) -> None:
        nonlocal examined, stopped
        relative_directory = directory.relative_to(root).as_posix()
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if examined >= limits.max_entries:
                        issue(relative_directory, "entry_limit", incomplete=True)
                        stopped = True
                        return
                    examined += 1
                    path = Path(entry.path)
                    relative = path.relative_to(root).as_posix()
                    try:
                        metadata = entry.stat(follow_symlinks=False)
                        if stat.S_ISLNK(metadata.st_mode):
                            issue(relative, "symlink")
                            continue
                        # Check containment even though symlinks are excluded.
                        if not path.resolve(strict=True).is_relative_to(root):
                            issue(relative, "outside_root", incomplete=True)
                            continue
                        name = entry.name.lower()
                        if stat.S_ISDIR(metadata.st_mode):
                            if name in EXCLUDED_DIRECTORIES or name.endswith(
                                ".egg-info"
                            ):
                                issue(relative, "excluded_directory")
                            elif depth >= limits.max_depth:
                                issue(relative, "depth_limit", incomplete=True)
                            else:
                                visit(path, depth + 1)
                                if stopped:
                                    return
                        elif not stat.S_ISREG(metadata.st_mode):
                            issue(relative, "non_regular_file")
                        elif (
                            name == ".env"
                            or name.startswith(".env.")
                            or name.startswith(("credentials.", "secrets."))
                        ):
                            issue(relative, "excluded_filename")
                        elif path.suffix.lower() not in SUPPORTED_SUFFIXES:
                            issue(relative, "unsupported_extension")
                        elif metadata.st_size > limits.max_file_bytes:
                            issue(relative, "file_size_limit", incomplete=True)
                        elif len(files) >= limits.max_files:
                            issue(relative, "file_limit", incomplete=True)
                            stopped = True
                            return
                        else:
                            files.append(DiscoveredFile(relative, metadata.st_size))
                    except OSError as exc:
                        issue(relative, "inspection_error", str(exc), incomplete=True)
        except OSError as exc:
            issue(relative_directory, "directory_error", str(exc), incomplete=True)

    visit(root, 0)
    return DiscoveryReport(
        root=root,
        files=tuple(sorted(files, key=lambda item: item.path)),
        issues=tuple(sorted(issues, key=lambda item: (item.path, item.reason))),
        entries_examined=examined,
        partial=partial,
        limits=limits,
    )
