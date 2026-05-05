#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "unified_state_snapshot_v1_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "security_signal_light_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_bool(v: Any, default: bool = False) -> bool:
    return bool(v) if v is not None else default


def build_signal(snapshot: dict[str, Any]) -> dict[str, Any]:
    summary = snapshot.get("summary") if isinstance(snapshot.get("summary"), dict) else {}
    meta = summary.get("meta") if isinstance(summary.get("meta"), dict) else {}
    reasons = summary.get("reasons") if isinstance(summary.get("reasons"), list) else []

    secret_ok = _as_bool(meta.get("secret_exposure_gate_ok"), False)
    ops_ok = _as_bool(meta.get("automation_ops_ready"), False)
    a_track_go = str(meta.get("a_track_go_nogo") or "UNKNOWN").upper()

    if not secret_ok:
        signal = "RED"
    elif secret_ok and not ops_ok:
        signal = "AMBER"
    elif secret_ok and ops_ok and a_track_go == "GO":
        signal = "GREEN"
    else:
        signal = "AMBER"

    one_line = (
        f"SECURITY={signal} | secret_gate={'OK' if secret_ok else 'BLOCKED'} | "
        f"ops_ready={'YES' if ops_ok else 'NO'} | a_track={a_track_go}"
    )
    return {
        "schema": "security_signal_light_v1",
        "generated_at_utc": _now_utc(),
        "source_snapshot": "docs/final/artifacts/unified_state_snapshot_v1_latest.json",
        "signal": signal,
        "one_line_status": one_line,
        "summary": {
            "secret_exposure_gate_ok": secret_ok,
            "automation_ops_ready": ops_ok,
            "a_track_go_nogo": a_track_go,
            "reason_count": len(reasons),
            "reasons": [str(x) for x in reasons],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-line security signal light from unified snapshot.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    src = args.input if args.input.is_absolute() else ROOT / args.input
    out = args.out if args.out.is_absolute() else ROOT / args.out
    payload = build_signal(_load(src))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    print(payload["one_line_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
