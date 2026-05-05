from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_agct_sasang_hypothesis_sweep_v1.py"


def test_agct_sasang_hypothesis_sweep_cli(tmp_path: Path) -> None:
    cohort = tmp_path / "cohort.csv"
    cohort.write_text(
        "\n".join(
            [
                "sample_id,expected_parent,risk_score",
                "s1,TY,0.10",
                "s2,SY,0.90",
                "s3,TE,0.30",
                "s4,SE,0.70",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    genotype = tmp_path / "genotype_long.csv"
    genotype.write_text(
        "\n".join(
            [
                "sample_id,rsid,genotype",
                "s1,rs1,AA",
                "s1,rs2,AA",
                "s2,rs1,CC",
                "s2,rs2,CC",
                "s3,rs1,GG",
                "s3,rs2,GG",
                "s4,rs1,TT",
                "s4,rs2,TT",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "agct_sweep.json"
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--cohort-csv",
            str(cohort),
            "--genotype-csv",
            str(genotype),
            "--permutation-repeats",
            "100",
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
    assert data["schema"] == "agct_sasang_hypothesis_sweep_v1"
    assert data["track"] == "B_TRACK"
    assert data["summary"]["paired_samples"] == 4
    assert data["summary"]["n_hypotheses"] == 24
    assert len(data["top_hypotheses"]) >= 1
    assert data["summary"]["best_mapping"]["A"] in {"TY", "SY", "TE", "SE"}
