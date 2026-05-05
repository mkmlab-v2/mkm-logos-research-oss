#!/usr/bin/env python3
"""Build one-page Markdown brief for Logos A-track review meeting."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _pct(v: Any) -> str:
    try:
        return f"{float(v) * 100:.2f}%"
    except Exception:
        return "n/a"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-packet", type=Path, default=ART / "logos_symbolic_release_signoff_packet_latest.json")
    ap.add_argument("--human-approval", type=Path, default=ART / "logos_symbolic_event_human_approval_latest.json")
    ap.add_argument("--out-md", type=Path, default=ART / "logos_symbolic_a_track_review_onepager_latest.md")
    args = ap.parse_args()

    packet = _load(Path(args.signoff_packet).resolve())
    approval = _load(Path(args.human_approval).resolve())

    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    checks = packet.get("checks") if isinstance(packet.get("checks"), dict) else {}
    metrics = packet.get("key_metrics") if isinstance(packet.get("key_metrics"), dict) else {}
    gate_metrics = metrics.get("gate_metrics_snapshot") if isinstance(metrics.get("gate_metrics_snapshot"), dict) else {}
    sources = metrics.get("source_breakdown_summary") if isinstance(metrics.get("source_breakdown_summary"), dict) else {}

    lines = [
        "# Logos A-track Review Onepager",
        "",
        f"- generated_at_utc: `{_now()}`",
        f"- packet_generated_at_utc: `{packet.get('generated_at_utc')}`",
        f"- approver: `{approval.get('approver')}`",
        f"- approved_at_utc: `{approval.get('approved_at_utc')}`",
        "",
        "## Decision",
        f"- recommended_manual_gate: `{summary.get('recommended_manual_gate')}`",
        f"- all_checks_pass: `{summary.get('all_checks_pass')}`",
        "- final_judgement: `GO (manual gate)`" if summary.get("recommended_manual_gate") == "GO_MANUAL_A_TRACK_GATE" else "- final_judgement: `HOLD`",
        "",
        "## Core Metrics",
        f"- evaluated_samples: `{gate_metrics.get('n_evaluated')}`",
        f"- hit_rate: `{_pct(gate_metrics.get('hit_rate'))}`",
        f"- holdout_samples: `{gate_metrics.get('holdout_n_evaluated')}`",
        f"- holdout_hit_rate: `{_pct(gate_metrics.get('holdout_hit_rate'))}`",
        f"- non_synthetic_samples: `{gate_metrics.get('non_synthetic_n_evaluated')}`",
        "",
        "## Gate Checks",
        f"- gate_human_approved: `{checks.get('gate_human_approved')}`",
        f"- candidate_status_approved: `{checks.get('candidate_status_approved')}`",
        f"- revalidation_ok: `{checks.get('revalidation_ok')}`",
        f"- hygiene_ok: `{checks.get('hygiene_ok')}`",
        f"- auto_bridge_locked: `{checks.get('auto_bridge_locked')}`",
        "",
        "## Source Snapshot",
        f"- source_count: `{sources.get('n_sources')}`",
        f"- best_source: `{sources.get('best_source_id')}` / `{_pct(sources.get('best_hit_rate'))}`",
        f"- worst_source: `{sources.get('worst_source_id')}` / `{_pct(sources.get('worst_hit_rate'))}`",
        "",
        "## Guardrails (Fixed)",
        "- Automatic A-track bridge: `DISABLED`",
        "- Automatic live trigger: `DISABLED`",
        "- Human approval required per release: `ENFORCED`",
        "",
        "## Meeting Conclusion Template",
        "- Resolution: `Approve A-track reflection under manual gate only`",
        "- Rollout mode: `gradual + rollback ready`",
        "- Next review checkpoint: `after next daily refresh`",
        "",
    ]

    out = Path(args.out_md).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

