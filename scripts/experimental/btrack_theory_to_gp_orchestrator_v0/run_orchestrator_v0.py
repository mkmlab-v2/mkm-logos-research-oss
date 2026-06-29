#!/usr/bin/env python3
"""B-track theory → general_prophecy orchestrator v0 ([HYPO], experimental, NON_GATING).

Wraps existing Logos GraphRAG + market CSV gate + gp template render + schema validate.
Does NOT promote Track A or trigger live trading. See orchestrator_spec_v0.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
DEFAULT_PACK = PKG / "packs" / "ai_sox_logos_v0.json"
DEFAULT_TEMPLATES = PKG / "proposition_templates_v0.json"
DEFAULT_SPEC = PKG / "orchestrator_spec_v0.json"
GP_SCHEMA = ROOT / "docs" / "final" / "GENERAL_PROPHECY_SCHEMA_V1.json"
GRAPHRAG = ROOT / "scripts" / "run_logos_subgraph_graphrag_router_v1.py"
GP_GENERATE = ROOT / "scripts" / "generate_general_prophecy_v1.py"
DEFAULT_AUDIT = ROOT / "reports" / "btrack_theory_to_gp_orchestrator_v0_latest.json"
DEFAULT_DRAFT = ROOT / "tests" / "fixtures" / "general_prophecy_registry_orchestrator_draft_v0.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(template: str, ctx: dict[str, Any]) -> str:
    out = template
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _market_audit(csv_path: Path, reference_date: str) -> dict[str, Any]:
    audit: dict[str, Any] = {"csv_path": str(csv_path), "ok": False}
    if not csv_path.is_file():
        audit["error"] = "csv_missing"
        return audit
    try:
        import pandas as pd
    except ImportError:
        audit["error"] = "pandas_missing"
        return audit
    df = pd.read_csv(csv_path)
    if "Date" not in df.columns or "Close" not in df.columns:
        audit["error"] = "csv_columns_invalid"
        return audit
    ref = df[df["Date"] <= reference_date]
    if ref.empty:
        audit["error"] = "no_rows_on_or_before_reference_date"
        return audit
    reference_high = float(ref["Close"].max())
    last = ref.iloc[-1]
    audit.update(
        {
            "ok": True,
            "reference_date": reference_date,
            "reference_high": reference_high,
            "last_row_date": str(last["Date"]),
            "last_close": float(last["Close"]),
            "row_count": int(len(df)),
            "threshold_90pct": pack_drawdown_threshold(reference_high, 0.10),
        }
    )
    return audit


def pack_drawdown_threshold(reference_high: float, pct: float) -> float:
    return round(reference_high * (1.0 - pct), 2)


def build_context(pack: dict[str, Any]) -> dict[str, Any]:
    drop_pct = int(pack.get("drop_pct", 5))
    drawdown_pct = int(pack.get("drawdown_pct", 10))
    drop_decimal = drop_pct / 100.0
    return {
        "pack_id": pack.get("pack_id", "unknown"),
        "reference_date": pack["reference_date"],
        "window_start": pack["window_start"],
        "window_end": pack["window_end"],
        "deadline_label": pack["deadline_label"],
        "resolution_deadline_utc": pack["resolution_deadline_utc"],
        "drop_window_label": pack["drop_window_label"],
        "drop_window_start": pack["drop_window_start"],
        "drop_window_end": pack["drop_window_end"],
        "drop_pct": drop_pct,
        "drop_pct_decimal": str(drop_decimal),
        "drawdown_pct": drawdown_pct,
        "drawdown_multiplier": pack.get("drawdown_multiplier", "0.90"),
        "market_csv_rel": pack["market"]["csv_rel"],
        "symbol_yahoo": pack["market"].get("symbol_yahoo", "^SOX"),
        "index_label": pack["market"].get("index_label", pack["market"].get("symbol_yahoo", "^SOX")),
        "motif_lanes": "+".join(pack.get("motif_lanes") or []),
        "seed_verses": ", ".join(pack.get("seed_verses") or []),
    }


def render_question(
    template: dict[str, Any],
    pack: dict[str, Any],
    ctx: dict[str, Any],
    *,
    layer3_ref: str | None,
    issued_at_utc: str,
) -> dict[str, Any]:
    motif_key = template["motif_key"]
    p_prior = (pack.get("motif_p_prior") or {}).get(motif_key)
    if p_prior is None:
        raise ValueError(f"missing motif_p_prior for {motif_key}")

    outcome = template["outcome_spec"]
    if isinstance(outcome, dict):
        outcome = {k: _fmt(str(v), ctx) if isinstance(v, str) else v for k, v in outcome.items()}

    return {
        "schema": "general_prophecy_question_v1",
        "research_rail": pack.get("research_rail", "B"),
        "boundary_ack": True,
        "question_id": template["question_id"],
        "prophecy_track": template.get("prophecy_track", "financial"),
        "question_text": _fmt(template["question_text"], ctx),
        "domain_tags": list(template.get("domain_tags") or []),
        "resolution_deadline_utc": _fmt(template["resolution_deadline_utc"], ctx),
        "resolution_criteria": _fmt(template["resolution_criteria"], ctx),
        "outcome_spec": outcome,
        "forecasts": [
            {
                "issued_at_utc": issued_at_utc,
                "probability_0_1": float(p_prior),
                "source_kind": "hybrid",
                "source_detail": _fmt(template["source_detail_template"], ctx),
                "brier_ready": True,
            }
        ],
        "resolution": {"status": "pending"},
        "layer3_interpretation_ref": layer3_ref or pack.get("graphrag_output_rel"),
        "epistemic_firewall": {
            "l1_probability_fields": ["forecasts[].probability_0_1"],
            "l3_narrative_forbidden_in": ["forecasts", "resolution"],
        },
    }


def build_registry_draft(
    pack: dict[str, Any],
    templates_doc: dict[str, Any],
    *,
    issued_at_utc: str | None = None,
) -> dict[str, Any]:
    issued = issued_at_utc or _utc_now()
    ctx = build_context(pack)
    tpl_bank = templates_doc.get("templates") or {}
    layer3_refs = pack.get("layer3_refs") or {}
    overrides_map = pack.get("template_overrides") or {}
    questions: list[dict[str, Any]] = []
    for tid in pack.get("template_ids") or []:
        raw = tpl_bank.get(tid)
        if not isinstance(raw, dict):
            raise ValueError(f"unknown template_id: {tid}")
        merged = dict(raw)
        ov = overrides_map.get(tid)
        if isinstance(ov, dict):
            merged.update(ov)
        if "question_id" not in merged:
            raise ValueError(f"template {tid} missing question_id after overrides")
        q = render_question(
            merged,
            pack,
            ctx,
            layer3_ref=layer3_refs.get(tid),
            issued_at_utc=issued,
        )
        questions.append(q)

    return {
        "schema": "general_prophecy_registry_v1",
        "version": "1.0.0",
        "research_rail": "B",
        "boundary_ack": True,
        "generated_at_utc": issued,
        "git_commit_hint": f"orchestrator_v0:{pack.get('pack_id', 'unknown')}",
        "questions": questions,
    }


def validate_gp_registry(doc: dict[str, Any]) -> None:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:
        raise SystemExit("jsonschema required: pip install jsonschema") from e
    schema = _load_json(GP_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(doc)


def run_graphrag(pack: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    query = pack.get("topic_query_graphrag") or ""
    out_rel = pack.get("graphrag_output_rel") or "reports/logos_graphrag_orchestrator_latest.json"
    out = ROOT / out_rel
    cmd = [sys.executable, str(GRAPHRAG), "--query", query, "--output-json", str(out), "--top-bridges", "3"]
    step: dict[str, Any] = {"cmd": [str(c) for c in cmd], "skipped": dry_run}
    if dry_run:
        step["status"] = "dry_run"
        return step
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    step["exit_code"] = cp.returncode
    step["stdout_tail"] = (cp.stdout or "").strip()[-500:]
    step["status"] = "ok" if cp.returncode == 0 else "fail"
    return step


def merge_registry(draft_path: Path, *, dry_run: bool) -> dict[str, Any]:
    primary = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
    cmd = [
        sys.executable,
        str(GP_GENERATE),
        "-i",
        str(primary),
        "--merge-from",
        str(draft_path),
        "--no-default-merge",
    ]
    if dry_run:
        cmd.append("--dry-run")
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "exit_code": cp.returncode,
        "stdout": (cp.stdout or "").strip(),
        "status": "ok" if cp.returncode == 0 else "fail",
    }


def orchestrate(
    *,
    pack_path: Path,
    templates_path: Path,
    draft_out: Path,
    audit_out: Path,
    skip_csv_check: bool = False,
    run_graphrag_flag: bool = False,
    graphrag_dry_run: bool = False,
    merge_registry_flag: bool = False,
    merge_dry_run: bool = False,
    write_draft: bool = True,
) -> dict[str, Any]:
    pack = _load_json(pack_path)
    templates_doc = _load_json(templates_path)
    spec = _load_json(DEFAULT_SPEC) if DEFAULT_SPEC.is_file() else {}

    csv_path = ROOT / pack["market"]["csv_rel"]
    market_audit = _market_audit(csv_path, pack["reference_date"])

    audit: dict[str, Any] = {
        "schema": "btrack_theory_to_gp_orchestrator_audit_v0",
        "generated_at_utc": _utc_now(),
        "pack_id": pack.get("pack_id"),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "spec_schema": spec.get("schema"),
        "market_audit": market_audit,
        "steps": [],
    }

    if not skip_csv_check and not market_audit.get("ok"):
        audit["decision"] = "BLOCKED_CSV_GATE"
        audit_out.parent.mkdir(parents=True, exist_ok=True)
        audit_out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return audit

    if run_graphrag_flag:
        audit["steps"].append({"stage": "graphrag_optional", **run_graphrag(pack, dry_run=graphrag_dry_run)})

    draft = build_registry_draft(pack, templates_doc)
    validate_gp_registry(draft)
    audit["steps"].append({"stage": "proposition_build", "question_count": len(draft["questions"])})
    audit["steps"].append({"stage": "schema_validate", "status": "ok"})

    if write_draft:
        draft_out.parent.mkdir(parents=True, exist_ok=True)
        draft_out.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            audit["draft_registry"] = str(draft_out.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except ValueError:
            audit["draft_registry"] = str(draft_out.resolve())

    if merge_registry_flag:
        mg = merge_registry(draft_out, dry_run=merge_dry_run)
        audit["steps"].append({"stage": "registry_merge_optional", **mg})
        audit["decision"] = "OK_MERGE_DRY_RUN" if merge_dry_run and mg.get("status") == "ok" else (
            "OK_MERGED" if mg.get("status") == "ok" else "MERGE_FAILED"
        )
    else:
        audit["decision"] = "OK_DRAFT_ONLY"

    audit["question_ids"] = [q["question_id"] for q in draft["questions"]]
    audit_out.parent.mkdir(parents=True, exist_ok=True)
    audit_out.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--templates", type=Path, default=DEFAULT_TEMPLATES)
    ap.add_argument("--draft-out", type=Path, default=DEFAULT_DRAFT)
    ap.add_argument("--audit-json", type=Path, default=DEFAULT_AUDIT)
    ap.add_argument("--skip-csv-check", action="store_true")
    ap.add_argument("--run-graphrag", action="store_true")
    ap.add_argument("--graphrag-dry-run", action="store_true")
    ap.add_argument("--merge-registry", action="store_true")
    ap.add_argument("--merge-dry-run", action="store_true")
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()

    audit = orchestrate(
        pack_path=ns.pack,
        templates_path=ns.templates,
        draft_out=ns.draft_out,
        audit_out=ns.audit_json,
        skip_csv_check=ns.skip_csv_check,
        run_graphrag_flag=ns.run_graphrag,
        graphrag_dry_run=ns.graphrag_dry_run,
        merge_registry_flag=ns.merge_registry,
        merge_dry_run=ns.merge_dry_run,
    )
    ok = str(audit.get("decision", "")).startswith("OK")
    print(json.dumps({"ok": ok, "decision": audit.get("decision"), "audit": str(ns.audit_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
