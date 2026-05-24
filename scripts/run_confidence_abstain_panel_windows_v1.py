#!/usr/bin/env python3
"""Run confidence_abstain_curve_v1 for fixed panel windows (30/60/90d) — same policy v1.1, no retuning.

Writes per-window JSON under reports/ and a compact summary for leading-indicator comparison.
research_only [HYPO] — does not touch operational prophecy eval.
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
CURVE = ROOT / "scripts/confidence_abstain_curve_v1.py"
DEFAULT_POLICY = ROOT / "docs/final/artifacts/confidence_abstain_policy_v1.1.json"
DEFAULT_SUMMARY = ROOT / "reports/confidence_abstain_curve_windows_summary_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _preset_table(doc: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for p in doc.get("presets") or []:
        if not isinstance(p, dict):
            continue
        m = p.get("full_panel") if isinstance(p.get("full_panel"), dict) else {}
        h = p.get("holdout_split") if isinstance(p.get("holdout_split"), dict) else {}
        rows.append(
            {
                "policy_id": p.get("policy_id"),
                "call_rate": m.get("call_rate"),
                "directional_skill": m.get("directional_skill"),
                "headline_skill": m.get("headline_skill"),
                "n_directional_calls": m.get("n_directional_calls"),
                "n_evaluated": m.get("n_evaluated"),
                "holdout_directional_skill": h.get("directional_skill"),
                "holdout_n_directional_calls": h.get("n_directional_calls"),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument(
        "--windows",
        default="30,60,90",
        help="Comma-separated recent-trading-days values.",
    )
    ap.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args(argv)

    if not args.policy_json.is_file():
        print(f"Missing policy: {args.policy_json}", file=sys.stderr)
        return 2

    windows: list[int] = []
    for part in str(args.windows).split(","):
        part = part.strip()
        if part:
            windows.append(max(1, int(part)))

    window_docs: list[dict[str, Any]] = []
    for n in windows:
        out = ROOT / f"reports/confidence_abstain_curve_v1_{n}d_latest.json"
        cp = subprocess.run(
            [
                sys.executable,
                str(CURVE),
                "--policy-json",
                str(args.policy_json),
                "--recent-trading-days",
                str(n),
                "--output",
                str(out),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if cp.returncode != 0:
            print(cp.stderr or cp.stdout, file=sys.stderr)
            return cp.returncode
        doc = _load_json(out)
        window_docs.append(
            {
                "recent_trading_days": n,
                "artifact": str(out.relative_to(ROOT)).replace("\\", "/"),
                "n_joined_rows": (doc.get("inputs") or {}).get("n_joined_rows"),
                "eval_date_first": (doc.get("inputs") or {}).get("eval_date_first"),
                "eval_date_last": (doc.get("inputs") or {}).get("eval_date_last"),
                "b0_score_rows_in_window": (doc.get("inputs") or {}).get("b0_score_rows_in_window"),
                "presets": _preset_table(doc),
            }
        )
        print(f"OK window={n}d -> {out.name}")

    summary = {
        "schema": "confidence_abstain_curve_windows_summary_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_json": str(args.policy_json.relative_to(ROOT)).replace("\\", "/"),
        "policy_version": _load_json(args.policy_json).get("version"),
        "windows": window_docs,
        "note": "Same confidence_abstain_policy presets across windows; thresholds not refit per window.",
    }
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.summary_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
