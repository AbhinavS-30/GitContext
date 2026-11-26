import hashlib
import math

import pytest

from gitcontext.bm25 import rank_bm25
from gitcontext.chunking import SourceChunk
from gitcontext.identities import chunk_id
from gitcontext.snapshots import IdentifiedChunk


def chunk(text, path="app.py"):
    source = SourceChunk(
        path,
        1,
        max(1, len(text.splitlines())),
        text,
        hashlib.sha256(text.encode()).hexdigest(),
        None,
        "module",
        False,
    )
    return IdentifiedChunk(
        chunk_id(source, policy_version="python-top-level-v1", max_lines=80), source
    )


def test_hand_calculated_single_term_single_document():
    item = chunk("alpha")
    report = rank_bm25([item], "alpha")
    assert report.matches[0].score == pytest.approx(math.log(4 / 3))
    assert report.matches[0].source == item.source
    assert report.matches[0].chunk_id == item.chunk_id
    assert report.matches[0].matched_terms == ("alpha",)
    assert report.document_count == 1 and report.average_document_length == 1
    assert report.ranking_parameters == (("k1", 1.2), ("b", 0.75))
    assert report.evidence_state == "saved_snapshot_not_freshness_checked"


def test_rare_term_carries_more_weight_than_common_term_at_equal_length():
    items = [
        chunk("rare filler", "a.py"),
        chunk("common filler", "b.py"),
        chunk("common other", "c.py"),
        chunk("common another", "d.py"),
    ]
    report = rank_bm25(items, "rare common")
    assert report.matches[0].source.path == "a.py"
    assert report.matches[0].score > report.matches[1].score


def test_frequency_benefit_saturates_when_length_normalization_disabled():
    items = [
        chunk("alpha", "one.py"),
        chunk("alpha alpha", "two.py"),
        chunk("alpha alpha alpha", "three.py"),
    ]
    scores = {m.source.path: m.score for m in rank_bm25(items, "alpha", b=0).matches}
    assert scores["three.py"] > scores["two.py"] > scores["one.py"]
    assert scores["three.py"] - scores["two.py"] < scores["two.py"] - scores["one.py"]


def test_length_normalization_and_disable_behavior():
    items = [chunk("alpha", "short.py"), chunk("alpha filler filler filler", "long.py")]
    report = rank_bm25(items, "alpha")
    assert report.matches[0].source.path == "short.py"
    assert report.matches[0].score > report.matches[1].score
    no_normalization = rank_bm25(items, "alpha", b=0)
    assert no_normalization.matches[0].score == no_normalization.matches[1].score


def test_empty_chunks_do_not_change_corpus_statistics_or_scores():
    item = chunk("alpha")
    original = rank_bm25([item], "alpha")
    assert rank_bm25([item, chunk("\n ___ !", "empty.py")], "alpha") == original
    assert rank_bm25([], "alpha").matches == ()
    assert rank_bm25([chunk("___")], "alpha").average_document_length == 0


@pytest.mark.parametrize("query", ["", "!!! ___", "absent"])
def test_empty_and_unmatched_query_return_no_hits(query):
    assert rank_bm25([chunk("alpha")], query).matches == ()


def test_query_repetition_ties_top_k_and_identifiers():
    items = [chunk("record_id", "b.py"), chunk("record_id", "a.py")]
    report = rank_bm25(items, "record_id")
    assert report == rank_bm25(list(reversed(items)), "record_id record_id")
    assert report.query_terms == ("id", "record", "record_id")
    assert report.matches[0].source.path == "a.py"
    assert len(rank_bm25(items, "record_id", top_k=1).matches) == 1
    assert math.isfinite(report.matches[0].score) and report.matches[0].score > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"k1": 0},
        {"k1": -1},
        {"k1": True},
        {"k1": float("nan")},
        {"b": -0.1},
        {"b": 1.1},
        {"b": False},
        {"b": float("inf")},
        {"top_k": 0},
        {"top_k": True},
        {"top_k": 101},
    ],
)
def test_invalid_options(kwargs):
    with pytest.raises(ValueError):
        rank_bm25([], "alpha", **kwargs)


def test_query_character_limit():
    with pytest.raises(ValueError):
        rank_bm25([], "x" * 2001)
