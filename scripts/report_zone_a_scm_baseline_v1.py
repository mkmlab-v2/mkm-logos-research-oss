#!/usr/bin/env python3
"""Baseline for zone_a_scm: router cohort, simulated must_keep + lexicon bloat, probe metrics, v4 S_real.

Uses current DomainSpecificRouter (includes Hangul ratio fallback). Simulates evaluate_report effective_must_keep
for strategy=A, intensity=extreme (hard + soft + master lexicon when available).

Optional ``--with-boming-jiju-lexicon`` merges ``scm_boming_jiju_lexicon_v1`` token hits into a parallel
``effective_must_keep_*_with_boming`` count for A/B must_keep bloat comparison. Integrity v4 ``S_real`` is still
computed from the probe JSON (reconstructed vs raw); it does not change unless the probe is regenerated with a
pipeline that consumes the extended must_keep set.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.calculate_integrity_cost_v4 import evaluate_v4  # noqa: E402
from scripts.core.domain_router import DomainSpecificRouter  # noqa: E402
from scripts.core.master_codebook_lexicon_v1_bridge import (  # noqa: E402
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
)
from scripts.core.scm_boming_jiju_lexicon_v1 import (  # noqa: E402
    DEFAULT_LEXICON_PATH as DEFAULT_BOMING_LEXICON_PATH,
    boming_jiju_hits_for_text,
)

DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_PROBE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_V2_UNIVERSAL_SHARD_PROBE_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "ZONE_A_SCM_BASELINE_V1.json"
SHARDS_ROOT = ROOT / "codebook" / "shards"


def simulate_effective_must_keep_a_extreme(
    raw: str,
    route: Any,
    *,
    cb_path: Path | None,
    boming_path: Path | None = None,
) -> tuple[set[str], dict[str, Any], set[str], dict[str, Any] | None]:
    """Match report_multilens_performance_eval A/extreme: hard + soft + lexicon.

    If ``boming_path`` is set and exists, also returns ``effective | boming_hits`` for overlay counts.
    """
    effective: set[str] = set()
    effective.update(str(x).lower() for x in route.must_keep_hard_terms)
    effective.update(str(x).lower() for x in route.must_keep_soft_terms)
    meta: dict[str, Any] = {"lexicon": None}
    if cb_path is not None and cb_path.is_file():
        hits, lmeta = lexicon_hits_for_text(raw, cb_path)
        effective.update(hits)
        meta["lexicon"] = lmeta
    else:
        meta["lexicon"] = {"status": "skipped", "reason": "export_not_found"}

    boming_meta: dict[str, Any] | None = None
    boming_raw_hits: set[str] = set()
    effective_with_boming = set(effective)
    if boming_path is not None and boming_path.is_file():
        boming_raw_hits, boming_meta = boming_jiju_hits_for_text(raw, boming_path)
        effective_with_boming |= boming_raw_hits
    return effective, meta, effective_with_boming, boming_meta, boming_raw_hits


def main() -> int:
    ap = argparse.ArgumentParser(description="zone_a_scm baseline: must_keep bloat + probe + v4.")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--probe-report", type=Path, default=DEFAULT_PROBE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-gap-bytes", type=int, default=1)
    ap.add_argument("--codebook", type=Path, default=None, help="Override master codebook lexicon path.")
    ap.add_argument(
        "--with-boming-jiju-lexicon",
        action="store_true",
        help="Merge scm_boming_jiju_lexicon_v1 hits into parallel must_keep counts (see --boming-jiju-lexicon-path).",
    )
    ap.add_argument(
        "--boming-jiju-lexicon-path",
        type=Path,
        default=None,
        help=f"Override 보명지주 JSON (default: {DEFAULT_BOMING_LEXICON_PATH.name}).",
    )
    args = ap.parse_args()

    inp_path = Path(args.input).resolve()
    if not inp_path.is_file():
        print("FAIL: input not found", inp_path, file=sys.stderr)
        return 1

    inp = json.loads(inp_path.read_text(encoding="utf-8"))
    cases = inp.get("compression_cases") or []
    router = DomainSpecificRouter(SHARDS_ROOT)
    cb_path = Path(args.codebook).resolve() if args.codebook else resolve_latest_codebook_path()
    boming_path: Path | None = None
    if args.with_boming_jiju_lexicon:
        boming_path = Path(args.boming_jiju_lexicon_path).resolve() if args.boming_jiju_lexicon_path else DEFAULT_BOMING_LEXICON_PATH.resolve()

    zone_a_ids: list[str] = []
    per_case: list[dict[str, Any]] = []
    for c in cases:
        raw = str(c.get("raw_text", ""))
        cid = str(c.get("id", ""))
        route = router.route(raw)
        if route.shard_id != "zone_a_scm":
            continue
        zone_a_ids.append(cid)
        eff, mmeta, eff_boming, bmeta, boming_raw = simulate_effective_must_keep_a_extreme(
            raw, route, cb_path=cb_path, boming_path=boming_path
        )
        row: dict[str, Any] = {
            "id": cid,
            "effective_must_keep_count": len(eff),
            "effective_must_keep_sample": sorted(eff)[:32],
            "lexicon_meta": mmeta.get("lexicon"),
        }
        if boming_path is not None:
            net_new = eff_boming - eff
            row["effective_must_keep_count_with_boming_jiju"] = len(eff_boming)
            row["boming_jiju_lexicon_matched_terms"] = sorted(boming_raw)[:32]
            row["boming_jiju_net_new_terms_vs_baseline"] = sorted(net_new)[:32]
            row["boming_jiju_lexicon_meta"] = bmeta
        per_case.append(row)

    n = len(zone_a_ids)
    counts = [p["effective_must_keep_count"] for p in per_case]
    avg_mk = sum(counts) / n if n else 0.0
    max_mk = max(counts) if counts else 0
    counts_b: list[int] = []
    raw_match_total = 0
    net_new_total = 0
    if boming_path is not None:
        counts_b = [int(p["effective_must_keep_count_with_boming_jiju"]) for p in per_case]
        for p in per_case:
            meta = p.get("boming_jiju_lexicon_meta") or {}
            raw_match_total += int(meta.get("hit_count") or 0)
            net_new_total += len(p.get("boming_jiju_net_new_terms_vs_baseline") or [])
    avg_mk_b = sum(counts_b) / len(counts_b) if counts_b else None
    max_mk_b = max(counts_b) if counts_b else None

    probe_path = Path(args.probe_report).resolve()
    probe_metrics: dict[str, Any] = {"probe_report": str(probe_path.relative_to(ROOT)).replace("\\", "/")}
    if probe_path.is_file():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        rows = (probe.get("compression_metrics") or {}).get("cases") or []
        by_id = {str(r.get("id")): r for r in rows}
        tok_savings: list[float] = []
        jaccs: list[float] = []
        for cid in zone_a_ids:
            r = by_id.get(cid)
            if not r:
                continue
            ts = r.get("token_saving_rate")
            if ts is not None:
                tok_savings.append(float(ts))
            j = r.get("reconstruction_fidelity_jaccard")
            if j is not None:
                jaccs.append(float(j))
        probe_metrics.update(
            {
                "cases_matched_in_probe": len(tok_savings),
                "mean_token_saving_rate_zone_a_cohort": sum(tok_savings) / len(tok_savings) if tok_savings else None,
                "mean_jaccard_zone_a_cohort": sum(jaccs) / len(jaccs) if jaccs else None,
            }
        )
    else:
        probe_metrics["error"] = "probe_report_missing"

    v4_summary: dict[str, Any] | None = None
    if probe_path.is_file():
        probe_doc = json.loads(probe_path.read_text(encoding="utf-8"))
        raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in cases}
        summ, _ = evaluate_v4(
            probe_doc,
            raw_by_id,
            merge_gap_bytes=int(args.merge_gap_bytes),
            shard_filter="zone_a_scm",
            include_case_rows=False,
        )
        v4_summary = dict(summ)

    payload = {
        "schema": "zone_a_scm_baseline_v1",
        "description": (
            "Router cohort zone_a_scm; must_keep simulated as A/extreme + lexicon. "
            "Probe metrics joined by id; v4 uses report-embedded route.shard_id filter."
        ),
        "source_input": str(inp_path.relative_to(ROOT)).replace("\\", "/"),
        "simulation": {
            "strategy": "A",
            "intensity": "extreme",
            "merge_soft_terms": True,
            "master_codebook_path": str(cb_path) if cb_path and cb_path.is_file() else None,
            "boming_jiju_lexicon_enabled": bool(boming_path),
            "boming_jiju_lexicon_path": str(boming_path).replace("\\", "/") if boming_path else None,
        },
        "summary": {
            "zone_a_scm_case_count": n,
            "zone_a_scm_ids": zone_a_ids,
            "effective_must_keep_count_avg": avg_mk,
            "effective_must_keep_count_max": max_mk,
            "effective_must_keep_count_avg_with_boming_jiju": avg_mk_b,
            "effective_must_keep_count_max_with_boming_jiju": max_mk_b,
            "boming_jiju_lexicon_raw_match_count_sum": raw_match_total if boming_path else None,
            "boming_jiju_net_new_term_instances_sum": net_new_total if boming_path else None,
        },
        "integrity_v4_note": (
            "global_real_saving_vs_raw is from probe rows (reconstructed vs raw); "
            "boming_jiju overlay does not alter v4 unless compression is re-run with that must_keep."
        ),
        "probe_join": probe_metrics,
        "integrity_cost_v4_merge_gap": int(args.merge_gap_bytes),
        "integrity_v4_summary_shard_filter_zone_a_scm": v4_summary,
        "per_case": per_case,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    line = f"OK: zone_a_scm n={n} avg_must_keep={avg_mk:.2f} max={max_mk}"
    if avg_mk_b is not None:
        line += f" avg_with_boming={avg_mk_b:.2f} max_with_boming={max_mk_b}"
    print(f"{line} wrote {out_path}")
    if v4_summary:
        print(
            f"     v4 global_real_saving_vs_raw (probe shard filter)={v4_summary.get('global_real_saving_vs_raw')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
