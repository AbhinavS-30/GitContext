import pytest

from gitcontext.tokenization import tokenize


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "save_reviewed_record",
            ("save_reviewed_record", "save", "reviewed", "record"),
        ),
        ("record_id", ("record_id", "record", "id")),
        ("ReviewedRecord", ("reviewedrecord", "reviewed", "record")),
        ("parseHTTPResponse", ("parsehttpresponse", "parse", "http", "response")),
        ("HTTPServer", ("httpserver", "http", "server")),
        ("__init__", ("__init__", "init")),
        ("foo__bar", ("foo__bar", "foo", "bar")),
        (
            "revision conflict: stale update!",
            ("revision", "conflict", "stale", "update"),
        ),
        ("app.models.Record", ("app", "models", "record")),
        ("HTTP2Client", ("http2client", "http2", "client")),
        ("status 409", ("status", "409")),
        ("café Straße 你好", ("café", "strasse", "你好")),
        ("", ()),
        ("!? --- ___ \n\t", ()),
    ],
)
def test_identifier_and_prose_policy(text, expected):
    assert tokenize(text) == expected


def test_occurrence_counts_are_preserved_without_duplicate_expansions():
    assert tokenize("Record record record") == ("record", "record", "record")
    assert tokenize("foo_foo foo_foo") == ("foo_foo", "foo", "foo_foo", "foo")


def test_query_and_source_can_share_parts_while_exact_identifier_survives():
    source = tokenize("def save_reviewed_record(record_id): pass")
    query = tokenize("save reviewed record")
    assert set(query) <= set(source)
    assert "save_reviewed_record" in source
    assert "record_id" in source
    assert tokenize("record_id") != tokenize("record id")


def test_tokenizer_is_repeatable_and_does_not_infer_synonyms():
    text = "def SaveRecord(record_id): ..."
    assert tokenize(text) == tokenize(text)
    assert "store" not in tokenize("save")
