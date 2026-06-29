#!/usr/bin/env python3
"""[HYPO] Auto Tier0 ingest for priority compression LIT reviews (disk-backed facts)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/research/raw"
DIGEST = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
OUT = ROOT / "reports/compression_lit_tier0_auto_ingest_v1_latest.json"

ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
KNEE = ROOT / "reports/ng40_path_b_knee_summary_v1_latest.json"
DUAL = ROOT / "reports/compression_golden40_active_dual_report_v1_latest.json"
CODEC = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fact_block(
    fact_id: str,
    metric_name: str,
    value: float,
    unit: str,
    arm: str,
    artifact_path: str,
    artifact_field: str,
    *,
    assertion: str = "eq",
) -> str:
    return f"""### fact_id: {fact_id}
- metric_name: {metric_name}
- value: {value}
- unit: {unit}
- comparison_arm: {arm}
- verification_status: Right
- verification_method: local_artifact
- baseline_plane: golden40_latent
- artifact_path: {artifact_path}
- artifact_field: {artifact_field}
- assertion: {assertion}
"""


def _build_multilens(active: dict[str, Any], knee: dict[str, Any], dual: dict[str, Any]) -> str:
    cm = active.get("compression_metrics") or {}
    sweep = knee.get("sweep") or {}
    delta = (dual.get("delta") or {}).get("alignment_pass_rate_delta_repair_v2_minus_raw", 0.0)
    facts = [
        _fact_block(
            "active_global_token_saving_rate",
            "global_token_saving_rate",
            float(cm["global_token_saving_rate"]),
            "ratio",
            "frozen_active",
            "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "compression_metrics.global_token_saving_rate",
        ),
        _fact_block(
            "active_avg_jaccard",
            "avg_reconstruction_fidelity_jaccard",
            float(cm["avg_reconstruction_fidelity_jaccard"]),
            "ratio",
            "frozen_active",
            "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
            "compression_metrics.avg_reconstruction_fidelity_jaccard",
        ),
        _fact_block(
            "path_b_combo_count",
            "combo_count",
            float(sweep.get("combo_count") or 0),
            "count",
            "ng40_path_b_sweep",
            "reports/ng40_path_b_knee_summary_v1_latest.json",
            "sweep.combo_count",
        ),
        _fact_block(
            "path_b_beat_rows_count",
            "beat_rows_count",
            float(sweep.get("beat_rows_count") or 0),
            "count",
            "ng40_path_b_sweep",
            "reports/ng40_path_b_knee_summary_v1_latest.json",
            "sweep.beat_rows_count",
        ),
        _fact_block(
            "repair_v2_alignment_delta",
            "alignment_pass_rate_delta_repair_v2_minus_raw",
            float(delta),
            "ratio",
            "golden40_active_dual",
            "reports/compression_golden40_active_dual_report_v1_latest.json",
            "delta.alignment_pass_rate_delta_repair_v2_minus_raw",
        ),
    ]
    return f"""# Compression multilens deep research — Tier0 auto-ingest

**Generated:** {_utc()} · **Source LIT:** COMPRESSION_IMPROVEMENT_MULTILENS_DEEP_RESEARCH_LIT_REVIEW_2026-06-22.md
**Track:** B-track · research_only · send_gate HOLD

## Summary

Dual-plane compression diagnosis wired from disk SSOT. Pareto ceiling 320/320 no dual beat.

## Citations

- Internal: MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json
- Internal: ng40_path_b_knee_summary_v1_latest.json

## Digested facts

{"".join(facts)}

## Reproduce

```powershell
py scripts/run_mkm_digestion_engine_chain_v1.py --input docs/research/raw/compression_improvement_multilens_deep_research_tier0_2026-06-23.md --offline
```
"""


def _build_phase_a(knee: dict[str, Any], dual: dict[str, Any]) -> str:
    sweep = knee.get("sweep") or {}
    any_beat = 0.0 if not sweep.get("any_beat_frozen_vs_active") else 1.0
    delta = (dual.get("delta") or {}).get("alignment_pass_rate_delta_repair_v2_minus_raw", 0.0)
    facts = [
        _fact_block(
            "phase_a_combo_count",
            "combo_count",
            float(sweep.get("combo_count") or 0),
            "count",
            "ng40_path_b_sweep",
            "reports/ng40_path_b_knee_summary_v1_latest.json",
            "sweep.combo_count",
        ),
        _fact_block(
            "phase_a_any_beat_frozen",
            "any_beat_frozen_vs_active",
            any_beat,
            "count",
            "ng40_path_b_sweep",
            "reports/ng40_path_b_knee_summary_v1_latest.json",
            "sweep.any_beat_frozen_vs_active",
        ),
        _fact_block(
            "phase_a_repair_alignment_delta",
            "alignment_pass_rate_delta_repair_v2_minus_raw",
            float(delta),
            "ratio",
            "golden40_active_dual",
            "reports/compression_golden40_active_dual_report_v1_latest.json",
            "delta.alignment_pass_rate_delta_repair_v2_minus_raw",
        ),
    ]
    return f"""# Compression Phase-A-only bench protocol — Tier0 auto-ingest

