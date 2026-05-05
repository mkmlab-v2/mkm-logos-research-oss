#!/usr/bin/env python3
"""Run a synthetic BTC-only guard drill.

Creates a temporary non-BTC scoped bundle and verifies hypothesis becomes abstain.
Writes:
- docs/final/artifacts/btc_only_guard_drill_latest.json
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "scripts/generate_btrack_hypothesis_prophecy_v1.py"
OUT = ROOT / "docs/final/artifacts/btc_only_guard_drill_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="btc_guard_drill_") as td:
        tdp = Path(td)
        bad_bundle = tdp / "bad_bundle.json"
        hyp_out = tdp / "hyp_out.json"
        bad_bundle.write_text(
            json.dumps(
                {
                    "schema": "btrack_llm_input_bundle_v1",
                    "artifacts": {
                        "macro_independent_lens": {
                            "scores": {"direction_score": 0.7, "confidence": 0.9},
                            "policy_scope": {
                                "trading_primary_asset": "KOSPI200",
                                "kospi_role": "gating",
                            },
                        }
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        cp = subprocess.run(
            [sys.executable, str(GEN), "--bundle", str(bad_bundle), "--output", str(hyp_out)],
            capture_output=True,
            text=True,
        )
        ok = cp.returncode == 0 and hyp_out.is_file()
        blocked = False
        direction = ""
        instrument = ""
        violations: list[str] = []
        if ok:
            doc = _load(hyp_out)
            pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
            meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
            guard = meta.get("btc_only_guard") if isinstance(meta.get("btc_only_guard"), dict) else {}
            blocked = bool(guard.get("blocked"))
            direction = str(pred.get("direction") or "")
            instrument = str(pred.get("instrument") or "")
            violations = guard.get("violations") if isinstance(guard.get("violations"), list) else []
            ok = ok and blocked and direction == "abstain" and instrument == "btc"

        out = {
            "schema": "btc_only_guard_drill_v1",
            "generated_at_utc": _utc_now(),
            "ok": ok,
            "blocked": blocked,
            "instrument": instrument,
            "direction": direction,
            "violations": violations,
            "generator_exit_code": cp.returncode,
            "stderr_tail": (cp.stderr or "")[-1200:],
        }
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT.resolve()}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
