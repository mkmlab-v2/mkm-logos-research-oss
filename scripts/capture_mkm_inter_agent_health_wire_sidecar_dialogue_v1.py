#!/usr/bin/env python3
"""M22: Capture health wire-first dialogue plain vs [HYPO] sidecar (atom uplift)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_health_wire_sidecar_dialogue_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def capture(*, turns: int = 4) -> dict[str, Any]:
    from scripts.run_mkm_inter_agent_dialogue_wire_first_v1 import run_dialogue

    plain = run_dialogue(turns=turns, scenario="health", use_ko_health_sidecar=False)
    sidecar = run_dialogue(turns=turns, scenario="health", use_ko_health_sidecar=True)

    def _avg_atoms(doc: dict[str, Any]) -> float:
        tr = doc.get("transcript") or []
        if not tr:
            return 0.0
        return sum(int((t.get("send") or {}).get("atom_id_count") or 0) for t in tr) / len(tr)

    plain_avg = _avg_atoms(plain)
    sidecar_avg = _avg_atoms(sidecar)
    uplift = round(sidecar_avg - plain_avg, 2)

    ok = (
        bool(plain.get("all_ok"))
        and bool(sidecar.get("all_ok"))
        and sidecar_avg > plain_avg
        and plain_avg <= 1.5
    )

    return {
        "ok": ok,
        "schema": "mkm_inter_agent_health_wire_sidecar_dialogue_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "turns": turns,
        "plain": {"session_id": plain.get("session_id"), "avg_atom_id_count": plain_avg},
        "sidecar": {"session_id": sidecar.get("session_id"), "avg_atom_id_count": sidecar_avg},
        "uplift_avg_atom_id_count": uplift,
        "boundary_ack": "Health wire-first mock only; not production bus.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = capture(turns=max(2, args.turns))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
