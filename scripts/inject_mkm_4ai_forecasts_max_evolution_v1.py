#!/usr/bin/env python3
"""Inject MKM 4AI Coordinator Layer-1 forecasts into max evolution prophecy registry [HYPO].

Modes:
  deterministic — local 4AI fusion only (default, offline, tier_0)
  hybrid        — LLM refine: Azure OpenAI first (MKM_LLM_PRIORITY=azure_first), Gemini developer fallback
  gemini        — Gemini developer billing only
  azure         — Azure OpenAI only (no Gemini fallback)

Billing SSOT: scripts/news_neutralizer_llm_v1.py (resolve_billing · llm_json).

Writes JSONL + applies to registry; report at reports/mkm_max_prophecy_4ai_forecast_inject_v1_latest.json
"""

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

from scripts.mkm_max_prophecy_4ai_forecast_lib_v1 import (
    SignalContext,
    clamp01,
    forecast_snapshots,
    fuse_4ai_probability,
    load_signal_context,
    utc_now,
)

ROW_SCHEMA = "general_prophecy_forecast_inject_row_v1"

DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
DEFAULT_JSONL = ROOT / "docs/final/artifacts/mkm_max_prophecy_4ai_forecasts_v1_latest.jsonl"
DEFAULT_REPORT = ROOT / "reports/mkm_max_prophecy_4ai_forecast_inject_v1_latest.json"
APPLY_SCRIPT = ROOT / "scripts/apply_general_prophecy_forecasts_jsonl_v1.py"
SOURCE_DETAIL_PREFIX = "mkm_4ai_coordinator_v1"

