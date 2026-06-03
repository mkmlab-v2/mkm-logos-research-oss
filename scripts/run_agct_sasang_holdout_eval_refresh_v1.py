from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Refresh AGCT Sasang holdout evaluation using full cohort defaults.")
    ap.add_argument(
        "--cohort-csv",
        type=Path,
        default=root / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv",
    )
    ap.add_argument(
        "--genotype-csv",
        type=Path,
        default=root / "tmp" / "bio_genotype_long_v1.csv",
    )
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_holdout_eval_v1_latest.json",
    )
    ns = ap.parse_args()

    missing = [p for p in (ns.cohort_csv, ns.genotype_csv) if not p.is_file()]
    if missing:
        print(
            "SKIP: AGCT Sasang holdout refresh — cohort/genotype CSV not on disk "
            f"(missing={[str(p) for p in missing]}). Restore via "
            "docs/final/artifacts/bio_dna_real_cohort_restore_pointer_v1.json",
            file=sys.stderr,
        )
        return 0

    cmd = [
        sys.executable,
        str(root / "scripts" / "run_agct_sasang_holdout_eval_v1.py"),
        "--cohort-csv",
        str(ns.cohort_csv),
        "--genotype-csv",
        str(ns.genotype_csv),
        "--holdout-ratio",
        str(ns.holdout_ratio),
        "--seed",
        str(ns.seed),
        "--permutation-repeats",
        str(ns.permutation_repeats),
        "--output-json",
        str(ns.output_json),
    ]
    proc = subprocess.run(cmd, cwd=str(root), check=False)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
