#!/usr/bin/env python3
"""Validate UNIVERSAL_ROOT_GATE_SPEC_V1.json and evaluate metric planes vs latest artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"
DEFAULT_SCHEMA = ROOT / "docs/final/schemas/universal_root_gate_spec_v1.schema.json"
DEFAULT_OUT = ROOT / "reports/universal_root_gate_eval_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_schema(spec: dict[str, Any], schema_path: Path) -> tuple[bool, str | None]:
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return True, "jsonschema_not_installed_skipped"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=spec, schema=schema)
    return True, None


def _eval_distortion(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    thr = (gates.get("distortion") or {}).get("thresholds") or {}
    ptr = (spec.get("artifact_pointers") or {}).get("nsm_audit_latest", "")
    raw_ptr = (spec.get("artifact_pointers") or {}).get(
        "nsm_audit_raw_latest", "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json"
    )
    audit = _read_json(ROOT / ptr) if ptr else None
    audit_raw = _read_json(ROOT / raw_ptr) if raw_ptr else None
    base = (audit or {}).get("baseline") or {}
    base_raw = (audit_raw or {}).get("baseline") or {}
    observed = {
        "audit_mode": audit.get("audit_mode") if audit else None,
        "pair_count": base.get("pair_count"),
        "prime_hit_rate": base.get("prime_hit_rate"),
        "english_only_distortion_rate": base.get("english_only_distortion_rate"),
        "negative_control_leak_count": base.get("negative_control_leak_count"),
        "raw_latin": {
            "prime_hit_rate": base_raw.get("prime_hit_rate"),
            "english_only_distortion_rate": base_raw.get("english_only_distortion_rate"),
            "negative_control_leak_count": base_raw.get("negative_control_leak_count"),
        },
        "delta_shadow_minus_raw": {
            "prime_hit_rate": round(
                float(base.get("prime_hit_rate") or 0) - float(base_raw.get("prime_hit_rate") or 0),
                4,
            )
            if base_raw
            else None,
            "english_only_distortion_rate": round(
                float(base.get("english_only_distortion_rate") or 0)
                - float(base_raw.get("english_only_distortion_rate") or 0),
                4,
            )
            if base_raw
            else None,
        },
    }
    checks = []
    if thr.get("fixture_pair_count_min") is not None:
        checks.append(
            {
                "name": "fixture_pair_count_min",
                "ok": (observed.get("pair_count") or 0) >= int(thr["fixture_pair_count_min"]),
                "observed": observed.get("pair_count"),
                "threshold": thr["fixture_pair_count_min"],
            }
        )
    if thr.get("min_prime_hit_rate") is not None:
        ph = observed.get("prime_hit_rate")
        checks.append(
            {
                "name": "min_prime_hit_rate",
                "ok": ph is not None and float(ph) >= float(thr["min_prime_hit_rate"]),
                "observed": ph,
                "threshold": thr["min_prime_hit_rate"],
            }
        )
    if thr.get("max_english_only_distortion_rate") is not None:
        dr = observed.get("english_only_distortion_rate")
        checks.append(
            {
                "name": "max_english_only_distortion_rate",
                "ok": dr is not None and float(dr) <= float(thr["max_english_only_distortion_rate"]),
                "observed": dr,
                "threshold": thr["max_english_only_distortion_rate"],
            }
        )
    if thr.get("max_negative_control_leaks") is not None:
        nl = observed.get("negative_control_leak_count")
        checks.append(
            {
                "name": "max_negative_control_leaks",
                "ok": nl is not None and int(nl) <= int(thr["max_negative_control_leaks"]),
                "observed": nl,
                "threshold": thr["max_negative_control_leaks"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else False
    return {"plane": "distortion", "enabled": True, "observed": observed, "checks": checks, "ok": ok}


def _eval_retrieve(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    thr = (gates.get("retrieve") or {}).get("thresholds") or {}
    ptr = (spec.get("artifact_pointers") or {}).get("logos_gold_eval_latest", "")
    doc = _read_json(ROOT / ptr) if ptr else None
    summ = (doc or {}).get("summary") or {}
    rates = summ.get("hit_at_k_rates") or {}
    observed = {
        "items_evaluated": summ.get("items_evaluated"),
        "hit_at_1": rates.get("1"),
        "hit_at_3": rates.get("3"),
        "hit_at_8": rates.get("8"),
        "gold_required_all_pass": summ.get("gold_required_all_pass"),
    }
    checks = []
    if thr.get("min_gold_items") is not None:
        checks.append(
            {
                "name": "min_gold_items",
                "ok": (observed.get("items_evaluated") or 0) >= int(thr["min_gold_items"]),
                "observed": observed.get("items_evaluated"),
                "threshold": thr["min_gold_items"],
            }
        )
    for k, key in [("min_hit_at_1", "hit_at_1"), ("min_hit_at_3", "hit_at_3"), ("min_hit_at_8", "hit_at_8")]:
        if thr.get(k) is not None:
            val = observed.get(key)
            checks.append(
                {
                    "name": k,
                    "ok": val is not None and float(val) >= float(thr[k]),
                    "observed": val,
                    "threshold": thr[k],
                }
            )
    if thr.get("gold_required_all_pass") is not None:
        checks.append(
            {
                "name": "gold_required_all_pass",
                "ok": observed.get("gold_required_all_pass") is True,
                "observed": observed.get("gold_required_all_pass"),
                "threshold": thr["gold_required_all_pass"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else False
    return {"plane": "retrieve", "enabled": True, "observed": observed, "checks": checks, "ok": ok}


def _eval_route(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    thr = (gates.get("route") or {}).get("thresholds") or {}
    ptr = (spec.get("artifact_pointers") or {}).get("shallow_oracle_gap_latest", "")
    doc = _read_json(ROOT / ptr) if ptr else None
    raw = (doc or {}).get("raw") or {}
    repair = (doc or {}).get("repair_v2") or {}
    gap = raw.get("routing_oracle_gap")
    if gap is None:
        gap = repair.get("routing_oracle_gap")
    observed = {"routing_oracle_gap": gap}
    checks = []
    if thr.get("max_routing_oracle_gap") is not None:
        checks.append(
            {
                "name": "max_routing_oracle_gap",
                "ok": gap is not None and float(gap) <= float(thr["max_routing_oracle_gap"]),
                "observed": gap,
                "threshold": thr["max_routing_oracle_gap"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else False
    return {"plane": "route", "enabled": True, "observed": observed, "checks": checks, "ok": ok}


def _eval_compress(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    plane_cfg = gates.get("compress") or {}
    enabled = bool(plane_cfg.get("enabled"))
    ptr = (spec.get("artifact_pointers") or {}).get(
        "comp_atom02_latest",
        "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json",
    )
    doc = _read_json(ROOT / ptr) if ptr else None
    if not doc:
        return {
            "plane": "compress",
            "enabled": enabled,
            "observed": {"status": "missing_comp_atom02_report"},
            "checks": [],
            "ok": not enabled,
            "skipped": not enabled,
        }
    parity = doc.get("active_report_parity") or {}
    ablation = doc.get("compression_ablation") or doc.get("ablation") or {}
    strict = ablation.get("lexicon_on") or {}
    profile = parity if parity.get("global_token_saving_rate") is not None else strict
    saving = profile.get("global_token_saving_rate")
    jaccard = profile.get("avg_reconstruction_fidelity_jaccard")
    observed = {
        "gate_profile": doc.get("gate_compress_profile") or "active_report_parity",
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": jaccard,
        "strict_lexicon_on_saving_rate": strict.get("global_token_saving_rate"),
        "disk_active_report_saving_rate": parity.get("disk_active_report_saving_rate"),
    }
    thr = plane_cfg.get("thresholds") or {}
    checks = []
    if thr.get("min_golden40_saving_pct") is not None:
        min_rate = float(thr["min_golden40_saving_pct"]) / 100.0
        checks.append(
            {
                "name": "min_golden40_saving_pct",
                "ok": saving is not None and float(saving) >= min_rate,
                "observed": saving,
                "threshold": min_rate,
            }
        )
    if thr.get("min_golden40_jaccard") is not None:
        checks.append(
            {
                "name": "min_golden40_jaccard",
                "ok": jaccard is not None and float(jaccard) >= float(thr["min_golden40_jaccard"]),
                "observed": jaccard,
                "threshold": thr["min_golden40_jaccard"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else False
    return {
        "plane": "compress",
        "enabled": enabled,
        "observed": observed,
        "checks": checks,
        "ok": ok if enabled else True,
        "skipped": not enabled,
    }


def _eval_cost(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    plane_cfg = gates.get("cost") or {}
    enabled = bool(plane_cfg.get("enabled"))
    ptr = (spec.get("artifact_pointers") or {}).get(
        "shallow_stress_gap_latest",
        "reports/ollama_shallow_oracle_gap_stress_v1_latest.json",
    )
    doc = _read_json(ROOT / ptr) if ptr else None
    report_path = ptr
    if not doc:
        fallback_ptr = (spec.get("artifact_pointers") or {}).get("shallow_oracle_gap_latest", "")
        doc = _read_json(ROOT / fallback_ptr) if fallback_ptr else None
        report_path = fallback_ptr or ptr
    raw = (doc or {}).get("raw") or {}
    skip = raw.get("cloud_skip_ratio")
    recall = raw.get("deep_routing_recall")
    observed = {
        "report": report_path,
        "bench_mode": doc.get("bench_mode") if doc else None,
        "fixtures_evaluated": doc.get("fixtures_evaluated") if doc else None,
        "cloud_skip_ratio": skip,
        "routing_oracle_gap": raw.get("routing_oracle_gap"),
        "router_hit_rate": raw.get("router_hit_rate"),
        "deep_routing_recall": recall,
    }
    thr = plane_cfg.get("thresholds") or {}
    checks = []
    if thr.get("min_cloud_skip_ratio") is not None:
        checks.append(
            {
                "name": "min_cloud_skip_ratio",
                "ok": skip is not None and float(skip) >= float(thr["min_cloud_skip_ratio"]),
                "observed": skip,
                "threshold": thr["min_cloud_skip_ratio"],
            }
        )
    if thr.get("min_deep_routing_recall") is not None:
        checks.append(
            {
                "name": "min_deep_routing_recall",
                "ok": recall is not None and float(recall) >= float(thr["min_deep_routing_recall"]),
                "observed": recall,
                "threshold": thr["min_deep_routing_recall"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else False
    return {
        "plane": "cost",
        "enabled": enabled,
        "observed": observed,
        "checks": checks,
        "ok": ok if enabled else True,
        "skipped": not enabled,
    }


def _eval_disabled_plane(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    plane = gates.get(name) or {}
    enabled = bool(plane.get("enabled"))
    return {
        "plane": name,
        "enabled": enabled,
        "observed": {"status": "not_evaluated" if not enabled else "missing_evaluator"},
        "checks": [],
        "ok": not enabled,
        "skipped": not enabled,
    }


def _eval_layer_c_mdl(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    plane_cfg = gates.get("layer_c_mdl") or {}
    enabled = bool(plane_cfg.get("enabled"))
    ptr = (spec.get("artifact_pointers") or {}).get("mdl_prune_poc_latest", "")
    poc = _read_json(ROOT / ptr) if ptr else _read_json(ROOT / "reports/universal_root_mdl_prune_poc_v1_latest.json")
    if not poc:
        return {
            "plane": "layer_c_mdl",
            "enabled": enabled,
            "observed": {"status": "missing_poc_report"},
            "checks": [],
            "ok": not enabled,
            "skipped": not enabled,
        }
    best = poc.get("best_sweep") or {}
    prune_meta = best.get("prune_meta") or {}
    observed = {
        "any_sweep_pass": poc.get("any_sweep_pass"),
        "baseline_jaccard": poc.get("baseline_jaccard"),
        "best_actual_reduction_pct": prune_meta.get("actual_reduction_pct"),
        "best_jaccard_delta_pp": best.get("jaccard_delta_pp_vs_baseline"),
    }
    thr = plane_cfg.get("thresholds") or {}
    checks = []
    if thr.get("min_row_reduction_pct") is not None:
        red = float(prune_meta.get("actual_reduction_pct") or 0.0)
        checks.append(
            {
                "name": "min_row_reduction_pct",
                "ok": red >= float(thr["min_row_reduction_pct"]) if poc.get("any_sweep_pass") else False,
                "observed": red,
                "threshold": thr["min_row_reduction_pct"],
            }
        )
    if thr.get("max_row_reduction_pct") is not None:
        red = float(prune_meta.get("actual_reduction_pct") or 0.0)
        checks.append(
            {
                "name": "max_row_reduction_pct",
                "ok": red <= float(thr["max_row_reduction_pct"]) if poc.get("any_sweep_pass") else False,
                "observed": red,
                "threshold": thr["max_row_reduction_pct"],
            }
        )
    if thr.get("min_jaccard_delta_pp") is not None:
        delta = float(best.get("jaccard_delta_pp_vs_baseline") or 0.0)
        checks.append(
            {
                "name": "min_jaccard_delta_pp",
                "ok": delta >= float(thr["min_jaccard_delta_pp"]) - 1e-9 if poc.get("any_sweep_pass") else False,
                "observed": delta,
                "threshold": thr["min_jaccard_delta_pp"],
            }
        )
    ok = all(c["ok"] for c in checks) if checks else bool(poc.get("any_sweep_pass"))
    return {
        "plane": "layer_c_mdl",
        "enabled": enabled,
        "observed": observed,
        "checks": checks,
        "ok": ok if enabled else True,
        "skipped": not enabled,
    }


def _eval_topology(spec: dict[str, Any]) -> dict[str, Any]:
    gates = (spec.get("promotion_gates") or {}).get("planes") or {}
    plane_cfg = gates.get("topology") or {}
    enabled = bool(plane_cfg.get("enabled"))
    ptr = (spec.get("artifact_pointers") or {}).get(
        "topology_crosswalk_gate_latest",
        "reports/universal_root_topology_crosswalk_gate_v1_latest.json",
    )
    gate_doc = _read_json(ROOT / ptr) if ptr else None
    report_ptr = (spec.get("artifact_pointers") or {}).get(
        "topology_crosswalk_latest",
        "reports/universal_root_topology_crosswalk_v1_latest.json",
    )
    report = _read_json(ROOT / report_ptr) if report_ptr else None
    summary = (report or {}).get("summary") or {}
    topo = (report or {}).get("topology_plane") or {}
    wall = (report or {}).get("wall_divergence") or {}
    observed = {
        "verse_reachable_rate": summary.get("verse_reachable_rate") or topo.get("verse_reachable_rate"),
        "prime_hit_rate": summary.get("prime_hit_rate"),
        "lexicon_only_without_topology_rate": wall.get("lexicon_only_without_topology_rate"),
        "negative_topology_leak_count": topo.get("negative_topology_leak_count"),
        "plane_separation_reported": wall.get("plane_separation_reported"),
        "gate_ok": (gate_doc or {}).get("gate_ok"),
    }
    thr = plane_cfg.get("thresholds") or {}
    checks = []
    if thr.get("fixture_pair_count_min") is not None:
        pair_count = int(summary.get("pair_count") or topo.get("pair_count") or 0)
        checks.append(
            {
                "name": "fixture_pair_count_min",
                "ok": pair_count >= int(thr["fixture_pair_count_min"]),
                "observed": pair_count,
                "threshold": thr["fixture_pair_count_min"],
            }
        )
    if thr.get("min_verse_reachable_rate") is not None:
        vr = observed.get("verse_reachable_rate")
        checks.append(
            {
                "name": "min_verse_reachable_rate",
                "ok": vr is not None and float(vr) >= float(thr["min_verse_reachable_rate"]),
                "observed": vr,
                "threshold": thr["min_verse_reachable_rate"],
            }
        )
    if thr.get("max_lexicon_only_without_topology_rate") is not None:
        lor = observed.get("lexicon_only_without_topology_rate")
        checks.append(
            {
                "name": "max_lexicon_only_without_topology_rate",
                "ok": lor is not None and float(lor) <= float(thr["max_lexicon_only_without_topology_rate"]),
                "observed": lor,
                "threshold": thr["max_lexicon_only_without_topology_rate"],
            }
        )
    gate_ok = (gate_doc or {}).get("gate_ok")
    if gate_ok is not None:
        checks.append({"name": "topology_gate_ok", "ok": bool(gate_ok), "observed": gate_ok, "threshold": True})
    ok = all(c["ok"] for c in checks) if checks else bool(gate_ok)
    return {
        "plane": "topology",
        "enabled": enabled,
        "observed": observed,
        "checks": checks,
        "ok": ok if enabled else True,
        "skipped": not enabled,
    }


def evaluate_spec(spec: dict[str, Any]) -> dict[str, Any]:
    planes = [
        _eval_distortion(spec),
        _eval_retrieve(spec),
        _eval_route(spec),
        _eval_cost(spec),
        _eval_compress(spec),
        _eval_layer_c_mdl(spec),
        _eval_topology(spec),
    ]
    enabled_planes = [p for p in planes if p.get("enabled")]
    all_enabled_ok = all(p["ok"] for p in enabled_planes)
    decision = "B_TRACK_RESEARCH_READY" if all_enabled_ok else "HOLD"
    return {
        "planes": planes,
        "all_enabled_planes_ok": all_enabled_ok,
        "research_ready_decision": decision,
        "track_a_promotion_forbidden": True,
        "send_gate": "HOLD",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-schema", action="store_true")
    ap.add_argument(
        "--enforce-promotion-gates",
        action="store_true",
        help="Exit 1 when enabled promotion planes fail (default: validate+report only)",
    )
    args = ap.parse_args()

    spec_path = args.spec if args.spec.is_absolute() else ROOT / args.spec
    if not spec_path.is_file():
        print(f"ABORT: missing spec {spec_path}", file=sys.stderr)
        return 1

    spec = _read_json(spec_path) or {}
    if spec.get("schema") != "universal_root_gate_spec_v1":
        print("ABORT: schema mismatch", file=sys.stderr)
        return 1

    schema_ok = True
    schema_note = None
    if not args.skip_schema and args.schema.is_file():
        try:
            schema_ok, schema_note = _validate_schema(spec, args.schema)
        except Exception as exc:  # noqa: BLE001
            schema_ok = False
            schema_note = str(exc)

    eval_doc = evaluate_spec(spec)
    out_doc = {
        "schema": "universal_root_gate_eval_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "spec_path": _rel(spec_path),
        "schema_validation_ok": schema_ok,
        "schema_validation_note": schema_note,
        "evaluation": eval_doc,
        "reproduce": "py scripts/check_universal_root_gate_spec_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ok = schema_ok
    if args.enforce_promotion_gates:
        ok = ok and eval_doc["all_enabled_planes_ok"]

    print(
        json.dumps(
            {
                "ok": ok,
                "schema_ok": schema_ok,
                "research_ready_decision": eval_doc["research_ready_decision"],
                "all_enabled_planes_ok": eval_doc["all_enabled_planes_ok"],
                "out": _rel(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
