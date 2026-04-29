#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze global atom submission artifacts into timestamped folder.")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_submission_freeze_latest.json")
    args = ap.parse_args()

    artifacts = [
        resolve("docs/final/artifacts/global_atom_network_academic_onepager_latest.json"),
        resolve("docs/final/artifacts/global_atom_network_submission_abstracts_latest.json"),
        resolve("docs/final/artifacts/global_atom_kdd_submission_template_latest.json"),
        resolve("docs/final/artifacts/global_atom_submission_bundle_latest.json"),
        resolve("docs/final/artifacts/global_atom_network_core100_phase_transition_report_latest.json"),
        resolve("docs/final/artifacts/multi_symbol_gate_summary_latest.json"),
        resolve("docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json"),
    ]

    freeze_stamp = stamp()
    freeze_dir = resolve(f"docs/final/artifacts/freeze/global_atom_submission_{freeze_stamp}")
    freeze_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    missing: list[str] = []
    for src in artifacts:
        if src.is_file():
            dst = freeze_dir / src.name
            shutil.copy2(src, dst)
            copied.append(str(dst))
        else:
            missing.append(str(src))

    outp = resolve(args.output_json)
    out = {
        "schema": "global_atom_submission_freeze_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "freeze_stamp": freeze_stamp,
        "freeze_dir": str(freeze_dir),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "copied_files": copied,
        "missing_files": missing,
    }
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

