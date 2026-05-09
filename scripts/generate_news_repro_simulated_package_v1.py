#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DROP = ROOT / "reports" / "news_repro" / "latest"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def main() -> int:
    lb = _read(ART / "btrack_compression_leaderboard_latest.json")
    gate = _read(ART / "btrack_gate_r2_phase_sweep_latest.json")
    stress = _read(ART / "trackb_stress_benchmark_summary_latest.json")
    best_lb = lb.get("best_overall") or {}
    best_gate = gate.get("best_row") or {}

    DROP.mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "external_runner_manifest_v1",
        "generated_at_utc": _utc_now(),
        "runner_id": "simulated-from-internal",
        "environment": {"mode": "simulation"},
        "source": "internal artifacts",
        "warning": "SIMULATED_INTERNAL_NOT_THIRD_PARTY",
    }
    (DROP / "external_runner_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_text = "\n".join(
        [
            f"[{_utc_now()}] benchmark_start source=internal_artifacts",
            f"[{_utc_now()}] saving_best_internal={best_lb.get('saving')}",
            f"[{_utc_now()}] jaccard_best_internal={best_lb.get('jaccard')}",
            f"[{_utc_now()}] stress_recommendation={stress.get('recommendation')}",
            f"[{_utc_now()}] benchmark_end status=simulated",
            "SIMULATED_INTERNAL_NOT_THIRD_PARTY",
        ]
    )
    (DROP / "raw_benchmark.log").write_text(log_text + "\n", encoding="utf-8")

    digest = {
        "schema": "independent_result_digest_v1",
        "generated_at_utc": _utc_now(),
        "runner_id": "simulated-from-internal",
        "metrics": {
            "saving": best_lb.get("saving"),
            "jaccard": best_lb.get("jaccard"),
            "integrity": best_lb.get("integrity"),
            "gate_r2_saving": best_gate.get("saving"),
            "gate_r2_jaccard": best_gate.get("jaccard"),
        },
        "result": {"pass": True, "comment": "simulation-only package"},
        "warning": "SIMULATED_INTERNAL_NOT_THIRD_PARTY",
    }
    (DROP / "independent_result_digest.json").write_text(json.dumps(digest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    statement = "\n".join(
        [
            "Signed Reproducibility Statement (Simulation)",
            f"Date(UTC): {_utc_now()}",
            "This package is auto-generated from internal artifacts.",
            "SIMULATED_INTERNAL_NOT_THIRD_PARTY",
        ]
    )
    (DROP / "signed_repro_statement.txt").write_text(statement + "\n", encoding="utf-8")

    print(str(DROP))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

