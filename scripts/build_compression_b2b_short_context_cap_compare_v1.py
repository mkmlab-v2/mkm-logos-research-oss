#!/usr/bin/env python3
"""Compare B2B PoC arms: economy overlay vs fidelity vs short-cap vs literal. [HYPO]"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/compression_b2b_short_context_cap_compare_v1_latest.json"
JACCARD_FLOOR = 0.73
HIGH_SAVING = 0.40


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _collapse_count(cases: list[dict[str, Any]]) -> int:
    n = 0
    for c in cases:
        if not isinstance(c, dict):
            continue
        jac = float(c.get("jaccard_proxy") or 0.0)
        saving = float(c.get("token_saving_rate_proxy") or 0.0)
        if saving >= HIGH_SAVING and jac < JACCARD_FLOOR:
            n += 1
    return n


def _arm_summary(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    cases = doc.get("cases") if isinstance(doc.get("cases"), list) else []
    cc = doc.get("case_count") or len(cases)
    cp = doc.get("cases_passed") or 0
    agg = doc.get("aggregate") or {}
    sku = (doc.get("sku_context") or {}).get("external_sku")
    return {
        "report_path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "external_sku": sku,
        "compression_profile": doc.get("compression_profile"),
        "short_context_policy": doc.get("short_context_policy"),
        "case_count": cc,
        "cases_passed": cp,
        "pass_rate": round(cp / cc, 4) if cc else 0.0,
        "mean_jaccard_all_cases": agg.get("mean_jaccard_proxy_all_cases"),
        "mean_saving_all_cases": agg.get("mean_token_saving_rate_proxy_all_cases"),
        "high_saving_jaccard_collapse_count": _collapse_count(cases),
    }


def build(arm_reports: dict[str, Path]) -> dict[str, Any]:
    by_sku: dict[str, list[dict[str, Any]]] = {}
    for key, path in arm_reports.items():
        if not path.is_file():
            continue
        arm_name = key.split(":", 1)[0] if ":" in key else key
        row = _arm_summary(path)
        row["arm"] = arm_name
        sku = str(row.get("external_sku") or "unknown")
        by_sku.setdefault(sku, []).append(row)

    winners: list[dict[str, Any]] = []
    for sku, rows in by_sku.items():
        if not rows:
            continue
        best = max(rows, key=lambda r: (r.get("pass_rate") or 0.0, r.get("mean_jaccard_all_cases") or 0.0))
        baseline = next((r for r in rows if r.get("arm") == "economy_overlay"), rows[0])
        winners.append(
            {
                "external_sku": sku,
                "best_arm": best.get("arm"),
                "best_pass_rate": best.get("pass_rate"),
                "best_collapse_count": best.get("high_saving_jaccard_collapse_count"),
                "baseline_pass_rate": baseline.get("pass_rate"),
                "baseline_collapse_count": baseline.get("high_saving_jaccard_collapse_count"),
                "delta_pass_rate_pp": round(100 * ((best.get("pass_rate") or 0) - (baseline.get("pass_rate") or 0)), 2),
                "delta_collapse": (baseline.get("high_saving_jaccard_collapse_count") or 0)
                - (best.get("high_saving_jaccard_collapse_count") or 0),
            }
        )

    return {
        "schema": "compression_b2b_short_context_cap_compare_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "jaccard_floor_ref": JACCARD_FLOOR,
        "high_saving_threshold": HIGH_SAVING,
        "arms": list(arm_reports.keys()),
        "by_sku": by_sku,
        "winners": winners,
        "summary": {
            "sku_count": len(by_sku),
            "any_improved_pass_rate": any((w.get("delta_pass_rate_pp") or 0) > 0 for w in winners),
            "note_ko": "short_cap = economy+overlay+threshold40+max_saving0.35+min_floor0",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    skus = {
        "MKM-SCM-A1": "scm_a1",
        "MKM-CHAT-D1": "chat_d1",
        "MKM-FIN-E1": "fin_e1",
        "MKM-MED-G1": "med_g1",
    }
    arm_suffix = {
        "economy_overlay": "overlay",
        "fidelity_overlay": "fidelity_overlay",
        "short_cap_overlay": "shortcap_overlay",
        "literal_overlay": "literal_overlay",
    }
    arm_reports: dict[str, Path] = {}
    for arm, suffix in arm_suffix.items():
        for external, slug in skus.items():
            p = ROOT / f"reports/customer_compression_stateless_poc_{slug}_{suffix}_v1_latest.json"
            if p.is_file():
                arm_reports[f"{arm}:{external}"] = p

    doc = build(arm_reports)
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "winners": doc.get("winners")}, ensure_ascii=False))
    return 0 if doc.get("by_sku") else 1


if __name__ == "__main__":
    raise SystemExit(main())
