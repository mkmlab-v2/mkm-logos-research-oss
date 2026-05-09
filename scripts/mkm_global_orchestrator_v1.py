#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SASANG = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"
DEFAULT_MYEONGNI = ROOT / "docs" / "final" / "artifacts" / "mkm_myeongni_response_v2_latest.json"
DEFAULT_LOGOS = ROOT / "docs" / "final" / "artifacts" / "mkm_logos_response_v2_latest.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "mkm_global_orchestrator_policy_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_global_orchestrator_latest.json"
DEFAULT_MYEONGNI_RUNTIME = ROOT / "reports" / "myeongni_conflict_arbitration_runtime_mode_latest.json"
DEFAULT_MYEONGNI_REALSET_GATE = ROOT / "docs" / "final" / "artifacts" / "myeongni_stage2_realset_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _norm_sasang(doc: dict[str, Any]) -> dict[str, Any]:
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    return {
        "lens": "sasang",
        "direction_score": _f(scores.get("direction_score"), 0.0),
        "confidence": _f(scores.get("confidence"), 0.5),
        "decision": "WATCH",
        "research_only": bool(doc.get("a_track_autobind_forbidden", True)),
        "source_schema": doc.get("schema"),
    }


def _norm_myeongni(doc: dict[str, Any]) -> dict[str, Any]:
    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
    final = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else {}
    gov = doc.get("governance") if isinstance(doc.get("governance"), dict) else {}
    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
    return {
        "lens": "myeongni",
        "direction_score": _f(core.get("direction_core"), 0.0),
        "confidence": _f(coord.get("confidence_adjusted"), _f(core.get("confidence_core"), 0.5)),
        "decision": str(final.get("decision") or "WATCH").upper(),
        "research_only": bool(gov.get("research_only", True)),
        "source_schema": doc.get("schema"),
    }


def _myeongni_guard_state(runtime_doc: dict[str, Any], realset_gate_doc: dict[str, Any]) -> dict[str, Any]:
    mode = str(runtime_doc.get("mode") or "").lower()
    policy_hash = str(runtime_doc.get("policy_hash") or "")
    runtime_verified = bool(runtime_doc.get("verification_pass", False))
    realset_pass = bool(realset_gate_doc.get("pass", False))
    return {
        "effective_mode": mode,
        "policy_hash": policy_hash,
        "runtime_verified": runtime_verified,
        "realset_gate_pass": realset_pass,
    }


def _norm_logos(doc: dict[str, Any]) -> dict[str, Any]:
    core = doc.get("core_layer") if isinstance(doc.get("core_layer"), dict) else {}
    final = doc.get("final_action") if isinstance(doc.get("final_action"), dict) else {}
    gov = doc.get("governance") if isinstance(doc.get("governance"), dict) else {}
    coord = doc.get("coordinator_layer") if isinstance(doc.get("coordinator_layer"), dict) else {}
    return {
        "lens": "logos",
        "direction_score": _f(core.get("direction_core"), 0.0),
        "confidence": _f(coord.get("confidence_adjusted"), _f(core.get("confidence_core"), 0.5)),
        "decision": str(final.get("decision") or "WATCH").upper(),
        "research_only": bool(gov.get("research_only", True)),
        "source_schema": doc.get("schema"),
    }


def _resolve(norms: list[dict[str, Any]], policy: dict[str, Any], guard: dict[str, Any]) -> tuple[dict[str, Any], int]:
    p = policy.get("decision_policy") if isinstance(policy.get("decision_policy"), dict) else {}
    w = policy.get("weights") if isinstance(policy.get("weights"), dict) else {}
    fail_closed = str(p.get("fail_closed_action", "HOLD")).upper()
    gmode = str(guard.get("effective_mode") or "")
    ghash = str(guard.get("policy_hash") or "")
    if not bool(guard.get("runtime_verified", False)):
        return {
            "decision": "HOLD",
            "reason": "myeongni_runtime_not_verified",
            "final_direction_score": 0.0,
            "final_confidence": 0.0,
            "effective_mode": gmode,
            "policy_hash": ghash,
        }, 2
    if not bool(guard.get("realset_gate_pass", False)):
        return {
            "decision": "HOLD",
            "reason": "myeongni_stage2_realset_gate_fail",
            "final_direction_score": 0.0,
            "final_confidence": 0.0,
            "effective_mode": gmode,
            "policy_hash": ghash,
        }, 2

    if len(norms) != 3:
        return {
            "decision": fail_closed,
            "reason": "missing_required_lens_inputs",
            "final_direction_score": 0.0,
            "final_confidence": 0.0,
            "effective_mode": gmode,
            "policy_hash": ghash,
        }, 2

    by_lens = {n["lens"]: n for n in norms}
    if any(l not in by_lens for l in ("sasang", "myeongni", "logos")):
        return {
            "decision": fail_closed,
            "reason": "invalid_lens_keys",
            "final_direction_score": 0.0,
            "final_confidence": 0.0,
            "effective_mode": gmode,
            "policy_hash": ghash,
        }, 2

    if any(str(n["decision"]).upper() == "HOLD" for n in norms):
        return {
            "decision": "HOLD",
            "reason": "lens_hard_hold",
            "final_direction_score": 0.0,
            "final_confidence": 0.0,
            "effective_mode": gmode,
            "policy_hash": ghash,
        }, 0

    ws = _f(w.get("sasang"), 0.34)
    wm = _f(w.get("myeongni"), 0.33)
    wl = _f(w.get("logos"), 0.33)
    wsum = ws + wm + wl
    if wsum <= 0:
        return {
            "decision": fail_closed,
            "reason": "invalid_weights_sum",
            "final_direction_score": 0.0,
            "final_confidence": 0.0,
            "effective_mode": gmode,
            "policy_hash": ghash,
        }, 2
    ws, wm, wl = ws / wsum, wm / wsum, wl / wsum

    d = (
        ws * _f(by_lens["sasang"]["direction_score"])
        + wm * _f(by_lens["myeongni"]["direction_score"])
        + wl * _f(by_lens["logos"]["direction_score"])
    )
    c = min(
        _f(by_lens["sasang"]["confidence"], 0.0),
        _f(by_lens["myeongni"]["confidence"], 0.0),
        _f(by_lens["logos"]["confidence"], 0.0),
    )

    go_conf_cut = _f(p.get("go_confidence_cut"), 0.70)
    go_dir_cut = _f(p.get("go_direction_abs_cut"), 0.25)
    hold_conf_cut = _f(p.get("hold_confidence_cut"), 0.35)
    hold_dir_cut = _f(p.get("hold_direction_abs_cut"), 0.10)
    if c < hold_conf_cut and abs(d) < hold_dir_cut:
        decision = "HOLD"
        reason = "low_confidence_low_direction"
    elif c >= go_conf_cut and abs(d) >= go_dir_cut:
        decision = "GO"
        reason = "high_confidence_and_direction"
    else:
        decision = "WATCH"
        reason = "intermediate_signal"

    if decision == "GO" and any(bool(n.get("research_only", False)) for n in norms):
        decision = "WATCH"
        reason = "research_only_guard"

    return {
        "decision": decision,
        "reason": reason,
        "final_direction_score": round(d, 6),
        "final_confidence": round(c, 6),
        "effective_mode": gmode,
        "policy_hash": ghash,
    }, 0


