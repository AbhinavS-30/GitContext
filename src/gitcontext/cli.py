"""A thin command-line boundary around snapshot operations."""

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

from gitcontext.discovery import DiscoveryLimits
from gitcontext.freshness import check_freshness
from gitcontext.persistence import load_snapshot, save_snapshot
from gitcontext.snapshots import Snapshot, build_snapshot


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and inspect local source snapshots."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("index", "inspect", "status", "refresh"):
        command = commands.add_parser(name)
        command.add_argument("path", type=Path, help="local repository directory")
        if name == "inspect":
            command.add_argument(
                "--chunk", help="show exact saved text for this chunk ID"
            )
        if name in ("index", "refresh"):
            for option in (
                "max_entries",
                "max_files",
                "max_file_bytes",
                "max_depth",
                "max_total_bytes",
                "max_lines",
            ):
                command.add_argument("--" + option.replace("_", "-"), type=_positive)
    return parser


def _summary(snapshot: Snapshot) -> dict:
    manifest = snapshot.manifest
    return {
        "snapshot_id": snapshot.snapshot_id,
        "selected_files": len(manifest.selected_paths),
        "read_files": len(manifest.files),
        "chunks": len(snapshot.chunks),
        "partial": manifest.partial,
        "degraded": manifest.degraded,
        "git": asdict(manifest.git),
        "issues": [asdict(issue) for issue in manifest.issues],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.path.is_symlink():
            raise ValueError("Repository root must not be a symlink")
        root = args.path.resolve(strict=True)
        if not root.is_dir():
            raise ValueError("Repository root must be a directory")
        storage = root / ".gitcontext"
        destination = storage / "snapshot.json"
        if storage.is_symlink() or destination.is_symlink():
            raise ValueError("Snapshot storage must not be a symlink")
        previous = None
        if args.command == "index":
            if destination.exists():
                raise ValueError("Snapshot already exists; use refresh explicitly")
        else:
            previous = load_snapshot(destination)
            if previous.root != root:
                raise ValueError(
                    "Saved snapshot belongs to a different repository root"
                )

        if args.command in ("index", "refresh"):
            baseline = previous.manifest.config if previous is not None else None
            limits = baseline.discovery_limits if baseline else DiscoveryLimits()
            overrides = {
                key: getattr(args, key)
                for key in asdict(limits)
                if getattr(args, key) is not None
            }
            limits = replace(limits, **overrides)
            budget = (
                args.max_total_bytes
                if args.max_total_bytes is not None
                else (baseline.max_total_bytes if baseline else 10_000_000)
            )
            line_limit = (
                args.max_lines
                if args.max_lines is not None
                else (baseline.max_lines if baseline else 80)
            )
            snapshot = build_snapshot(
                root,
                discovery_limits=limits,
                max_total_bytes=budget,
                max_lines=line_limit,
            )
            output = _summary(snapshot)
            if snapshot.manifest.partial:
                output["saved"] = False
                output["reason"] = (
                    "Partial rebuild refused; previous snapshot preserved"
                )
                print(json.dumps(output, indent=2, ensure_ascii=False))
                return 4
            storage.mkdir(mode=0o700, exist_ok=True)
            save_snapshot(snapshot, destination)
            output["saved"] = True
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return 0

        assert previous is not None
        if args.command == "status":
            freshness = check_freshness(previous, root)
            output = {
                "snapshot_id": previous.snapshot_id,
                "saved_partial": previous.manifest.partial,
                "saved_degraded": previous.manifest.degraded,
                **asdict(freshness),
            }
            print(json.dumps(output, indent=2, ensure_ascii=False))
            return {"current": 0, "stale": 3, "unknown": 4}[freshness.status]

        output = {
            **_summary(previous),
            "evidence_state": "saved_snapshot_not_freshness_checked",
            "config": asdict(previous.manifest.config),
            "files": [asdict(file) for file in previous.manifest.files],
        }
        if args.chunk is not None:
            found = next(
                (item for item in previous.chunks if item.chunk_id == args.chunk), None
            )
            if found is None:
                raise ValueError("Chunk ID is not in the saved snapshot")
            output["chunk"] = asdict(found)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
