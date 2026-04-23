#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    c = data.get("checks") or {}
    m = data.get("metrics") or {}
    lines = [
        "# Canon Promotion Go No-Go v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- verdict: {data.get('verdict')}",
        "",
        "## Checks",
        f"- promotion_gate_ok: {c.get('promotion_gate_ok')}",
        f"- day7_ready_ok: {c.get('day7_ready_ok')}",
        f"- freeze_v2_stability_ok: {c.get('freeze_v2_stability_ok')}",
        f"- delta_governance_ok: {c.get('delta_governance_ok')}",
        "",
        "## Metrics",
        f"- promotion_status: {m.get('promotion_status')}",
        f"- day7_verdict: {m.get('day7_verdict')}",
        f"- freeze_v2_stability_status: {m.get('freeze_v2_stability_status')}",
        f"- freeze_v2_frozen_rate: {m.get('freeze_v2_frozen_rate')}",
        f"- delta_governance_status: {m.get('delta_governance_status')}",
        f"- delta_governance_hold_streak: {m.get('delta_governance_hold_streak')}",
        "",
        "## Hold Reasons",
    ]
    hold_reasons = list(data.get("hold_reasons") or [])
    if hold_reasons:
        lines.extend([f"- {r}" for r in hold_reasons])
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-page promotion go/no-go verdict from core artifacts.")
    ap.add_argument(
        "--promotion-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_gate_v1.json",
    )
    ap.add_argument(
        "--day7-checkpoint-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_day7_checkpoint_gate_v1.json",
    )
    ap.add_argument(
        "--freeze-v2-stability-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--delta-governance-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_delta_cutoff_governance_gate_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.md",
    )
    args = ap.parse_args()

    promotion = _read_json(Path(args.promotion_gate_json))
    day7 = _read_json(Path(args.day7_checkpoint_json))
    freeze_stability = _read_json(Path(args.freeze_v2_stability_gate_json))
    delta_governance = _read_json(Path(args.delta_governance_json))

    checks = {
        "promotion_gate_ok": str(promotion.get("status") or "") == "pass",
        "day7_ready_ok": str(day7.get("verdict") or "") == "ready",
        "freeze_v2_stability_ok": str(freeze_stability.get("status") or "") == "pass",
        "delta_governance_ok": str(delta_governance.get("status") or "") == "pass",
    }
    hold_reasons = [k for k, ok in checks.items() if not ok]
    verdict = "go" if all(checks.values()) else "no_go"

    metrics = {
        "promotion_status": str(promotion.get("status") or "missing"),
        "day7_verdict": str(day7.get("verdict") or "missing"),
        "freeze_v2_stability_status": str(freeze_stability.get("status") or "missing"),
        "freeze_v2_frozen_rate": float(((freeze_stability.get("metrics") or {}).get("frozen_rate")) or 0.0),
        "delta_governance_status": str(delta_governance.get("status") or "missing"),
        "delta_governance_hold_streak": int(((delta_governance.get("metrics") or {}).get("hold_streak")) or 0),
    }

    out = {
        "schema": "original_corpus_regime_singularity_canon_promotion_go_no_go_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "promotion_gate_json": str(args.promotion_gate_json),
            "day7_checkpoint_json": str(args.day7_checkpoint_json),
            "freeze_v2_stability_gate_json": str(args.freeze_v2_stability_gate_json),
            "delta_governance_json": str(args.delta_governance_json),
        },
        "verdict": verdict,
        "checks": checks,
        "metrics": metrics,
        "hold_reasons": hold_reasons,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

