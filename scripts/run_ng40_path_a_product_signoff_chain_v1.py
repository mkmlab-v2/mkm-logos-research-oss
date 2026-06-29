#!/usr/bin/env python3
"""[HYPO] Step 2/2: Path A product — spine byte_exact + sidecar preview sign-off chain."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "experiments/nextgen_clean_slate_cpu_v1/NG40_PATH_A_PRODUCT_SPEC_V1.json"
OUT_MANIFEST = ROOT / "reports/ng40_path_a_product_signoff_chain_v1_latest.json"
CANONICAL_KEEP = 0.88


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"script": script, "args": extra or [], "exit_code": int(cp.returncode), "parsed": parsed}


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-auto-ops", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(
        _run(
            "scripts/run_nextgen_hybrid_b2b_design_bundle_v1.py",
            ["--keep-ratios", "0.75", "0.82", "0.88"],
        )
    )
    steps.append(_run("scripts/run_nextgen_guarded_b2b_decode_contract_v1.py"))
    steps.append(
        _run(
            "scripts/run_nextgen_hybrid_spine_logos_stack_v1.py",
            ["--keep-ratio", str(CANONICAL_KEEP)],
        )
    )
    steps.append(_run("scripts/run_nextgen_hybrid_spine_trilane_stack_v1.py"))
    steps.append(
        _run(
            "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
            [
                "--human-approve-research",
                "--reviewer",
                "commander",
                "--note",
                f"Path A product spine+sidecar keep={CANONICAL_KEEP} research signoff",
            ],
        )
    )
    if not args.skip_auto_ops:
        steps.append(_run("scripts/run_ng40_recommended_auto_ops_v1.py"))

    bundle = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_b2b_design_bundle_v1_latest.json"
    )
    guarded = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_guarded_b2b_decode_contract_v1_latest.json"
    )
    hybrid = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_logos_stack_v1_latest.json"
    )
    trilane = _load(
        "experiments/nextgen_clean_slate_cpu_v1/results/ng40_hybrid_spine_trilane_stack_v1_latest.json"
    )
    packet = _load("reports/btrack_nextgen_promotion_candidate_packet_v1_latest.json")
    promo_step = next(
        (
            s
            for s in steps
            if s.get("script") == "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py"
        ),
        None,
    )
    promo_parsed = (promo_step or {}).get("parsed") or {}

    contract_met = bool((bundle or {}).get("contract_met"))
    if bundle and not contract_met:
        contract_met = bool((bundle.get("guarded_b2b") or {}).get("contract_met"))
    if guarded and not contract_met:
        g_agg = guarded.get("aggregate") or {}
        contract_met = bool(g_agg.get("contract_met"))

    manifest = {
        "schema": "ng40_path_a_product_signoff_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "spec_pointer": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "canonical_keep_ratio": CANONICAL_KEEP,
        "product_gates": {
            "byte_exact_subset_parity": (hybrid or {}).get("aggregate", {}).get(
                "byte_exact_subset_parity"
            ),
            "guarded_contract_met": bool(
                ((guarded or {}).get("aggregate") or {}).get("contract_met")
                or (guarded or {}).get("contract_met")
                or ((bundle or {}).get("guarded_b2b") or {}).get("contract_met")
            ),
            "trilane_byte_exact": (trilane or {}).get("aggregate", {}).get(
                "byte_exact_subset_parity"
            ),
            "product_ready": contract_met
            and float((hybrid or {}).get("aggregate", {}).get("byte_exact_subset_parity") or 0)
            >= 1.0,
        },
        "promotion_packet": {
            "export_prep_ready": promo_parsed.get("export_prep_ready")
            if promo_parsed.get("export_prep_ready") is not None
            else (packet or {}).get("export_prep_ready"),
            "path_a_product_policy": (packet or {}).get("path_a_product_policy"),
            "apply_forbidden": promo_parsed.get("apply_forbidden")
            if promo_parsed.get("apply_forbidden") is not None
            else (packet or {}).get("apply_forbidden"),
            "note_ko": "auto_ops가 패킷을 덮어쓸 수 있음 — promotion 스텝 parsed 우선",
        },
        "steps": steps,
        "forbidden": ["--apply-active for hybrid product lane"],
    }
    OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(OUT_MANIFEST),
                "product_ready": manifest["product_gates"]["product_ready"],
                "export_prep_ready": manifest["promotion_packet"]["export_prep_ready"],
            },
            ensure_ascii=False,
        )
    )
    hard = any(s["exit_code"] != 0 for s in steps[:5])
    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
