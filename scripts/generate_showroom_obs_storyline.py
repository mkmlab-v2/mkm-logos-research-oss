#!/usr/bin/env python3
"""Generate short OBS storyline lines from event payload."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _line(obj: Dict[str, Any]) -> List[str]:
    risk = str(obj.get("risk_level", "INFO")).upper()
    direction = str(obj.get("public_signal_direction", "HOLD")).upper()
    trust = str(obj.get("trust_level", "UNKNOWN")).upper()
    reason = str(obj.get("abstract_reason", "No summary"))[:72]
    ts = str(obj.get("timestamp", datetime.now(timezone.utc).isoformat()))
    return [
        f"[{ts}] MODE={direction} RISK={risk} TRUST={trust}",
        f"Signal summary: {reason}",
        "Delayed public telemetry • not investment advice",
    ]


def generate(src: Path, out: Path) -> Dict[str, Any]:
    obj = json.loads(src.read_text(encoding="utf-8"))
    lines = _line(obj)
    payload = {
        "schema": "showroom_obs_storyline_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_json": str(src.as_posix()),
        "lines": lines,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate OBS storyline JSON from one event payload.")
    p.add_argument("--src", required=True, help="Input event json")
    p.add_argument("--out", required=True, help="Output storyline json")
    return p


def main() -> int:
    ns = _parser().parse_args()
    payload = generate(Path(ns.src), Path(ns.out))
    print(payload["schema"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
