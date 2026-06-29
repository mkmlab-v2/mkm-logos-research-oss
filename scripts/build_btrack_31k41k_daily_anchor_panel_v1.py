#!/usr/bin/env python3

"""Build per-eval_date 31k/41k anchor panel (Phase 1b, research-only).



Modes:

  timeseries_v1 — per-date density/coverage from verse_4pipeline + daily move sign

  static_global_proxy — legacy panel-static values (comparison only)

"""



from __future__ import annotations



import argparse

import importlib.util

import json

import sys

from datetime import datetime, timezone

from pathlib import Path

from typing import Any



ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json"

DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_31k41k_daily_anchor_panel_v1_latest.json"

DEFAULT_VERSE = ROOT / "data/logos/verse_4pipeline_full_31102.json"

DEFAULT_MAPPING = ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json"





def _load_module(name: str, rel: str):

    path = ROOT / rel

    spec = importlib.util.spec_from_file_location(name, path)

    mod = importlib.util.module_from_spec(spec)

    assert spec.loader

    sys.modules[name] = mod

    spec.loader.exec_module(mod)

    return mod





def _read(path: Path) -> dict[str, Any]:

    if not path.is_file():

        return {}

    try:

        doc = json.loads(path.read_text(encoding="utf-8-sig"))

    except json.JSONDecodeError:

        return {}

    return doc if isinstance(doc, dict) else {}





def _iso_now() -> str:

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")





