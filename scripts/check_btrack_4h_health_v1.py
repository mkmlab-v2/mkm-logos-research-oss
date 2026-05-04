#!/usr/bin/env python3
"""Lightweight B-Track artifact health check (no network, no full daily chain).

Writes ``docs/final/artifacts/btrack_4h_health_latest.json`` with parse results and exit 0/1.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_HYPOTHESIS = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_HIT_RATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_eval_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_4h_health_latest.json"

SCHEMA = "btrack_4h_health_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _check_file(path: Path, *, required_keys: tuple[str, ...]) -> dict[str, Any]:
    rec: dict[str, Any] = {"path": str(path).replace("\\", "/"), "exists": path.is_file()}
    if not path.is_file():
        rec["ok"] = False
        rec["error"] = "missing"
        return rec
    try:
        raw = path.read_text(encoding="utf-8")
        doc = json.loads(raw)
    except json.JSONDecodeError as e:
        rec["ok"] = False
        rec["error"] = f"json_decode:{e}"
        return rec
    if not isinstance(doc, dict):
        rec["ok"] = False
        rec["error"] = "not_object"
        return rec
    missing = [k for k in required_keys if k not in doc]
    if missing:
        rec["ok"] = False
        rec["error"] = f"missing_keys:{missing}"
        return rec
    rec["ok"] = True
    rec["schema"] = doc.get("schema")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description="B-Track 4h-style health snapshot (artifact presence + JSON parse).")
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--hit-rate-json", type=Path, default=DEFAULT_HIT_RATE)
    ap.add_argument("--skip-hit-rate", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    hyp_chk = _check_file(args.hypothesis_json, required_keys=("schema", "prediction"))
    score_chk = _check_file(args.score_json, required_keys=("schema", "rows"))
    hit_chk: dict[str, Any] | None = None
    if not args.skip_hit_rate:
        hit_chk = _check_file(args.hit_rate_json, required_keys=("schema", "metrics"))

    ok = hyp_chk.get("ok") and score_chk.get("ok") and (hit_chk is None or hit_chk.get("ok"))

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "checks": {"hypothesis": hyp_chk, "score": score_chk, "hit_rate_eval": hit_chk},
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    print(f"WROTE: {args.output.resolve()}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
