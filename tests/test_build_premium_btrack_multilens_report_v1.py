from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_premium_btrack_multilens_report_v1.py"
EXAMPLE = ROOT / "docs" / "final" / "schemas" / "premium_btrack_multilens_report_v1.example.json"
SCHEMA = ROOT / "docs" / "final" / "schemas" / "premium_btrack_multilens_report_v1.schema.json"


def test_build_premium_v0_writes_md_and_json_validates(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    out = tmp_path / "out"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--out-dir",
        str(out),
        "--example-path",
        str(EXAMPLE),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr

    md = out / "premium_btrack_multilens_report_v1.md"
    js = out / "premium_btrack_multilens_report_v1.json"
    assert md.is_file()
    assert js.is_file()
    text = md.read_text(encoding="utf-8")
    assert "[HYPO]" in text
    assert "not_live_trading" in text

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    instance = json.loads(js.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)

    for lid in ("myeongni", "sasang", "logos"):
        assert (out / f"lens_{lid}_premium_slice_v0.md").is_file()
