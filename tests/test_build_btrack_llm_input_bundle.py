"""Regression: B-track LLM input bundle includes minority monthly slot and version 1.1.0."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_btrack_llm_input_bundle_outputs_v11_schema(tmp_path: Path) -> None:
    myeongni = tmp_path / "myeongni.json"
    sasang = tmp_path / "sasang.json"
    logos = tmp_path / "logos.json"
    fusion = tmp_path / "fusion.json"
    minority = tmp_path / "minority_monthly.json"
    out = tmp_path / "bundle.json"
    for p, label in (
        (myeongni, "m"),
        (sasang, "s"),
        (logos, "l"),
        (fusion, "f"),
        (minority, "mm"),
    ):
        p.write_text(json.dumps({"slot": label}), encoding="utf-8")

    cmd = [
        "py",
        str(ROOT / "scripts" / "build_btrack_llm_input_bundle.py"),
        "--myeongni",
        str(myeongni),
        "--sasang",
        str(sasang),
        "--logos",
        str(logos),
        "--fusion",
        str(fusion),
        "--minority-monthly",
        str(minority),
        "--output",
        str(out),
    ]
    cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    assert cp.returncode == 0, cp.stderr + cp.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "1.1.0"
    assert data["artifacts"]["myeongni_independent_lens"]["slot"] == "m"
    assert data["artifacts"]["independent_lens_shadow_minority_monthly"]["slot"] == "mm"
    assert "independent_lens_shadow_minority_monthly" in data["artifact_paths"]
    assert str(minority.resolve()) in data["artifact_paths"]["independent_lens_shadow_minority_monthly"]
