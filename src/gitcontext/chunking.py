"""Partition Python source into exact, non-overlapping line ranges."""

import ast
import io
from dataclasses import dataclass
from typing import Literal

from gitcontext.discovery import DiscoveryIssue
from gitcontext.reading import SourceFile

PYTHON_CHUNKING_VERSION = "python-top-level-v1"
SymbolType = Literal["function", "async_function", "class", "module", "fallback"]


@dataclass(frozen=True)
class SourceChunk:
    path: str
    start_line: int
    end_line: int
    text: str
    content_sha256: str
    symbol_name: str | None
    symbol_type: SymbolType
    is_fragment: bool


@dataclass(frozen=True)
class ChunkingReport:
    chunks: tuple[SourceChunk, ...]
    issues: tuple[DiscoveryIssue, ...]
    policy_version: str
    max_lines: int


def chunk_python(source: SourceFile, *, max_lines: int = 80) -> ChunkingReport:
    """Keep top-level definitions together; preserve all remaining source too.

    Methods/nested definitions remain inside the enclosing top-level chunk.
    Definitions under control flow remain module source. Oversized ranges are
    split into non-overlapping fragments. Parse failures use line-based fallback.
    Lines are one-based and inclusive; text is never regenerated from the AST.
    """
    if type(max_lines) is not int or max_lines < 1:
        raise ValueError("max_lines must be a positive integer")
    # Universal newline recognition without altering original newline characters.
    # Unlike str.splitlines(), a form feed does not create a new Python line.
    lines = io.StringIO(source.text, newline="").readlines()
    chunks: list[SourceChunk] = []
    issues: list[DiscoveryIssue] = []

    def emit(start: int, end: int, name: str | None, kind: SymbolType) -> None:
        fragmented = end - start + 1 > max_lines
        for first in range(start, end + 1, max_lines):
            last = min(first + max_lines - 1, end)
            chunks.append(
                SourceChunk(
                    path=source.path,
                    start_line=first,
                    end_line=last,
                    text="".join(lines[first - 1 : last]),
                    content_sha256=source.content_sha256,
                    symbol_name=name,
                    symbol_type=kind,
                    is_fragment=fragmented,
                )
            )

    try:
        tree = ast.parse(source.text, filename=source.path)
    except (SyntaxError, ValueError, RecursionError) as exc:
        reason = "syntax_error" if isinstance(exc, SyntaxError) else "parse_error"
        issues.append(DiscoveryIssue(source.path, reason, str(exc)))
        emit(1, len(lines), None, "fallback")
    else:
        cursor = 1
        for node in tree.body:
            if not isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ):
                continue
            start = min([node.lineno, *(item.lineno for item in node.decorator_list)])
            end = node.end_lineno
            assert end is not None  # ast.parse supplies end positions for definitions.
            emit(cursor, start - 1, None, "module")
            if isinstance(node, ast.ClassDef):
                kind: SymbolType = "class"
            elif isinstance(node, ast.AsyncFunctionDef):
                kind = "async_function"
            else:
                kind = "function"
            emit(start, end, node.name, kind)
            cursor = end + 1
        emit(cursor, len(lines), None, "module")

    return ChunkingReport(
        tuple(chunks), tuple(issues), PYTHON_CHUNKING_VERSION, max_lines
    )
