#!/usr/bin/env python3
"""Build machine-readable audit snapshot for MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1 (G0-G11).

G12 (live trading / external billing) remains human-only — never auto-pass.

Writes: docs/final/artifacts/mkm_promotion_gate_evidence_bundle_v1.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "mkm_promotion_gate_evidence_bundle_v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _exists(root: Path, rel: str) -> bool:
    return (root / rel.replace("/", os.sep)).is_file()


def run_verify_p0(root: Path) -> tuple[int, str]:
    ps1 = root / "scripts" / "verify_p0_constitution_gate_paths.ps1"
    if not ps1.is_file():
        return -1, "verify_p0_constitution_gate_paths.ps1 missing"
    # Prefer pwsh (Linux CI + Windows); fallback powershell on Windows.
    for shell, args in (
        ("pwsh", ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-WorkspaceRoot", str(root)]),
        ("powershell", ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-WorkspaceRoot", str(root)]),
    ):
        try:
            p = subprocess.run(
                args,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=600,
            )
        except FileNotFoundError:
            continue
        tail = (p.stdout or "")[-4000:] + (p.stderr or "")[-2000:]
        return p.returncode, tail.strip()
    return -1, "no pwsh/powershell available to run P0 gate"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path.cwd())
    ap.add_argument("--dry-run", action="store_true", help="Print bundle dict only; do not write file")
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()

    out_path = root / "docs" / "final" / "artifacts" / "mkm_promotion_gate_evidence_bundle_v1.json"

    gates: dict[str, dict] = {}

    code_g0, tail_g0 = run_verify_p0(root)
    gates["G0"] = {
        "status": "pass" if code_g0 == 0 else "fail",
        "exit_code": code_g0,
        "artifact": "scripts/verify_p0_constitution_gate_paths.ps1",
        "log_tail": tail_g0[:3500] if tail_g0 else "",
    }

    gates["G1"] = {
        "status": "pass" if _exists(root, ".github/workflows/dual-regime-integrity.yml") else "fail",
        "evidence_path": ".github/workflows/dual-regime-integrity.yml",
        "note": "CI success requires GitHub Actions run record; local checks path only.",
    }

    playbook = "docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md"
    gates["G2"] = {
        "status": "policy",
        "evidence_path": playbook,
        "note": "B→A promotion claims require §9 checklist + measured SLA; not auto-verified here.",
    }

    g3_paths = [
        "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        "docs/final/artifacts/general_compression_kpi_gate_v2.json",
    ]
    g3_ok = all(_exists(root, p) for p in g3_paths)
    gates["G3"] = {
        "status": "pass" if g3_ok else "fail",
        "paths_checked": g3_paths,
    }

    g4_paths = [
        "docs/final/artifacts/track_a_conversational_cost_simulation_latest.json",
    ]
    gates["G4"] = {
        "status": "pass" if all(_exists(root, p) for p in g4_paths) else "optional_missing",
        "paths_checked": g4_paths,
        "note": "Regenerate: py scripts/run_track_a_conversational_cost_simulation.py when pilot needs fresh sim.",
    }

    g5_paths = [
        "docs/final/artifacts/track_a_shadow_corpus_eval_latest.json",
    ]
    gates["G5"] = {
        "status": "pass" if all(_exists(root, p) for p in g5_paths) else "optional_missing",
        "paths_checked": g5_paths,
        "note": "Regenerate: py scripts/run_track_a_shadow_corpus_eval.py",
    }

    g6_paths = ["docs/final/artifacts/track_a_metering_band_gate_latest.json"]
    gates["G6"] = {
        "status": "pass" if all(_exists(root, p) for p in g6_paths) else "optional_missing",
        "paths_checked": g6_paths,
        "note": "Regenerate after metering chain when pilot enables band gate artifact.",
    }

    g7_ok = _exists(root, "docs/final/openapi_token_compression_stub_v1.yaml") and _exists(
        root, "scripts/compression_token_api_stub.py"
    )
    gates["G7"] = {
        "status": "pass" if g7_ok else "fail",
        "paths_checked": [
            "docs/final/openapi_token_compression_stub_v1.yaml",
            "scripts/compression_token_api_stub.py",
            "tests/test_compression_token_api_stub.py",
        ],
        "note": "Full regression: pytest tests/test_compression_token_api_stub.py",
    }

    gates["G8"] = {
        "status": "pass" if _exists(root, "scripts/core/sovereign_jsonl.py") else "fail",
        "evidence_path": "scripts/core/sovereign_jsonl.py",
    }

    gates["G9"] = {
        "status": "pass" if _exists(root, "projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.sh") else "fail",
        "evidence_path": "projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.sh",
        "note": "dual-regime runs this harness; local exit 0 required for parity.",
    }

    gates["G10"] = {
        "status": "pass" if _exists(root, "scripts/run_fact_lock_bundle.ps1") else "fail",
        "evidence_path": "scripts/run_fact_lock_bundle.ps1",
        "note": "Run locally for full bundle; not executed inside this builder.",
    }

    gates["G11"] = {
        "status": "pass" if _exists(root, "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md") else "fail",
        "evidence_path": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
    }

    gates["G12"] = {
        "status": "human_required",
        "note": "Live trading / external billing requires explicit commander GO — never automated.",
    }

    bundle = {
        "schema": SCHEMA,
        "version": 1,
        "generated_at_utc": _utc_now_iso(),
        "workspace_root_hint": str(root),
        "gates": gates,
    }

    if args.dry_run:
        print(json.dumps(bundle, indent=2, ensure_ascii=False))
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")

    hard_fail = code_g0 != 0 or gates["G1"]["status"] != "pass" or gates["G3"]["status"] != "pass"
    hard_fail = hard_fail or gates["G7"]["status"] != "pass" or gates["G8"]["status"] != "pass"
    hard_fail = hard_fail or gates["G9"]["status"] != "pass" or gates["G10"]["status"] != "pass"
    hard_fail = hard_fail or gates["G11"]["status"] != "pass"
    if hard_fail:
        print("FAIL: one or more hard gates did not pass (see gates.*.status).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
