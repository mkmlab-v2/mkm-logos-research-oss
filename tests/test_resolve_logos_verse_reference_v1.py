from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "resolve_logos_verse_reference_v1.py"


def _load_module():
    import sys

    spec = importlib.util.spec_from_file_location("resolve_logos_verse_reference_v1", RESOLVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_john_19_34_resolves_to_jhn():
    mod = _load_module()
    refs = mod.resolve_verse_references_in_text("John 19:34")
    assert len(refs) == 1
    assert refs[0].verse_id == "Jhn.19.34"
    assert refs[0].resolve_via == "alias_colon"


def test_canon_dot_jhn_passthrough():
    mod = _load_module()
    refs = mod.resolve_verse_references_in_text("See Jhn.19.34 for blood and water.")
    assert refs[0].verse_id == "Jhn.19.34"


def test_john_dot_form_normalizes():
    mod = _load_module()
    refs = mod.resolve_verse_references_in_text("John.19.34")
    assert refs[0].verse_id == "Jhn.19.34"


def test_korean_gospel_john():
    mod = _load_module()
    refs = mod.resolve_verse_references_in_text("요한복음 19:34")
    assert refs[0].verse_id == "Jhn.19.34"


def test_first_epistle_not_gospel():
    mod = _load_module()
    refs = mod.resolve_verse_references_in_text("1 John 5:6")
    assert refs[0].verse_id == "1John.5.6"


def test_cli_json_primary(tmp_path):
    import subprocess
    import sys

    out = tmp_path / "resolve.json"
    proc = subprocess.run(
        [sys.executable, str(RESOLVER), "John 19:34", "-o", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["primary_verse_id"] == "Jhn.19.34"
    assert doc["track"] == "L"
