#!/usr/bin/env python3
"""Run M26 prompt PoC metric evaluation from baseline/overlay pairs."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAIRS = ROOT / "tests" / "fixtures" / "lens_music_prompt_poc_pairs_sample_v1.jsonl"
DEFAULT_OUT = ROOT / "reports" / "lens_music_prompt_poc_metric_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sent_count(text: str) -> int:
    parts = re.split(r"[.!?]\s+|[.!?]$", text.strip())
    return len([p for p in parts if p.strip()])


def _style_match(text: str, style: str) -> bool:
    t = text.strip()
    if style == "bright_concise":
        return _sent_count(t) <= 2
    if style == "calm_guarded":
        return _sent_count(t) <= 3 and ("보수" in t or "차분" in t or "주의" in t)
    if style == "empathetic_reflective":
        return _sent_count(t) >= 1 and ("정리" in t or "단계" in t or "안정" in t)
    return False


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pairs-jsonl", type=Path, default=DEFAULT_PAIRS)
    ap.add_argument("--target-style-delta", type=float, default=0.30)
    ap.add_argument("--target-overlay-style-match", type=float, default=0.67)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.pairs_jsonl)
    baseline_sent_total = 0
    overlay_sent_total = 0
    overlay_style_hit = 0
    pair_rows = []

    for r in rows:
        baseline = str(r.get("baseline_response_text") or "")
        overlay = str(r.get("overlay_response_text") or "")
        expected_style = str(r.get("expected_overlay_style") or "")
        b_sent = _sent_count(baseline)
        o_sent = _sent_count(overlay)
        baseline_sent_total += b_sent
        overlay_sent_total += o_sent
        style_ok = _style_match(overlay, expected_style)
        if style_ok:
            overlay_style_hit += 1
        pair_rows.append(
            {
                "id": r.get("id"),
                "expected_overlay_style": expected_style,
                "baseline_sent_count": b_sent,
                "overlay_sent_count": o_sent,
                "overlay_style_match": style_ok,
            }
        )

    n = len(rows)
    base_avg = (baseline_sent_total / n) if n else 0.0
    overlay_avg = (overlay_sent_total / n) if n else 0.0
    # Positive means overlay got shorter than baseline.
    style_delta = ((base_avg - overlay_avg) / base_avg) if base_avg > 0 else 0.0
    overlay_style_match_rate = (overlay_style_hit / n) if n else 0.0
    passed = style_delta >= float(args.target_style_delta) and overlay_style_match_rate >= float(args.target_overlay_style_match)

    out = {
        "schema": "lens_music_prompt_poc_metric_v1",
        "generated_at_utc": _utc_now(),
        "samples_count": n,
        "kpi": {
            "baseline_avg_sent_count": round(base_avg, 6),
            "overlay_avg_sent_count": round(overlay_avg, 6),
            "style_delta_rate": round(style_delta, 6),
            "overlay_style_match_rate": round(overlay_style_match_rate, 6),
        },
        "targets": {
            "style_delta_rate_min": float(args.target_style_delta),
            "overlay_style_match_rate_min": float(args.target_overlay_style_match),
        },
        "result": {
            "passed": passed,
            "state": "GO" if passed else "WATCH",
        },
        "rows": pair_rows,
        "note": "M26 PoC metric report for prompt-overlay style control. Advisory-only.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": out["result"]["state"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
