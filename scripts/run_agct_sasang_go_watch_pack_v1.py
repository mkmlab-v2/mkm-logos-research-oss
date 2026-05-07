from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description="Build AGCT Sasang go/watch pack from repeated daily-chain runs.")
    ap.add_argument("--start-seed", type=int, default=20260505)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument(
        "--thresholds-json",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "agct_sasang_btrack_daily_thresholds_v1.json",
    )
    ap.add_argument(
        "--daily-chain-script",
        type=Path,
        default=root / "scripts" / "run_agct_sasang_btrack_daily_chain_v1.py",
    )
    ap.add_argument(
        "--daily-output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_btrack_daily_chain_v1_latest.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_go_watch_pack_v1_latest.json",
    )
    ns = ap.parse_args()

    runs: list[dict[str, Any]] = []
    for i in range(max(1, int(ns.runs))):
        seed = int(ns.start_seed) + i
        _run(
            [
                sys.executable,
                str(ns.daily_chain_script),
                "--seed",
                str(seed),
                "--thresholds-json",
                str(ns.thresholds_json),
                "--output-json",
                str(ns.daily_output_json),
            ],
            root,
        )
        latest = _read_json(ns.daily_output_json)
        runs.append(
            {
                "seed": seed,
                "decision": latest.get("decision"),
                "checks": latest.get("checks"),
                "metrics": latest.get("metrics"),
            }
        )

    go_count = sum(1 for r in runs if str(r.get("decision")) == "GO_BTRACK")
    payload = {
        "schema": "agct_sasang_go_watch_pack_v1",
        "generated_at_utc": _utc_now(),
        "thresholds_json": str(ns.thresholds_json),
        "runs": runs,
        "summary": {
            "n_runs": len(runs),
            "go_count": go_count,
            "review_required_count": len(runs) - go_count,
            "all_go": go_count == len(runs),
        },
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json}")
    print(f"GO={go_count}/{len(runs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
