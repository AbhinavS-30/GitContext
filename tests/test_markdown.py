import hashlib
import io

import pytest

from gitcontext.markdown import chunk_markdown
from gitcontext.reading import SourceFile


def source(text):
    raw = text.encode()
    return SourceFile("README.md", text, len(raw), hashlib.sha256(raw).hexdigest())


def check_partition(original, report):
    assert "".join(c.text for c in report.chunks) == original.text
    lines = io.StringIO(original.text, newline="").readlines()
    cursor = 1
    for chunk in report.chunks:
        assert chunk.start_line == cursor
        assert chunk.text == "".join(lines[chunk.start_line - 1 : chunk.end_line])
        assert chunk.content_sha256 == original.content_sha256
        assert chunk.path == original.path
        cursor = chunk.end_line + 1
    assert cursor == len(lines) + 1


def test_headings_preamble_duplicates_and_closing_hashes():
    original = source("Intro\n# Setup\nInstall\n## Config ###\nLocal\n# Setup\nAgain")
    report = chunk_markdown(original)
    check_partition(original, report)
    assert [c.symbol_name for c in report.chunks] == [None, "Setup", "Config", "Setup"]
    assert [(c.start_line, c.end_line) for c in report.chunks] == [
        (1, 1),
        (2, 3),
        (4, 5),
        (6, 7),
    ]
    assert report.chunks[0].symbol_type == "markdown_preamble"
    assert not report.issues


@pytest.mark.parametrize("marker", ["```", "~~~~"])
def test_fenced_code_headings_do_not_split(marker):
    original = source(
        f"# Example\n{marker}python\n# comment\n## also code\n{marker}\n# Real\nText\n"
    )
    report = chunk_markdown(original)
    check_partition(original, report)
    assert [c.symbol_name for c in report.chunks] == ["Example", "Real"]
    assert not report.issues


def test_fence_closer_requires_matching_character_length_and_no_info():
    original = source(
        "# A\n````python\n```\n# code\n~~~~\n````bad\n# still code\n`````\n# B\n"
    )
    report = chunk_markdown(original)
    check_partition(original, report)
    assert [c.symbol_name for c in report.chunks] == ["A", "B"]
    assert not report.issues


def test_unclosed_fence_is_reported_and_preserved():
    original = source("# Example\n```python\n# remains code\n")
    report = chunk_markdown(original)
    check_partition(original, report)
    assert len(report.chunks) == 1
    assert report.issues[0].reason == "unclosed_fence"
    assert "line 2" in report.issues[0].detail


def test_large_section_fragments_keep_heading_metadata():
    original = source("# Setup\none\ntwo\nthree\nfour\n")
    report = chunk_markdown(original, max_lines=2)
    check_partition(original, report)
    assert len(report.chunks) == 3
    assert all(c.is_fragment and c.symbol_name == "Setup" for c in report.chunks)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_newlines_unicode_and_heading_at_start(newline):
    original = source(newline.join(["# café", "你好", "## Next", "end"]))
    report = chunk_markdown(original)
    check_partition(original, report)
    assert [c.symbol_name for c in report.chunks] == ["café", "Next"]


@pytest.mark.parametrize("text", ["", "plain text", "\n\n", "Heading\n=======\n"])
def test_no_atx_headings(text):
    original = source(text)
    report = chunk_markdown(original)
    check_partition(original, report)
    assert all(c.symbol_type == "markdown_preamble" for c in report.chunks)


def test_heading_boundaries_and_indentation():
    original = source(
        "#Title\n####### Not a heading\n    # indented code\n   ## Valid\n#\n"
    )
    report = chunk_markdown(original)
    check_partition(original, report)
    assert [c.symbol_name for c in report.chunks] == [None, "Valid", ""]


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_limit(value):
    with pytest.raises(ValueError):
        chunk_markdown(source("# Title"), max_lines=value)
