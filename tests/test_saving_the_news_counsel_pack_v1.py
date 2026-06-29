"""Saving the News counsel pack scripts."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_manifest_and_zip_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    art = tmp_path / "artifacts"
    art.mkdir()
    src = art / "sample.md"
    src.write_text("# sample\n", encoding="utf-8")
    manifest_mod = _load("manifest", "scripts/build_saving_the_news_counsel_export_manifest_v1.py")
    zip_mod = _load("zip", "scripts/build_saving_the_news_counsel_zip_pack_v1.py")
    monkeypatch.setattr(manifest_mod, "ROOT", tmp_path)
    monkeypatch.setattr(manifest_mod, "ART", art)
    monkeypatch.setattr(manifest_mod, "DEFAULT_PATHS", ("artifacts/sample.md",))
    monkeypatch.setattr(manifest_mod, "HANDOFF_OUT", art / "handoff.json")
    manifest_path = art / "manifest.json"
    monkeypatch.setattr(manifest_mod, "DEFAULT_OUT", manifest_path)
    doc = manifest_mod.build_manifest(["artifacts/sample.md"])
    manifest_path.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(zip_mod, "ROOT", tmp_path)
    monkeypatch.setattr(zip_mod, "MANIFEST", manifest_path)
    zpath = art / "pack.zip"
    meta = zip_mod.build_zip(zip_path=zpath)
    assert meta["ok"] is True
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
    assert "artifacts/sample.md" in names


def test_signoff_requires_reference() -> None:
    mod = _load("signoff", "scripts/record_saving_the_news_legal_counsel_signoff_v1.py")
    with pytest.raises(ValueError):
        mod.build(counsel_reference="", reviewer="x", notes="", ready_for_external_send=False)
