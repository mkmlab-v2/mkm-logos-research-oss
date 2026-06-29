#!/usr/bin/env python3
"""Run [HYPO] GPU hybrid parallel smoke steps and write one rollup JSON (no active write)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/mkm_gpu_hybrid_parallel_auto_smoke_v1_latest.json"
HYBRID_SPEC = ROOT / "reports/mkm_gpu_hybrid_transition_spec_v1_latest.json"
ATOM02 = ROOT / "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json"
GPU_SMOKE = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_auto_smoke_v1_latest.json"
GPU_MERGED = ROOT / "reports/constitution/btrack_pilot/comp_en_tech_semantic_gpu_poc_oov_patch_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, step_id: str) -> dict:
    t0 = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    elapsed = (datetime.now(timezone.utc) - t0).total_seconds()
    tail = (proc.stdout or proc.stderr or "")[-800:]
    return {
        "step_id": step_id,
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "elapsed_s": round(elapsed, 2),
        "ok": proc.returncode == 0,
        "output_tail": tail.strip(),
    }


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-run", action="store_true", help="Only rollup existing artifacts")
    ap.add_argument("--max-cases", type=int, default=8)
    ap.add_argument("--skip-31k-shadow", action="store_true")
    ap.add_argument("--include-resweep-status", action="store_true", help="Note merged OOV patch if on disk")
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_run:
        steps.append(
            _run(
                [sys.executable, "scripts/comp_atom02_lexicon_must_keep_analysis_v1.py"],
                step_id="compression_41k_ablation_golden40",
            )
        )
        steps.append(
            _run(
                [
                    sys.executable,
                    "scripts/run_en_tech_semantic_gpu_poc_v1.py",
                    "--max-cases",
                    str(args.max_cases),
                    "--semantic-device",
                    "cuda",
                    "--out-json",
                    str(GPU_SMOKE.relative_to(ROOT)).replace("\\", "/"),
                ],
                step_id="compression_41k_gpu_semantic_poc",
            )
        )
        if not args.skip_31k_shadow:
            steps.append(
                _run(
                    [
                        sys.executable,
                        "scripts/run_btrack_31k41k_prophecy_shadow_chain_v1.py",
                        "--daily-fast",
                        "--skip-gate",
                    ],
                    step_id="prophecy_shadow_31k_daily_fast",
                )
            )
        steps.append(
            _run(
                [sys.executable, "scripts/build_mkm_gpu_hybrid_transition_spec_v1.py"],
                step_id="hybrid_spec_refresh",
            )
        )

    atom02 = _load_json(ATOM02)
    gpu = _load_json(GPU_SMOKE)
    merged = _load_json(GPU_MERGED) if args.include_resweep_status else None
    hybrid = _load_json(HYBRID_SPEC)

    ablation_delta = (atom02 or {}).get("compression_ablation", {}).get("delta_on_minus_off") or {}
    gpu_agg = (gpu or {}).get("aggregate") or {}
    beat = (gpu or {}).get("beat_frozen_cpu_outpost")
    merged_agg = (merged or {}).get("aggregate") or {}
    merged_beat = (merged or {}).get("beat_frozen_cpu_literal_research_only")

    doc = {
        "schema": "mkm_gpu_hybrid_parallel_auto_smoke_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "hypo_label": "[HYPO]",
        "hybrid_spec_pointer": str(HYBRID_SPEC.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "all_steps_ok": all(s.get("ok") for s in steps) if steps else None,
        "metrics_rollup": {
            "compression_41k_lexicon_ablation_delta_on_minus_off": ablation_delta,
            "gpu_poc_auto_smoke": {
                "path": str(GPU_SMOKE.relative_to(ROOT)).replace("\\", "/"),
                "case_count": gpu_agg.get("case_count"),
                "jaccard_min": gpu_agg.get("jaccard_min"),
                "jaccard_mean": gpu_agg.get("jaccard_mean"),
                "beat_frozen_cpu_outpost": beat,
                "gpu_semantic_status": ((gpu or {}).get("gpu_semantic") or {}).get("status"),
            },
            "oov_resweep_merged_optional": {
                "present": merged is not None,
                "path": str(GPU_MERGED.relative_to(ROOT)).replace("\\", "/") if merged else None,
                "case_count": merged_agg.get("case_count"),
                "jaccard_min": merged_agg.get("jaccard_min"),
                "jaccard_mean": merged_agg.get("jaccard_mean"),
                "beat_frozen_cpu_literal_research_only": merged_beat,
                "scope_note": "en_tech matrix lane only — not Golden-40 41k retire gate",
            },
        },
        "verdict": {
            "parallel_smoke_runnable_locally": True,
            "41k_retire_allowed": False,
            "track_a_promotion": "blocked — TRACK_A_STRICT_LOCK",
            "single_gpu_loop_merge": "forbidden per hybrid spec",
            "en_tech_120_beat_frozen_literal_research_only": merged_beat,
        },
        "guardrails": (hybrid or {}).get("guardrails") or [],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "all_steps_ok": doc["all_steps_ok"]}, ensure_ascii=False))
    return 0 if (doc["all_steps_ok"] is not False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
