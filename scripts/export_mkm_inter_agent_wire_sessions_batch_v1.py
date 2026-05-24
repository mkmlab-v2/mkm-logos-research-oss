#!/usr/bin/env python3
"""M15a: Batch-export wire sessions for trading / health / lexicon_dense (JSONL + manifest)."""

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

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_sessions_batch_v1_latest.json"
SCENARIOS = ("trading", "health", "lexicon_dense")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_batch(
    *,
    scenarios: tuple[str, ...] = SCENARIOS,
    turns: int = 4,
    out_dir: Path | None = None,
    sidecar_scenarios: tuple[str, ...] = (),
) -> dict[str, Any]:
    from scripts.export_mkm_inter_agent_wire_session_v1 import export_session

    out_dir = out_dir or (ROOT / "docs/final/artifacts")
    out_dir.mkdir(parents=True, exist_ok=True)

    sessions: dict[str, Any] = {}
    combined_jsonl = out_dir / "mkm_inter_agent_wire_sessions_batch_v1_latest.jsonl"
    all_ok = True

    with combined_jsonl.open("w", encoding="utf-8") as combined:
        for scenario in scenarios:
            doc = export_session(
                scenario=scenario,
                turns=turns,
                use_ko_health_sidecar=scenario in sidecar_scenarios,
            )
            all_ok = all_ok and bool(doc.get("ok"))
            per_jsonl = out_dir / f"mkm_inter_agent_wire_session_{scenario}_v1_latest.jsonl"
            with per_jsonl.open("w", encoding="utf-8") as fh:
                for row in doc.get("envelopes") or []:
                    line = {**row, "scenario": scenario, "session_id": doc.get("session_id")}
                    fh.write(json.dumps(line, ensure_ascii=False) + "\n")
                    combined.write(json.dumps(line, ensure_ascii=False) + "\n")

            sessions[scenario] = {
                "ok": doc.get("ok"),
                "session_id": doc.get("session_id"),
                "envelope_count": doc.get("envelope_count"),
                "all_envelopes_schema_valid": doc.get("all_envelopes_schema_valid"),
                "envelopes_jsonl": per_jsonl.relative_to(ROOT).as_posix(),
                "total_envelope_utf8_bytes": sum(
                    int(r.get("envelope_utf8_byte_len") or 0) for r in doc.get("envelopes") or []
                ),
                "use_ko_health_sidecar": scenario in sidecar_scenarios,
            }

    return {
        "ok": all_ok and all(s.get("ok") for s in sessions.values()),
        "schema": "mkm_inter_agent_wire_sessions_batch_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "turns_per_session": turns,
        "scenario_count": len(scenarios),
        "scenarios": list(scenarios),
        "sessions": sessions,
        "combined_jsonl": combined_jsonl.relative_to(ROOT).as_posix(),
        "total_envelopes": sum(int(s.get("envelope_count") or 0) for s in sessions.values()),
        "sidecar_scenarios": list(sidecar_scenarios),
        "boundary_ack": "Batch B-track session replay; not production bus or Track A.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument(
        "--scenarios",
        nargs="+",
        choices=SCENARIOS,
        default=list(SCENARIOS),
    )
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "docs/final/artifacts")
    ap.add_argument(
        "--sidecar-scenarios",
        nargs="*",
        choices=SCENARIOS,
        default=[],
        help="Apply use_ko_health_sidecar for these scenarios (e.g. health).",
    )
    args = ap.parse_args()

    doc = export_batch(
        scenarios=tuple(args.scenarios),
        turns=max(2, args.turns),
        out_dir=args.out_dir,
        sidecar_scenarios=tuple(args.sidecar_scenarios),
    )
    args.manifest_json.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "manifest": str(args.manifest_json)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
