"""Validate, save, and load local snapshots without half-written publication."""

import hashlib
import io
import json
import os
import stat
import tempfile
from pathlib import Path, PurePosixPath

from pydantic import TypeAdapter

from gitcontext.chunking import PYTHON_CHUNKING_VERSION
from gitcontext.identities import CHUNK_ID_VERSION, chunk_id
from gitcontext.markdown import MARKDOWN_CHUNKING_VERSION
from gitcontext.snapshots import SNAPSHOT_VERSION, Snapshot, snapshot_id

MAX_SNAPSHOT_BYTES = 64_000_000
ADAPTER = TypeAdapter(Snapshot)


def _relative(path: str) -> None:
    value = PurePosixPath(path)
    if (
        not path
        or value.is_absolute()
        or ".." in value.parts
        or value.as_posix() != path
        or path == "."
    ):
        raise ValueError("Invalid repository-relative path")


def _validate(snapshot: Snapshot) -> None:
    manifest = snapshot.manifest
    config = manifest.config
    if manifest.schema_version != SNAPSHOT_VERSION:
        raise ValueError("Unsupported snapshot schema")
    if (config.python_policy, config.markdown_policy, config.chunk_id_version) != (
        PYTHON_CHUNKING_VERSION,
        MARKDOWN_CHUNKING_VERSION,
        CHUNK_ID_VERSION,
    ):
        raise ValueError("Unsupported chunk identity policy")
    if config.max_lines < 1 or config.max_total_bytes < 1:
        raise ValueError("Invalid resource limits")
    if not snapshot.root.is_absolute():
        raise ValueError("Snapshot root must be absolute")
    if snapshot.snapshot_id != snapshot_id(manifest):
        raise ValueError("Snapshot ID mismatch")
    selected = manifest.selected_paths
    if tuple(sorted(set(selected))) != selected:
        raise ValueError("Selected paths must be sorted and unique")
    for path in selected:
        _relative(path)
    paths = tuple(file.path for file in manifest.files)
    if tuple(sorted(set(paths))) != paths or not set(paths) <= set(selected):
        raise ValueError("Invalid processed-file inventory")
    if set(paths) != set(selected) and not manifest.partial:
        raise ValueError("Missing selected files require partial status")
    if len(selected) > config.discovery_limits.max_files:
        raise ValueError("File count exceeds configured limit")
    references = {item.chunk_id: item.source for item in snapshot.chunks}
    if len(references) != len(snapshot.chunks):
        raise ValueError("Duplicate chunk IDs")
    used: list[str] = []
    total = 0
    for file in manifest.files:
        try:
            chunks = [references[ref] for ref in file.chunk_ids]
        except KeyError as exc:
            raise ValueError("Missing chunk reference") from exc
        used.extend(file.chunk_ids)
        text = "".join(chunk.text for chunk in chunks)
        raw = text.encode("utf-8")
        if (
            len(raw) != file.size_bytes
            or hashlib.sha256(raw).hexdigest() != file.content_sha256
        ):
            raise ValueError("File content hash or size mismatch")
        if file.size_bytes > config.discovery_limits.max_file_bytes or "\0" in text:
            raise ValueError("File violates source-reading policy")
        total += len(raw)
        lines = io.StringIO(text, newline="").readlines()
        cursor = 1
        suffix = PurePosixPath(file.path).suffix.lower()
        if suffix not in (".py", ".md"):
            raise ValueError("Unsupported source file type")
        policy = config.python_policy if suffix == ".py" else config.markdown_policy
        for ref, chunk in zip(file.chunk_ids, chunks, strict=True):
            if chunk.path != file.path or chunk.content_sha256 != file.content_sha256:
                raise ValueError("Chunk/file metadata mismatch")
            if chunk.start_line != cursor or not cursor <= chunk.end_line <= len(lines):
                raise ValueError("Invalid chunk line coverage")
            if chunk.end_line - cursor + 1 > config.max_lines:
                raise ValueError("Chunk exceeds configured line limit")
            if chunk.text != "".join(lines[cursor - 1 : chunk.end_line]):
                raise ValueError("Chunk text/line mismatch")
            if ref != chunk_id(
                chunk, policy_version=policy, max_lines=config.max_lines
            ):
                raise ValueError("Chunk ID mismatch")
            cursor = chunk.end_line + 1
        if cursor != len(lines) + 1:
            raise ValueError("Incomplete source coverage")
    if len(used) != len(set(used)) or set(used) != set(references):
        raise ValueError("Duplicate or unreferenced chunks")
    if total > config.max_total_bytes:
        raise ValueError("Source exceeds total-byte budget")


def _decode(raw: bytes) -> Snapshot:
    try:
        original = json.loads(raw)
        snapshot = ADAPTER.validate_json(raw, strict=True)
        # Dataclass adapters ignore unknown fields; this exact-shape check rejects
        # unknown or omitted default fields rather than silently repairing input.
        if original != json.loads(ADAPTER.dump_json(snapshot)):
            raise ValueError("Unexpected or omitted snapshot fields")
        _validate(snapshot)
        return snapshot
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("Invalid saved snapshot") from exc


def load_snapshot(path: Path) -> Snapshot:
    """Load bounded regular-file JSON; never execute saved data or target code."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb", buffering=0) as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("Snapshot must be a regular file")
        raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Saved snapshot exceeds byte limit")
    return _decode(raw)


def save_snapshot(snapshot: Snapshot, path: Path) -> None:
    """Publish a validated sibling file with atomic replacement on POSIX.

    A pre-replacement failure leaves the old destination intact. The destination
    directory must exist and be trusted. Concurrent writers are last-writer-wins.
    """
    path = Path(path)
    raw = ADAPTER.dump_json(snapshot, warnings="error")
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Snapshot exceeds byte limit")
    _decode(raw)
    temporary = None
    try:
        fd, name = tempfile.mkstemp(prefix=".snapshot-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        load_snapshot(temporary)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
