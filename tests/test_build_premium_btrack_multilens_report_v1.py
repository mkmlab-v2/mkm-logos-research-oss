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


def test_build_premium_best_effort_uses_fixture_json(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    art = tmp_path / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "myeongni_independent_lens_latest.json").write_text(
        json.dumps(
            {
                "schema": "myeongni_independent_lens_v0",
                "version": "0.1.0",
                "lens_id": "myeongni",
                "ts_utc": "2026-01-01T00:00:00Z",
                "scores": {"direction_score": 0.1, "confidence": 0.5},
                "myeongri_stream_outputs": {"state_id": 1, "rationale": "fixture"},
                "provenance": {"source": "test"},
                "note": "fixture",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "sasang_independent_lens_latest.json").write_text(
        json.dumps(
            {
                "schema": "sasang_independent_lens_v0",
                "version": "0.2.0",
                "lens_id": "sasang",
                "ts_utc": "2026-01-01T00:00:00Z",
                "scores": {"direction_score": 0.2, "confidence": 0.6},
                "sasang_stream_outputs": {
                    "regime_hypothesis": "x",
                    "mapping_target": "y",
                    "rationale": "fixture",
                },
                "provenance": {"source": "test"},
                "note": "fixture",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "logos_independent_lens_latest.json").write_text(
        json.dumps(
            {
                "schema": "logos_independent_lens_v0",
                "version": "0.2.0",
                "lens_id": "logos",
                "ts_utc": "2026-01-01T00:00:00Z",
                "scores": {"direction_score": -0.1, "confidence": 0.4},
                "evidence_refs": [],
                "provenance": {"source": "test"},
                "note": "fixture",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    out = tmp_path / "out"
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--mode",
        "best-effort",
        "--myeongni-json",
        str(art / "myeongni_independent_lens_latest.json"),
        "--sasang-json",
        str(art / "sasang_independent_lens_latest.json"),
        "--logos-json",
        str(art / "logos_independent_lens_latest.json"),
        "--out-dir",
        str(out),
        "--example-path",
        str(EXAMPLE),
    ]
    r = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout + r.stderr

    md = out / "premium_btrack_multilens_report_v1.md"
    text = md.read_text(encoding="utf-8")
    assert "Disk engine snapshot" in text
    assert "Numeric alignment" in text
    assert "v0.5 best-effort disk" in text

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    instance = json.loads((out / "premium_btrack_multilens_report_v1.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)

    caveats = instance.get("coordinator", {}).get("caveats", [])
    assert caveats and "Fact-Lock trace (best-effort disk ingest)" in caveats[0]
    owners = {s.get("owner"): s for s in instance.get("pipeline", []) if isinstance(s, dict)}
    assert "lens_myeongni_premium_slice_v0.md" in str(owners.get("myeongni", {}).get("outputs"))
    assert "premium_multilens_synthesis_v0.md" in str(owners.get("coordinator", {}).get("outputs"))
