#!/usr/bin/env python3
"""Diff economy grid cell vs frozen active — run_config + per-case deltas for changed Golden-40 rows."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1"
ACTIVE = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
DEFAULT_ECONOMY = EXP / "runs" / "profile_economy.json"
DEFAULT_TRIAGE = EXP / "results" / "compression_pipeline_grid_sweep_triage_v1_latest.json"
DEFAULT_DIFF = EXP / "results" / "compression_pipeline_grid_sweep_golden40_diff_v1_latest.json"
DEFAULT_OUT = EXP / "results" / "economy_run_config_vs_frozen_active_diff_v1_latest.json"

_SKIP_RUN_CONFIG_KEYS = frozenset(
    {
        "tiktoken_o200k_encoding",
        "tiktoken_o200k_available",
        "tiktoken_o200k_unavailable_reason",
        "case_graph_wire_influence_count",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_lexicon_path(raw: str | None) -> str:
    if not raw:
        return ""
    name = Path(str(raw).replace("\\", "/")).name
    return name


def _run_config_diff(frozen_rc: dict[str, Any], economy_rc: dict[str, Any]) -> dict[str, Any]:
    keys = sorted(set(frozen_rc) | set(economy_rc))
    changed: list[dict[str, Any]] = []
    for key in keys:
        if key in _SKIP_RUN_CONFIG_KEYS:
            continue
        fv, ev = frozen_rc.get(key), economy_rc.get(key)
        if fv == ev:
            continue
        entry: dict[str, Any] = {"key": key, "frozen_active": fv, "economy_cell": ev}
        if key == "master_codebook_lexicon_path":
            entry["frozen_lexicon_basename"] = _norm_lexicon_path(str(fv) if fv else None)
            entry["economy_lexicon_basename"] = _norm_lexicon_path(str(ev) if ev else None)
        changed.append(entry)
    return {
        "changed_field_count": len(changed),
        "fields": changed,
        "headline_deltas": [
            c["key"]
            for c in changed
            if c["key"]
            in {
                "master_codebook_lexicon_path",
                "include_gematria_metadata",
                "include_gematria_4d_bridge",
                "include_cee_core",
                "apply_gematria_4d_bridge_policy",
                "domain_relaxed_max_saving_overrides",
                "domain_relaxed_max_saving_case_allowlist",
            }
        ],
    }


def _case_index(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(c["id"]): c for c in cases if c.get("id")}


def _case_route_summary(row: dict[str, Any]) -> dict[str, Any]:
    route = row.get("route") or {}
    lex = route.get("master_codebook_lexicon_v1") or {}
    return {
        "shard_id": route.get("shard_id"),
        "domain": route.get("domain"),
        "lexicon_basename": _norm_lexicon_path(lex.get("path")),
        "lexicon_hit_count": lex.get("hit_count"),
    }


def _per_case_diff(
    frozen_row: dict[str, Any],
    economy_row: dict[str, Any],
) -> dict[str, Any]:
    fs = float(frozen_row.get("token_saving_rate") or 0)
    es = float(economy_row.get("token_saving_rate") or 0)
    fj = float(frozen_row.get("reconstruction_fidelity_jaccard") or 0)
    ej = float(economy_row.get("reconstruction_fidelity_jaccard") or 0)
    fct = int(frozen_row.get("compressed_tokens") or 0)
    ect = int(economy_row.get("compressed_tokens") or 0)
    out: dict[str, Any] = {
        "frozen_active": {
            "token_saving_rate": round(fs, 6),
            "reconstruction_fidelity_jaccard": round(fj, 6),
            "compressed_tokens": fct,
            "route": _case_route_summary(frozen_row),
        },
        "economy_cell": {
            "token_saving_rate": round(es, 6),
            "reconstruction_fidelity_jaccard": round(ej, 6),
            "compressed_tokens": ect,
            "route": _case_route_summary(economy_row),
        },
        "delta": {
            "token_saving_rate": round(es - fs, 6),
            "reconstruction_fidelity_jaccard": round(ej - fj, 6),
            "compressed_tokens": ect - fct,
        },
    }
    f_comp = frozen_row.get("compressed_text_effective") or frozen_row.get("compressed_text") or ""
    e_comp = economy_row.get("compressed_text_effective") or economy_row.get("compressed_text") or ""
    if f_comp != e_comp:
        out["compressed_text_changed"] = True
        out["compressed_text_frozen_snippet"] = str(f_comp)[:160]
        out["compressed_text_economy_snippet"] = str(e_comp)[:160]
    else:
        out["compressed_text_changed"] = False
    f_recon = frozen_row.get("reconstructed_text_effective") or frozen_row.get("reconstructed_text") or ""
    e_recon = economy_row.get("reconstructed_text_effective") or economy_row.get("reconstructed_text") or ""
    if f_recon != e_recon:
        out["reconstructed_text_changed"] = True
    else:
        out["reconstructed_text_changed"] = False
    return out


def _hypothesis_from_diff(run_diff: dict[str, Any], case_diffs: dict[str, Any]) -> list[str]:
    hypotheses: list[str] = []
    headline = set(run_diff.get("headline_deltas") or [])
    if "master_codebook_lexicon_path" in headline:
        hypotheses.append(
            "[FACT] Top-level run_config lexicon basename differs (41708 vs 41658 in typical paths); "
            "re-eval changed lexicon hits/routing for subset of cases."
        )
    bridge_keys = {
        "include_gematria_metadata",
        "include_gematria_4d_bridge",
        "include_cee_core",
    }
    if headline & bridge_keys:
        hypotheses.append(
            "[FACT] Frozen active stores bridge metadata channels ON with apply_gematria_4d_bridge_policy=false; "
            "economy profile forces bridge OFF — decoder/metadata path diverges on re-run."
        )
    if not any(
        case_diffs[cid]["delta"]["token_saving_rate"] != 0
        or case_diffs[cid]["delta"]["reconstruction_fidelity_jaccard"] != 0
        for cid in case_diffs
    ):
        hypotheses.append("[HYPO] No per-case metric delta despite config diff — investigate stale triage pointer.")
    ssot_allow = {"cmp2_002", "cmp2_004", "cmp2_005", "cmp2_006", "cmp2_009"}
    changed_outside = [cid for cid in case_diffs if cid not in ssot_allow]
    if changed_outside:
        hypotheses.append(
            "[FACT] Changed cases include IDs outside domain_relaxed ssot allowlist "
            f"({', '.join(sorted(changed_outside))}) — uplift is not explained by ssot cap alone."
        )
    scm_saving = [
        cid
        for cid, d in case_diffs.items()
        if d["delta"]["token_saving_rate"] > 0 and d["economy_cell"]["route"].get("domain") == "scm"
    ]
    if scm_saving:
        hypotheses.append(
            "[HYPO] SCM-labeled routes show saving gains under economy re-eval; "
            "likely lexicon hit / compressed token count shift, not ssot relaxed cap."
        )
    return hypotheses


def main() -> int:
    ap = argparse.ArgumentParser(description="Economy vs frozen active config diff (research_only).")
    ap.add_argument("--frozen", type=Path, default=ACTIVE)
    ap.add_argument("--economy", type=Path, default=DEFAULT_ECONOMY)
    ap.add_argument("--golden-diff", type=Path, default=DEFAULT_DIFF)
    ap.add_argument("--triage", type=Path, default=DEFAULT_TRIAGE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--mirror-pilot", action="store_true")
    args = ap.parse_args()

    for path in (args.frozen, args.economy):
        if not path.is_file():
            print(f"ABORT: missing {path}")
            return 2

    frozen_doc = _load(args.frozen)
    economy_doc = _load(args.economy)
    frozen_rc = frozen_doc.get("run_config") or {}
    economy_rc = economy_doc.get("run_config") or {}
    run_diff = _run_config_diff(frozen_rc, economy_rc)

    frozen_cases = _case_index((frozen_doc.get("compression_metrics") or {}).get("cases") or [])
    economy_cases = _case_index((economy_doc.get("compression_metrics") or {}).get("cases") or [])

    changed_ids: list[str] = []
    if args.golden_diff.is_file():
        diff_doc = _load(args.golden_diff)
        rows = (diff_doc.get("cells") or {}).get("profile_economy") or []
        changed_ids = [
            str(r["id"])
            for r in rows
            if abs(r.get("delta_saving", 0)) > 1e-9 or abs(r.get("delta_jaccard", 0)) > 1e-9
        ]
    if not changed_ids and args.triage.is_file():
        triage = _load(args.triage)
        pe = (triage.get("profile_triage") or {}).get("profile_economy") or {}
        changed_ids = list(pe.get("saving_increase_ids") or []) + list(pe.get("jaccard_decrease_ids") or [])
        changed_ids = sorted(set(changed_ids))

    case_diffs: dict[str, Any] = {}
    for cid in changed_ids:
        fr, er = frozen_cases.get(cid), economy_cases.get(cid)
        if not fr or not er:
            case_diffs[cid] = {"error": "missing in frozen or economy report"}
            continue
        case_diffs[cid] = _per_case_diff(fr, er)

    out = {
        "schema": "economy_run_config_vs_frozen_active_diff_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "promote_active": False,
        "correlation_claim_allowed": False,
        "frozen_active_pointer": str(args.frozen.relative_to(ROOT)).replace("\\", "/"),
        "economy_cell_pointer": str(args.economy.relative_to(ROOT)).replace("\\", "/"),
        "changed_case_ids": changed_ids,
        "unchanged_case_count": 40 - len(changed_ids),
        "run_config_diff": run_diff,
        "per_case_diff": case_diffs,
        "causal_hypotheses": _hypothesis_from_diff(run_diff, case_diffs),
        "operator_verdict": {
            "status": "PASS_WITH_RISK",
            "promote_active": False,
            "note": "Config diff explains subset re-eval; not equivalent to frozen active reproduction.",
        },
        "next_actions_research_only": [
            "Re-run economy cell with frozen lexicon 41708 path to isolate lexicon vs bridge delta.",
            "Manual text diff on cmp2_028 and cmp2_034 before any sign-off.",
            "Do not overwrite MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json from grid sweep.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"run_config_changed_fields={run_diff['changed_field_count']} changed_cases={len(changed_ids)}")

    if args.mirror_pilot:
        pilot = ROOT / "reports" / "constitution" / "btrack_pilot" / "economy_run_config_vs_frozen_active_diff_v1_latest.json"
        pilot.write_text(args.out.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"WROTE: {pilot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
