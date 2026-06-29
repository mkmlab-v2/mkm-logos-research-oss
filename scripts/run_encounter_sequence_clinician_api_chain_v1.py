#!/usr/bin/env python3
"""Clinician API E2E: intake fusion → encounter_sequence → han turn [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/encounter_sequence_clinician_api_e2e_smoke_v1_latest.json"
DEFAULT_SLUG = "park_geumja"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


def run_chain(*, slug: str = DEFAULT_SLUG) -> dict[str, Any]:
    ptr_path = ROOT / "reports" / f"{slug}_intake_ssot_pointer_v1.json"
    if not ptr_path.is_file():
        return {"schema": "encounter_sequence_clinician_api_e2e_v1", "smoke_ok": False, "reason": "pointer_missing"}
    pointer = json.loads(ptr_path.read_text(encoding="utf-8-sig"))
    paths = pointer.get("paths") if isinstance(pointer.get("paths"), dict) else {}
    intake_rel = str(paths.get("intake") or f"reports/{slug}_intake_fusion_v1.json")
    intake_path = ROOT / intake_rel
    bundle_path = ROOT / str(paths.get("bundle_json") or f"reports/{slug}_patient_care_bundle_latest.json")
    seq_path = ROOT / "reports" / f"{slug}_encounter_sequence_v1.json"

    fusion = _run(
        [
            PY,
            str(ROOT / "scripts/build_patient_intake_fusion_draft_v1.py"),
            "--intake-json",
            str(intake_path),
            "--bundle-out",
            str(bundle_path),
            "--myeongni-out",
            str(ROOT / "reports" / f"{slug}_myeongni_full_latest.json"),
            "--rationale-out",
            str(ROOT / "reports" / f"{slug}_intake_fusion_rationale_latest.json"),
            "--with-encounter-sequence",
            "--encounter-sequence-out",
            str(seq_path),
            "--skip-intake-json-schema",
        ]
    )
    if fusion.returncode != 0:
        return {
            "schema": "encounter_sequence_clinician_api_e2e_v1",
            "smoke_ok": False,
            "reason": "fusion_failed",
            "stderr": (fusion.stderr or "")[-500:],
        }

    bundle = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
    prov = bundle.get("provenance") if isinstance(bundle.get("provenance"), dict) else {}
    seq_id = str(prov.get("encounter_sequence_id") or "")
    has_seq_pointer = bool(seq_id and seq_path.is_file())

    if has_seq_pointer:
        import importlib.util

        ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
        patch_path = ROOT / "scripts/patch_patient_care_bundle_encounter_sequence_ref_v1.py"
        spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            seq_doc = json.loads(seq_path.read_text(encoding="utf-8-sig"))
            existing = {
                str((r.get("encounter") or {}).get("sequence_id") or "")
                for r in mod.iter_ledger_records(ROOT)
            }
            if seq_id not in existing:
                daily = mod.append_encounter_sequence_line(ROOT, seq_doc)
            else:
                base = ROOT / "data/clinic"
                daily = next(iter(sorted(base.glob("encounter_sequence_v1_*.jsonl"))), base / "encounter_sequence_v1.sample.jsonl")
            spec2 = importlib.util.spec_from_file_location("patch_ref", patch_path)
            if spec2 and spec2.loader:
                patch_mod = importlib.util.module_from_spec(spec2)
                spec2.loader.exec_module(patch_mod)
                patched = patch_mod.patch_bundle(
                    bundle,
                    encounter_ref=str((seq_doc.get("encounter") or {}).get("ref_token") or ""),
                    encounter_sequence_id=seq_id,
                    encounter_sequence_ledger_ref=str(daily.relative_to(ROOT)).replace("\\", "/"),
                )
                bundle_path.write_text(json.dumps(patched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                bundle = patched

    han = _run(
        [
            PY,
            str(ROOT / "scripts/build_han_physician_clinical_assist_turn_v1.py"),
            "--slug",
            slug,
            "--validate-schema",
        ]
    )
    if han.returncode != 0:
        return {
            "schema": "encounter_sequence_clinician_api_e2e_v1",
            "smoke_ok": False,
            "reason": "han_turn_failed",
            "stderr": (han.stderr or "")[-500:],
        }

    turn_path = ROOT / "reports" / f"{slug}_han_physician_assist_turn_v1.json"
    turn = json.loads(turn_path.read_text(encoding="utf-8-sig"))
    l0 = (turn.get("layers") or {}).get("L0_clinical_safety") or {}
    l0_layer_ok = isinstance(l0, dict) and "red_flags_ko" in l0

    smoke_ok = has_seq_pointer and l0_layer_ok
    return {
        "schema": "encounter_sequence_clinician_api_e2e_v1",
        "generated_at_utc": _utc(),
        "smoke_ok": smoke_ok,
        "slug": slug,
        "ref_token": pointer.get("ref_token"),
        "encounter_sequence_id": seq_id,
        "sequence_path": str(seq_path).replace("\\", "/"),
        "bundle_path": str(bundle_path).replace("\\", "/"),
        "han_turn_path": str(turn_path).replace("\\", "/"),
        "l0_layer_present": l0_layer_ok,
        "l0_router_triggered": l0.get("l0_router_triggered"),
        "rail": "Track B",
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slug", default=DEFAULT_SLUG)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = run_chain(slug=args.slug)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("smoke_ok"), "slug": doc.get("slug")}))
    return 0 if doc.get("smoke_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
