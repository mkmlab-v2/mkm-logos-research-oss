#!/usr/bin/env python3
"""Per-row failure panel for B2B industry PoC (Jaccard collapse vs high saving). [HYPO]"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/compression_b2b_industry_failure_panel_v1_latest.json"
JACCARD_FLOOR = 0.73
HIGH_SAVING_THRESHOLD = 0.40


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _classify(row: dict[str, Any]) -> str:
    jac = float(row.get("jaccard_proxy") or 0.0)
    saving = float(row.get("token_saving_rate_proxy") or 0.0)
    if row.get("ok"):
        return "pass"
    if saving >= HIGH_SAVING_THRESHOLD and jac < JACCARD_FLOOR:
        return "high_saving_jaccard_collapse"
    if jac < JACCARD_FLOOR:
        return "jaccard_below_floor"
    return "other_fail"


def _panel_from_poc(doc: dict[str, Any]) -> dict[str, Any]:
    cases = doc.get("cases") if isinstance(doc.get("cases"), list) else []
    sku = (doc.get("sku_context") or {}).get("external_sku")
    overlay = doc.get("must_keep_overlay") or {}
    failures: list[dict[str, Any]] = []
    by_class: dict[str, int] = {}
    for c in cases:
        if not isinstance(c, dict):
            continue
        cls = _classify(c)
        by_class[cls] = by_class.get(cls, 0) + 1
        if cls != "pass":
            failures.append(
                {
                    "id": c.get("id"),
                    "failure_class": cls,
                    "token_saving_rate_proxy": c.get("token_saving_rate_proxy"),
                    "jaccard_proxy": c.get("jaccard_proxy"),
                    "router_shard_id": c.get("router_shard_id"),
                }
            )
    cc = doc.get("case_count") or len(cases)
    cp = doc.get("cases_passed") or 0
    return {
        "external_sku": sku,
        "poc_report_path": doc.get("_source_path"),
        "loss_profile": doc.get("loss_profile"),
        "must_keep_overlay_applied": bool(overlay.get("applied")),
        "must_keep_overlay_term_count": overlay.get("term_count"),
        "case_count": cc,
        "cases_passed": cp,
        "pass_rate": round(cp / cc, 4) if cc else 0.0,
        "failure_class_counts": by_class,
        "failures": failures[:40],
        "failures_truncated": len(failures) > 40,
    }


def build(*, poc_paths: list[Path]) -> dict[str, Any]:
    panels: list[dict[str, Any]] = []
    for p in poc_paths:
        if not p.is_file():
            continue
        doc = json.loads(p.read_text(encoding="utf-8-sig"))
        doc["_source_path"] = p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p)
        panels.append(_panel_from_poc(doc))
    total_fail = sum(
        (p.get("failure_class_counts") or {}).get("high_saving_jaccard_collapse", 0) for p in panels
    )
    return {
        "schema": "compression_b2b_industry_failure_panel_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_only": True,
        "jaccard_floor_ref": JACCARD_FLOOR,
        "high_saving_threshold": HIGH_SAVING_THRESHOLD,
        "sku_panels": panels,
        "summary": {
            "sku_count": len(panels),
            "total_high_saving_jaccard_collapse": total_fail,
            "note_ko": "high_saving_jaccard_collapse = saving≥40% & J<0.73 — 과압축 본진 패널",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--poc-json",
        type=Path,
        action="append",
        default=[],
        help="PoC report JSON (repeatable). Default: industry SKU overlay reports if present.",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    paths = [p.resolve() for p in args.poc_json] if args.poc_json else []
    if not paths:
        for slug in ("scm_a1", "chat_d1", "fin_e1", "med_g1"):
            p = ROOT / f"reports/customer_compression_stateless_poc_{slug}_overlay_v1_latest.json"
            if p.is_file():
                paths.append(p)

    doc = build(poc_paths=paths)
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out), "sku_count": len(doc["sku_panels"])}, ensure_ascii=False))
    return 0 if doc["sku_panels"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
