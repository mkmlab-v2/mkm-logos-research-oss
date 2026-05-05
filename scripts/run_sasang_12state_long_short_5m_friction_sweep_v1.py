#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "sasang_12state_long_short_5m_friction_sweep_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(fee_bps: float, slip_bps: float, out_json: Path) -> dict:
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/run_sasang_12state_long_short_5m_factcheck_v1.py",
            "--fee-oneway-bps",
            str(fee_bps),
            "--slippage-roundtrip-bps",
            str(slip_bps),
            "--output-json",
            str(out_json),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    row = {
        "fee_oneway_bps": fee_bps,
        "slippage_roundtrip_bps": slip_bps,
        "exit_code": cp.returncode,
        "output_json": str(out_json),
    }
    if cp.returncode != 0:
        row["error"] = (cp.stderr or cp.stdout)[-500:]
        return row
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    results = doc.get("results") if isinstance(doc.get("results"), list) else []
    by_mode = {r.get("mode"): r for r in results if isinstance(r, dict)}
    long_ret = float(by_mode.get("long_only", {}).get("total_return", 0.0))
    short_ret = float(by_mode.get("short_only", {}).get("total_return", 0.0))
    row.update(
        {
            "long_total_return": long_ret,
            "short_total_return": short_ret,
            "both_down": long_ret < 0.0 and short_ret < 0.0,
        }
    )
    return row


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    scenarios = [
        (2.0, 2.0),
        (3.0, 2.0),
        (4.0, 4.0),
        (5.0, 6.0),
        (6.0, 8.0),
    ]
    rows = []
    for fee, slip in scenarios:
        scenario_out = ART / f"_tmp_sasang_5m_factcheck_f{int(fee*10)}_s{int(slip*10)}.json"
        rows.append(_run(fee, slip, scenario_out))
    ok_rows = [r for r in rows if r.get("exit_code") == 0]
    both_down_count = sum(1 for r in ok_rows if r.get("both_down"))
    OUT.write_text(
        json.dumps(
            {
                "schema": "sasang_12state_long_short_5m_friction_sweep_v1",
                "generated_at_utc": _now(),
                "rows": rows,
                "summary": {
                    "scenario_count": len(rows),
                    "ok_count": len(ok_rows),
                    "both_down_count": both_down_count,
                    "both_down_ratio": (both_down_count / len(ok_rows)) if ok_rows else 0.0,
                },
                "track_wall": {"track_b_only": True, "a_track_autobind_forbidden": True},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {OUT}")
    return 0 if len(ok_rows) == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
