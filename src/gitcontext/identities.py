"""Deterministic references to chunks within an indexed repository scope."""

import hashlib
import json
from dataclasses import asdict

from gitcontext.chunking import SourceChunk

CHUNK_ID_VERSION = "chunk-v1"


def chunk_id(chunk: SourceChunk, *, policy_version: str, max_lines: int) -> str:
    """Identify exact chunk data and the configuration that produced it.

    This does not validate the chunk against a file, identify a repository, or
    establish freshness. Callers must obtain configuration from its chunking report.
    """
    if not isinstance(policy_version, str) or not policy_version.strip():
        raise ValueError("policy_version must be a nonempty string")
    if type(max_lines) is not int or max_lines < 1:
        raise ValueError("max_lines must be a positive integer")
    payload = {
        "id_version": CHUNK_ID_VERSION,
        "chunk": asdict(chunk),
        "policy_version": policy_version,
        "max_lines": max_lines,
    }
    # Canonical serialization: field order and whitespace cannot vary by caller.
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return f"{CHUNK_ID_VERSION}:{hashlib.sha256(encoded).hexdigest()}"
