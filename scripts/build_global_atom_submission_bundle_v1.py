#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def file_item(path: Path) -> dict[str, Any]:
    exists = path.is_file()
    generated = None
    if exists:
        try:
            generated = load(path).get("generated_at_utc")
        except Exception:
            generated = None
    return {"path": str(path), "exists": exists, "generated_at_utc": generated}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build global atom submission bundle manifest.")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_submission_bundle_latest.json")
    args = ap.parse_args()

    outp = resolve(args.output_json)
    artifacts = {
        "onepager": resolve("docs/final/artifacts/global_atom_network_academic_onepager_latest.json"),
        "abstracts": resolve("docs/final/artifacts/global_atom_network_submission_abstracts_latest.json"),
        "kdd_template": resolve("docs/final/artifacts/global_atom_kdd_submission_template_latest.json"),
        "phase_report": resolve("docs/final/artifacts/global_atom_network_core100_phase_transition_report_latest.json"),
        "full_canon_batch_report": resolve("docs/final/artifacts/global_atom_full_canon_batch_report_latest.json"),
        "full_canon_consolidated_manifest": resolve("docs/final/artifacts/global_atom_full_canon/global_atom_full_canon_consolidated_manifest_latest.json"),
        "gate_summary": resolve("docs/final/artifacts/multi_symbol_gate_summary_latest.json"),
        "counterfactual_comparison": resolve("docs/final/artifacts/multi_symbol_counterfactual_comparison_latest.json"),
    }
    packet = {k: file_item(v) for k, v in artifacts.items()}
    ready = all(item["exists"] for item in packet.values())
    out = {
        "schema": "global_atom_submission_bundle_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "ready": ready,
        "artifact_packet": packet,
        "note": "Bundle manifest for KDD/AAAI form fill and supplementary attachment.",
    }
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

