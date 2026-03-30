# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.85, K:0.55, M:0.45}
# Balance: 87
# Purpose: Build state-sasang ops bundle from relaxed intersection and regime probes.
# Keywords: state, sasang, relaxed, checklist, approval, bundle
#!/usr/bin/env python3
"""Build state-sasang operational bundle from relaxed intersection outputs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _cosine_map(path: Path) -> Dict[str, float]:
    doc = _load(path)
    out: Dict[str, float] = {}
    for h in doc.get("hits", []):
        vid = str(h.get("verse_id", "")).strip()
        c = h.get("cosine_to_regime_fingerprint_4d")
        if vid and c is not None:
            out[vid] = float(c)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    root = _root()
    bt = root / "backtest_results"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--intersection",
        type=Path,
        default=bt / "LOGOS_RESONANCE_BTC_EXT_K6866_PROBE_INTERSECTION_TOP6866_RELAXED_N2_C0.json",
    )
    ap.add_argument(
        "--bull",
        type=Path,
        default=bt / "LOGOS_RESONANCE_BTC_EXT_K6866_PROBE_bull_pump_TOP6866.json",
    )
    ap.add_argument(
        "--bear",
        type=Path,
        default=bt / "LOGOS_RESONANCE_BTC_EXT_K6866_PROBE_bear_trend_TOP6866.json",
    )
    ap.add_argument(
        "--sideways",
        type=Path,
        default=bt / "LOGOS_RESONANCE_BTC_EXT_K6866_PROBE_sideways_accumulation_TOP6866.json",
    )
    ap.add_argument(
        "--capitulation",
        type=Path,
        default=bt / "LOGOS_RESONANCE_BTC_EXT_K6866_PROBE_capitulation_TOP6866.json",
    )
    ap.add_argument(
        "--logos-map",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "LOGOS_STATE_MAPPING_V1.json",
    )
    ap.add_argument(
        "--sasang-draft",
        type=Path,
        default=root / "docs" / "final" / "artifacts" / "SASANG_CROSS_REF_DRAFT.json",
    )
    ap.add_argument("--prefix", type=str, default="LOGOS_RESONANCE_BTC_EXT_K6866_RELAXED_N2_C0")
    args = ap.parse_args()

    inter = _load(args.intersection)
    logos = _load(args.logos_map)
    sas = _load(args.sasang_draft)
    relaxed_ids = set(inter.get("relaxed_gate", {}).get("verse_ids", []))

    mbull = _cosine_map(args.bull)
    mbear = _cosine_map(args.bear)
    mside = _cosine_map(args.sideways)
    mcap = _cosine_map(args.capitulation)
    regime_maps = (mbull, mbear, mside, mcap)

    # 1) Bridge
    state_hits: List[Dict[str, Any]] = []
    for row in logos.get("assignments", []):
        vid = str(row.get("verse_id", "")).strip()
        sid = int(row.get("state_id"))
        if vid in relaxed_ids:
            state_hits.append(
                {
                    "state_id": sid,
                    "verse_id": vid,
                    "cosine_state_verse": row.get("cosine_state_verse"),
                }
            )
    state_hits.sort(key=lambda x: x["state_id"])
    sas_rows: List[Dict[str, Any]] = []
    for row in sas.get("entries", []):
        cref = str(row.get("canonical_ref", "")).strip()
        sas_rows.append(
            {
                "entry_id": row.get("entry_id"),
                "sasang_type": row.get("sasang_type"),
                "state_candidate_id": row.get("state_candidate_id"),
                "canonical_ref": cref,
                "in_relaxed_gate": cref in relaxed_ids,
            }
        )
    bridge = {
        "schema": "relaxed_gate_state_sasang_bridge_v1",
        "generated_at_utc": _now(),
        "base_intersection": str(args.intersection),
        "relaxed_count": len(relaxed_ids),
        "state_anchor_hits_count": len(state_hits),
        "state_anchor_hits": state_hits,
        "sasang_anchor_rows": sas_rows,
        "sasang_anchor_hit_count": sum(1 for r in sas_rows if r["in_relaxed_gate"]),
    }
    bridge_path = bt / f"{args.prefix}_STATE_SASANG_BRIDGE.json"
    _write(bridge_path, bridge)

    # 2) Anchor-only priority rows
    state_by_verse = {r["verse_id"]: r for r in state_hits}
    sas_by_verse: Dict[str, List[Dict[str, Any]]] = {}
    for r in sas_rows:
        vid = r["canonical_ref"]
        if vid:
            sas_by_verse.setdefault(vid, []).append(
                {
                    "entry_id": r["entry_id"],
                    "sasang_type": r["sasang_type"],
                    "state_candidate_id": r["state_candidate_id"],
                }
            )
    anchor_rows: List[Dict[str, Any]] = []
    for vid in sorted(relaxed_ids):
        vals = [m[vid] for m in regime_maps if vid in m]
        if len(vals) < 2:
            continue
        st = state_by_verse.get(vid)
        sl = sas_by_verse.get(vid, [])
        if st is None and not sl:
            continue
        anchor_rows.append(
            {
                "verse_id": vid,
                "support_regimes": len(vals),
                "mean_cosine": round(sum(vals) / len(vals), 6),
                "bottleneck_cosine": round(min(vals), 6),
                "state_anchor": st,
                "sasang_links": sl,
            }
        )
    anchor_rows.sort(
        key=lambda r: (
            -r["support_regimes"],
            -r["mean_cosine"],
            -r["bottleneck_cosine"],
            r["verse_id"],
        )
    )
    prio = {
        "schema": "state_sasang_priority_report_v1",
        "variant": "anchor_only",
        "generated_at_utc": _now(),
        "generated_from": str(args.intersection),
        "hit_count": len(anchor_rows),
        "hits": anchor_rows,
    }
    prio_path = bt / f"{args.prefix}_STATE_SASANG_PRIORITY_ANCHOR_ONLY.json"
    _write(prio_path, prio)

    # 3) Ops summary
    state_summary: List[Dict[str, Any]] = []
    by_state: Dict[int, List[Dict[str, Any]]] = {}
    sasang_type_counts: Dict[str, int] = {}
    for h in anchor_rows:
        st = h.get("state_anchor") or {}
        sid = st.get("state_id")
        if sid is None:
            continue
        by_state.setdefault(int(sid), []).append(h)
        for s in h.get("sasang_links", []):
            t = str(s.get("sasang_type"))
            sasang_type_counts[t] = sasang_type_counts.get(t, 0) + 1
    for sid in sorted(by_state):
        rows = by_state[sid]
        best = rows[0]
        state_summary.append(
            {
                "state_id": sid,
                "anchor_count": len(rows),
                "best_verse_id": best["verse_id"],
                "best_mean_cosine": best["mean_cosine"],
                "best_bottleneck_cosine": best["bottleneck_cosine"],
                "sasang_types_union": sorted(
                    {str(s.get("sasang_type")) for r in rows for s in r.get("sasang_links", [])}
                ),
                "one_line": (
                    f"state_{sid} best anchor {best['verse_id']} "
                    f"(mean={best['mean_cosine']}, bottleneck={best['bottleneck_cosine']})"
                ),
            }
        )
    ops = {
        "schema": "state_sasang_priority_ops_summary_v1",
        "generated_at_utc": _now(),
        "source": str(prio_path),
        "total_anchor_hits": len(anchor_rows),
        "state_summary": state_summary,
        "sasang_type_counts": sasang_type_counts,
        "hits": anchor_rows,
    }
    ops_path = bt / f"{args.prefix}_STATE_SASANG_OPS_SUMMARY.json"
    _write(ops_path, ops)

    # 4) Top5 priority
    scored = []
    for row in state_summary:
        mean = float(row.get("best_mean_cosine", 0.0))
        bott = float(row.get("best_bottleneck_cosine", 0.0))
        anchor = int(row.get("anchor_count", 0))
        sas_bonus = 0.02 if row.get("sasang_types_union") else 0.0
        score = 0.6 * mean + 0.3 * bott + 0.1 * min(anchor, 3) / 3.0 + sas_bonus
        scored.append({**row, "priority_score": round(score, 6)})
    scored.sort(
        key=lambda x: (
            -x["priority_score"],
            -float(x.get("best_mean_cosine", 0.0)),
            -float(x.get("best_bottleneck_cosine", 0.0)),
        )
    )
    top5 = []
    for i, row in enumerate(scored[:5], start=1):
        top5.append(
            {
                "rank": i,
                "state_id": row["state_id"],
                "priority_score": row["priority_score"],
                "best_verse_id": row["best_verse_id"],
                "best_mean_cosine": row["best_mean_cosine"],
                "best_bottleneck_cosine": row["best_bottleneck_cosine"],
                "sasang_types_union": row["sasang_types_union"],
                "one_line": row["one_line"],
            }
        )
    top5_doc = {
        "schema": "state_execution_priority_top5_v1",
        "generated_at_utc": _now(),
        "source_ops_summary": str(ops_path),
        "total_states": len(scored),
        "top5": top5,
    }
    top5_path = bt / f"{args.prefix}_STATE_EXECUTION_PRIORITY_TOP5.json"
    _write(top5_path, top5_doc)

    # 5) Checklist + evaluation + approval packet
    checklist_items: List[Dict[str, Any]] = []
    for row in top5:
        level = "green" if float(row["priority_score"]) >= 0.15 else ("yellow" if float(row["priority_score"]) >= 0.08 else "red")
        checklist_items.append(
            {
                "state_id": row["state_id"],
                "rank": row["rank"],
                "priority_score": row["priority_score"],
                "target_verse_id": row["best_verse_id"],
                "sasang_types_union": row["sasang_types_union"],
                "input_checklist": [
                    {"id": "I1", "check": "Verse in relaxed pool", "status": "pending"},
                    {"id": "I2", "check": "Regime cosine tuple present", "status": "pending"},
                    {"id": "I3", "check": "State anchor match", "status": "pending"},
                ],
                "validation_checklist": [
                    {"id": "V1", "check": "support_regimes >= 2", "status": "pending"},
                    {"id": "V2", "check": "mean/bottleneck present", "status": "pending"},
                    {"id": "V3", "check": "all probe files present", "status": "pending"},
                ],
                "risk_gate": {
                    "level": level,
                    "rules": [
                        "B-track only; no A-track auto-merge",
                        "Human approval needed for threshold-policy changes",
                        "Hold if bottleneck_cosine drops below -0.2",
                    ],
                },
            }
        )
    checklist = {
        "schema": "state_execution_checklist_top5_v1",
        "generated_at_utc": _now(),
        "source_priority_top5": str(top5_path),
        "generated_count": len(checklist_items),
        "items": checklist_items,
    }
    checklist_path = bt / f"{args.prefix}_STATE_EXECUTION_CHECKLIST_TOP5.json"
    _write(checklist_path, checklist)

    state_anchor_map = {int(s["state_id"]): s["verse_id"] for s in state_hits}
    evaluated_items = []
    passed = 0
    for item in checklist_items:
        vid = str(item["target_verse_id"])
        sid = int(item["state_id"])
        vals = [m[vid] for m in regime_maps if vid in m]
        support = len(vals)
        i1 = vid in relaxed_ids
        i2 = bool(vals)
        i3 = state_anchor_map.get(sid) == vid
        v1 = support >= 2
        v2 = bool(vals)
        v3 = all(p.is_file() for p in (args.bull, args.bear, args.sideways, args.capitulation))
        flags = {"I1": i1, "I2": i2, "I3": i3, "V1": v1, "V2": v2, "V3": v3}
        for block_name in ("input_checklist", "validation_checklist"):
            for c in item[block_name]:
                c["status"] = "pass" if flags.get(c["id"], False) else "fail"
        item["computed_metrics"] = {
            "support_regimes_observed": support,
            "mean_cosine_observed": (sum(vals) / len(vals)) if vals else None,
            "bottleneck_cosine_observed": min(vals) if vals else None,
        }
        item["overall_status"] = "pass" if all(flags.values()) else "fail"
        if item["overall_status"] == "pass":
            passed += 1
        evaluated_items.append(item)
    evaluated = {
        "schema": "state_execution_checklist_evaluation_v1",
        "generated_at_utc": _now(),
        "source_checklist": str(checklist_path),
        "items": evaluated_items,
        "evaluation": {
            "passed_items": passed,
            "total_items": len(evaluated_items),
            "pass_rate": passed / max(1, len(evaluated_items)),
        },
    }
    evaluated_path = bt / f"{args.prefix}_STATE_EXECUTION_CHECKLIST_TOP5_EVALUATED.json"
    _write(evaluated_path, evaluated)

    approval_items = []
    go = 0
    for item in evaluated_items:
        m = item.get("computed_metrics", {})
        bott = m.get("bottleneck_cosine_observed")
        decision = "go" if item.get("overall_status") == "pass" and bott is not None and float(bott) >= -0.2 else "hold"
        reasons = ["all_gates_passed"] if decision == "go" else ["checklist_or_guardrail_failed"]
        approval_items.append(
            {
                "state_id": item.get("state_id"),
                "decision": decision,
                "risk_level": item.get("risk_gate", {}).get("level"),
                "target_verse_id": item.get("target_verse_id"),
                "priority_score": item.get("priority_score"),
                "support_regimes_observed": m.get("support_regimes_observed"),
                "mean_cosine_observed": m.get("mean_cosine_observed"),
                "bottleneck_cosine_observed": bott,
                "reasons": reasons,
            }
        )
        if decision == "go":
            go += 1
    approval = {
        "schema": "state_execution_approval_packet_v1",
        "generated_at_utc": _now(),
        "source_evaluated_checklist": str(evaluated_path),
        "total_items": len(approval_items),
        "go_count": go,
        "hold_count": len(approval_items) - go,
        "items": approval_items,
    }
    approval_path = bt / f"{args.prefix}_STATE_EXECUTION_APPROVAL_PACKET_TOP5.json"
    _write(approval_path, approval)

    print(
        json.dumps(
            {
                "ok": True,
                "bridge": str(bridge_path),
                "priority_anchor_only": str(prio_path),
                "ops_summary": str(ops_path),
                "priority_top5": str(top5_path),
                "checklist": str(checklist_path),
                "evaluated": str(evaluated_path),
                "approval_packet": str(approval_path),
                "go_count": go,
                "hold_count": len(approval_items) - go,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
