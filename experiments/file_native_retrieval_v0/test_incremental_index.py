from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from experiments.file_native_retrieval_v0 import incremental_index as inc
from experiments.file_native_retrieval_v0 import retrieval


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))


def _build_two(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "def alpha():\n    return 1\n")
    _write(root / "b.md", "beta\n")
    manifest = tmp_path / "index.json"
    doc, counters = inc.update_index(root, ["a.py", "b.md"], manifest)
    return root, manifest, doc, counters


def test_initial_build_rebuilds_all(tmp_path: Path) -> None:
    _, _, doc, counters = _build_two(tmp_path)
    assert len(doc["sources"]) == 2
    assert counters.as_dict() == {
        "reused_count": 0,
        "rebuilt_count": 2,
        "removed_count": 0,
        "total_count": 2,
    }


def test_unchanged_run_reuses_all_without_rebuild(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, manifest, _, _ = _build_two(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("unchanged fast path must not rebuild/read/hash source")

    monkeypatch.setattr(inc, "_rebuild_record", forbidden)
    _, counters = inc.update_index(root, ["a.py", "b.md"], manifest)
    assert counters.reused_count == 2
    assert counters.rebuilt_count == 0


def test_one_edit_rebuilds_only_one(tmp_path: Path) -> None:
    root, manifest, _, _ = _build_two(tmp_path)
    _write(root / "a.py", "def alpha():\n    return 22\n")
    _, counters = inc.update_index(root, ["a.py", "b.md"], manifest)
    assert (counters.rebuilt_count, counters.reused_count) == (1, 1)


def test_one_add_rebuilds_only_new_source(tmp_path: Path) -> None:
    root, manifest, _, _ = _build_two(tmp_path)
    _write(root / "c.json", '{"c": 3}\n')
    _, counters = inc.update_index(root, ["a.py", "b.md", "c.json"], manifest)
    assert (counters.rebuilt_count, counters.reused_count, counters.total_count) == (1, 2, 3)


def test_removed_source_is_dropped(tmp_path: Path) -> None:
    root, manifest, _, _ = _build_two(tmp_path)
    doc, counters = inc.update_index(root, ["a.py"], manifest)
    assert [row["path"] for row in doc["sources"]] == ["a.py"]
    assert counters.removed_count == 1
    assert counters.total_count == 1


def test_manifest_serialization_is_deterministic(tmp_path: Path) -> None:
    _, _, doc, _ = _build_two(tmp_path)
    reversed_doc = {"schema_version": doc["schema_version"], "sources": list(reversed(doc["sources"]))}
    assert inc.serialize_manifest(doc) == inc.serialize_manifest(reversed_doc)


def test_corrupt_manifest_errors_explicitly(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "x = 1\n")
    manifest = tmp_path / "index.json"
    manifest.write_text("{broken", encoding="utf-8")
    with pytest.raises(inc.ManifestError):
        inc.update_index(root, ["a.py"], manifest, on_corrupt="error")


def test_corrupt_manifest_full_rescan_recovers_explicitly(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "x = 1\n")
    manifest = tmp_path / "index.json"
    manifest.write_text("{broken", encoding="utf-8")
    doc, counters = inc.update_index(root, ["a.py"], manifest, on_corrupt="full_rescan")
    assert counters.rebuilt_count == 1
    assert counters.reused_count == 0
    assert inc.load_manifest(manifest) == doc


def test_atomic_write_leaves_valid_final_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "x = 1\n")
    manifest = tmp_path / "index.json"
    calls = []
    real_replace = inc.os.replace

    def tracked_replace(src, dst):
        calls.append((Path(src), Path(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(inc.os, "replace", tracked_replace)
    doc, _ = inc.update_index(root, ["a.py"], manifest)
    assert calls and calls[-1][1] == manifest
    assert json.loads(manifest.read_text(encoding="utf-8")) == doc
    assert not list(tmp_path.glob(".index.json.*.tmp"))


@pytest.mark.parametrize("bad", ["../escape.py", "/absolute.py", "C:/absolute.py", "a/../b.py"])
def test_path_escape_or_absolute_rejected(tmp_path: Path, bad: str) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    with pytest.raises(ValueError):
        inc.update_index(root, [bad], tmp_path / "index.json")


def test_full_rescan_rebuilds_all(tmp_path: Path) -> None:
    root, manifest, _, _ = _build_two(tmp_path)
    _, counters = inc.update_index(root, ["a.py", "b.md"], manifest, full_rescan=True)
    assert counters.rebuilt_count == 2
    assert counters.reused_count == 0


def test_rebuilt_sha256_equals_actual_bytes(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "payload = 'source bytes'\n")
    doc, _ = inc.update_index(root, ["a.py"], tmp_path / "index.json")
    expected = hashlib.sha256((root / "a.py").read_bytes()).hexdigest()
    row = doc["sources"][0]
    assert row["sha256"] == expected
    assert row["record"]["source_hash"] == expected


def test_counters_cover_reuse_rebuild_remove_and_total(tmp_path: Path) -> None:
    root, manifest, _, _ = _build_two(tmp_path)
    _write(root / "a.py", "def alpha():\n    return 9\n")
    _write(root / "c.json", '{"new": true}\n')
    _, counters = inc.update_index(root, ["a.py", "c.json"], manifest)
    assert counters.as_dict() == {
        "reused_count": 0,
        "rebuilt_count": 2,
        "removed_count": 1,
        "total_count": 2,
    }


def test_literal_relations_preserved_for_rebuilt_source(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "# see b.md\nx = 1\n")
    _write(root / "b.md", "target\n")
    doc, _ = inc.update_index(root, ["a.py", "b.md"], tmp_path / "index.json")
    a = next(row["record"] for row in doc["sources"] if row["path"] == "a.py")
    assert a["relations"] == [{"target": "b.md", "kind": "literal_path_reference"}]


def test_added_approved_target_refreshes_relation_on_stat_reused_source(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "# see b.md\nx = 1\n")
    manifest = tmp_path / "index.json"
    first, _ = inc.update_index(root, ["a.py"], manifest)
    assert first["sources"][0]["record"]["relations"] == []
    a_stat = (root / "a.py").stat()

    _write(root / "b.md", "target\n")
    updated, counters = inc.update_index(root, ["a.py", "b.md"], manifest)
    a = next(row for row in updated["sources"] if row["path"] == "a.py")
    assert (a["size"], a["mtime_ns"]) == (a_stat.st_size, a_stat.st_mtime_ns)
    assert a["record"]["relations"] == [{"target": "b.md", "kind": "literal_path_reference"}]
    assert counters.as_dict() == {"reused_count": 1, "rebuilt_count": 1, "removed_count": 0, "total_count": 2}


def test_removed_approved_target_is_dropped_from_reused_relation_without_source_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "# see b.md\nx = 1\n")
    _write(root / "b.md", "target\n")
    manifest = tmp_path / "index.json"
    first, _ = inc.update_index(root, ["a.py", "b.md"], manifest)
    a_first = next(row for row in first["sources"] if row["path"] == "a.py")
    assert a_first["record"]["relations"] == [{"target": "b.md", "kind": "literal_path_reference"}]

    def forbidden(*args, **kwargs):
        raise AssertionError("removal-only relation refresh must not read source body")

    monkeypatch.setattr(inc, "_read_source_text", forbidden)
    updated, counters = inc.update_index(root, ["a.py"], manifest)
    assert updated["sources"][0]["record"]["relations"] == []
    assert counters.as_dict() == {"reused_count": 1, "rebuilt_count": 0, "removed_count": 1, "total_count": 1}


def test_rename_removes_old_relation_and_adds_new_literal_relation(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "# old.md new.md\nx = 1\n")
    _write(root / "old.md", "old\n")
    manifest = tmp_path / "index.json"
    inc.update_index(root, ["a.py", "old.md"], manifest)
    a_stat = (root / "a.py").stat()

    (root / "old.md").unlink()
    _write(root / "new.md", "new\n")
    updated, counters = inc.update_index(root, ["a.py", "new.md"], manifest)
    a = next(row for row in updated["sources"] if row["path"] == "a.py")
    assert (a["size"], a["mtime_ns"]) == (a_stat.st_size, a_stat.st_mtime_ns)
    assert a["record"]["relations"] == [{"target": "new.md", "kind": "literal_path_reference"}]
    assert counters.as_dict() == {"reused_count": 1, "rebuilt_count": 1, "removed_count": 1, "total_count": 2}


def test_identical_approved_set_keeps_zero_source_body_read_fast_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, manifest, _, _ = _build_two(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("identical approved set must not read/rebuild source")

    monkeypatch.setattr(inc, "_read_source_text", forbidden)
    monkeypatch.setattr(inc, "_rebuild_record", forbidden)
    _, counters = inc.update_index(root, ["a.py", "b.md"], manifest)
    assert counters.as_dict() == {"reused_count": 2, "rebuilt_count": 0, "removed_count": 0, "total_count": 2}


def test_incremental_relations_match_clean_build_after_add_remove(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    _write(root / "a.py", "# b.md c.md\nx = 1\n")
    _write(root / "b.md", "old target\n")
    _write(root / "c.md", "new target\n")
    manifest = tmp_path / "index.json"
    inc.update_index(root, ["a.py", "b.md"], manifest)

    updated, counters = inc.update_index(root, ["a.py", "c.md"], manifest)
    clean = retrieval.build(root, ["a.py", "c.md"])
    incremental_relations = {row["path"]: row["record"]["relations"] for row in updated["sources"]}
    clean_relations = {row["source_path"]: row["relations"] for row in clean}
    assert incremental_relations == clean_relations
    assert counters.as_dict() == {"reused_count": 1, "rebuilt_count": 1, "removed_count": 1, "total_count": 2}
