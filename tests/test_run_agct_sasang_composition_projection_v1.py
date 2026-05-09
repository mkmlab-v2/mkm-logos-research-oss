from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_agct_sasang_composition_projection_v1.py"


def test_agct_sasang_composition_projection_cli(tmp_path: Path) -> None:
    genotype = tmp_path / "genotype_long.csv"
    genotype.write_text(
        "\n".join(
            [
                "sample_id,rsid,genotype",
                "s1,rs1,AA",
                "s1,rs2,AT",
                "s2,rs1,CC",
                "s2,rs2,CG",
                "s3,rs1,GG",
                "s3,rs2,GT",
                "s4,rs1,TT",
                "s4,rs2,TA",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    cohort = tmp_path / "cohort.csv"
    cohort.write_text(
        "\n".join(
            [
                "sample_id,risk_score",
                "s1,0.10",
                "s2,0.40",
                "s3,0.80",
                "s4,0.20",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "projection.json"

    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--genotype-csv",
            str(genotype),
            "--cohort-csv",
            str(cohort),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == "agct_sasang_composition_projection_v1"
    assert data["track"] == "B_TRACK"
    assert data["summary"]["samples_used"] == 4
    assert set(data["summary"]["axis_top_counts"].keys()) == {"TY", "SY", "TE", "SE"}
    assert len(data["sample_projection_preview"]) >= 1