def _pair_debug(norms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    m = {n["lens"]: n for n in norms}
    pairs = [("sasang", "myeongni"), ("sasang", "logos"), ("myeongni", "logos")]
    rows: list[dict[str, Any]] = []
    for a, b in pairs:
        da = _f(m[a]["direction_score"])
        db = _f(m[b]["direction_score"])
        ca = _f(m[a]["confidence"])
        cb = _f(m[b]["confidence"])
        rows.append(
            {
                "pair": f"{a}+{b}",
                "direction_mean": round((da + db) / 2.0, 6),
                "confidence_min": round(min(ca, cb), 6),
                "direction_gap_abs": round(abs(da - db), 6),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="MKM global orchestrator v1 (single decision core).")
    ap.add_argument("--sasang-json", type=Path, default=DEFAULT_SASANG)
    ap.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI)
    ap.add_argument("--logos-json", type=Path, default=DEFAULT_LOGOS)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--myeongni-runtime-json", type=Path, default=DEFAULT_MYEONGNI_RUNTIME)
    ap.add_argument("--myeongni-realset-gate-json", type=Path, default=DEFAULT_MYEONGNI_REALSET_GATE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--debug-pairs", action="store_true", help="Emit pair diagnostics only for debugging.")
    args = ap.parse_args()

    sasang_path = args.sasang_json if args.sasang_json.is_absolute() else ROOT / args.sasang_json
    myeongni_path = args.myeongni_json if args.myeongni_json.is_absolute() else ROOT / args.myeongni_json
    logos_path = args.logos_json if args.logos_json.is_absolute() else ROOT / args.logos_json
    policy_path = args.policy_json if args.policy_json.is_absolute() else ROOT / args.policy_json
    runtime_path = (
        args.myeongni_runtime_json if args.myeongni_runtime_json.is_absolute() else ROOT / args.myeongni_runtime_json
    )
    realset_gate_path = (
        args.myeongni_realset_gate_json
        if args.myeongni_realset_gate_json.is_absolute()
        else ROOT / args.myeongni_realset_gate_json
    )
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    try:
        sasang_doc = _read_json(sasang_path)
        myeongni_doc = _read_json(myeongni_path)
        logos_doc = _read_json(logos_path)
        policy_doc = _read_json(policy_path)
        runtime_doc = _read_json(runtime_path)
        realset_gate_doc = _read_json(realset_gate_path)
        guard = _myeongni_guard_state(runtime_doc, realset_gate_doc)
        norms = [_norm_sasang(sasang_doc), _norm_myeongni(myeongni_doc), _norm_logos(logos_doc)]
        resolved, exit_code = _resolve(norms, policy_doc, guard)
    except Exception as e:
        out = {
            "schema": "mkm_global_orchestrator_v1",
            "generated_at_utc": _now(),
            "result": {
                "decision": "HOLD",
                "reason": f"exception:{type(e).__name__}",
                "final_direction_score": 0.0,
                "final_confidence": 0.0,
            },
            "errors": [str(e)],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "out": str(out_path), "decision": "HOLD"}, ensure_ascii=False))
        return 2

    out = {
        "schema": "mkm_global_orchestrator_v1",
        "generated_at_utc": _now(),
        "inputs": {
            "sasang_json": str(sasang_path),
            "myeongni_json": str(myeongni_path),
            "logos_json": str(logos_path),
            "policy_json": str(policy_path),
                "myeongni_runtime_json": str(runtime_path),
                "myeongni_realset_gate_json": str(realset_gate_path),
        },
        "normalized_lenses": norms,
            "myeongni_guard": guard,
        "result": resolved,
        "errors": [],
    }
    if args.debug_pairs:
        out["pair_diagnostics"] = _pair_debug(norms)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": resolved["decision"], "out": str(out_path)}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
