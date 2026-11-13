"""Compare saved source scope with a bounded read, without refreshing it."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from gitcontext.discovery import (
    EXCLUDED_DIRECTORIES,
    SUPPORTED_SUFFIXES,
    DiscoveryIssue,
    DiscoveryLimits,
    discover_repository,
)
from gitcontext.reading import read_sources
from gitcontext.snapshots import Snapshot, SnapshotConfig


@dataclass(frozen=True)
class FreshnessReport:
    status: Literal["current", "stale", "unknown"]
    added: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    config_changes: tuple[str, ...] = ()
    issues: tuple[DiscoveryIssue, ...] = ()
    limitations: tuple[str, ...] = ()


def check_freshness(
    snapshot: Snapshot,
    root: Path,
    *,
    discovery_limits: DiscoveryLimits | None = None,
    max_total_bytes: int | None = None,
    max_lines: int | None = None,
) -> FreshnessReport:
    """Read/hash supported files using saved limits unless explicitly overridden.

    Partial old/new observations take precedence over stale: known differences
    remain in the report but freshness as a whole stays unknown. Removed means
    absent from supported scope, not necessarily physically deleted. This is a
    point-in-time check, not an atomic snapshot, and performs no writes or Git calls.
    """
    saved = snapshot.manifest.config
    limits = saved.discovery_limits if discovery_limits is None else discovery_limits
    budget = saved.max_total_bytes if max_total_bytes is None else max_total_bytes
    line_limit = saved.max_lines if max_lines is None else max_lines
    for name, value in (("max_total_bytes", budget), ("max_lines", line_limit)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    current = SnapshotConfig(
        discovery_limits=limits,
        max_total_bytes=budget,
        max_lines=line_limit,
        supported_suffixes=tuple(sorted(SUPPORTED_SUFFIXES)),
        excluded_directories=tuple(sorted(EXCLUDED_DIRECTORIES)),
    )
    previous_config = asdict(saved)
    changed_config = tuple(
        sorted(
            key
            for key, value in asdict(current).items()
            if previous_config[key] != value
        )
    )
    try:
        if Path(root).resolve(strict=True) != snapshot.root:
            return FreshnessReport(
                "unknown",
                config_changes=changed_config,
                limitations=("repository_root_mismatch",),
            )
        discovery = discover_repository(root, limits)
        reading = read_sources(discovery, max_total_bytes=budget)
    except (OSError, ValueError) as exc:
        return FreshnessReport(
            "unknown",
            config_changes=changed_config,
            issues=(DiscoveryIssue(".", "freshness_inspection_failed", str(exc)),),
            limitations=("inspection_failed",),
        )
    old_paths = set(snapshot.manifest.selected_paths)
    new_paths = {item.path for item in discovery.files}
    old_hashes = {file.path: file.content_sha256 for file in snapshot.manifest.files}
    new_hashes = {file.path: file.content_sha256 for file in reading.files}
    added = tuple(sorted(new_paths - old_paths))
    # An incomplete traversal cannot establish that a missing path was removed.
    removed = tuple(sorted(old_paths - new_paths)) if not discovery.partial else ()
    modified = tuple(
        sorted(
            path
            for path in old_hashes.keys() & new_hashes.keys()
            if old_hashes[path] != new_hashes[path]
        )
    )
    limitations = []
    if snapshot.manifest.partial:
        limitations.append("saved_snapshot_partial")
    if reading.partial:
        limitations.append("current_inspection_partial")
    if limitations:
        status = "unknown"
    elif added or removed or modified or changed_config:
        status = "stale"
    else:
        status = "current"
    return FreshnessReport(
        status,
        added,
        modified,
        removed,
        changed_config,
        reading.issues,
        tuple(limitations),
    )
