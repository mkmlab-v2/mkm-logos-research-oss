#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


def _pct(n: int, d: int) -> float:
    if d <= 0:
        return 0.0
    return round(n / d, 6)


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    m = data["metrics"]
    r = data["ratios"]
    t = data["top_autotune_reasons"]
    s = data.get("freeze_v2_stability_gate") or {}
    lines = [
        "# Canon Rehearsal Weekly Summary v1",
        "",
        f"- generated_at_utc: {data['generated_at_utc']}",
        f"- window_size: {m['window_size']}",
        "",
        "## Core Ratios",
        f"- task_success_rate: {r['task_success_rate']}",
        f"- promotion_pass_rate: {r['promotion_pass_rate']}",
        f"- governance_pass_rate: {r['governance_pass_rate']}",
        f"- autotune_applied_rate: {r['autotune_applied_rate']}",
        f"- autotune_hold_rate: {r['autotune_hold_rate']}",
        "",
        "## Counts",
        f"- task_success_count: {m['task_success_count']}",
        f"- promotion_pass_count: {m['promotion_pass_count']}",
        f"- governance_pass_count: {m['governance_pass_count']}",
        f"- autotune_applied_count: {m['autotune_applied_count']}",
        f"- autotune_hold_count: {m['autotune_hold_count']}",
        "",
        "## Freeze V2 Stability",
        f"- status: {s.get('status', 'missing')}",
        f"- frozen_rate: {s.get('frozen_rate')}",
        f"- window_size: {s.get('window_size')}",
        "",
        "## Top Autotune Reasons",
    ]
    if t:
        for row in t:
            lines.append(f"- {row['reason']}: {row['count']}")
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly summary from rehearsal status history.")
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_rehearsal_status_history_v1.jsonl",
    )
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument(
        "--freeze-v2-stability-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_rehearsal_weekly_summary_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_rehearsal_weekly_summary_v1.md",
    )
    args = ap.parse_args()

    rows = _read_jsonl(Path(args.history_jsonl))
    freeze_stability = _read_json(Path(args.freeze_v2_stability_gate_json))
    freeze_from_history: dict[str, Any] = {}
    window = max(1, int(args.window))
    recent = rows[-window:]
    n = len(recent)

    task_success_count = 0
    promotion_pass_count = 0
    governance_pass_count = 0
    autotune_applied_count = 0
    autotune_hold_count = 0
    reason_counter: Counter[str] = Counter()

    for r in recent:
        task = r.get("task") or {}
        if str(task.get("last_result")) in {"0", "0x0"}:
            task_success_count += 1

        promo = r.get("promotion_gate") or {}
        if str(promo.get("status") or "") == "pass":
            promotion_pass_count += 1

        gov = r.get("delta_governance_gate") or {}
        if str(gov.get("status") or "") == "pass":
            governance_pass_count += 1

        auto = r.get("delta_cutoff_autotune") or {}
        auto_status = str(auto.get("status") or "")
        if auto_status == "applied":
            autotune_applied_count += 1
        elif auto_status == "hold":
            autotune_hold_count += 1
        reason = str(auto.get("apply_reason") or "").strip()
        if reason:
            reason_counter[reason] += 1
        if isinstance(r.get("freeze_v2_stability_gate"), dict):
            freeze_from_history = dict(r.get("freeze_v2_stability_gate") or {})

    freeze_effective = freeze_from_history if freeze_from_history else {
        "status": str(freeze_stability.get("status") or "missing"),
        "window_size": int(((freeze_stability.get("metrics") or {}).get("window_size")) or 0),
        "frozen_rate": float(((freeze_stability.get("metrics") or {}).get("frozen_rate")) or 0.0),
        "generated_at_utc": str(freeze_stability.get("generated_at_utc") or ""),
    }

    out = {
        "schema": "original_corpus_regime_singularity_canon_rehearsal_weekly_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "history_jsonl": str(args.history_jsonl),
            "window": window,
            "freeze_v2_stability_gate_json": str(args.freeze_v2_stability_gate_json),
        },
        "metrics": {
            "window_size": n,
            "task_success_count": task_success_count,
            "promotion_pass_count": promotion_pass_count,
            "governance_pass_count": governance_pass_count,
            "autotune_applied_count": autotune_applied_count,
            "autotune_hold_count": autotune_hold_count,
        },
        "ratios": {
            "task_success_rate": _pct(task_success_count, n),
            "promotion_pass_rate": _pct(promotion_pass_count, n),
            "governance_pass_rate": _pct(governance_pass_count, n),
            "autotune_applied_rate": _pct(autotune_applied_count, n),
            "autotune_hold_rate": _pct(autotune_hold_count, n),
        },
        "top_autotune_reasons": [
            {"reason": reason, "count": count}
            for reason, count in reason_counter.most_common(3)
        ],
        "freeze_v2_stability_gate": freeze_effective,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

