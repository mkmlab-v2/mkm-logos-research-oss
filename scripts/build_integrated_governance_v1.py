#!/usr/bin/env python3
"""Build integrated governance artifact from Core 3-Engine gates.

This script provides a deterministic local builder for:
  docs/final/artifacts/integrated_governance_v1_latest.json

It uses three engine gate artifacts:
  - kospi_biblical_single_lane_commercial_gate_v1_latest.json
  - kospi_myeongri_standalone_commercial_gate_v1_latest.json
  - kospi_sasang_single_lane_commercial_gate_v1_latest.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _pick_biblical_score(doc: dict[str, Any]) -> float:
    metrics = doc.get("current_metrics") if isinstance(doc.get("current_metrics"), dict) else {}
    active = metrics.get("external_active_for_gate") if isinstance(metrics.get("external_active_for_gate"), dict) else {}
    acc = active.get("accuracy")
    if isinstance(acc, (int, float)):
        return float(acc)
    return 0.0


def _pick_myeongri_score(doc: dict[str, Any]) -> float:
    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    acc = metrics.get("accuracy")
    if isinstance(acc, (int, float)):
        return float(acc)
    return 0.0


def _pick_sasang_score(doc: dict[str, Any]) -> float:
    chosen = doc.get("latest_single_lane_gate") if isinstance(doc.get("latest_single_lane_gate"), dict) else {}
    cand = chosen.get("chosen_candidate") if isinstance(chosen.get("chosen_candidate"), dict) else {}
    acc = cand.get("accuracy")
    if isinstance(acc, (int, float)):
        return float(acc)
    return 0.0


def _engine_passes(doc_bib: dict[str, Any], doc_mye: dict[str, Any], doc_sas: dict[str, Any], require_biblical_stability: bool) -> tuple[bool, bool, bool, list[str]]:
    reasons: list[str] = []

    bib_pass = bool(doc_bib.get("precommercial_ready"))
    if require_biblical_stability:
        stability = doc_bib.get("stability") if isinstance(doc_bib.get("stability"), dict) else {}
        bib_pass = bib_pass and bool(stability.get("stability_go"))
    if not bib_pass:
        reasons.append("biblical_core_not_ready")

    mye_pass = bool(doc_mye.get("standalone_commercial_ready"))
    if not mye_pass:
        reasons.append("myeongri_v4_1_not_ready")

    sas_pass = bool(doc_sas.get("commercial_ready"))
    if not sas_pass:
        reasons.append("sasang_strict_not_ready")

    return bib_pass, mye_pass, sas_pass, reasons


def build_payload(
    config: dict[str, Any],
    doc_bib: dict[str, Any],
    doc_mye: dict[str, Any],
    doc_sas: dict[str, Any],
) -> dict[str, Any]:
    weights = config.get("weights") if isinstance(config.get("weights"), dict) else {}
    w_b = float(weights.get("biblical_core", 0.34))
    w_m = float(weights.get("myeongri_v4_1", 0.33))
    w_s = float(weights.get("sasang_strict", 0.33))
    w_sum = w_b + w_m + w_s
    if w_sum <= 0:
        w_b, w_m, w_s = 0.34, 0.33, 0.33
        w_sum = 1.0
    w_b, w_m, w_s = w_b / w_sum, w_m / w_sum, w_s / w_sum

    policy = config.get("policy") if isinstance(config.get("policy"), dict) else {}
    require_biblical_stability = bool(policy.get("require_biblical_stability", False))

    bib_pass, mye_pass, sas_pass, veto_codes = _engine_passes(
        doc_bib=doc_bib,
        doc_mye=doc_mye,
        doc_sas=doc_sas,
        require_biblical_stability=require_biblical_stability,
    )
    all_pass = bib_pass and mye_pass and sas_pass

    s_b = _pick_biblical_score(doc_bib)
    s_m = _pick_myeongri_score(doc_mye)
    s_s = _pick_sasang_score(doc_sas)
    final_score = _clamp((w_b * s_b) + (w_m * s_m) + (w_s * s_s), 0.0, 1.0)

    if all_pass:
        final_regime = "ATTACK"
        final_action_allowed = True
        is_fallback = False
    else:
        final_regime = "HOLD"
        final_action_allowed = False
        is_fallback = True
        if not veto_codes:
            veto_codes = ["fallback_guard_triggered"]

    return {
        "schema": "integrated_governance_v1",
        "generated_at_utc": _now_utc(),
        "input_artifacts": {
            "config": str(config.get("_path") or ""),
            "biblical_core_gate": str(doc_bib.get("_path") or ""),
            "myeongri_gate": str(doc_mye.get("_path") or ""),
            "sasang_gate": str(doc_sas.get("_path") or ""),
        },
        "weights": {
            "biblical_core": round(w_b, 6),
            "myeongri_v4_1": round(w_m, 6),
            "sasang_strict": round(w_s, 6),
        },
        "engine_status": {
            "biblical_core": {"gate_status": "PASS" if bib_pass else "FAIL", "score": round(s_b, 6)},
            "myeongri_v4_1": {"gate_status": "PASS" if mye_pass else "FAIL", "score": round(s_m, 6)},
            "sasang_strict": {"gate_status": "PASS" if sas_pass else "FAIL", "score": round(s_s, 6)},
        },
        "final_regime": final_regime,
        "final_action_allowed": final_action_allowed,
        "is_fallback": is_fallback,
        "final_score": round(final_score, 6),
        "veto_reason_codes": veto_codes,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_art = root / "docs" / "final" / "artifacts"

    ap = argparse.ArgumentParser(description="Build integrated governance artifact v1.")
    ap.add_argument("--config-json", default=str(default_art / "integrated_governance_config_v1.json"))
    ap.add_argument("--biblical-json", default=str(default_art / "kospi_biblical_single_lane_commercial_gate_v1_latest.json"))
    ap.add_argument("--myeongri-json", default=str(default_art / "kospi_myeongri_standalone_commercial_gate_v1_latest.json"))
    ap.add_argument("--sasang-json", default=str(default_art / "kospi_sasang_single_lane_commercial_gate_v1_latest.json"))
    ap.add_argument("--out-json", default=str(default_art / "integrated_governance_v1_latest.json"))
    args = ap.parse_args()

    config_path = Path(args.config_json)
    bib_path = Path(args.biblical_json)
    mye_path = Path(args.myeongri_json)
    sas_path = Path(args.sasang_json)
    out_path = Path(args.out_json)

    cfg = _safe_json(config_path)
    if not cfg:
        raise SystemExit(f"missing or invalid config: {config_path}")
    cfg["_path"] = str(config_path)

    bib = _safe_json(bib_path)
    mye = _safe_json(mye_path)
    sas = _safe_json(sas_path)
    if not bib:
        raise SystemExit(f"missing or invalid biblical gate: {bib_path}")
    if not mye:
        raise SystemExit(f"missing or invalid myeongri gate: {mye_path}")
    if not sas:
        raise SystemExit(f"missing or invalid sasang gate: {sas_path}")
    bib["_path"] = str(bib_path)
    mye["_path"] = str(mye_path)
    sas["_path"] = str(sas_path)

    payload = build_payload(cfg, bib, mye, sas)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
