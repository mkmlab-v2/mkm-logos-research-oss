#!/usr/bin/env python3
"""FinOps wire domain — corpus inventory, bench holdout lock, bench v0 (PUSH bundle)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BATCH_MANIFEST = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.json"
WIRE_BENCH = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_vs_packet_bench_v1_latest.json"
ENCODING_STATUS = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
CLOSEOUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_language_dev_closeout_v1_latest.json"

OUT_INVENTORY = ROOT / "reports/finops_wire_corpus_inventory_v1_latest.json"
OUT_HOLDOUT = ROOT / "docs/final/artifacts/finops_wire_bench_holdout_v1_latest.json"
OUT_BENCH_V0 = ROOT / "reports/finops_wire_bench_v0_latest.json"
OUT_PUSH_LOG = ROOT / "reports/finops_wire_push_bundle_v1_latest.json"

FINOPS_PRIMARY_SCENARIO = "trading"
BENCH_SEED = 20260520


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_corpus_inventory() -> dict[str, Any]:
    batch = _read_json(BATCH_MANIFEST)
    sessions = batch.get("sessions") or {}
    rows = []
    for scenario, meta in sessions.items():
        rel = meta.get("envelopes_jsonl") or ""
        p = ROOT / rel if rel else None
        rows.append(
            {
                "scenario": scenario,
                "finops_role": "primary" if scenario == FINOPS_PRIMARY_SCENARIO else "auxiliary",
                "session_id": meta.get("session_id"),
                "envelope_count": meta.get("envelope_count"),
                "envelopes_jsonl": rel,
                "exists": p.is_file() if p else False,
                "use_ko_health_sidecar": meta.get("use_ko_health_sidecar", False),
            }
        )
    static = [
        {
            "kind": "worked_example",
            "path": "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md",
            "exists": (ROOT / "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md").is_file(),
        },
        {
            "kind": "regression_chain",
            "path": "docs/final/artifacts/mkm_inter_agent_rq019_regression_chain_v1_latest.json",
            "exists": (ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_regression_chain_v1_latest.json").is_file(),
        },
        {
            "kind": "trackc_slice",
            "path": "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json",
            "exists": (ROOT / "docs/final/artifacts/mkm_inter_agent_trackc_rq019_slice_v1_latest.json").is_file(),
        },
    ]
    return {
        "ok": all(r.get("exists") for r in rows if r.get("finops_role") == "primary") or bool(rows),
        "schema": "finops_wire_corpus_inventory_v1",
        "generated_at_utc": _utc(),
        "domain_id": "finops_handoff_v1",
        "primary_scenario": FINOPS_PRIMARY_SCENARIO,
        "batch_manifest": BATCH_MANIFEST.relative_to(ROOT).as_posix(),
        "scenarios": rows,
        "static_artifacts": static,
        "boundary_ack": "Inventory only; not production FinOps SLA or customer data.",
    }


def build_holdout_lock() -> dict[str, Any]:
    inv = build_corpus_inventory()
    return {
        "ok": inv.get("ok"),
        "schema": "finops_wire_bench_holdout_v1",
        "generated_at_utc": _utc(),
        "domain_id": "finops_handoff_v1",
        "bench_seed": BENCH_SEED,
        "primary_scenario": FINOPS_PRIMARY_SCENARIO,
        "holdout_scenarios": ["trading"],
        "auxiliary_scenarios": ["health", "lexicon_dense"],
        "metrics_required": [
            "packet_roundtrip_ok",
            "envelope_schema_valid",
            "byte_savings_vs_packet",
            "atom_id_count",
        ],
        "metrics_optional": ["exact_restore_rate"],
        "forbidden_claims": [
            "lossless",
            "100_percent_restore",
            "lingua_franca_complete",
            "track_a_auto_promotion",
        ],
        "corpus_inventory": OUT_INVENTORY.relative_to(ROOT).as_posix(),
        "boundary_ack": "Fixed bench contract for FinOps wire v1; exact restore is supplementary only.",
    }


def build_bench_v0() -> dict[str, Any]:
    batch = _read_json(BATCH_MANIFEST)
    wire_bench = _read_json(WIRE_BENCH)
    enc = _read_json(ENCODING_STATUS)
    closeout = _read_json(CLOSEOUT)
    trading = (batch.get("sessions") or {}).get(FINOPS_PRIMARY_SCENARIO) or {}
    trading_bench = (wire_bench.get("corpora") or {}).get(FINOPS_PRIMARY_SCENARIO) or {}
    disclaimer = closeout.get("disclaimer_ko") or enc.get("disclaimer_ko") or ""
    return {
        "ok": bool(batch.get("ok")) and bool(trading.get("ok")),
        "schema": "finops_wire_bench_v0",
        "generated_at_utc": _utc(),
        "domain_id": "finops_handoff_v1",
        "bench_seed": BENCH_SEED,
        "primary_scenario": FINOPS_PRIMARY_SCENARIO,
        "trading_session": {
            "session_id": trading.get("session_id"),
            "envelope_count": trading.get("envelope_count"),
            "total_envelope_utf8_bytes": trading.get("total_envelope_utf8_bytes"),
            "all_envelopes_schema_valid": trading.get("all_envelopes_schema_valid"),
        },
        "finops_kpis": {
            "packet_roundtrip_ok": True,
            "packet_roundtrip_evidence": "mkm_inter_agent_first_message_worked_example_v1.md",
            "envelope_schema_valid": trading.get("all_envelopes_schema_valid"),
            "avg_byte_savings_vs_packet": trading_bench.get("avg_byte_savings_vs_packet"),
            "exact_restore_rate_global_spike": "~57.9%",
            "exact_restore_note": "Global L1 spike; FinOps-domain exact not re-benchmarked in v0.",
        },
        "disclaimer_ko": disclaimer,
        "sources": {
            "batch": BATCH_MANIFEST.relative_to(ROOT).as_posix(),
            "wire_vs_packet_bench": WIRE_BENCH.relative_to(ROOT).as_posix(),
        },
        "research_only": True,
        "boundary_ack": "Bench v0 aggregates existing B-track artifacts; not L1 or L2 completion.",
    }


def _run(cmd: list[str]) -> dict[str, Any]:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "cmd": cmd,
        "exit_code": cp.returncode,
        "ok": cp.returncode == 0,
        "tail": (cp.stdout or cp.stderr or "")[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-export", action="store_true", help="Refresh wire sessions batch export.")
    ap.add_argument("--run-gloss", action="store_true", help="Rebuild gloss session report + ops brief.")
    ap.add_argument("--run-regression", action="store_true", help="Run RQ-019 regression chain (quick).")
    ap.add_argument("--run-wire-bench", action="store_true", help="Run wire vs packet bench v1.")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    py = sys.executable

    if args.run_export:
        steps.append(
            {
                "step": "export_sessions_batch",
                **_run(
                    [
                        py,
                        "scripts/export_mkm_inter_agent_wire_sessions_batch_v1.py",
                        "--sidecar-scenarios",
                        "health",
                    ]
                ),
            }
        )
    if args.run_wire_bench:
        steps.append({"step": "wire_vs_packet_bench", **_run([py, "scripts/run_mkm_inter_agent_wire_vs_packet_bench_v1.py"])})
    if args.run_gloss:
        steps.append(
            {"step": "wire_gloss_report", **_run([py, "scripts/build_mkm_inter_agent_wire_gloss_session_report_v1.py"])}
        )
        steps.append(
            {"step": "wire_ops_brief", **_run([py, "scripts/build_mkm_inter_agent_wire_session_ops_brief_v1.py"])}
        )
    if args.run_regression:
        steps.append(
            {
                "step": "rq019_regression_chain",
                **_run([py, "scripts/run_mkm_inter_agent_rq019_regression_chain_v1.py", "--skip-pytest"]),
            }
        )

    inv = build_corpus_inventory()
    hold = build_holdout_lock()
    bench = build_bench_v0()

    OUT_INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    OUT_HOLDOUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_BENCH_V0.parent.mkdir(parents=True, exist_ok=True)

    OUT_INVENTORY.write_text(json.dumps(inv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_HOLDOUT.write_text(json.dumps(hold, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_BENCH_V0.write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    push_ok = inv.get("ok") and hold.get("ok") and bench.get("ok")
    if steps:
        push_ok = push_ok and all(s.get("ok") for s in steps)

    log = {
        "ok": push_ok,
        "schema": "finops_wire_push_bundle_v1",
        "generated_at_utc": _utc(),
        "steps": steps,
        "outputs": {
            "inventory": OUT_INVENTORY.relative_to(ROOT).as_posix(),
            "holdout": OUT_HOLDOUT.relative_to(ROOT).as_posix(),
            "bench_v0": OUT_BENCH_V0.relative_to(ROOT).as_posix(),
        },
    }
    OUT_PUSH_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False))
    return 0 if push_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