def main() -> int:

    ap = argparse.ArgumentParser(description=__doc__)

    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)

    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)

    ap.add_argument(

        "--feature-mode",

        choices=("timeseries_v2", "timeseries_v1", "static_global_proxy", "auto"),

        default="auto",

        help="auto = timeseries_v2 when verse JSON exists else static proxy.",

    )

    ap.add_argument(
        "--rolling-sample-size",
        type=int,
        default=256,
        help="Per-eval_date rotating lexicon sample from canon (timeseries_v2).",
    )

    ap.add_argument("--verse-json", type=Path, default=DEFAULT_VERSE)

    ap.add_argument("--logos-mapping-json", type=Path, default=DEFAULT_MAPPING)

    ap.add_argument("--logos-lens-json", type=Path, default=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json")

    ap.add_argument("--hypothesis-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")

    ap.add_argument("--corpus-baseline-json", type=Path, default=ROOT / "docs/final/artifacts/corpus_counting_baseline_comparison_v1_latest.json")
    ap.add_argument(
        "--per-row-density-scale",
        type=float,
        default=1.0,
        help="Multiply per-row logos_anchor_density after build (research contrast; e.g. 0).",
    )

    args = ap.parse_args()



    feat_mod = _load_module("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")

    ts_mod = _load_module("btrack_31k41k_daily_anchor_timeseries_v1", "scripts/btrack_31k41k_daily_anchor_timeseries_v1.py")



    score_doc = _read(args.score_json)

    btc_rows = feat_mod.btc_score_rows(score_doc)

    dates = sorted({str(r.get("eval_date"))[:10] for r in btc_rows})

    by_date = {str(r.get("eval_date"))[:10]: r for r in btc_rows}



    mode = args.feature_mode

    if mode == "auto":

        mode = "timeseries_v2" if args.verse_json.is_file() else "static_global_proxy"



    global_features = feat_mod.compute_all_features(

        logos_mapping_path=args.logos_mapping_json,

        logos_lens_path=args.logos_lens_json,

        hypothesis_path=args.hypothesis_json,

        corpus_baseline_path=args.corpus_baseline_json,

    )

    corpus = _read(args.corpus_baseline_json)

    canon_denom, lexicon_rows = feat_mod.load_operational_denominators(corpus)



    panel_rows: list[dict[str, Any]] = []

    timeseries_ready = False

    verse_ids_loaded: list[str] = []



    if mode in ("timeseries_v1", "timeseries_v2"):

        mapping = _read(args.logos_mapping_json)

        assignment_ids = ts_mod.assignment_verse_ids(mapping)

        if not assignment_ids:

            print(f"[WARN] no assignments in {args.logos_mapping_json}; falling back to static_global_proxy")

            mode = "static_global_proxy"

        elif not args.verse_json.is_file():

            print(f"[WARN] missing {args.verse_json}; falling back to static_global_proxy")

            mode = "static_global_proxy"

        else:

            sample_size = max(0, int(args.rolling_sample_size))

            if mode == "timeseries_v2" and sample_size <= 0:
                mode = "timeseries_v1"

            if mode == "timeseries_v2" and sample_size > 0:

                print(f"[INFO] loading verse catalog from {args.verse_json} ...")

                catalog = ts_mod.load_verse_id_catalog(args.verse_json)

                if not catalog:

                    print("[WARN] empty verse catalog; falling back to timeseries_v1")

                    mode = "timeseries_v1"

                else:

                    union_ids = ts_mod.union_rotating_sample_ids(dates, catalog, sample_size)

                    union_ids.update(assignment_ids)

                    print(

                        f"[INFO] loading {len(union_ids)} verses "

                        f"(assignments={len(assignment_ids)} rotating_union={len(union_ids)}) ..."

                    )

                    verse_by_id = ts_mod.load_verse_subset(args.verse_json, union_ids)

                    verse_ids_loaded = sorted(verse_by_id.keys())

                    for i, d in enumerate(dates):

                        row = by_date.get(d)

                        if not row:

                            continue

                        rotating_ids = ts_mod.rotating_sample_verse_ids(d, i, catalog, sample_size)

                        panel_rows.append(

                            ts_mod.compute_timeseries_row_v2(

                                row,

                                verse_by_id=verse_by_id,

                                assignment_ids=assignment_ids,

                                rotating_ids=rotating_ids,

                                rolling_sample_size=sample_size,

                                canon_denominator=canon_denom,

                                lexicon_rows=lexicon_rows,

                            )

                        )

                    timeseries_ready = bool(panel_rows) and len(verse_by_id) > 0

            if mode == "timeseries_v1":

                verse_by_id = ts_mod.load_verse_subset(args.verse_json, set(assignment_ids))

                verse_ids_loaded = sorted(verse_by_id.keys())

                panel_rows = []

                for d in dates:

                    row = by_date.get(d)

                    if not row:

                        continue

                    panel_rows.append(

                        ts_mod.compute_timeseries_row(

                            row,

                            verse_by_id=verse_by_id,

                            assignment_ids=assignment_ids,

                            canon_denominator=canon_denom,

                            lexicon_rows=lexicon_rows,

                        )

                    )

                timeseries_ready = bool(panel_rows) and len(verse_by_id) > 0



    if mode == "static_global_proxy":

        panel_rows = []

        for d in dates:

            panel_rows.append(

                {

                    "eval_date": d,

                    "logos_anchor_density_31k_v1": global_features["logos_anchor_density_31k_v1"],

                    "lexicon_coverage_41k_v1": global_features["lexicon_coverage_41k_v1"],

                    "anchor_conflict_ratio_v1": global_features["anchor_conflict_ratio_v1"],

                    "feature_mode": "static_global_proxy",

                    "timeseries_ready": False,

                }

            )



    scale = float(args.per_row_density_scale)
    if scale != 1.0:
        for row in panel_rows:
            dens = row.get("logos_anchor_density_31k_v1")
            if isinstance(dens, dict) and dens.get("value") is not None:
                try:
                    dens = dict(dens)
                    dens["value"] = round(float(dens["value"]) * scale, 8)
                    dens["per_row_density_scale"] = scale
                    row["logos_anchor_density_31k_v1"] = dens
                except (TypeError, ValueError):
                    pass

    density_values = [

        (r.get("logos_anchor_density_31k_v1") or {}).get("value")

        for r in panel_rows

        if isinstance(r.get("logos_anchor_density_31k_v1"), dict)

    ]

    n_distinct_density = len({v for v in density_values if v is not None})



    out = {

        "schema": "btrack_31k41k_daily_anchor_panel_v1",

        "generated_at_utc": _iso_now(),

        "research_only": True,

        "non_gating": True,

        "hypothesis_tier": "B",

        "feature_mode": mode,

        "timeseries_ready": timeseries_ready,

        "disclaimer": (
            "timeseries_v2: assignments + per-date rotating lexicon sample (not full-canon scan). "
            "timeseries_v1: assignments only. static_global_proxy: panel-constant values."
        ),

        "inputs": {
            "score_json": str(args.score_json),
            "verse_json": str(args.verse_json) if mode.startswith("timeseries") else None,
            "logos_mapping_json": str(args.logos_mapping_json),
            "rolling_sample_size": int(args.rolling_sample_size) if mode == "timeseries_v2" else None,
            "n_dates": len(dates),
            "assignment_verse_count": len(verse_ids_loaded) if verse_ids_loaded else None,
            "n_distinct_density_values": n_distinct_density,
            "per_row_density_scale": scale if scale != 1.0 else None,
        },

        "global_features": global_features,

        "rows": panel_rows,

        "next_steps": (

            []

            if timeseries_ready

            else [

                "provide verse_4pipeline_full_31102.json and LOGOS_STATE_MAPPING assignments",

                "re-run with --feature-mode timeseries_v1",

            ]

        ),

    }



    args.out_json.parent.mkdir(parents=True, exist_ok=True)

    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out_json}")

    print(

        f"n_dates={len(dates)} feature_mode={mode} timeseries_ready={timeseries_ready} "

        f"n_distinct_density={n_distinct_density}"

    )

    return 0 if panel_rows else 1





if __name__ == "__main__":

    raise SystemExit(main())

