"""Shared, deterministic lexical terms for queries and source chunks."""

import re

TOKENIZATION_VERSION = "code-words-v1"
WORDS = re.compile(r"\w+", re.UNICODE)
CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def tokenize(text: str) -> tuple[str, ...]:
    """Keep case-folded identifiers and their underscore/ASCII-camel parts.

    Terms repeat across source occurrences, but each occurrence emits a normalized
    term at most once. Digits remain in terms; punctuation separates words. This
    does not infer synonyms, remove stopwords, stem words, or parse code syntax.
    """
    terms: list[str] = []
    for match in WORDS.finditer(text):
        word = match.group()
        if not word.strip("_"):
            continue
        candidates = [word.casefold()]
        for part in word.split("_"):
            candidates.extend(
                piece.casefold() for piece in CAMEL_BOUNDARY.split(part) if piece
            )
        # dict preserves first-seen order and avoids double-counting a plain word
        # once as a full term and again as an identical split part.
        terms.extend(dict.fromkeys(candidates))
    return tuple(terms)
