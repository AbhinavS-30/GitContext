"""A small, explicit Markdown heading policy, not a complete Markdown parser."""

import io
import re

from gitcontext.chunking import ChunkingReport, SourceChunk
from gitcontext.discovery import DiscoveryIssue
from gitcontext.reading import SourceFile

MARKDOWN_CHUNKING_VERSION = "markdown-atx-v1"
HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|[ \t]*)$")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def chunk_markdown(source: SourceFile, *, max_lines: int = 80) -> ChunkingReport:
    """Partition on ATX headings outside fences; retain every original line.

    Each heading starts a section ending before the next heading of any level.
    Preamble text gets its own range. No heading hierarchy is inferred. Underlined
    headings, HTML blocks, and list/blockquote containers are not parsed.
    """
    if type(max_lines) is not int or max_lines < 1:
        raise ValueError("max_lines must be a positive integer")
    lines = io.StringIO(source.text, newline="").readlines()
    sections: list[tuple[int, str | None]] = [(1, None)]
    fence_char: str | None = None
    fence_length = 0
    fence_start = 0

    for number, line in enumerate(lines, 1):
        text = line.rstrip("\r\n")
        fence = FENCE.fullmatch(text)
        if fence_char is not None:
            if (
                fence is not None
                and fence[1][0] == fence_char
                and len(fence[1]) >= fence_length
                and not fence[2].strip(" \t")
            ):
                fence_char = None
            continue
        if fence is not None:
            # Backtick fence info strings may not contain backticks.
            if fence[1][0] == "~" or "`" not in fence[2]:
                fence_char = fence[1][0]
                fence_length = len(fence[1])
                fence_start = number
                continue
        heading = HEADING.fullmatch(text)
        if heading is not None:
            title = (heading[2] or "").strip(" \t")
            title = re.sub(r"[ \t]+#+[ \t]*$", "", title)
            if title and not title.strip("#"):
                title = ""
            sections.append((number, title))

    chunks: list[SourceChunk] = []
    for index, (start, title) in enumerate(sections):
        end = sections[index + 1][0] - 1 if index + 1 < len(sections) else len(lines)
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
                    symbol_name=title,
                    symbol_type=(
                        "markdown_preamble" if title is None else "markdown_section"
                    ),
                    is_fragment=fragmented,
                )
            )
    issues = ()
    if fence_char is not None:
        issues = (
            DiscoveryIssue(
                source.path,
                "unclosed_fence",
                f"Fence opened at line {fence_start}; remaining lines kept as code",
            ),
        )
    return ChunkingReport(tuple(chunks), issues, MARKDOWN_CHUNKING_VERSION, max_lines)
