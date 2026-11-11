import hashlib
import io

import pytest

from gitcontext.chunking import chunk_python
from gitcontext.reading import SourceFile


def source(text: str) -> SourceFile:
    raw = text.encode("utf-8")
    return SourceFile("app.py", text, len(raw), hashlib.sha256(raw).hexdigest())


def assert_exact_partition(original, report):
    lines = io.StringIO(original.text, newline="").readlines()
    assert "".join(chunk.text for chunk in report.chunks) == original.text
    cursor = 1
    for chunk in report.chunks:
        assert chunk.start_line == cursor
        assert chunk.end_line >= chunk.start_line
        assert chunk.text == "".join(lines[chunk.start_line - 1 : chunk.end_line])
        assert chunk.path == original.path
        assert chunk.content_sha256 == original.content_sha256
        cursor = chunk.end_line + 1
    assert cursor == len(lines) + 1


def test_decorators_imports_comments_and_async_ranges():
    original = source(
        "import os\n\n# permission policy\n@require_permission\n"
        "@other(\n    flag=True\n)\ndef save(record):\n"
        "    validate(record)\n    persist(record)\n\n"
        "async def load():\n    return 1\n# trailing comment\n"
    )
    report = chunk_python(original)
    assert_exact_partition(original, report)
    function = next(chunk for chunk in report.chunks if chunk.symbol_name == "save")
    assert (function.start_line, function.end_line) == (4, 10)
    assert function.text.startswith("@require_permission\n")
    assert [(c.symbol_name, c.symbol_type) for c in report.chunks] == [
        (None, "module"),
        ("save", "function"),
        (None, "module"),
        ("load", "async_function"),
        (None, "module"),
    ]
    assert not report.issues


def test_methods_and_nested_definitions_have_no_duplicate_chunks():
    original = source(
        "class Store:\n    def save(self):\n        def validate():\n"
        "            return True\n        return validate()\n\n"
        "def outer():\n    def inner():\n        return 1\n    return inner()\n"
    )
    report = chunk_python(original)
    assert_exact_partition(original, report)
    assert [c.symbol_name for c in report.chunks if c.symbol_name] == ["Store", "outer"]
    assert report.chunks[0].symbol_type == "class"


def test_oversized_definition_fragments_retain_symbol_and_exact_lines():
    original = source(
        "@decorator\ndef large():\n    x = 1\n    y = 2\n    return x + y\n"
    )
    report = chunk_python(original, max_lines=2)
    assert_exact_partition(original, report)
    assert [(c.start_line, c.end_line) for c in report.chunks] == [
        (1, 2),
        (3, 4),
        (5, 5),
    ]
    assert all(c.is_fragment and c.symbol_name == "large" for c in report.chunks)


def test_syntax_error_uses_visible_exact_fallback():
    original = source("def broken(:\n    pass\n# still useful text\n")
    report = chunk_python(original, max_lines=2)
    assert_exact_partition(original, report)
    assert report.issues[0].reason == "syntax_error"
    assert report.issues[0].path == "app.py"
    assert all(c.symbol_type == "fallback" for c in report.chunks)
    assert all(c.symbol_name is None for c in report.chunks)


@pytest.mark.parametrize(
    "text", ["", "\n\n", "# comment", "x = 1", "import os\nx = 1\n"]
)
def test_empty_and_module_only_files(text):
    original = source(text)
    report = chunk_python(original, max_lines=1)
    assert_exact_partition(original, report)
    assert not report.issues
    assert all(c.symbol_type == "module" for c in report.chunks)


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_line_endings_unicode_and_form_feed(newline):
    text = newline.join(["# café", "\fdef greet():", "    return '你好'"])
    original = source(text)
    report = chunk_python(original)
    assert_exact_partition(original, report)
    assert not report.issues
    assert report.chunks[1].start_line == 2
    assert report.chunks[1].end_line == 3


def test_conditional_definition_stays_in_module_chunk_without_execution():
    original = source(
        "raise RuntimeError('never execute')\nif True:\n    def f(): pass\n"
    )
    report = chunk_python(original)
    assert_exact_partition(original, report)
    assert len(report.chunks) == 1
    assert report.chunks[0].symbol_type == "module"


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_line_limit(value):
    with pytest.raises(ValueError, match="positive integer"):
        chunk_python(source("pass"), max_lines=value)
