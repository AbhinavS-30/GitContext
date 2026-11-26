"""Transparent lexical ranking of already prepared source chunks."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from gitcontext.chunking import SourceChunk
from gitcontext.snapshots import IdentifiedChunk
from gitcontext.tokenization import TOKENIZATION_VERSION, tokenize

LEXICAL_RANKING_VERSION = "distinct-term-overlap-v1"
MAX_QUERY_CHARACTERS = 2_000
MAX_TOP_K = 100


@dataclass(frozen=True)
class LexicalMatch:
    chunk_id: str
    score: int | float
    matched_terms: tuple[str, ...]
    source: SourceChunk


@dataclass(frozen=True)
class LexicalReport:
    query_terms: tuple[str, ...]
    matches: tuple[LexicalMatch, ...]
    ranking_version: str = LEXICAL_RANKING_VERSION
    tokenization_version: str = TOKENIZATION_VERSION
    evidence_state: Literal["saved_snapshot_not_freshness_checked"] = (
        "saved_snapshot_not_freshness_checked"
    )


def rank_chunks(
    chunks: Sequence[IdentifiedChunk], query: str, *, top_k: int = 5
) -> LexicalReport:
    """Count unique normalized query terms occurring in each chunk's text.

    No frequency/length weighting, synonyms, probability estimates, or external
    inference. Input chunks should come from a built/validated snapshot. This pure
    function performs no I/O and does not establish freshness; callers must do so
    before presenting source references as current.
    """
    if type(top_k) is not int or not 1 <= top_k <= MAX_TOP_K:
        raise ValueError(f"top_k must be an integer between 1 and {MAX_TOP_K}")
    if len(query) > MAX_QUERY_CHARACTERS:
        raise ValueError(f"Query exceeds {MAX_QUERY_CHARACTERS} characters")
    terms = set(tokenize(query))
    matches: list[LexicalMatch] = []
    if terms:
        for chunk in chunks:
            matched = tuple(sorted(terms.intersection(tokenize(chunk.source.text))))
            if matched:
                matches.append(
                    LexicalMatch(chunk.chunk_id, len(matched), matched, chunk.source)
                )
    matches.sort(
        key=lambda match: (
            -match.score,
            match.source.path,
            match.source.start_line,
            match.source.end_line,
            match.chunk_id,
        )
    )
    return LexicalReport(tuple(sorted(terms)), tuple(matches[:top_k]))
