#!/usr/bin/env python3
"""Wave 3 — offline UI resonance simulation for batch cosmic anchors (no CF deploy).

Reproducible:
  py scripts/run_logos_cosmic_anchor_ui_resonance_sim_v1.py

Output:
  docs/final/artifacts/logos_cosmic_anchor_ui_resonance_sim_v1_latest.json
"""

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

from scripts.core.mkmlife_cosmic_anchor_orb_draft_v1 import (
    draft_fingerprint,
    infer_stress_from_orb_context,
    resolve_cosmic_anchor_orb_draft,
)

BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
BATCH_MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_cosmic_anchor_ui_resonance_sim_v1_latest.json"

STRESS_LEVELS = (0.28, 0.35, 0.62, 0.78)

SCENARIO_FIXTURES: list[dict[str, Any]] = [
    {
        "scenario_id": "neutral_orb",
        "question": "",
        "context_blob": "",
        "expected_stress": 0.35,
    },
    {
        "scenario_id": "motif_light_calm",
        "question": "빛 motif — 평안한 관측",
        "context_blob": "회복과 평안",
        "expected_stress": 0.4,
    },
    {
        "scenario_id": "motif_door_watch",
        "question": "문(θυρα) — 길을 찾는 중",
        "context_blob": "스트레스와 긴장",
        "expected_stress": 0.62,
    },
    {
        "scenario_id": "motif_seed_crisis",
        "question": "씨앗 — 고난 속 죽음과 열매",
        "context_blob": "위기 suffering pain",
        "expected_stress": 0.78,
    },
]

UI_PARAMS = (
    "min_padding_px",
    "max_blocks_per_view",
    "intensity_budget",
    "pulse_period_ms",
    "layout_density",
    "contrast_cap",
)


def _load_anchors(batch_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(batch_dir.glob("*.json")):
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    return rows


def _param_diversity(drafts: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in UI_PARAMS:
        vals = [float(d[key]) for d in drafts if key in d]
        if not vals:
            continue
        out[key] = {
            "min": round(min(vals), 4) if isinstance(vals[0], float) else min(vals),
            "max": round(max(vals), 4) if isinstance(vals[0], float) else max(vals),
            "mean": round(statistics.mean(vals), 4),
            "stdev": round(statistics.pstdev(vals), 4) if len(vals) > 1 else 0.0,
            "range": round(max(vals) - min(vals), 4),
            "unique_count": len({round(v, 4) if isinstance(v, float) else v for v in vals}),
        }
    return out


def build_sim(*, batch_dir: Path = BATCH_DIR) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    anchors = _load_anchors(batch_dir)
    manifest = {}
    if BATCH_MANIFEST.is_file():
        manifest = json.loads(BATCH_MANIFEST.read_text(encoding="utf-8"))

    per_anchor: list[dict[str, Any]] = []
    drafts_neutral: list[dict[str, Any]] = []
    fingerprints_neutral: set[str] = set()

    for anchor in anchors:
        aid = anchor.get("anchor_id")
        align = anchor.get("kernel_alignment") or []
        drafts_by_stress: dict[str, Any] = {}
        for stress in STRESS_LEVELS:
            d = resolve_cosmic_anchor_orb_draft(anchor, stress)
            drafts_by_stress[str(stress)] = d
        neutral = drafts_by_stress["0.35"]
        drafts_neutral.append(neutral)
        fingerprints_neutral.add(draft_fingerprint(neutral))

        motif = anchor.get("motif_lemma") or {}
        per_anchor.append(
            {
                "anchor_id": aid,
                "verse_refs": anchor.get("verse_refs") or [],
                "motif_lemma": motif,
                "vector_4d": anchor.get("vector_4d"),
                "top1_primitive": align[0].get("primitive") if align else None,
                "draft_by_stress": drafts_by_stress,
            }
        )

    scenario_runs: list[dict[str, Any]] = []
    lookup = manifest.get("lookup_by_verse_ref") or {}
    scenario_targets = [
        ("Jhn.1.5", "light"),
        ("Jhn.10.9", "door"),
        ("Jhn.12.24", "seed"),
    ]
    anchor_by_id = {a.get("anchor_id"): a for a in anchors}

    for fixture in SCENARIO_FIXTURES:
        stress = infer_stress_from_orb_context(
            fixture.get("question", ""),
            fixture.get("context_blob", ""),
        )
        entry: dict[str, Any] = {
            "scenario_id": fixture["scenario_id"],
            "inferred_stress": stress,
            "expected_stress": fixture["expected_stress"],
            "motif_samples": [],
        }
        for verse_ref, label in scenario_targets:
            anchor_id = lookup.get(verse_ref)
            anchor = anchor_by_id.get(anchor_id)
            if not anchor:
                continue
            draft = resolve_cosmic_anchor_orb_draft(anchor, stress)
            entry["motif_samples"].append(
                {
                    "label": label,
                    "verse_ref": verse_ref,
                    "anchor_id": anchor_id,
                    "orb_draft": draft,
                }
            )
        scenario_runs.append(entry)

    diversity_neutral = _param_diversity(drafts_neutral)
    meaningful_ui_spread = any(
        diversity_neutral.get(k, {}).get("range", 0) > 0 for k in UI_PARAMS
    )

    return {
        "schema": "logos_cosmic_anchor_ui_resonance_sim_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "cf_deploy_required": False,
        "batch_dir": batch_dir.relative_to(ROOT).as_posix(),
        "batch_manifest": BATCH_MANIFEST.relative_to(ROOT).as_posix(),
        "anchor_count": len(anchors),
        "stress_levels": list(STRESS_LEVELS),
        "summary": {
            "distinct_draft_fingerprints_at_stress_0.35": len(fingerprints_neutral),
            "ui_param_diversity_at_stress_0.35": diversity_neutral,
            "meaningful_ui_spread_at_neutral_stress": meaningful_ui_spread,
            "top1_primitive_histogram": _histogram(
                [r["top1_primitive"] for r in per_anchor if r.get("top1_primitive")]
            ),
        },
        "scenario_runs": scenario_runs,
        "per_anchor": per_anchor,
        "reproducible_command": "py scripts/run_logos_cosmic_anchor_ui_resonance_sim_v1.py",
        "notes_ko": (
            "오프라인 공명 시뮬 — mkmlife TS resolveCosmicAnchorOrbDraft Python mirror. "
            "CF redeploy 없음. pilot 3 public wire는 별도 Wave 3b."
        ),
    }


def _histogram(values: list[str]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for v in values:
        hist[v] = hist.get(v, 0) + 1
    return hist


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=BATCH_DIR)
    args = parser.parse_args()
    if not args.batch_dir.is_dir():
        print(f"ERROR: batch dir missing: {args.batch_dir}", file=sys.stderr)
        return 1
    sim = build_sim(batch_dir=args.batch_dir)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sim, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = sim["summary"]
    print(f"WROTE: {OUT}")
    print(
        f"  anchors={sim['anchor_count']} "
        f"fingerprints@0.35={s['distinct_draft_fingerprints_at_stress_0.35']} "
        f"meaningful_spread={s['meaningful_ui_spread_at_neutral_stress']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
