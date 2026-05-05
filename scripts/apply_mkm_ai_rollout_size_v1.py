#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROLLOUT = ROOT / "docs" / "final" / "artifacts" / "mkm_ai_micro_scale_rollout_status_latest.json"
DEFAULT_ENGINE_INPUT = ROOT / "docs" / "final" / "artifacts" / "btc_limited_live_engine_input_from_lens_combo_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply MKM rollout recommended size into engine input.")
    p.add_argument("--rollout-status", type=Path, default=DEFAULT_ROLLOUT)
    p.add_argument("--engine-input", type=Path, default=DEFAULT_ENGINE_INPUT)
    p.add_argument("--force", action="store_true", help="Apply even if rollout decision is not promotion/hold.")
    p.add_argument("--max-abs-delta-usd", type=float, default=20.0)
    p.add_argument("--write", action="store_true", help="Persist changes. Default is dry-run.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    rollout = _read_json(args.rollout_status)
    engine = _read_json(args.engine_input)

    decision = str(rollout.get("decision") or "")
    if not args.force and decision not in {"PROMOTE_ONE_STAGE", "HOLD_STAGE", "KEEP_MAX_STAGE"}:
        raise SystemExit(f"Unsafe decision for apply: {decision}")

    recommended = float(((rollout.get("sizing") or {}).get("recommended_size_usd") or 0.0))
    current = float(((engine.get("engine_input") or {}).get("size_usd") or 0.0))
    delta = abs(recommended - current)
    if delta > float(args.max_abs_delta_usd):
        raise SystemExit(f"Size delta too large ({delta:.4f} > {args.max_abs_delta_usd:.4f})")

    engine.setdefault("engine_input", {})
    engine["engine_input"]["size_usd"] = recommended
    engine["rollout_control"] = {
        "schema": "mkm_ai_rollout_apply_audit_v1",
        "applied_at_utc": _utc_now(),
        "source_rollout_status": str(args.rollout_status),
        "decision": decision,
        "target_stage": rollout.get("target_stage"),
        "previous_size_usd": current,
        "applied_size_usd": recommended,
        "dry_run": not args.write,
    }

    if args.write:
        args.engine_input.write_text(json.dumps(engine, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[OK] wrote: {args.engine_input}")
    else:
        print("[DRY-RUN] no file changed")

    print(f"decision={decision}")
    print(f"size_usd: {current} -> {recommended}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
