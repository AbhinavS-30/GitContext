import json
from dataclasses import replace

import pytest

from gitcontext.persistence import load_snapshot, save_snapshot
from gitcontext.snapshots import build_snapshot, snapshot_id


@pytest.fixture
def saved(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("@guard\ndef save():\n    return True\n")
    (root / "README.md").write_text("# Setup\nInstall\n")
    (root / "empty.py").write_bytes(b"")
    snapshot = build_snapshot(root)
    path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, path)
    return snapshot, path


def test_roundtrip_preserves_all_fields_and_is_private(saved):
    snapshot, path = saved
    assert load_snapshot(path) == snapshot
    assert path.stat().st_mode & 0o777 == 0o600
    assert not list(path.parent.glob(".snapshot-*.tmp"))


@pytest.mark.parametrize("operation", ["write", "replace", "fsync", "verify"])
def test_failed_publication_preserves_previous_file(saved, monkeypatch, operation):
    snapshot, path = saved
    original = path.read_bytes()
    (snapshot.root / "app.py").write_text("pass")
    refreshed = build_snapshot(snapshot.root)

    def fail(*args, **kwargs):
        raise OSError("simulated write failure")

    if operation == "write":
        from gitcontext import persistence

        original_open = persistence.os.fdopen

        class InterruptedWrite:
            def __init__(self, stream):
                self.stream = stream

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.stream.close()

            def write(self, raw):
                self.stream.write(raw[: len(raw) // 2])
                raise OSError("simulated interrupted write")

        monkeypatch.setattr(
            persistence.os,
            "fdopen",
            lambda *args, **kwargs: InterruptedWrite(original_open(*args, **kwargs)),
        )
    elif operation == "verify":
        monkeypatch.setattr("gitcontext.persistence.load_snapshot", fail)
    else:
        monkeypatch.setattr(f"gitcontext.persistence.os.{operation}", fail)
    with pytest.raises(OSError):
        save_snapshot(refreshed, path)
    assert path.read_bytes() == original
    assert not list(path.parent.glob(".snapshot-*.tmp"))


def test_successful_replacement(saved):
    snapshot, path = saved
    (snapshot.root / "app.py").write_text("pass")
    refreshed = build_snapshot(snapshot.root)
    save_snapshot(refreshed, path)
    assert load_snapshot(path) == refreshed
    assert refreshed.snapshot_id != snapshot.snapshot_id


@pytest.mark.parametrize(
    "change",
    ["json", "schema", "snapshot_id", "chunk_text", "missing_ref", "extra", "type"],
)
def test_corruption_is_rejected(saved, change):
    _, path = saved
    data = json.loads(path.read_bytes())
    if change == "json":
        path.write_bytes(b'{"unfinished":')
    else:
        if change == "schema":
            data["manifest"]["schema_version"] = "future-v99"
        elif change == "snapshot_id":
            data["snapshot_id"] = "snapshot-v2:fake"
        elif change == "chunk_text":
            data["chunks"][0]["source"]["text"] = "altered"
        elif change == "missing_ref":
            data["chunks"].pop()
        elif change == "extra":
            data["manifest"]["unexpected"] = True
        else:
            data["manifest"]["partial"] = "false"
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_snapshot(path)


def test_recomputed_manifest_id_cannot_hide_inconsistent_chunk_metadata(saved):
    snapshot, path = saved
    original = path.read_bytes()
    file = snapshot.manifest.files[0]
    bad_file = replace(file, content_sha256="a" * 64)
    manifest = replace(
        snapshot.manifest, files=(bad_file, *snapshot.manifest.files[1:])
    )
    corrupted = replace(snapshot, manifest=manifest, snapshot_id=snapshot_id(manifest))
    with pytest.raises(ValueError):
        save_snapshot(corrupted, path)
    assert path.read_bytes() == original


def test_partial_and_degraded_flags_roundtrip(tmp_path):
    (tmp_path / "bad.py").write_bytes(b"\xff")
    (tmp_path / "broken.py").write_text("def broken(:\n")
    snapshot = build_snapshot(tmp_path)
    assert snapshot.manifest.partial and snapshot.manifest.degraded
    path = tmp_path / "saved.json"
    save_snapshot(snapshot, path)
    assert load_snapshot(path) == snapshot


def test_load_limit_is_enforced(saved, monkeypatch):
    _, path = saved
    monkeypatch.setattr("gitcontext.persistence.MAX_SNAPSHOT_BYTES", 10)
    with pytest.raises(ValueError, match="byte limit"):
        load_snapshot(path)


def test_loader_refuses_symlink(saved):
    _, path = saved
    link = path.parent / "link.json"
    link.symlink_to(path)
    with pytest.raises(OSError):
        load_snapshot(link)
