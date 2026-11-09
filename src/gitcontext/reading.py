"""Read discovered source with bounded bytes and explicit failures (POSIX)."""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from gitcontext.discovery import DiscoveryIssue, DiscoveryReport


@dataclass(frozen=True)
class SourceFile:
    path: str
    text: str
    size_bytes: int
    content_sha256: str


@dataclass(frozen=True)
class ReadingReport:
    files: tuple[SourceFile, ...]
    issues: tuple[DiscoveryIssue, ...]
    bytes_read: int
    partial: bool


def _open_source(root_fd: int, relative: str) -> int:
    """Open each component relative to a pinned directory, refusing symlinks."""
    path = Path(relative)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Expected a repository-relative path without '..'")
    directory_fd = os.dup(root_fd)
    try:
        for part in path.parts[:-1]:
            next_fd = os.open(
                part,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            os.close(directory_fd)
            directory_fd = next_fd
        return os.open(
            path.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
    finally:
        os.close(directory_fd)


def read_sources(
    discovery: DiscoveryReport, *, max_total_bytes: int = 10_000_000
) -> ReadingReport:
    """Read UTF-8 source, preserving newlines; reject NULs and invalid UTF-8.

    The total budget includes failed decoding and oversized reads. At most one
    extra byte is read to detect total-budget overflow, then reading stops.
    Discovery issues and partial status are preserved. No source is executed.
    """
    if type(max_total_bytes) is not int or max_total_bytes < 1:
        raise ValueError("max_total_bytes must be a positive integer")
    files: list[SourceFile] = []
    issues = list(discovery.issues)
    consumed = 0
    partial = discovery.partial
    try:
        root_fd = os.open(discovery.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        return ReadingReport(
            (), (*issues, DiscoveryIssue(".", "root_read_error", str(exc))), 0, True
        )

    try:
        for selected in discovery.files:
            remaining = max_total_bytes - consumed
            if remaining <= 0:
                issues.append(DiscoveryIssue(selected.path, "total_byte_limit"))
                partial = True
                break
            try:
                fd = _open_source(root_fd, selected.path)
                # Unbuffered I/O avoids reading ahead beyond the byte budget.
                with os.fdopen(fd, "rb", buffering=0) as stream:
                    before = os.fstat(stream.fileno())
                    if not stat.S_ISREG(before.st_mode):
                        issues.append(DiscoveryIssue(selected.path, "non_regular_file"))
                        partial = True
                        continue
                    cap = min(discovery.limits.max_file_bytes, remaining)
                    raw = stream.read(cap + 1)
                    consumed += len(raw)
                    after = os.fstat(stream.fileno())
                if len(raw) > remaining:
                    issues.append(DiscoveryIssue(selected.path, "total_byte_limit"))
                    partial = True
                    break
                if len(raw) > discovery.limits.max_file_bytes:
                    issues.append(DiscoveryIssue(selected.path, "file_size_limit"))
                    partial = True
                    continue
                if after.st_size != len(raw) or (
                    before.st_size,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                ) != (
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                ):
                    issues.append(DiscoveryIssue(selected.path, "changed_during_read"))
                    partial = True
                    continue
                if b"\x00" in raw:
                    issues.append(DiscoveryIssue(selected.path, "nul_content"))
                    partial = True
                    continue
                text = raw.decode("utf-8")
                files.append(
                    SourceFile(
                        path=selected.path,
                        text=text,
                        size_bytes=len(raw),
                        content_sha256=hashlib.sha256(raw).hexdigest(),
                    )
                )
            except UnicodeDecodeError as exc:
                issues.append(DiscoveryIssue(selected.path, "invalid_utf8", str(exc)))
                partial = True
            except (OSError, ValueError) as exc:
                issues.append(DiscoveryIssue(selected.path, "read_error", str(exc)))
                partial = True
    finally:
        os.close(root_fd)
    return ReadingReport(tuple(files), tuple(issues), consumed, partial)
