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


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    checks = data.get("checks") or {}
    lines = [
        "# Canon Nextday Observation Report v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- verdict: {data.get('verdict')}",
        "",
        "## Checks",
        f"- go_no_go_ok: {checks.get('go_no_go_ok')}",
        f"- freeze_v2_stability_ok: {checks.get('freeze_v2_stability_ok')}",
        f"- ops_alert_clear_ok: {checks.get('ops_alert_clear_ok')}",
        f"- strict_freeze_drift_stable_ok: {checks.get('strict_freeze_drift_stable_ok')}",
        "",
        "## Hold Reasons",
    ]
    reasons = list(data.get("hold_reasons") or [])
    if reasons:
        lines.extend([f"- {x}" for x in reasons])
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build nextday no-touch observation report from core operational artifacts.")
    ap.add_argument(
        "--go-no-go-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json",
    )
    ap.add_argument(
        "--freeze-v2-stability-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--rehearsal-latest-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_rehearsal_status_latest.json",
    )
    ap.add_argument(
        "--strict-freeze-drift-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_nextday_observation_report_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_nextday_observation_report_v1.md",
    )
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_nextday_observation_history_v1.jsonl",
    )
    ap.add_argument(
        "--append-history",
        action="store_true",
        help="Append report row into history JSONL.",
    )
    args = ap.parse_args()

    go_no_go = _read_json(Path(args.go_no_go_json))
    freeze_stability = _read_json(Path(args.freeze_v2_stability_gate_json))
    rehearsal = _read_json(Path(args.rehearsal_latest_json))
    drift = _read_json(Path(args.strict_freeze_drift_gate_json))

    checks = {
        "go_no_go_ok": str(go_no_go.get("verdict") or "") == "go",
        "freeze_v2_stability_ok": str(freeze_stability.get("status") or "") == "pass",
        "ops_alert_clear_ok": bool((rehearsal.get("ops_alert_summary") or {}).get("ops_alert")) is False,
        "strict_freeze_drift_stable_ok": str(drift.get("status") or "") == "stable",
    }
    reasons = [k for k, ok in checks.items() if not ok]
    out = {
        "schema": "original_corpus_regime_singularity_canon_nextday_observation_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "go_no_go_json": str(args.go_no_go_json),
            "freeze_v2_stability_gate_json": str(args.freeze_v2_stability_gate_json),
            "rehearsal_latest_json": str(args.rehearsal_latest_json),
            "strict_freeze_drift_gate_json": str(args.strict_freeze_drift_gate_json),
        },
        "verdict": "pass" if all(checks.values()) else "hold",
        "checks": checks,
        "hold_reasons": reasons,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    if args.append_history:
        _append_jsonl(Path(args.history_jsonl), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

