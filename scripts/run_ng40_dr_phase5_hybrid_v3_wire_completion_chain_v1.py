#!/usr/bin/env python3
"""[HYPO] DR Phase 5 — hybrid router v3 SSOT wire + spec sync.

research_only · send_gate HOLD · never --apply-active.
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
PY = sys.executable
OUT = ROOT / "reports/ng40_dr_phase5_hybrid_v3_wire_completion_chain_v1_latest.json"
WIRE_SPIKE = ROOT / "reports/compression_hybrid_router_v3_wire_spike_v1_latest.json"
SPEC = ROOT / "docs/final/artifacts/compression_hybrid_router_spec_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-800:],
    }


def _load(rel: str) -> dict[str, Any] | None:
    p = ROOT / rel.replace("/", "\\")
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-v3-ablation", action="store_true")
    ap.add_argument("--skip-wire-spike", action="store_true")
    ap.add_argument("--skip-spec-sync", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_v3_ablation:
        steps.append(
            _run(
                "conditional_fusion_v3",
                [
                    PY,
                    "scripts/run_compression_conditional_fusion_ablation_v3_ssot_guard_codec_rerun_v1.py",
                    "--holdout-frac",
                    "0.2",
                ],
            )
        )

    if not args.skip_wire_spike:
        steps.append(
            _run("hybrid_router_v3_wire", [PY, "scripts/run_compression_hybrid_router_v3_wire_spike_v1.py"])
        )

    if not args.skip_spec_sync:
        steps.append(
            _run(
                "sync_hybrid_router_spec",
                [
                    PY,
                    "scripts/sync_compression_hybrid_router_spec_from_spike_v1.py",
                    "--spike",
                    str(WIRE_SPIKE.relative_to(ROOT)).replace("\\", "/"),
                ],
            )
        )

    if not args.skip_pytest:
        steps.append(
            _run(
                "pytest_hybrid_v3_wire",
                [PY, "-m", "pytest", "tests/test_compression_hybrid_router_v3_wire_v1.py", "-q"],
            )
        )

    failed = [s for s in steps if s["exit_code"] != 0]
    wire = _load("reports/compression_hybrid_router_v3_wire_spike_v1_latest.json")
    spec = _load("docs/final/artifacts/compression_hybrid_router_spec_v1.json")
    phase4 = _load("reports/ng40_dr_phase4_conditional_fusion_completion_chain_v1_latest.json")

    g40_binding = next(
        (b for b in (spec or {}).get("corpus_bindings") or [] if b.get("corpus_id") == "golden40_internal"),
        {},
    )
    g40_corp = next((c for c in (wire or {}).get("corpora") or [] if c.get("corpus_id") == "golden40_internal"), {})

    doc: dict[str, Any] = {
        "schema": "ng40_dr_phase5_hybrid_v3_wire_completion_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_active_write": False,
        "apply_forbidden": True,
        "chain_ok": len(failed) == 0,
        "failed_steps": [s["id"] for s in failed],
        "steps": steps,
        "hybrid_v3_wire": {
            "golden40_backend": g40_binding.get("backend"),
            "golden40_j_proxy": ((g40_corp.get("result") or {}).get("raw") or {}).get("mean_jaccard_proxy"),
            "hybrid_raw_j": ((wire or {}).get("comparison") or {})
            .get("hybrid_routed", {})
            .get("raw", {})
            .get("mean_jaccard_proxy"),
            "wire_delta_min_j_pp": (wire or {}).get("golden40_wire_delta", {}).get("min_jaccard_delta_pp"),
            "spec_digest": (spec or {}).get("sync_from_spike", {}).get("binding_table_digest"),
        },
        "phase4_pointer": {
            "v3_conditional_saving": (phase4 or {})
            .get("conditional_fusion_stack", {})
            .get("v3_codec_saving"),
            "v3_min_j": (phase4 or {}).get("conditional_fusion_stack", {}).get("v3_codec_min_j"),
        },
        "headline_ko": (
            "golden40_internal: llmlingua2 regress → mkm_conditional_fusion_v3_ssot_guard "
            f"(J~{((g40_corp.get('result') or {}).get('raw') or {}).get('mean_jaccard_proxy', 0):.3f})"
        ),
        "pointers": {
            "wire_spike": "reports/compression_hybrid_router_v3_wire_spike_v1_latest.json",
            "hybrid_spec": "docs/final/artifacts/compression_hybrid_router_spec_v1.json",
            "v3_ablation": "reports/compression_conditional_fusion_ablation_v3_ssot_guard_v1_latest.json",
            "phase4_chain": "reports/ng40_dr_phase4_conditional_fusion_completion_chain_v1_latest.json",
        },
        "reproducible_command": "py scripts/run_ng40_dr_phase5_hybrid_v3_wire_completion_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": doc["chain_ok"], "failed_steps": doc["failed_steps"]}, ensure_ascii=False))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
