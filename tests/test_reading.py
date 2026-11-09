from dataclasses import replace
from types import SimpleNamespace

import pytest

from gitcontext.discovery import DiscoveredFile, DiscoveryLimits, discover_repository
from gitcontext.reading import read_sources


def test_change_detected_during_read(tmp_path, monkeypatch):
    import os

    (tmp_path / "app.py").write_text("pass")
    original = os.fstat
    calls = 0

    def changed(fd):
        nonlocal calls
        calls += 1
        metadata = original(fd)
        return SimpleNamespace(
            st_mode=metadata.st_mode,
            st_size=metadata.st_size,
            st_mtime_ns=metadata.st_mtime_ns + (calls > 1),
            st_ctime_ns=metadata.st_ctime_ns,
        )

    monkeypatch.setattr("gitcontext.reading.os.fstat", changed)
    report = read_sources(discover_repository(tmp_path))
    assert not report.files
    assert report.partial
    assert report.issues[0].reason == "changed_during_read"


def test_fifo_replacement_does_not_block(tmp_path):
    import os

    source = tmp_path / "app.py"
    source.write_text("pass")
    discovery = discover_repository(tmp_path)
    source.unlink()
    os.mkfifo(source)
    report = read_sources(discovery)
    assert report.partial
    assert report.bytes_read == 0
    assert report.issues[0].reason == "non_regular_file"


def test_preserves_text_and_does_not_execute(tmp_path):
    raw = 'raise RuntimeError("never execute")\r\n# café\r\n'.encode()
    (tmp_path / "app.py").write_bytes(raw)
    report = read_sources(discover_repository(tmp_path))
    assert report.files[0].text == raw.decode()
    assert report.files[0].size_bytes == len(raw)
    assert report.bytes_read == len(raw)
    assert not report.partial


def test_growth_after_discovery_is_bounded(tmp_path):
    source = tmp_path / "app.py"
    source.write_bytes(b"pass")
    discovery = discover_repository(tmp_path, DiscoveryLimits(max_file_bytes=5))
    source.write_bytes(b"x" * 100)
    report = read_sources(discovery)
    assert not report.files
    assert report.partial
    assert report.bytes_read == 6
    assert report.issues[0].reason == "file_size_limit"


@pytest.mark.parametrize(
    "raw,reason", [(b"\xff", "invalid_utf8"), (b"a\0b", "nul_content")]
)
def test_bad_content_is_reported(tmp_path, raw, reason):
    (tmp_path / "bad.py").write_bytes(raw)
    report = read_sources(discover_repository(tmp_path))
    assert not report.files
    assert report.partial
    assert report.bytes_read == len(raw)
    assert report.issues[0].reason == reason


def test_deleted_file_does_not_discard_other_results(tmp_path):
    (tmp_path / "a.py").write_text("pass")
    (tmp_path / "b.md").write_text("docs")
    discovery = discover_repository(tmp_path)
    (tmp_path / "a.py").unlink()
    report = read_sources(discovery)
    assert [source.path for source in report.files] == ["b.md"]
    assert report.partial
    assert report.issues[0].reason == "read_error"


@pytest.mark.parametrize("directory_link", [False, True])
def test_replaced_symlinks_are_not_followed(tmp_path, directory_link):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    source = repo / "sub/app.py"
    source.write_text("pass")
    discovery = discover_repository(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "app.py").write_text("private")
    source.unlink()
    if directory_link:
        (repo / "sub").rmdir()
        (repo / "sub").symlink_to(outside, target_is_directory=True)
    else:
        source.symlink_to(outside / "app.py")
    report = read_sources(discovery)
    assert not report.files
    assert report.bytes_read == 0
    assert report.partial


def test_rejects_parent_escape_and_absolute_path(tmp_path):
    discovery = discover_repository(tmp_path)
    for path in ("../outside.py", str(tmp_path / "absolute.py")):
        report = read_sources(replace(discovery, files=(DiscoveredFile(path, 0),)))
        assert report.partial
        assert report.bytes_read == 0
        assert report.issues[0].reason == "read_error"


def test_total_budget_counts_rejected_content(tmp_path):
    (tmp_path / "a.py").write_bytes(b"\xff" * 4)
    (tmp_path / "b.py").write_bytes(b"pass")
    report = read_sources(discover_repository(tmp_path), max_total_bytes=6)
    assert not report.files
    assert report.bytes_read == 7
    assert report.partial
    assert [issue.reason for issue in report.issues] == [
        "invalid_utf8",
        "total_byte_limit",
    ]


def test_exact_budget_and_empty_file(tmp_path):
    (tmp_path / "a.py").write_bytes(b"")
    (tmp_path / "b.py").write_bytes(b"pass")
    report = read_sources(discover_repository(tmp_path), max_total_bytes=4)
    assert len(report.files) == 2
    assert not report.partial
    assert report.bytes_read == 4


def test_preserves_discovery_partial_status(tmp_path):
    (tmp_path / "big.py").write_bytes(b"12345")
    report = read_sources(
        discover_repository(tmp_path, DiscoveryLimits(max_file_bytes=1))
    )
    assert report.partial
    assert report.issues[0].reason == "file_size_limit"


def test_replaced_root_is_rejected(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    discovery = discover_repository(repo)
    repo.rmdir()
    repo.symlink_to(tmp_path, target_is_directory=True)
    report = read_sources(discovery)
    assert report.partial
    assert report.issues[0].reason == "root_read_error"


@pytest.mark.parametrize("budget", [0, -1, True, 1.5])
def test_invalid_budget(tmp_path, budget):
    with pytest.raises(ValueError):
        read_sources(discover_repository(tmp_path), max_total_bytes=budget)
