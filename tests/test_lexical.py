import hashlib

import pytest

from gitcontext.chunking import SourceChunk
from gitcontext.identities import chunk_id
from gitcontext.lexical import rank_chunks
from gitcontext.snapshots import IdentifiedChunk, build_snapshot


def chunk(text, path="app.py", start=1):
    source = SourceChunk(
        path,
        start,
        start + len(text.splitlines()) - 1,
        text,
        hashlib.sha256(text.encode()).hexdigest(),
        None,
        "module",
        False,
    )
    return IdentifiedChunk(
        chunk_id(source, policy_version="python-top-level-v1", max_lines=80), source
    )


def test_distinct_coverage_beats_repetition_and_metadata_is_preserved():
    repeated = chunk("save " * 10, "a.py")
    coverage = chunk("save record", "b.py")
    report = rank_chunks([repeated, coverage], "save record")
    assert [match.source.path for match in report.matches] == ["b.py", "a.py"]
    assert [match.score for match in report.matches] == [2, 1]
    assert report.matches[0].matched_terms == ("record", "save")
    assert report.matches[0].source == coverage.source
    assert report.matches[0].chunk_id == coverage.chunk_id
    assert report.evidence_state == "saved_snapshot_not_freshness_checked"


def test_query_repetition_does_not_inflate_scores():
    chunks = [chunk("save record")]
    assert (
        rank_chunks(chunks, "save save record").matches
        == rank_chunks(chunks, "save record").matches
    )


def test_full_identifier_is_an_additional_matching_term():
    exact = chunk("record_id", "z.py")
    parts = chunk("record id", "a.py")
    report = rank_chunks([parts, exact], "record_id")
    assert report.query_terms == ("id", "record", "record_id")
    assert [match.score for match in report.matches] == [3, 2]
    assert report.matches[0].source.path == "z.py"


def test_source_frequency_and_length_do_not_change_equal_coverage():
    short = chunk("save record", "a.py")
    long = chunk("save record " * 100, "b.py")
    assert [
        match.score for match in rank_chunks([long, short], "save record").matches
    ] == [2, 2]


def test_ties_are_stable_by_path_then_lines_independent_of_input_order():
    chunks = [
        chunk("save", "b.py"),
        chunk("save", "a.py", 10),
        chunk("save", "a.py", 2),
    ]
    forward = rank_chunks(chunks, "save")
    backward = rank_chunks(list(reversed(chunks)), "save")
    assert forward == backward
    assert [(m.source.path, m.source.start_line) for m in forward.matches] == [
        ("a.py", 2),
        ("a.py", 10),
        ("b.py", 1),
    ]


def test_top_k_and_no_zero_score_results():
    chunks = [chunk("save", "b.py"), chunk("save", "a.py"), chunk("unrelated", "c.py")]
    assert len(rank_chunks(chunks, "save").matches) == 2
    assert rank_chunks(chunks, "save", top_k=1).matches[0].source.path == "a.py"


@pytest.mark.parametrize("query", ["", "___ !!!", "store"])
def test_empty_or_unmatched_queries_have_no_results(query):
    assert rank_chunks([chunk("save")], query).matches == ()


def test_empty_corpus_and_case_normalization():
    assert not rank_chunks([], "save").matches
    assert (
        rank_chunks([chunk("ReviewedRecord")], "REVIEWED record").matches[0].score == 2
    )


def test_real_snapshot_python_and_markdown_can_both_match(tmp_path):
    (tmp_path / "app.py").write_text("def save_record():\n    pass\n")
    (tmp_path / "README.md").write_text("# Persistence\nSave reviewed records here.\n")
    snapshot = build_snapshot(tmp_path)
    report = rank_chunks(snapshot.chunks, "save")
    assert {match.source.path for match in report.matches} == {"app.py", "README.md"}
    references = {item.chunk_id: item.source for item in snapshot.chunks}
    assert all(references[match.chunk_id] == match.source for match in report.matches)


def test_token_expansion_can_make_match_count_larger_than_input_word_count():
    report = rank_chunks([chunk("parseHTTPResponse")], "parseHTTPResponse")
    assert len(report.query_terms) == 4
    assert report.matches[0].score == 4  # A term count, never a probability.


@pytest.mark.parametrize("value", [0, -1, True, 1.5, 101])
def test_invalid_top_k(value):
    with pytest.raises(ValueError):
        rank_chunks([], "save", top_k=value)


def test_query_character_bound():
    with pytest.raises(ValueError, match="characters"):
        rank_chunks([], "x" * 2_001)
    assert rank_chunks([], "x" * 2_000).matches == ()
