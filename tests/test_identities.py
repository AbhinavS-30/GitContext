import hashlib
from dataclasses import replace

import pytest

from gitcontext.chunking import chunk_python
from gitcontext.identities import chunk_id
from gitcontext.markdown import chunk_markdown
from gitcontext.reading import SourceFile


def report_for(text="def save():\n    return True\n", path="app.py", max_lines=80):
    raw = text.encode()
    source = SourceFile(path, text, len(raw), hashlib.sha256(raw).hexdigest())
    return chunk_python(source, max_lines=max_lines)


def identify(chunk, report):
    return chunk_id(
        chunk, policy_version=report.policy_version, max_lines=report.max_lines
    )


def test_repeatable_across_rebuilds_and_has_versioned_format():
    first = report_for()
    second = report_for()
    reference = identify(first.chunks[0], first)
    assert reference == identify(second.chunks[0], second)
    prefix, digest = reference.split(":")
    assert prefix == "chunk-v1"
    assert len(digest) == 64
    assert int(digest, 16) >= 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("path", "other.py"),
        ("start_line", 2),
        ("end_line", 3),
        ("text", "def save():\n    return None\n"),
        ("content_sha256", "a" * 64),
        ("symbol_name", "other"),
        ("symbol_type", "async_function"),
        ("is_fragment", True),
    ],
)
def test_identity_changes_when_source_reference_changes(field, value):
    report = report_for()
    original = report.chunks[0]
    assert identify(original, report) != identify(
        replace(original, **{field: value}), report
    )


def test_config_changes_even_when_chunk_text_stays_the_same():
    first = report_for(max_lines=80)
    second = report_for(max_lines=100)
    assert first.chunks == second.chunks
    assert identify(first.chunks[0], first) != identify(second.chunks[0], second)
    changed = replace(first, policy_version="python-top-level-v2")
    assert identify(first.chunks[0], first) != identify(changed.chunks[0], changed)


def test_duplicate_markdown_titles_and_text_have_distinct_locations():
    text = "# Setup\nRun it\n# Setup\nRun it\n"
    raw = text.encode()
    report = chunk_markdown(
        SourceFile("README.md", text, len(raw), hashlib.sha256(raw).hexdigest())
    )
    assert report.chunks[0].text == report.chunks[1].text
    assert identify(report.chunks[0], report) != identify(report.chunks[1], report)


@pytest.mark.parametrize("max_lines", [0, -1, True, 1.5])
def test_invalid_line_limit(max_lines):
    report = report_for()
    with pytest.raises(ValueError):
        chunk_id(
            report.chunks[0], policy_version=report.policy_version, max_lines=max_lines
        )


@pytest.mark.parametrize("version", ["", " ", None])
def test_invalid_policy_version(version):
    report = report_for()
    with pytest.raises(ValueError):
        chunk_id(report.chunks[0], policy_version=version, max_lines=80)
