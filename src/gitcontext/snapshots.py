"""Build an in-memory inventory; no target execution or persistence."""

import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from gitcontext.chunking import PYTHON_CHUNKING_VERSION, SourceChunk, chunk_python
from gitcontext.discovery import (
    EXCLUDED_DIRECTORIES,
    SUPPORTED_SUFFIXES,
    DiscoveryIssue,
    DiscoveryLimits,
    discover_repository,
)
from gitcontext.identities import CHUNK_ID_VERSION, chunk_id
from gitcontext.markdown import MARKDOWN_CHUNKING_VERSION, chunk_markdown
from gitcontext.reading import read_sources

SNAPSHOT_VERSION = "snapshot-v1"


@dataclass(frozen=True)
class SnapshotConfig:
    discovery_limits: DiscoveryLimits
    max_total_bytes: int
    max_lines: int
    supported_suffixes: tuple[str, ...]
    excluded_directories: tuple[str, ...]
    discovery_policy: str = "allowlist-no-symlinks-v1"
    reading_policy: str = "posix-utf8-strict-nul-reject-v1"
    python_policy: str = PYTHON_CHUNKING_VERSION
    markdown_policy: str = MARKDOWN_CHUNKING_VERSION
    chunk_id_version: str = CHUNK_ID_VERSION
    parser_runtime: str = sys.version.split()[0]


@dataclass(frozen=True)
class FileManifest:
    path: str
    size_bytes: int
    content_sha256: str
    chunk_ids: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotManifest:
    schema_version: str
    config: SnapshotConfig
    selected_paths: tuple[str, ...]
    files: tuple[FileManifest, ...]
    issues: tuple[DiscoveryIssue, ...]
    partial: bool
    degraded: bool


@dataclass(frozen=True)
class IdentifiedChunk:
    chunk_id: str
    source: SourceChunk


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    root: Path
    manifest: SnapshotManifest
    chunks: tuple[IdentifiedChunk, ...]


def build_snapshot(
    root: Path,
    *,
    discovery_limits: DiscoveryLimits | None = None,
    max_total_bytes: int = 10_000_000,
    max_lines: int = 80,
) -> Snapshot:
    """Compose discovery, reading, chunking, and identities for one repository.

    IDs exclude root paths and diagnostic wording. Partial means source was missed;
    degraded means chunking emitted issues (e.g. syntax fallback/unclosed fences).
    Neither flag is an atomicity guarantee or a retrieval-quality measurement.
    """
    for name, value in (("max_total_bytes", max_total_bytes), ("max_lines", max_lines)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    discovered = discover_repository(root, discovery_limits)
    reading = read_sources(discovered, max_total_bytes=max_total_bytes)
    config = SnapshotConfig(
        discovery_limits=discovered.limits,
        max_total_bytes=max_total_bytes,
        max_lines=max_lines,
        supported_suffixes=tuple(sorted(SUPPORTED_SUFFIXES)),
        excluded_directories=tuple(sorted(EXCLUDED_DIRECTORIES)),
    )
    files: list[FileManifest] = []
    chunks: list[IdentifiedChunk] = []
    issues = list(reading.issues)
    degraded = False
    for source in sorted(reading.files, key=lambda item: item.path):
        chunker = (
            chunk_python
            if Path(source.path).suffix.lower() == ".py"
            else chunk_markdown
        )
        report = chunker(source, max_lines=max_lines)
        issues.extend(report.issues)
        degraded = degraded or bool(report.issues)
        references = []
        for chunk in report.chunks:
            reference = chunk_id(
                chunk, policy_version=report.policy_version, max_lines=report.max_lines
            )
            references.append(reference)
            chunks.append(IdentifiedChunk(reference, chunk))
        files.append(
            FileManifest(
                source.path, source.size_bytes, source.content_sha256, tuple(references)
            )
        )
    manifest = SnapshotManifest(
        schema_version=SNAPSHOT_VERSION,
        config=config,
        selected_paths=tuple(sorted(item.path for item in discovered.files)),
        files=tuple(files),
        issues=tuple(
            sorted(issues, key=lambda item: (item.path, item.reason, item.detail))
        ),
        partial=reading.partial,
        degraded=degraded,
    )
    payload = asdict(manifest)
    # Diagnostics can contain machine-specific paths or OS wording; retain them in
    # the manifest but identify issue paths/reasons only, independent of wording.
    payload["issues"] = sorted(
        [{"path": issue.path, "reason": issue.reason} for issue in manifest.issues],
        key=lambda item: (item["path"], item["reason"]),
    )
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    reference = f"{SNAPSHOT_VERSION}:{hashlib.sha256(encoded).hexdigest()}"
    return Snapshot(reference, discovered.root, manifest, tuple(chunks))
