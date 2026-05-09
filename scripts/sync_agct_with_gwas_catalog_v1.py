#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare active AGCT-Sasang weights against GWAS anchor expectations.")
    ap.add_argument(
        "--weights-json",
        type=Path,
        default=Path("tmp/agct_sasang_axis_weights_active_btrack_v1.json"),
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_gwas_alignment_v1_latest.json"),
    )
    ns = ap.parse_args()

    w = _load_json(ns.weights_json)

    # Minimal anchor table from known Sasang GWAS discussion in this workspace.
    # This is B-track alignment logic, not causal/clinical proof.
    anchors = [
        {
            "rsid": "rs10937331",
            "expected_axis": "TE",
            "reason": "Sasang GWAS TE-associated locus (chr3q27.3 proxy).",
            "citation": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3306582/",
        },
        {
            "rsid": "rs12431592",
            "expected_axis": "SY",
            "reason": "Sasang GWAS SY-associated locus (14q22.3 / ALDH1A2 region proxy).",
            "citation": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3306582/",
        },
        {
            "rsid": "rs7180547",
            "expected_axis": "SE",
            "reason": "Sasang GWAS SE-associated locus (15q22.2 / AKAP11 region proxy).",
            "citation": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3306582/",
        },
        {
            "rsid": "rs7193144",
            "expected_axis": "SE",
            "reason": "FTO obesity-risk inverse with So-Eum in replication analyses.",
            "citation": "https://bmccomplementmedtherapies.biomedcentral.com/articles/10.1186/s12906-015-0609-4",
        },
    ]

    # Base-to-axis weights are the tunable model core. We derive a proxy axis preference
    # by identifying which base most strongly activates each expected axis.
    base_axis = {b: w[b] for b in ("A", "C", "G", "T")}
    per_axis_best_base: dict[str, str] = {}
    for axis in ("TY", "SY", "TE", "SE"):
        best = sorted(
            ((b, float(base_axis[b][axis])) for b in ("A", "C", "G", "T")),
            key=lambda kv: kv[1],
            reverse=True,
        )[0][0]
        per_axis_best_base[axis] = best

    # Proxy mapping from rsid to representative base signal used in this engine family.
    rsid_base_proxy = {
        "rs10937331": "G",
        "rs12431592": "C",
        "rs7180547": "T",
        "rs7193144": "T",
    }

    rows = []
    passed = 0
    for a in anchors:
        rsid = a["rsid"]
        expected_axis = a["expected_axis"]
        proxy_base = rsid_base_proxy[rsid]
        expected_weight = float(base_axis[proxy_base][expected_axis])
        top_axis_for_base = sorted(
            ((ax, float(base_axis[proxy_base][ax])) for ax in ("TY", "SY", "TE", "SE")),
            key=lambda kv: kv[1],
            reverse=True,
        )[0][0]
        ok = top_axis_for_base == expected_axis
        passed += 1 if ok else 0
        rows.append(
            {
                "rsid": rsid,
                "expected_axis": expected_axis,
                "proxy_base": proxy_base,
                "top_axis_for_proxy_base": top_axis_for_base,
                "expected_axis_weight": expected_weight,
                "alignment_ok": ok,
                "reason": a["reason"],
                "citation": a["citation"],
            }
        )

    score = passed / len(rows) if rows else 0.0
    payload = {
        "schema": "agct_gwas_alignment_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "weights_json": str(ns.weights_json.resolve()),
        },
        "summary": {
            "anchors_total": len(rows),
            "anchors_aligned": passed,
            "alignment_score": score,
            "alignment_grade": "STRONG" if score >= 0.75 else ("MODERATE" if score >= 0.5 else "WEAK"),
            "per_axis_best_base": per_axis_best_base,
        },
        "anchor_results": rows,
        "notes": [
            "This is GWAS-anchor directional alignment, not causal proof.",
            "Use independent real cohort for final biological validity claims.",
        ],
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} alignment_score={score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
