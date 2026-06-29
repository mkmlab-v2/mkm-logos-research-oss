"""Layer C MDL lexicon prune PoC helpers (Morfessor EM+Prune-class surface sweep) [HYPO]."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.core.master_codebook_lexicon_v1_bridge import unicode_word_tokens
from scripts.report_multilens_performance_eval import evaluate_report

ROOT = Path(__file__).resolve().parents[1]
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
BASELINE_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"

_GH_ATOM_RE = re.compile(r"^[GH]\d", re.IGNORECASE)
DEFAULT_SWEEP_PCTS = (5.0, 10.0, 15.0)
DEFAULT_JACCARD_FLOOR_DELTA_PP = 0.005


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def golden40_unicode_tokens(input_path: Path | None = None) -> frozenset[str]:
    src = _load_json(input_path or INPUT_V2)
    out: set[str] = set()
    for case in src.get("compression_cases") or []:
        if isinstance(case, dict):
            out |= unicode_word_tokens(str(case.get("raw_text") or ""))
    return frozenset(out)


def must_keep_reason(entry: dict[str, Any], golden_tokens: frozenset[str]) -> str | None:
    nf = str(entry.get("normalized_form") or "").strip().lower()
    if nf and nf in golden_tokens:
        return "golden40_surface_hit"
    strongs = entry.get("lexicon_strongs_candidates") or []
    if isinstance(strongs, list) and strongs:
        return "lexicon_strongs_linked"
    hints = entry.get("morphhb_strongs_hints") or []
    if isinstance(hints, list) and hints:
        return "morphhb_strongs_linked"
    if entry.get("morphhb_chosen"):
        return "morphhb_chosen"
    aid = str(entry.get("atom_id") or "")
    if _GH_ATOM_RE.match(aid):
        return "atom_id_g_h_prefix"
    return None


def mdl_prune_priority(entry: dict[str, Any], golden_tokens: frozenset[str]) -> tuple[float, int, str]:
    """Higher tuple sorts first for removal (low corpus utility)."""
    nf = str(entry.get("normalized_form") or "").strip().lower()
    occ = int(entry.get("occurrences") or 0)
    in_g40 = 1 if nf in golden_tokens else 0
    return (float(in_g40), float(occ), nf)


def prune_lexicon_entries(
    entries: list[dict[str, Any]],
    *,
    target_reduction_pct: float,
    golden_tokens: frozenset[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    total = len(entries)
    target_remove = max(0, int(round(total * target_reduction_pct / 100.0)))
    must_keep: list[dict[str, Any]] = []
    prune_pool: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        reason = must_keep_reason(ent, golden_tokens)
        if reason:
            must_keep.append(ent)
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            prune_pool.append(ent)
    prune_pool.sort(key=lambda e: mdl_prune_priority(e, golden_tokens))
    removed = prune_pool[: min(target_remove, len(prune_pool))]
    removed_ids = {id(x) for x in removed}
    kept = must_keep + [e for e in prune_pool if id(e) not in removed_ids]
    actual_removed = total - len(kept)
    meta = {
        "target_reduction_pct": target_reduction_pct,
        "baseline_row_count": total,
        "must_keep_count": len(must_keep),
        "must_keep_reasons": reasons,
        "prune_pool_count": len(prune_pool),
        "removed_count": actual_removed,
        "kept_row_count": len(kept),
        "actual_reduction_pct": round(100.0 * actual_removed / total, 4) if total else 0.0,
    }
    return kept, meta


def write_pruned_lexicon(
    baseline_doc: dict[str, Any],
    kept_entries: list[dict[str, Any]],
    *,
    out_path: Path,
    sweep_pct: float,
    prune_meta: dict[str, Any],
) -> None:
    out = deepcopy(baseline_doc)
    out["entries"] = kept_entries
    out["row_count"] = len(kept_entries)
    out["mdl_prune_poc_meta"] = {
        "schema": "universal_root_mdl_prune_poc_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "sweep_reduction_pct_target": sweep_pct,
        **prune_meta,
        "note": "B-track candidate only — production pointer unchanged.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evaluate_golden40_compress(
    lexicon_path: Path,
    *,
    input_path: Path | None = None,
) -> dict[str, Any]:
    src = _load_json(input_path or INPUT_V2)
    baseline = _load_json(BASELINE_V2) if BASELINE_V2.is_file() else {}
    decision = _load_json(DECISION) if DECISION.is_file() else {}
    selected = decision.get("selected_candidate") or {}
    baseline_j = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))
    report = evaluate_report(
        src,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=str(selected.get("strategy", "A")),
        intensity=str(selected.get("intensity", "extreme")),
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_j,
        general_max_saving_rate=float(selected.get("general_max_saving_rate", 0.35)),
        sensitive_max_saving_rate=float(selected.get("sensitive_max_saving_rate", 0.3)),
        hangul_max_saving_rate=float(selected.get("hangul_max_saving_rate", 0.6)),
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_path=lexicon_path,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        apply_gematria_4d_bridge_policy=False,
        include_cee_core=True,
    )
    cm = report.get("compression_metrics") or {}
    return {
        "case_count": cm.get("case_count"),
        "global_token_saving_rate": cm.get("global_token_saving_rate"),
        "avg_reconstruction_fidelity_jaccard": cm.get("avg_reconstruction_fidelity_jaccard"),
        "avg_sensitive_integrity": cm.get("avg_sensitive_integrity"),
    }


def run_mdl_sweep(
    baseline_lexicon_path: Path,
    *,
    sweep_pcts: tuple[float, ...] = DEFAULT_SWEEP_PCTS,
    jaccard_floor_delta_pp: float = DEFAULT_JACCARD_FLOOR_DELTA_PP,
    scratch_dir: Path,
    input_path: Path | None = None,
) -> dict[str, Any]:
    baseline_doc = _load_json(baseline_lexicon_path)
    entries = [e for e in (baseline_doc.get("entries") or []) if isinstance(e, dict)]
    golden_tokens = golden40_unicode_tokens(input_path)
    baseline_metrics = evaluate_golden40_compress(baseline_lexicon_path, input_path=input_path)
    baseline_j = float(baseline_metrics.get("avg_reconstruction_fidelity_jaccard") or 0.0)
    jaccard_floor = baseline_j - jaccard_floor_delta_pp

    sweep_rows: list[dict[str, Any]] = []
    passing: list[dict[str, Any]] = []
    for pct in sweep_pcts:
        kept, prune_meta = prune_lexicon_entries(entries, target_reduction_pct=pct, golden_tokens=golden_tokens)
        out_path = scratch_dir / f"mdl_prune_{int(pct)}pct_v1.json"
        write_pruned_lexicon(baseline_doc, kept, out_path=out_path, sweep_pct=pct, prune_meta=prune_meta)
        metrics = evaluate_golden40_compress(out_path, input_path=input_path)
        jaccard = float(metrics.get("avg_reconstruction_fidelity_jaccard") or 0.0)
        delta_pp = jaccard - baseline_j
        try:
            rel_path = str(out_path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            rel_path = str(out_path)
        row = {
            "sweep_reduction_pct_target": pct,
            "pruned_lexicon_path": rel_path,
            "prune_meta": prune_meta,
            "golden40_metrics": metrics,
            "jaccard_delta_pp_vs_baseline": round(delta_pp, 6),
            "jaccard_floor": round(jaccard_floor, 6),
            "pass_jaccard_floor": jaccard >= jaccard_floor - 1e-9,
            "pass_reduction_band": 5.0 <= prune_meta["actual_reduction_pct"] <= 15.0,
        }
        row["pass_poc"] = row["pass_jaccard_floor"] and row["pass_reduction_band"]
        sweep_rows.append(row)
        if row["pass_poc"]:
            passing.append(row)

    best = max(sweep_rows, key=lambda r: (r["pass_poc"], r["prune_meta"]["actual_reduction_pct"])) if sweep_rows else None
    try:
        baseline_rel = str(baseline_lexicon_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        baseline_rel = str(baseline_lexicon_path)
    return {
        "baseline_lexicon_path": baseline_rel,
        "baseline_row_count": len(entries),
        "golden40_token_count": len(golden_tokens),
        "baseline_golden40_metrics": baseline_metrics,
        "baseline_jaccard": baseline_j,
        "jaccard_floor_delta_pp": jaccard_floor_delta_pp,
        "jaccard_floor": jaccard_floor,
        "sweep_rows": sweep_rows,
        "any_sweep_pass": bool(passing),
        "best_sweep": best,
    }