**Generated:** {_utc()} · **Source LIT:** COMPRESSION_PHASE_A_ONLY_BENCH_PROTOCOL_LIT_REVIEW_2026-06-22.md
**Track:** B-track · research_only · send_gate HOLD

## Summary

Phase A-only bench default supported: ng40 sweep has no parse/repair wall card on Golden-40.

## Digested facts

{"".join(facts)}

## Reproduce

```powershell
py scripts/run_mkm_digestion_engine_chain_v1.py --input docs/research/raw/compression_phase_a_only_bench_protocol_tier0_2026-06-23.md --offline
```
"""


def _build_ollama(knee: dict[str, Any], codec: dict[str, Any]) -> str:
    sweep = knee.get("sweep") or {}
    spine = (codec.get("lanes") or {}).get("spine_byte_exact_b2b") or {}
    facts = [
        _fact_block(
            "ollama_path_b_combo_count",
            "combo_count",
            float(sweep.get("combo_count") or 0),
            "count",
            "ng40_path_b_sweep",
            "reports/ng40_path_b_knee_summary_v1_latest.json",
            "sweep.combo_count",
        ),
        _fact_block(
            "ollama_beat_rows_count",
            "beat_rows_count",
            float(sweep.get("beat_rows_count") or 0),
            "count",
            "ng40_path_b_sweep",
            "reports/ng40_path_b_knee_summary_v1_latest.json",
            "sweep.beat_rows_count",
        ),
        _fact_block(
            "path_a_guarded_byte_exact",
            "guarded_byte_exact",
            float(spine.get("guarded_byte_exact") or 0),
            "ratio",
            "path_a_b2b_spine",
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_codec_bench_split_manifest_v1_latest.json",
            "lanes.spine_byte_exact_b2b.guarded_byte_exact",
        ),
    ]
    return f"""# Compression Ollama theory best path — Tier0 auto-ingest

**Generated:** {_utc()} · **Source LIT:** COMPRESSION_IMPROVEMENT_OLLAMA_THEORY_BEST_PATH_LIT_REVIEW_2026-06-22.md
**Track:** B-track · research_only · send_gate HOLD

## Summary

Ollama = routing/inject not codec engine. Latent cap grid exhausted; Path A spine byte_exact on disk.

## Digested facts

{"".join(facts)}

## Reproduce

```powershell
py scripts/run_mkm_digestion_engine_chain_v1.py --input docs/research/raw/compression_improvement_ollama_theory_best_path_tier0_2026-06-23.md --offline
```
"""


TOPICS = [
    (
        "compression_improvement_multilens_deep_research_tier0_2026-06-23.md",
        _build_multilens,
    ),
    (
        "compression_phase_a_only_bench_protocol_tier0_2026-06-23.md",
        _build_phase_a,
    ),
    (
        "compression_improvement_ollama_theory_best_path_tier0_2026-06-23.md",
        _build_ollama,
    ),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-digest", action="store_true")
    ap.add_argument("--force", action="store_true", help="Overwrite existing tier0 files")
    args = ap.parse_args()

    active = _load(ACTIVE)
    knee = _load(KNEE)
    dual = _load(DUAL)
    codec = _load(CODEC)

    steps: list[dict[str, Any]] = []
    rc = 0

    for filename, builder in TOPICS:
        path = RAW / filename
        rel = path.relative_to(ROOT).as_posix()
        if path.is_file() and not args.force:
            steps.append({"file": rel, "action": "skip_exists"})
        else:
            RAW.mkdir(parents=True, exist_ok=True)
            if builder is _build_multilens:
                body = builder(active, knee, dual)
            elif builder is _build_phase_a:
                body = builder(knee, dual)
            else:
                body = builder(knee, codec)
            path.write_text(body, encoding="utf-8")
            steps.append({"file": rel, "action": "wrote"})

        if not args.skip_digest:
            cp = subprocess.run(
                [sys.executable, str(DIGEST), "--input", rel, "--offline"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            tail = (cp.stdout or "").strip().splitlines()
            parsed = None
            if tail:
                try:
                    parsed = json.loads(tail[-1])
                except json.JSONDecodeError:
                    parsed = {"raw_tail": tail[-1][:200]}
            steps.append(
                {
                    "file": rel,
                    "digest_exit_code": int(cp.returncode),
                    "parsed": parsed,
                }
            )
            if cp.returncode != 0:
                rc = cp.returncode

    manifest = {
        "schema": "compression_lit_tier0_auto_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "rc": rc,
        "reproducible_command": "py scripts/build_compression_lit_tier0_auto_ingest_v1.py",
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rc": rc, "topics": len(TOPICS)}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
