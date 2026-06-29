#!/usr/bin/env python3
"""Build clinic LOI Figma reverse-sync pack (Layer B opt-in).

Requires clinic landing gate PASS. No Figma API call — disk pack for human import.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/clinic_loi_figma_reverse_sync_pack_v1_latest.json"
GATE = ROOT / "reports/clinic_km_mmp_landing_gate_v1_latest.json"
GATE_SCRIPT = ROOT / "scripts/check_clinic_km_mmp_landing_gate_v1.py"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    proc = subprocess.run([sys.executable, str(GATE_SCRIPT)], cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode

    gate = json.loads(GATE.read_text(encoding="utf-8-sig")) if GATE.is_file() else {}
    if gate.get("decision") != "PASS":
        print("clinic gate not PASS", file=sys.stderr)
        return 1

    core_artifacts = {
        "dtcg_tokens": "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json",
        "preview_html": "reports/clinic_km_mmp_loi_preview_v1.html",
        "copy_md": "reports/clinic_km_mmp_landing_copy_v1.md",
        "reference_seed": "reports/design_reference_seed_clinic_loi_v1.example.json",
        "glass_ab_commander": "reports/trust_composition_glass_blur_commander_visual_v1_latest.json",
        "figma_token_map": "docs/final/artifacts/clinic_loi_figma_token_map_v1.json",
    }
    optional_artifacts = {
        "tokens_studio_export": "reports/clinic_loi_figma_tokens_studio_export_v1.json",
        "figma_reference_screenshot": "reports/clinic_loi_figma_reference_screenshot_v1.png",
    }
    for rel in core_artifacts.values():
        if not (ROOT / rel.replace("/", "\\")).is_file():
            print(f"missing artifact: {rel}", file=sys.stderr)
            return 1

    artifacts = dict(core_artifacts)
    for key, rel in optional_artifacts.items():
        if (ROOT / rel.replace("/", "\\")).is_file():
            artifacts[key] = rel

    doc: dict[str, Any] = {
        "schema": "clinic_loi_figma_reverse_sync_pack_v1",
        "generated_at_utc": _utc(),
        "layer": "B_opt_in",
        "send_gate": "HOLD",
        "lane_status": "frozen_deferred",
        "ready_for_external_send": False,
        "surface_default": "flat_baseline",
        "glass_note_ko": "glass/blur는 commander A/B에서 clinic LOI 기본 적용 금지 — flat만 Figma 역이관 1차",
        "figma_import_hints": [
            "Tokens Studio: import DTCG JSON (primitive→semantic→component)",
            "Frame: open preview HTML as visual reference — do not flatten hex outside tokens",
            "Copy: wedge + HOLD card from copy_md — forbidden list in gate SSOT",
        ],
        "artifacts": artifacts,
        "reproduce": "py scripts/build_clinic_loi_figma_reverse_sync_pack_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
