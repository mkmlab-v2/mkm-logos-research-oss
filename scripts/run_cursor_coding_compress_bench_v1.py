#!/usr/bin/env python3
"""B-track bench: Cursor-like coding prompts through Track A evaluate_report (research_only)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
from scripts.report_multilens_performance_eval import evaluate_report

DEFAULT_INPUT = ROOT / "data/btrack/cursor_coding_compress_bench_v1.example.jsonl"
DEFAULT_OUT = ROOT / "reports/cursor_coding_compress_bench_v1_latest.json"
DEFAULT_HARDENING = ROOT / "data/btrack/compression_coding_proxy_hardening_v1.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
ACTIVE_BASELINE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]")

# PoC gate — research_only; not Track A promotion.
GATE_MIN_SAVING = 0.30
GATE_MIN_JACCARD = 0.75


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _baseline_jaccard() -> float:
    if not ACTIVE_BASELINE.is_file():
        return 0.0
    doc = _load_json(ACTIVE_BASELINE)
    return float(doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0))


def _selected_profile() -> dict[str, Any]:
    if not DECISION.is_file():
        return {"strategy": "A", "intensity": "extreme"}
    sel = _load_json(DECISION).get("selected_candidate") or {}
    return {
        "strategy": sel.get("strategy", "A"),
        "intensity": sel.get("intensity", "extreme"),
        "general_max_saving_rate": sel.get("general_max_saving_rate"),
        "sensitive_max_saving_rate": sel.get("sensitive_max_saving_rate"),
        "hangul_max_saving_rate": sel.get("hangul_max_saving_rate"),
    }


def _load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("raw_text"):
            rows.append(row)
    return rows


def _token_in(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _load_lane_intensity(hardening_path: Path) -> dict[str, str]:
    if not hardening_path.is_file():
        return {}
    doc = json.loads(hardening_path.read_text(encoding="utf-8-sig"))
    block = doc.get("lane_intensity")
    return block if isinstance(block, dict) else {}


def _profile_for_lane(base: dict[str, Any], lane: str | None, lane_intensity: dict[str, str]) -> dict[str, Any]:
    prof = dict(base)
    if lane and lane in lane_intensity:
        prof["intensity"] = lane_intensity[lane]
    return prof


def _identity_metrics(text: str) -> dict[str, Any]:
    tok = _token_in(text)
    return {
        "global_token_saving_rate": 0.0,
        "reconstruction_fidelity_jaccard": 1.0,
        "raw_tokens": tok,
        "compressed_tokens": tok,
    }


def _poc_gate(rows: list[dict[str, Any]]) -> tuple[bool, dict[str, Any]]:
    if not rows:
        return False, {"min_jaccard": 0.0, "compressible_avg_saving": 0.0, "compressible_count": 0}
    min_jac = min(r["reconstruction_fidelity_jaccard"] for r in rows)
    compressible = [r for r in rows if r.get("proxy_path") == "live_compress"]
    if compressible:
        avg_saving = sum(r["token_saving_rate"] for r in compressible) / len(compressible)
    else:
        avg_saving = 0.0
    poc_pass = min_jac >= GATE_MIN_JACCARD and (
        not compressible or avg_saving >= GATE_MIN_SAVING
    )
    return poc_pass, {
        "min_jaccard": min_jac,
        "compressible_avg_saving": avg_saving,
        "compressible_count": len(compressible),
    }


def _eval_one(text: str, profile: dict[str, Any]) -> dict[str, Any]:
    doc = {
        "compression_cases": [
            {"id": "cursor-live", "raw_text": text, "compressed_text": "", "reconstructed_text": ""}
        ],
        "fusion_answer_cases": [],
    }
    _bp = env_apply_gematria_4d_bridge_policy()
    report = evaluate_report(
        doc,
        source_input="btrack:cursor_coding_bench_v1",
        mode="experimental",
        strategy=str(profile.get("strategy", "A")),
        intensity=str(profile.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=1.5,
        baseline_avg_jaccard=_baseline_jaccard(),
        general_max_saving_rate=profile.get("general_max_saving_rate"),
        sensitive_max_saving_rate=profile.get("sensitive_max_saving_rate"),
        hangul_max_saving_rate=profile.get("hangul_max_saving_rate"),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=_bp,
        include_gematria_4d_bridge=_bp,
        include_cee_core=_bp,
        apply_gematria_4d_bridge_policy=_bp,
    )
    comp = report.get("compression_metrics") or {}
    cases = comp.get("cases") or []
    first = cases[0] if cases and isinstance(cases[0], dict) else {}
    return {
        "global_token_saving_rate": float(comp.get("global_token_saving_rate") or 0.0),
        "reconstruction_fidelity_jaccard": float(
            first.get("reconstruction_fidelity_jaccard") or comp.get("avg_reconstruction_fidelity_jaccard") or 0.0
        ),
        "raw_tokens": first.get("raw_tokens"),
        "compressed_tokens": first.get("compressed_tokens"),
    }


def _eval_proxy_aligned(
    text: str,
    profile: dict[str, Any],
    *,
    lane: str | None,
    lane_intensity: dict[str, str],
) -> dict[str, Any]:
    from scripts.core.compression_hardening_v1 import (
        should_bypass_compression,
        should_circuit_break_report,
    )

    tok = _token_in(text)
    if should_bypass_compression(tok):
        out = _identity_metrics(text)
        out["proxy_path"] = "gatekeeper_bypass"
        return out

    prof = _profile_for_lane(profile, lane, lane_intensity)

    from scripts.core.coding_proxy_context_v1 import compressible_has_structured_blocks
    from scripts.core.coding_proxy_compress_v1 import coding_proxy_compress_surface

    if compressible_has_structured_blocks(text):
        cp = coding_proxy_compress_surface(text, profile, lane=lane, lane_intensity=lane_intensity)
        metrics = {
            "global_token_saving_rate": float(cp.get("global_token_saving_rate") or 0.0),
            "reconstruction_fidelity_jaccard": float(cp.get("reconstruction_fidelity_jaccard") or 0.0),
            "raw_tokens": cp.get("raw_tokens"),
            "compressed_tokens": cp.get("compressed_tokens"),
            "proxy_path": cp.get("proxy_path"),
            "intensity_used": cp.get("intensity_used"),
            "structured_preserve": cp.get("structured_preserve"),
        }
    else:
        metrics = _eval_one(text, prof)
    report_stub = {
        "compression_metrics": {
            "avg_jaccard": metrics["reconstruction_fidelity_jaccard"],
            "global_token_saving_rate": metrics["global_token_saving_rate"],
        }
    }
    cb_on, cb_reasons = should_circuit_break_report(report_stub)
    if cb_on:
        out = _identity_metrics(text)
        out["proxy_path"] = "circuit_break_identity"
        out["circuit_break_reasons"] = cb_reasons
        return out

    metrics["proxy_path"] = "live_compress"
    metrics["intensity_used"] = prof.get("intensity")
    return metrics


def run_bench(
    input_path: Path,
    *,
    dry_run: bool,
    proxy_aligned: bool,
    hardening_path: Path,
) -> dict[str, Any]:
    profile = _selected_profile()
    lane_intensity = _load_lane_intensity(hardening_path) if proxy_aligned else {}
    cases_in = _load_cases(input_path)
    if dry_run:
        return {
            "schema": "cursor_coding_compress_bench_v1",
            "generated_at_utc": _utc(),
            "hypothesis_tier": "B",
            "research_only": True,
            "dry_run": True,
            "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "case_count": len(cases_in),
            "profile": profile,
            "gate_thresholds": {"min_saving": GATE_MIN_SAVING, "min_jaccard": GATE_MIN_JACCARD},
            "proxy_aligned": proxy_aligned,
            "boundary_ack": "Dry-run only; no evaluate_report executed.",
        }

    rows: list[dict[str, Any]] = []
    for item in cases_in:
        raw = str(item["raw_text"])
        lane = item.get("lane")
        if proxy_aligned:
            metrics = _eval_proxy_aligned(
                raw, profile, lane=str(lane) if lane else None, lane_intensity=lane_intensity
            )
        else:
            metrics = _eval_one(raw, profile)
            metrics["proxy_path"] = "raw_evaluate_report"
        row: dict[str, Any] = {
            "id": item.get("id"),
            "lane": lane,
            "token_saving_rate": metrics["global_token_saving_rate"],
            "reconstruction_fidelity_jaccard": metrics["reconstruction_fidelity_jaccard"],
            "raw_tokens": metrics.get("raw_tokens"),
            "compressed_tokens": metrics.get("compressed_tokens"),
            "proxy_path": metrics.get("proxy_path"),
        }
        if metrics.get("intensity_used"):
            row["intensity_used"] = metrics["intensity_used"]
        if metrics.get("circuit_break_reasons"):
            row["circuit_break_reasons"] = metrics["circuit_break_reasons"]
        rows.append(row)

    n = len(rows) or 1
    avg_saving = sum(r["token_saving_rate"] for r in rows) / n
    avg_jac = sum(r["reconstruction_fidelity_jaccard"] for r in rows) / n
    min_jac = min((r["reconstruction_fidelity_jaccard"] for r in rows), default=0.0)
    poc_pass, gate_detail = _poc_gate(rows) if proxy_aligned else (
        avg_saving >= GATE_MIN_SAVING and min_jac >= GATE_MIN_JACCARD,
        {"min_jaccard": min_jac, "compressible_avg_saving": avg_saving, "compressible_count": n},
    )

    return {
        "schema": "cursor_coding_compress_bench_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "not_track_a_promotion",
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "proxy_aligned": proxy_aligned,
        "hardening_config": str(hardening_path.relative_to(ROOT)).replace("\\", "/")
        if proxy_aligned and hardening_path.is_file()
        else None,
        "profile": profile,
        "frozen_bench_reference": {
            "active_global_saving": 0.47116736990154706,
            "note": "Enterprise 40-case bench; separate from this coding slice.",
        },
        "aggregate": {
            "case_count": len(rows),
            "avg_token_saving_rate": avg_saving,
            "avg_reconstruction_fidelity_jaccard": avg_jac,
            "min_reconstruction_fidelity_jaccard": min_jac,
        },
        "gate_thresholds": {
            "min_saving": GATE_MIN_SAVING,
            "min_jaccard": GATE_MIN_JACCARD,
            "saving_scope": "compressible_cases_only" if proxy_aligned else "all_cases_avg",
        },
        "poc_gate": {
            "pass": poc_pass,
            "adapter_wiring_allowed": poc_pass,
            **gate_detail,
        },
        "cases": rows,
        "next_if_pass": "scripts/build_local_cursor_compress_adapter_v1.py --write-plan",
        "forbidden_claims": [
            "cursor_unlimited_replacement",
            "production_sla",
            "ms_headline_47_percent_on_coding",
        ],
        "boundary_ack": "B-track PoC only; not customer-wide generalization.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Cursor coding prompt compression bench (B-track).")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--proxy-aligned",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Mirror coding proxy: gatekeeper bypass + circuit breaker + lane intensity (default on).",
    )
    ap.add_argument("--hardening-config", default=str(DEFAULT_HARDENING))
    args = ap.parse_args()

    hardening_path = Path(args.hardening_config)
    if not hardening_path.is_absolute():
        hardening_path = ROOT / hardening_path
    if args.proxy_aligned and not args.dry_run:
        os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening_path)
        from scripts.core.compression_hardening_v1 import _config_doc

        _config_doc.cache_clear()

    input_path = Path(args.input_jsonl)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not input_path.is_file():
        raise SystemExit(f"missing input: {input_path}")

    doc = run_bench(
        input_path,
        dry_run=bool(args.dry_run),
        proxy_aligned=bool(args.proxy_aligned),
        hardening_path=hardening_path,
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))

    if args.dry_run:
        return 0
    return 0 if doc.get("poc_gate", {}).get("pass") else 2


if __name__ == "__main__":
    raise SystemExit(main())
