#!/usr/bin/env python3
"""Build final GO/NO-GO packet for Logos symbolic A-track manual gate."""
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


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-json", type=Path, default=ART / "logos_symbolic_event_promotion_gate_latest.json")
    ap.add_argument("--candidate-json", type=Path, default=ART / "logos_symbolic_event_track_a_candidate_latest.json")
    ap.add_argument("--revalidation-json", type=Path, default=ART / "logos_symbolic_revalidation_report_latest.json")
    ap.add_argument("--hygiene-json", type=Path, default=ART / "logos_symbolic_data_hygiene_audit_latest.json")
    ap.add_argument("--source-breakdown-json", type=Path, default=ART / "logos_symbolic_source_performance_breakdown_latest.json")
    ap.add_argument("--out-json", type=Path, default=ART / "logos_symbolic_release_signoff_packet_latest.json")
    ap.add_argument("--out-md", type=Path, default=ART / "logos_symbolic_release_signoff_packet_latest.md")
    args = ap.parse_args()

    gate = _load_json(Path(args.gate_json).resolve())
    candidate = _load_json(Path(args.candidate_json).resolve())
    revalidation = _load_json(Path(args.revalidation_json).resolve())
    hygiene = _load_json(Path(args.hygiene_json).resolve())
    breakdown = _load_json(Path(args.source_breakdown_json).resolve())

    gate_decision = str(gate.get("decision") or "")
    candidate_status = str(candidate.get("status") or "")
    revalidation_status = str(revalidation.get("status") or "")
    hygiene_status = str(hygiene.get("status") or "")
    track_wall = gate.get("track_wall") if isinstance(gate.get("track_wall"), dict) else {}
    auto_bridge_locked = bool(track_wall.get("promotion_to_a_track_allowed") is False) and bool(
        track_wall.get("live_trigger_auto_enabled") is False
    )

    checks = {
        "gate_human_approved": gate_decision == "GO_RESEARCH_PROMOTION_CANDIDATE_WITH_HUMAN_APPROVAL",
        "candidate_status_approved": candidate_status == "APPROVED_CANDIDATE",
        "revalidation_ok": revalidation_status == "ok",
        "hygiene_ok": hygiene_status == "ok",
        "auto_bridge_locked": auto_bridge_locked,
    }
    all_checks_pass = all(checks.values())
    recommended_manual_gate = "GO_MANUAL_A_TRACK_GATE" if all_checks_pass else "HOLD_RESEARCH_ONLY"

    packet = {
        "schema": "logos_symbolic_release_signoff_packet_v1",
        "generated_at_utc": _now(),
        "summary": {
            "recommended_manual_gate": recommended_manual_gate,
            "all_checks_pass": all_checks_pass,
            "note": "Manual gate only. No automatic A-track/live bridge.",
        },
        "checks": checks,
        "key_metrics": {
            "gate_metrics_snapshot": gate.get("metrics_snapshot"),
            "revalidation_overall": revalidation.get("overall"),
            "hygiene_news_counts": hygiene.get("news_counts"),
            "source_breakdown_summary": breakdown.get("summary"),
        },
        "evidence_refs": {
            "gate_json": str(Path(args.gate_json).resolve()).replace("\\", "/"),
            "candidate_json": str(Path(args.candidate_json).resolve()).replace("\\", "/"),
            "revalidation_json": str(Path(args.revalidation_json).resolve()).replace("\\", "/"),
            "hygiene_json": str(Path(args.hygiene_json).resolve()).replace("\\", "/"),
            "source_breakdown_json": str(Path(args.source_breakdown_json).resolve()).replace("\\", "/"),
        },
        "guardrails": [
            "Manual decision required for any A-track reflection.",
            "Live trigger auto-enable remains forbidden.",
            "If approved, use gradual rollout and rollback-ready execution only.",
        ],
    }

    out_json = Path(args.out_json).resolve()
    out_md = Path(args.out_md).resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Logos Symbolic Release Signoff Packet",
                "",
                f"- generated_at_utc: `{packet['generated_at_utc']}`",
                f"- recommended_manual_gate: `{recommended_manual_gate}`",
                f"- all_checks_pass: `{all_checks_pass}`",
                "",
                "## Checks",
                f"- gate_human_approved: `{checks['gate_human_approved']}`",
                f"- candidate_status_approved: `{checks['candidate_status_approved']}`",
                f"- revalidation_ok: `{checks['revalidation_ok']}`",
                f"- hygiene_ok: `{checks['hygiene_ok']}`",
                f"- auto_bridge_locked: `{checks['auto_bridge_locked']}`",
                "",
                "## Guardrails",
                "- Manual decision required for any A-track reflection.",
                "- Live trigger auto-enable remains forbidden.",
                "- If approved, use gradual rollout and rollback-ready execution only.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

