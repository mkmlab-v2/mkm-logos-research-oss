# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.3}
# Balance: 93
# Purpose: Run Week-4 selective router constraints A/B mix experiment.
# Keywords: track_a, week4, selective_router, constraints, ab_test
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import evaluate_report

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_A = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
PACK = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_experiment_pack_v1.json"
OUT = ROOT / "docs" / "final" / "artifacts" / "track_a_week4_selective_router_ab_v1.json"

BASE_MUST_KEEP = {"사상의학", "체질", "sasang", "myeongri", "bible"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_e3_config(pack_doc: dict[str, Any]) -> tuple[list[str], list[str]]:
    experiments = ((pack_doc.get("pack") or {}).get("experiments") or [])
    e3 = next((x for x in experiments if str(x.get("id")) == "W4-E3"), {})
    cfg = e3.get("config") or {}
    denied = [str(x).strip().lower() for x in (cfg.get("router_off_denied_domains") or []) if str(x).strip()]
    allowed = [str(x).strip().lower() for x in (cfg.get("router_off_allowed_domains") or []) if str(x).strip()]
    return denied, allowed


def _build_case_map(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = (report.get("compression_metrics", {}) or {}).get("cases", [])
    return {str((r or {}).get("id")): r for r in rows if str((r or {}).get("id"))}


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _summarize_selected_cases(cases: list[dict[str, Any]]) -> dict[str, float]:
    before = 0.0
    after = 0.0
    jacc = []
    integ = []
    leak = []
    for row in cases:
        tb = float(row.get("o200k_tokens_before", row.get("o200k_raw_tokens", 0.0)) or 0.0)
        ta = float(row.get("o200k_tokens_after", row.get("o200k_compressed_tokens", 0.0)) or 0.0)
        if tb <= 0.0:
            tb = float(row.get("o200k_raw_tokens", row.get("raw_tokens", 0.0)) or 0.0)
        if ta <= 0.0:
            ta = float(row.get("o200k_compressed_tokens", row.get("compressed_tokens", 0.0)) or 0.0)
        before += tb
        after += ta
        jacc.append(float(row.get("reconstruction_fidelity_jaccard", 0.0)))
        integ.append(float(row.get("sensitive_integrity", 0.0)))
        leak.append(1.0 if bool(row.get("sensitive_leak", False)) else 0.0)
    saving = ((before - after) / before) if before > 0.0 else 0.0
    return {
        "global_token_saving_rate": saving,
        "avg_reconstruction_fidelity_jaccard": _avg(jacc),
        "avg_sensitive_integrity": _avg(integ),
        "sensitive_leak_rate": _avg(leak),
    }


def _report_metrics(report: dict[str, Any]) -> dict[str, float]:
    m = report.get("compression_metrics", {}) or {}
    return {
        "global_token_saving_rate": float(m.get("global_token_saving_rate", 0.0)),
        "avg_reconstruction_fidelity_jaccard": float(m.get("avg_reconstruction_fidelity_jaccard", 0.0)),
        "avg_sensitive_integrity": float(m.get("avg_sensitive_integrity", 0.0)),
        "sensitive_leak_rate": float(m.get("sensitive_leak_rate", 0.0)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=INPUT_V2)
    ap.add_argument("--active-a-report", type=Path, default=ACTIVE_A)
    ap.add_argument("--pack", type=Path, default=PACK)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--saving-floor", type=float, default=0.48)
    ap.add_argument("--jaccard-floor", type=float, default=0.82)
    ap.add_argument("--integrity-floor", type=float, default=1.0)
    args = ap.parse_args()

    input_doc = _load_json(args.input if args.input.is_absolute() else ROOT / args.input)
    active_doc = _load_json(args.active_a_report if args.active_a_report.is_absolute() else ROOT / args.active_a_report)
    pack_doc = _load_json(args.pack if args.pack.is_absolute() else ROOT / args.pack)
    denied_domains, allowed_domains = _read_e3_config(pack_doc)

    active_profile = active_doc.get("active_profile", {})
    strategy = str(active_profile.get("strategy", "A"))
    intensity = str(active_profile.get("intensity", "extreme"))
    gc = float(active_profile.get("general_max_saving_rate", 0.54))
    sc = float(active_profile.get("sensitive_max_saving_rate", 0.5))
    hc = float(active_profile.get("hangul_max_saving_rate", 0.48))

    router_on = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )
    router_off = evaluate_report(
        input_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep=set(BASE_MUST_KEEP),
        general_max_saving_rate=gc,
        sensitive_max_saving_rate=sc,
        hangul_max_saving_rate=hc,
        use_domain_router=False,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )

    on_map = _build_case_map(router_on)
    off_map = _build_case_map(router_off)
    selected_cases: list[dict[str, Any]] = []
    switched_to_off = 0
    total_cases = 0
    for cid, on_case in on_map.items():
        off_case = off_map.get(cid)
        if not off_case:
            selected_cases.append(on_case)
            total_cases += 1
            continue
        domain = str((((on_case.get("route") or {}).get("domain")) or "")).lower()
        use_off = domain not in set(denied_domains)
        chosen = off_case if use_off else on_case
        if use_off:
            switched_to_off += 1
        selected_cases.append(chosen)
        total_cases += 1

    mixed = _summarize_selected_cases(selected_cases)
    on_metrics = _report_metrics(router_on)
    off_metrics = _report_metrics(router_off)

    gate = {
        "saving_floor_ok": mixed["global_token_saving_rate"] >= args.saving_floor,
        "jaccard_floor_ok": mixed["avg_reconstruction_fidelity_jaccard"] >= args.jaccard_floor,
        "integrity_floor_ok": mixed["avg_sensitive_integrity"] >= args.integrity_floor,
    }
    decision = (
        "GO_W4_E4_POLICY_REPLAY"
        if gate["saving_floor_ok"] and gate["jaccard_floor_ok"] and gate["integrity_floor_ok"]
        else "HOLD_W4_E3_NO_VIABLE"
    )

    out_doc = {
        "schema": "track_a_week4_selective_router_ab_v1",
        "generated_at_utc": _now_utc(),
        "inputs": {
            "input": str(args.input),
            "active_a_report": str(args.active_a_report),
            "pack": str(args.pack),
            "router_off_denied_domains": denied_domains,
            "router_off_allowed_domains": allowed_domains,
            "caps": {"general": gc, "sensitive": sc, "hangul": hc},
            "floors": {
                "saving_floor": args.saving_floor,
                "jaccard_floor": args.jaccard_floor,
                "integrity_floor": args.integrity_floor,
            },
        },
        "mix_stats": {
            "total_cases": total_cases,
            "switched_to_router_off_cases": switched_to_off,
            "switched_ratio": (switched_to_off / total_cases) if total_cases else 0.0,
        },
        "metrics": {
            "router_on": on_metrics,
            "router_off": off_metrics,
            "selective_mixed": mixed,
            "delta_mixed_vs_on": {
                "saving": mixed["global_token_saving_rate"] - on_metrics["global_token_saving_rate"],
                "jaccard": mixed["avg_reconstruction_fidelity_jaccard"] - on_metrics["avg_reconstruction_fidelity_jaccard"],
                "integrity": mixed["avg_sensitive_integrity"] - on_metrics["avg_sensitive_integrity"],
            },
        },
        "gate": gate,
        "decision": decision,
        "next_action": (
            "Proceed to W4-E4 policy replay with selective-router candidate."
            if decision == "GO_W4_E4_POLICY_REPLAY"
            else "Keep router-on baseline and hold commercialization claim under policy floor."
        ),
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