SYSTEM_PROMPT = (
    "You are a B-track calibration forecaster (research_only, non-gating). "
    "Return JSON only with key forecasts: array of "
    '{"question_id": string, "probability_0_1": number in [0.05,0.95]}. '
    "No narrative."
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _env_truthy(name: str) -> bool:
    return str(os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _llm_available() -> bool:
    try:
        from scripts.news_neutralizer_llm_v1 import azure_openai_config, load_workspace_dotenv

        load_workspace_dotenv()
        if azure_openai_config():
            return True
    except Exception:
        pass
    for k in ("GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY", "GOOGLE_API_KEY"):
        if (os.environ.get(k) or "").strip():
            return True
    return False


def _pending_questions(
    doc: dict[str, Any],
    *,
    id_prefix: str,
    max_rows: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        qid = str(q.get("question_id") or "")
        if id_prefix and not qid.startswith(id_prefix):
            continue
        res = q.get("resolution") or {}
        if str(res.get("status") or "pending") != "pending":
            continue
        out.append(q)
        if max_rows > 0 and len(out) >= max_rows:
            break
    return out


def _compact_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "question_id": q.get("question_id"),
            "question_text": (q.get("question_text") or "")[:400],
            "domain_tags": q.get("domain_tags") or [],
        }
        for q in questions
    ]


def parse_forecast_probability_map(parsed: dict[str, Any] | list[Any]) -> dict[str, float]:
    """Normalize LLM JSON (object with forecasts[] or bare list) to question_id -> p."""
    items: list[Any]
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        raw = parsed.get("forecasts")
        if isinstance(raw, list):
            items = raw
        else:
            items = [parsed]
    else:
        return {}

    out: dict[str, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        qid = item.get("question_id")
        p = item.get("probability_0_1")
        if isinstance(qid, str) and isinstance(p, (int, float)):
            out[qid] = clamp01(float(p))
    return out


def _parse_raw_array_fallback(raw: str) -> dict[str, float]:
    m = re.search(r"\[[\s\S]*\]", raw or "")
    if not m:
        return {}
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
    return parse_forecast_probability_map(arr)


def _llm_batch_probs_once(
    questions: list[dict[str, Any]],
    *,
    billing: str,
    timeout_sec: int,
    flash_model: str,
    azure_deployment: str | None,
) -> tuple[dict[str, float], dict[str, Any]]:
    from scripts.news_neutralizer_llm_v1 import llm_json, load_workspace_dotenv

    load_workspace_dotenv()
    compact = _compact_questions(questions)
    user = json.dumps({"forecasts_request": compact}, ensure_ascii=False)
    parsed, raw, resolved, model_label = llm_json(
        billing=billing,
        system=SYSTEM_PROMPT,
        user=user,
        timeout=timeout_sec,
        flash_model=flash_model,
        pro_model=flash_model,
        azure_deployment=azure_deployment,
    )
    prob_map = parse_forecast_probability_map(parsed)
    if not prob_map and raw:
        prob_map = _parse_raw_array_fallback(raw)
    return prob_map, {
        "billing_resolved": resolved,
        "model_label": model_label,
        "raw_len": len(raw or ""),
    }


def fetch_llm_batch_probs(
    questions: list[dict[str, Any]],
    *,
    mode: str,
    billing: str,
    timeout_sec: int,
    flash_model: str,
    azure_deployment: str | None,
) -> tuple[dict[str, float], dict[str, str], dict[str, Any]]:
    """Returns (prob_map, source_by_qid, llm_meta)."""
    prob_map: dict[str, float] = {}
    source_by_qid: dict[str, str] = {}
    meta: dict[str, Any] = {"mode": mode, "billing_requested": billing, "attempts": []}

    if mode == "deterministic":
        return prob_map, source_by_qid, meta

    errors: list[str] = []

    def _try(bill: str, source_suffix: str) -> bool:
        try:
            m, attempt = _llm_batch_probs_once(
                questions,
                billing=bill,
                timeout_sec=timeout_sec,
                flash_model=flash_model,
                azure_deployment=azure_deployment,
            )
            meta["attempts"].append({**attempt, "billing_arg": bill, "n_probs": len(m)})
            if m:
                for qid, p in m.items():
                    prob_map[qid] = p
                    source_by_qid[qid] = f"{SOURCE_DETAIL_PREFIX}:{source_suffix}"
                return True
            errors.append(f"{bill}:empty_map")
            return False
        except Exception as e:
            errors.append(f"{bill}:{e}")
            meta["attempts"].append({"billing_arg": bill, "error": str(e)})
            return False

    if mode == "azure":
        if not _try("azure", "azure_refine"):
            raise RuntimeError("; ".join(errors) or "azure_batch_empty")
    elif mode == "gemini":
        if not _try("developer", "gemini_refine"):
            raise RuntimeError("; ".join(errors) or "gemini_batch_empty")
    elif mode == "hybrid":
        if billing in ("auto", "azure"):
            _try("azure", "azure_refine")
        if not prob_map and billing in ("auto", "developer"):
            _try("developer", "gemini_refine")
    else:
        raise ValueError(f"unknown mode: {mode}")

    meta["llm_errors"] = errors
    meta["llm_applied_count"] = len(prob_map)
    return prob_map, source_by_qid, meta


def build_inject_rows(
    questions: list[dict[str, Any]],
    ctx: SignalContext,
    *,
    mode: str,
    billing: str,
    flash_model: str,
    timeout_sec: int,
    azure_deployment: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    llm_map: dict[str, float] = {}
    source_by_qid: dict[str, str] = {}
    llm_meta: dict[str, Any] = {}
    llm_err: str | None = None

    if mode != "deterministic":
        try:
            llm_map, source_by_qid, llm_meta = fetch_llm_batch_probs(
                questions,
                mode=mode,
                billing=billing,
                timeout_sec=timeout_sec,
                flash_model=flash_model,
                azure_deployment=azure_deployment,
            )
        except Exception as e:
            llm_err = str(e)
            if mode in ("gemini", "azure"):
                raise

    rows: list[dict[str, Any]] = []
    meta_rows: list[dict[str, Any]] = []
    issued = utc_now()

    for q in questions:
        qid = str(q.get("question_id"))
        fusion = fuse_4ai_probability(q, ctx)
        p = float(fusion["probability_0_1"])
        source = f"{SOURCE_DETAIL_PREFIX}:deterministic"
        if qid in llm_map:
            p = llm_map[qid]
            source = source_by_qid.get(qid, f"{SOURCE_DETAIL_PREFIX}:llm_refine")
        elif mode in ("gemini", "azure") and llm_map:
            continue

        rows.append(
            {
                "schema": ROW_SCHEMA,
                "question_id": qid,
                "mode": "replace_matching_detail_prefix",
                "detail_prefix": SOURCE_DETAIL_PREFIX,
                "forecasts": forecast_snapshots(
                    probability=p,
                    source_detail=source,
                    issued_at=issued,
                ),
            }
        )
        meta_rows.append({"question_id": qid, "probability_0_1": p, "fusion": fusion, "source": source})

    azure_n = sum(1 for r in meta_rows if ":azure_refine" in r["source"])
    gemini_n = sum(1 for r in meta_rows if ":gemini_refine" in r["source"])

    return rows, {
        "mode": mode,
        "billing": billing,
        "azure_applied_count": azure_n,
        "gemini_applied_count": gemini_n,
        "deterministic_count": sum(1 for r in meta_rows if r["source"].endswith("deterministic")),
        "llm_error": llm_err,
        "llm_meta": llm_meta,
        "signal_sources": ctx.sources_present,
        "rows": meta_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--question-id-prefix", default="max.", help="Only inject matching ids (empty = all pending)")
    ap.add_argument("--max-rows", type=int, default=0, help="Cap rows (0 = no cap)")
    ap.add_argument(
        "--mode",
        choices=["deterministic", "hybrid", "gemini", "azure"],
        default="deterministic",
    )
    ap.add_argument(
        "--billing",
        choices=["auto", "azure", "developer"],
        default=os.environ.get("MKM_MAX_PROPHECY_BILLING", "auto"),
        help="LLM billing route (auto=azure_first per MKM_LLM_PRIORITY)",
    )
    ap.add_argument("--skip-apply", action="store_true", help="Write JSONL only")
    ap.add_argument(
        "--flash-model",
        default=os.environ.get("MKM_MAX_PROPHECY_GEMINI_MODEL", "gemini-2.5-flash"),
        help="Gemini flash model when billing resolves to developer/vertex",
    )
    ap.add_argument(
        "--azure-deployment",
        default=os.environ.get("MKM_MAX_PROPHECY_AZURE_DEPLOYMENT") or os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        help="Azure deployment override (default AZURE_OPENAI_DEPLOYMENT)",
    )
    ap.add_argument("--timeout-sec", type=int, default=int(os.environ.get("MKM_MAX_PROPHECY_LLM_TIMEOUT_SEC", "120")))
    ns = ap.parse_args()

    if _env_truthy("MKM_MAX_PROPHECY_USE_GEMINI") and ns.mode == "deterministic":
        ns.mode = "hybrid"

    if not ns.registry.is_file():
        print(f"missing registry: {ns.registry}", file=sys.stderr)
        return 2

    doc = _load(ns.registry)
    ctx = load_signal_context(ROOT)
    questions = _pending_questions(doc, id_prefix=ns.question_id_prefix, max_rows=ns.max_rows)
    if not questions:
        print(json.dumps({"ok": True, "injected": 0, "reason": "no_pending_questions"}))
        return 0

    rows, meta = build_inject_rows(
        questions,
        ctx,
        mode=ns.mode,
        billing=ns.billing,
        flash_model=ns.flash_model,
        timeout_sec=ns.timeout_sec,
        azure_deployment=(ns.azure_deployment or "").strip() or None,
    )

    ns.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with ns.output_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    apply_stats: dict[str, Any] = {}
    if not ns.skip_apply:
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(APPLY_SCRIPT),
                "--jsonl",
                str(ns.output_jsonl),
                "--registry",
                str(ns.registry),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode
        try:
            apply_stats = json.loads((proc.stdout or "").strip().splitlines()[-1])
        except json.JSONDecodeError:
            apply_stats = {"stdout": proc.stdout[-400:]}

    report = {
        "schema": "mkm_max_prophecy_4ai_forecast_inject_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "research_mode": "max_b_track",
        "registry": str(ns.registry.relative_to(ROOT)).replace("\\", "/"),
        "jsonl": str(ns.output_jsonl.relative_to(ROOT)).replace("\\", "/"),
        "question_id_prefix": ns.question_id_prefix,
        "inject_meta": meta,
        "apply_stats": apply_stats,
        "n_rows": len(rows),
    }
    ns.report.parent.mkdir(parents=True, exist_ok=True)
    ns.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "n_rows": len(rows), "report": str(ns.report), **apply_stats}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
