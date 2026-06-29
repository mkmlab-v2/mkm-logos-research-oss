#!/usr/bin/env python3
"""Build dynamic_resonance_stats from sandbox batch + force lexicon + geumhwa ([HYPO])."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_dynamic_tuning_v1 import orb_ui_hints_from_dynamic, tune_anchor_vector
from scripts.core.logos_fundamental_force_lexicon_v1 import primitive_to_force

SANDBOX_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_sandbox_v1"
OUT_ART = ROOT / "docs/final/artifacts/logos_dynamic_resonance_stats_v1_latest.json"
OUT_PUBLIC = (
    ROOT / "projects/mkm/mkm-life/public/data/logos_dynamic_resonance_sidecar_v1.json"
)
PRESET_MAP = {
    "job_suffering_reason": "cosmic_anchor_seed_jhn_12_24",
    "motif_light": "cosmic_anchor_light_jhn_1_5",
    "motif_door": "cosmic_anchor_door_jhn_10_9",
}


def build_dynamic_stats(
    *,
    sandbox_dir: Path = SANDBOX_DIR,
    session_age: float = 1.0,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    per_anchor: list[dict[str, Any]] = []
    spreads_sandbox: list[float] = []
    spreads_dynamic: list[float] = []

    for path in sorted(sandbox_dir.glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        align = row.get("kernel_alignment") or []
        top_primitive = align[0].get("primitive") if align else None
        force_row = primitive_to_force(str(top_primitive)) if top_primitive else None
        force_id = force_row.get("force_id") if force_row else None
        tuned = tune_anchor_vector(row, force_id=force_id, session_age=session_age)
        v_dyn = tuned.get("vector_4d_dynamic")
        if not v_dyn:
            continue
        spreads_sandbox.append(float(tuned["spread_4d_sandbox"]))
        spreads_dynamic.append(float(tuned["spread_4d_dynamic"]))
        ui = orb_ui_hints_from_dynamic(
            v_dyn,
            geumhwa_index_val=float(tuned["geumhwa_index"]),
            decay_factor=float(tuned["geumhwa_decay_factor"]),
        )
        per_anchor.append(
            {
                "anchor_id": row.get("anchor_id"),
                "file_stem": path.stem,
                "verse_refs": row.get("verse_refs") or [],
                **tuned,
                "orb_ui_hints": ui,
            }
        )

    mean_sandbox = statistics.mean(spreads_sandbox) if spreads_sandbox else 0.0
    mean_dynamic = statistics.mean(spreads_dynamic) if spreads_dynamic else 0.0
    by_id = {r["anchor_id"]: r for r in per_anchor if r.get("anchor_id")}
    preset_sidecar = {
        preset: by_id[aid] for preset, aid in PRESET_MAP.items() if aid in by_id
    }

    return {
        "schema": "logos_dynamic_resonance_stats_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "materialize_batch": False,
        "production_kernel_recipe_id": "gematria_bridge_v1",
        "sandbox_kernel_recipe_id": "gematria_bridge_sandbox_v1",
        "inputs": {
            "sandbox_batch_dir": sandbox_dir.relative_to(ROOT).as_posix(),
            "force_lexicon": "docs/final/artifacts/logos_fundamental_force_lexicon_v1.json",
            "geumhwa_exchange": "docs/verified_knowledge_base/unified_field_theory/geumhwa_exchange.json",
        },
        "session_age": session_age,
        "summary": {
            "anchor_count": len(per_anchor),
            "mean_spread_4d_sandbox": round(mean_sandbox, 6),
            "mean_spread_4d_dynamic": round(mean_dynamic, 6),
            "spread_delta_dynamic_minus_sandbox": round(mean_dynamic - mean_sandbox, 6),
            "mean_spread_4d_dynamic_min_target": 0.05,
            "dynamic_spread_target_met": mean_dynamic >= 0.05,
        },
        "theory_to_code_pointer": "docs/final/artifacts/logos_theory_to_code_pointer_v1_latest.json",
        "per_anchor": per_anchor,
        "preset_sidecar": preset_sidecar,
        "reproducible_command": "py scripts/run_logos_dynamic_tuning_chain_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sandbox-dir", type=Path, default=SANDBOX_DIR)
    parser.add_argument("--out-artifact", type=Path, default=OUT_ART)
    parser.add_argument("--out-public", type=Path, default=OUT_PUBLIC)
    parser.add_argument("--session-age", type=float, default=1.0)
    args = parser.parse_args()

    if not args.sandbox_dir.is_dir():
        print(f"FAIL: missing sandbox dir {args.sandbox_dir}", file=sys.stderr)
        return 1

    doc = build_dynamic_stats(sandbox_dir=args.sandbox_dir, session_age=args.session_age)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_public.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(payload, encoding="utf-8")

    public_doc = {
        "schema": "logos_dynamic_resonance_sidecar_v1",
        "version": "1.0.0",
        "generated_at_utc": doc["generated_at_utc"],
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "preset_sidecar": doc["preset_sidecar"],
        "summary": doc["summary"],
        "disclaimer_ko": (
            "[HYPO] sandbox 동역학 sidecar — production batch·커널·Track A 미합선."
        ),
    }
    args.out_public.write_text(
        json.dumps(public_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"WROTE: {args.out_artifact}\n"
        f"  anchors={doc['summary']['anchor_count']} "
        f"mean_spread_dynamic={doc['summary']['mean_spread_4d_dynamic']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
