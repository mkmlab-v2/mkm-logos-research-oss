#!/usr/bin/env python3
"""[HYPO] No-Guard Limit Stress Test — B-track sandbox; all enterprise guards disabled.

Isolated lane: experiments/no_guard_limit_test/
Never mutates Track A active report or production hardening defaults.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SANDBOX = ROOT / "experiments" / "no_guard_limit_test"
DEFAULT_PROFILE = SANDBOX / "no_guard_profile_v1.json"
DEFAULT_INPUT = SANDBOX / "stress_cases_v1.example.jsonl"
DEFAULT_OUT = SANDBOX / "results" / "no_guard_limit_stress_test_v1_latest.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[^\s]")
IDENT_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")

# Track A frozen reference — informational contrast only (FAIL-COMP-004).
TRACK_A_FROZEN_SAVING = 0.47538677918424754
TRACK_A_FROZEN_JACCARD = 0.8904921794966301
ULTRA_SAVING_POLICY_MIN = 0.49

# Scenario B candidate thresholds (stress lane only — not promotion gates).
BREAKTHROUGH_MIN_JACCARD = 0.75
BREAKTHROUGH_MIN_SAVING = 0.90


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token_in(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_cases(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict) and row.get("raw_text") is not None:
            rows.append(row)
    return rows


def _apply_no_guard_hardening(profile_path: Path) -> None:
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(profile_path.resolve())
    from scripts.core.compression_hardening_v1 import _config_doc

    _config_doc.cache_clear()


def _harvest_repo_must_keep(
    *,
    max_files: int,
    max_terms: int,
) -> tuple[set[str], dict[str, Any]]:
    """Simulate corpus bloat via oversized must_keep — does not mutate production lexicon."""
    terms: set[str] = set()
    files_scanned = 0
    roots = [ROOT / "scripts", ROOT / "tests"]
    for base in roots:
        if not base.is_dir():
            continue
        for py_path in sorted(base.rglob("*.py")):
            if max_files and files_scanned >= max_files:
                break
            if ".venv" in py_path.parts or "node_modules" in py_path.parts:
                continue
            try:
                text = py_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in IDENT_RE.finditer(text):
                terms.add(m.group(0))
                if max_terms and len(terms) >= max_terms:
                    break
            files_scanned += 1
            if max_terms and len(terms) >= max_terms:
                break
        if max_terms and len(terms) >= max_terms:
            break
    meta = {
        "files_scanned": files_scanned,
        "term_count": len(terms),
        "max_files_cap": max_files,
        "max_terms_cap": max_terms,
        "roots": [str(p.relative_to(ROOT)).replace("\\", "/") for p in roots if p.is_dir()],
    }
    return terms, meta


def _classify_scenario(
    *,
    ok: bool,
    jaccard: float | None,
    saving: float | None,
    error: str | None,
) -> str:
    if error or not ok:
        return "A_physical_collapse"
    if jaccard is None:
        return "inconclusive"
    if jaccard < 0.20:
        return "A_quality_collapse"
    if jaccard < 0.50:
        return "A_quality_collapse"
    if (
        jaccard >= BREAKTHROUGH_MIN_JACCARD
        and saving is not None
        and saving >= BREAKTHROUGH_MIN_SAVING
    ):
        return "B_breakthrough_candidate"
    return "inconclusive"


def _eval_no_guard(
    text: str,
    *,
    lane: str | None,
    lane_intensity: dict[str, str],
    must_keep_extra: set[str],
) -> dict[str, Any]:
    """Always compress — never gatekeeper bypass, never circuit-breaker identity."""
    from scripts.core.compression_hardening_v1 import should_bypass_compression
    from scripts.core.multilens_bridge_policy_env import env_apply_gematria_4d_bridge_policy
    from scripts.report_multilens_performance_eval import evaluate_report

    tok = _token_in(text)
    t0 = time.perf_counter()
    err: str | None = None
    metrics: dict[str, Any] = {}

    try:
        if should_bypass_compression(tok):
            metrics["guard_leak"] = "gatekeeper_still_bypassed"
        profile = {"strategy": "A", "intensity": "extreme"}
        if lane and lane in lane_intensity:
            profile["intensity"] = lane_intensity[lane]

        must_keep = {
            "사상의학",
            "체질",
            "sasang",
            "myeongni",
            "bible",
            *must_keep_extra,
        }
        doc = {
            "compression_cases": [
                {
                    "id": "no-guard-live",
                    "raw_text": text,
                    "compressed_text": "",
                    "reconstructed_text": "",
                }
            ],
            "fusion_answer_cases": [],
        }
        _bp = env_apply_gematria_4d_bridge_policy()
        report = evaluate_report(
            doc,
            source_input="btrack:no_guard_limit_stress_v1",
            mode="experimental",
            strategy=str(profile["strategy"]),
            intensity=str(profile["intensity"]),
            must_keep=must_keep,
            jaccard_drop_threshold_pp=999.0,
            baseline_avg_jaccard=0.0,
            use_domain_router=True,
            use_master_codebook_lexicon_v1=True,
            include_gematria_metadata=True,
            include_gematria_4d_bridge=True,
            include_cee_core=True,
            apply_gematria_4d_bridge_policy=True,
            emit_semantic_pointer=True,
        )
        comp = report.get("compression_metrics") or {}
        cases = comp.get("cases") or []
        first = cases[0] if cases and isinstance(cases[0], dict) else {}
        saving = float(comp.get("global_token_saving_rate") or 0.0)
        jaccard = float(
            first.get("reconstruction_fidelity_jaccard")
            or comp.get("avg_reconstruction_fidelity_jaccard")
            or 0.0
        )
        metrics = {
            "global_token_saving_rate": saving,
            "reconstruction_fidelity_jaccard": jaccard,
            "raw_tokens": first.get("raw_tokens", tok),
            "compressed_tokens": first.get("compressed_tokens"),
            "ultra_saving_policy_ok": saving >= ULTRA_SAVING_POLICY_MIN,
            "ultra_saving_policy_min": ULTRA_SAVING_POLICY_MIN,
            "track_a_frozen_saving_reference": TRACK_A_FROZEN_SAVING,
            "semantic_pointer_present": bool(first.get("semantic_pointer")),
            "proxy_path": "no_guard_live_compress",
            "intensity_used": profile.get("intensity"),
            "circuit_breaker_applied": False,
        }
    except Exception as exc:
        err = f"{type(exc).__name__}:{exc}"
        metrics = {
            "global_token_saving_rate": None,
            "reconstruction_fidelity_jaccard": None,
            "proxy_path": "no_guard_exception",
            "error": err,
            "traceback_tail": traceback.format_exc().splitlines()[-6:],
        }

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    metrics["elapsed_ms"] = round(elapsed_ms, 2)
    metrics["input_tokens"] = tok
    scenario = _classify_scenario(
        ok=err is None,
        jaccard=metrics.get("reconstruction_fidelity_jaccard"),
        saving=metrics.get("global_token_saving_rate"),
        error=err,
    )
    metrics["scenario"] = scenario
    return metrics


def run_stress(
    input_path: Path,
    profile_path: Path,
    *,
    dry_run: bool,
    corpus_expansion: bool,
    corpus_max_files: int,
    corpus_max_terms: int,
    max_cases: int,
) -> dict[str, Any]:
    profile_doc = _load_json(profile_path) if profile_path.is_file() else {}
    lane_intensity = profile_doc.get("lane_intensity") if isinstance(profile_doc.get("lane_intensity"), dict) else {}
    cases_in = _load_cases(input_path)
    if max_cases > 0:
        cases_in = cases_in[:max_cases]

    corpus_meta: dict[str, Any] | None = None
    must_keep_extra: set[str] = set()
    if corpus_expansion and not dry_run:
        must_keep_extra, corpus_meta = _harvest_repo_must_keep(
            max_files=corpus_max_files,
            max_terms=corpus_max_terms,
        )

    if dry_run:
        return {
            "schema": "no_guard_limit_stress_test_v1",
            "generated_at_utc": _utc(),
            "hypothesis_tier": "B",
            "research_only": True,
            "track_wall": "not_track_a_promotion",
            "dry_run": True,
            "sandbox_root": str(SANDBOX.relative_to(ROOT)).replace("\\", "/"),
            "profile_path": str(profile_path.relative_to(ROOT)).replace("\\", "/"),
            "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "case_count": len(cases_in),
            "guards_disabled": {
                "gatekeeper_bypass_max_tokens": 0,
                "circuit_breaker": "off_in_runner",
                "sla_floor_enforcement": False,
                "corpus_expansion": corpus_expansion,
            },
            "track_a_frozen_reference": {
                "global_token_saving_rate": TRACK_A_FROZEN_SAVING,
                "avg_jaccard": TRACK_A_FROZEN_JACCARD,
                "note": "Contrast only — stress lane does not overwrite active report.",
            },
            "boundary_ack": "Dry-run only; no evaluate_report executed.",
            "forbidden_claims": [
                "track_a_promotion_from_stress_lane",
                "production_sla",
                "99_percent_universal_headline",
            ],
        }

    if not dry_run:
        _apply_no_guard_hardening(profile_path)

    rows: list[dict[str, Any]] = []
    for item in cases_in:
        raw = str(item["raw_text"])
        lane = item.get("lane")
        metrics = _eval_no_guard(
            raw,
            lane=str(lane) if lane else None,
            lane_intensity=lane_intensity,
            must_keep_extra=must_keep_extra,
        )
        rows.append(
            {
                "id": item.get("id"),
                "lane": lane,
                "token_saving_rate": metrics.get("global_token_saving_rate"),
                "reconstruction_fidelity_jaccard": metrics.get("reconstruction_fidelity_jaccard"),
                "raw_tokens": metrics.get("raw_tokens"),
                "compressed_tokens": metrics.get("compressed_tokens"),
                "elapsed_ms": metrics.get("elapsed_ms"),
                "proxy_path": metrics.get("proxy_path"),
                "scenario": metrics.get("scenario"),
                "ultra_saving_policy_ok": metrics.get("ultra_saving_policy_ok"),
                "semantic_pointer_present": metrics.get("semantic_pointer_present"),
                "guard_leak": metrics.get("guard_leak"),
                "error": metrics.get("error"),
            }
        )

    scenarios = [r.get("scenario") for r in rows]
    breakthroughs = [r for r in rows if r.get("scenario") == "B_breakthrough_candidate"]
    collapses = [r for r in rows if str(r.get("scenario", "")).startswith("A_")]
    avg_saving_vals = [r["token_saving_rate"] for r in rows if r.get("token_saving_rate") is not None]
    avg_jac_vals = [
        r["reconstruction_fidelity_jaccard"]
        for r in rows
        if r.get("reconstruction_fidelity_jaccard") is not None
    ]

    aggregate_scenario = "inconclusive"
    if any(s == "B_breakthrough_candidate" for s in scenarios):
        aggregate_scenario = "B_breakthrough_candidate"
    elif any(s == "A_physical_collapse" for s in scenarios):
        aggregate_scenario = "A_physical_collapse"
    elif any(s == "A_quality_collapse" for s in scenarios):
        aggregate_scenario = "A_quality_collapse"

    return {
        "schema": "no_guard_limit_stress_test_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "not_track_a_promotion",
        "dry_run": False,
        "sandbox_root": str(SANDBOX.relative_to(ROOT)).replace("\\", "/"),
        "profile_path": str(profile_path.relative_to(ROOT)).replace("\\", "/"),
        "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
        "guards_disabled": {
            "gatekeeper_bypass_max_tokens": 0,
            "circuit_breaker": "off_in_runner",
            "sla_floor_enforcement": False,
            "emit_semantic_pointer": True,
            "apply_gematria_4d_bridge_policy": True,
            "corpus_expansion": corpus_expansion,
            "corpus_meta": corpus_meta,
            "corpus_must_keep_extra_count": len(must_keep_extra),
        },
        "track_a_frozen_reference": {
            "global_token_saving_rate": TRACK_A_FROZEN_SAVING,
            "avg_jaccard": TRACK_A_FROZEN_JACCARD,
        },
        "aggregate": {
            "case_count": len(rows),
            "avg_token_saving_rate": sum(avg_saving_vals) / len(avg_saving_vals) if avg_saving_vals else None,
            "avg_reconstruction_fidelity_jaccard": sum(avg_jac_vals) / len(avg_jac_vals) if avg_jac_vals else None,
            "min_reconstruction_fidelity_jaccard": min(avg_jac_vals) if avg_jac_vals else None,
            "scenario": aggregate_scenario,
            "breakthrough_count": len(breakthroughs),
            "collapse_count": len(collapses),
            "total_elapsed_ms": round(sum(r.get("elapsed_ms") or 0 for r in rows), 2),
        },
        "cases": rows,
        "interpretation_ko": {
            "A_physical_collapse": "예외·크래시·극저 Jaccard — 가드가 필요했던 이유를 실측",
            "A_quality_collapse": "연산은 됐으나 품질 붕괴 — 무가드 압축이 업스트림을 오염시킬 수 있음",
            "B_breakthrough_candidate": "고절감+고Jaccard 동시 — 승격 검토 전제로만 기록 (human sign-off 필수)",
            "inconclusive": "뚜렷한 붕괴·돌파 모두 아님",
        },
        "next_if_breakthrough": "human sign-off + separate promotion bundle — never auto-merge Track A",
        "forbidden_claims": [
            "track_a_promotion_from_stress_lane",
            "production_sla",
            "99_percent_universal_headline",
            "logos_verse_rag_as_compression_anchor",
        ],
        "boundary_ack": "No-Guard sandbox only; mainline hardening and active report untouched.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="No-Guard Limit Stress Test (B-track sandbox — all guards disabled)."
    )
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--profile-json", default=str(DEFAULT_PROFILE))
    ap.add_argument("--out-json", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--corpus-expansion",
        action="store_true",
        help="Harvest repo identifiers into must_keep (simulates dictionary bloat).",
    )
    ap.add_argument("--corpus-max-files", type=int, default=120)
    ap.add_argument("--corpus-max-terms", type=int, default=5000)
    ap.add_argument("--max-cases", type=int, default=0, help="0 = all cases in input JSONL")
    args = ap.parse_args()

    input_path = Path(args.input_jsonl)
    profile_path = Path(args.profile_json)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    if not profile_path.is_absolute():
        profile_path = ROOT / profile_path
    if not input_path.is_file():
        raise SystemExit(f"missing input: {input_path}")
    if not profile_path.is_file():
        raise SystemExit(f"missing profile: {profile_path}")

    doc = run_stress(
        input_path,
        profile_path,
        dry_run=bool(args.dry_run),
        corpus_expansion=bool(args.corpus_expansion),
        corpus_max_files=max(0, int(args.corpus_max_files)),
        corpus_max_terms=max(0, int(args.corpus_max_terms)),
        max_cases=max(0, int(args.max_cases)),
    )
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    print(f"aggregate_scenario={doc.get('aggregate', {}).get('scenario', 'n/a')}")

    if args.dry_run:
        return 0
    # Stress lane: exit 0 on completion; collapse is data not process failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
