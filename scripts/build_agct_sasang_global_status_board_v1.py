#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build AGCT+Sasang+Global unified status board.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--baseline-json",
        type=Path,
        default=root / "reports" / "agct_sigma_locked_baseline_chain_v1_latest.json",
    )
    ap.add_argument(
        "--h2h-json",
        type=Path,
        default=root / "reports" / "agct_sigma_head_to_head_3batch_v1_latest.json",
    )
    ap.add_argument(
        "--reasoning-json",
        type=Path,
        default=root / "reports" / "sasang_dna_market_reasoning_v1_latest.json",
    )
    ap.add_argument(
        "--coordinator-json",
        type=Path,
        default=root / "reports" / "mkm_global_coordinator_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_global_status_board_v1_latest.json",
    )
    ap.add_argument(
        "--output-md",
        type=Path,
        default=root / "reports" / "agct_sasang_global_status_board_v1_latest.md",
    )
    ns = ap.parse_args()

    baseline = _read_json(ns.baseline_json)
    h2h = _read_json(ns.h2h_json)
    reasoning = _read_json(ns.reasoning_json)
    coordinator = _read_json(ns.coordinator_json)

    baseline_summary = baseline.get("summary", {})
    h2h_winner = h2h.get("winner", {})
    reasoning_transition = reasoning.get("byungjeungyakri_transition", {})
    decision = coordinator.get("decision", {})

    payload = {
        "schema": "agct_sasang_global_status_board_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "status_board": {
            "baseline_status": baseline_summary.get("status"),
            "h2h_winner_sigma": h2h_winner.get("sigma"),
            "sasang_byung_state": reasoning_transition.get("state"),
            "global_coordinator_action": decision.get("action"),
            "global_agreement_rate": coordinator.get("fusion", {}).get("agreement_rate"),
            "alert_reasons": baseline_summary.get("alert_reasons", []),
        },
        "artifacts": {
            "baseline_json": str(ns.baseline_json.resolve()),
            "h2h_json": str(ns.h2h_json.resolve()),
            "reasoning_json": str(ns.reasoning_json.resolve()),
            "coordinator_json": str(ns.coordinator_json.resolve()),
        },
    }

    md_lines = [
        "# AGCT + Sasang + Global Status Board v1",
        "",
        f"- generated_at_utc: {payload['generated_at_utc']}",
        f"- baseline_status: {payload['status_board']['baseline_status']}",
        f"- h2h_winner_sigma: {payload['status_board']['h2h_winner_sigma']}",
        f"- sasang_byung_state: {payload['status_board']['sasang_byung_state']}",
        f"- global_coordinator_action: {payload['status_board']['global_coordinator_action']}",
        f"- global_agreement_rate: {payload['status_board']['global_agreement_rate']}",
        "",
        "## Alerts",
    ]
    alerts = payload["status_board"]["alert_reasons"] or []
    if alerts:
        md_lines.extend([f"- {a}" for a in alerts])
    else:
        md_lines.append("- none")

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ns.output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()}")
    print(f"WROTE: {ns.output_md.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
