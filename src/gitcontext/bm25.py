"""A local, explicit positive-IDF BM25 candidate over prepared chunks."""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from gitcontext.lexical import MAX_QUERY_CHARACTERS, MAX_TOP_K, LexicalMatch
from gitcontext.snapshots import IdentifiedChunk
from gitcontext.tokenization import TOKENIZATION_VERSION, tokenize

BM25_VERSION = "bm25-positive-idf-v1"
BM25_K1 = 1.2
BM25_B = 0.75
BM25_PARAMETERS = (("k1", BM25_K1), ("b", BM25_B))


@dataclass(frozen=True)
class BM25Report:
    query_terms: tuple[str, ...]
    matches: tuple[LexicalMatch, ...]
    document_count: int
    average_document_length: float
    ranking_parameters: tuple[tuple[str, float], ...]
    ranking_version: str = BM25_VERSION
    tokenization_version: str = TOKENIZATION_VERSION
    evidence_state: Literal["saved_snapshot_not_freshness_checked"] = (
        "saved_snapshot_not_freshness_checked"
    )


def rank_bm25(
    chunks: Sequence[IdentifiedChunk],
    query: str,
    *,
    top_k: int = 5,
    k1: float = BM25_K1,
    b: float = BM25_B,
) -> BM25Report:
    """Weight unique query terms by rarity, saturated TF, and expanded-token length.

    Corpus statistics omit token-empty chunks. No I/O, inference, stopword filter,
    stemming, label fitting, or freshness verification occurs here. Python API
    parameter overrides are explicit; CLI comparisons use the frozen defaults.
    """
    if type(top_k) is not int or not 1 <= top_k <= MAX_TOP_K:
        raise ValueError(f"top_k must be an integer between 1 and {MAX_TOP_K}")
    if len(query) > MAX_QUERY_CHARACTERS:
        raise ValueError(f"Query exceeds {MAX_QUERY_CHARACTERS} characters")
    for name, value in (("k1", k1), ("b", b)):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite and numeric")
    if k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("k1 must be positive and b must be between 0 and 1")
    terms = tuple(sorted(set(tokenize(query))))
    documents = []
    frequencies: Counter[str] = Counter()
    for chunk in chunks:
        counts = Counter(tokenize(chunk.source.text))
        if counts:
            documents.append((chunk, counts, counts.total()))
            frequencies.update(counts.keys())
    count = len(documents)
    average_length = sum(length for _, _, length in documents) / count if count else 0.0
    matches = []
    for chunk, counts, length in documents:
        matched = tuple(term for term in terms if term in counts)
        if not matched:
            continue
        contributions = []
        normalization = k1 * (1 - b + b * length / average_length)
        for term in matched:
            idf = math.log1p(
                (count - frequencies[term] + 0.5) / (frequencies[term] + 0.5)
            )
            tf = counts[term]
            contributions.append(idf * tf * (k1 + 1) / (tf + normalization))
        score = math.fsum(contributions)
        if not math.isfinite(score):
            raise ValueError("BM25 parameters produced a non-finite score")
        matches.append(LexicalMatch(chunk.chunk_id, score, matched, chunk.source))
    matches.sort(
        key=lambda match: (
            -match.score,
            match.source.path,
            match.source.start_line,
            match.source.end_line,
            match.chunk_id,
        )
    )
    return BM25Report(
        terms,
        tuple(matches[:top_k]),
        count,
        average_length,
        (("k1", float(k1)), ("b", float(b))),
    )
