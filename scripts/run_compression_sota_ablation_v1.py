#!/usr/bin/env python3
"""[HYPO] B-track SOTA ablation — MKM economy (V2 stateless) vs LLMLingua-2 on fixed corpora.

Writes reports/compression_sota_ablation_v1_latest.json. research_only; SEND_GATE HOLD.
Does not claim Track A ACTIVE 47% or customer SLA.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TOKEN_RE = re.compile(r"\S+")
DEFAULT_OUT = ROOT / "reports/compression_sota_ablation_v1_latest.json"
GOLDEN40_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_REPORT = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"

CORPORA: list[dict[str, Any]] = [
    {
        "corpus_id": "golden40_internal",
        "label": "Golden-40 internal eval input (40 cases)",
        "source_type": "eval_json",
        "path": str(GOLDEN40_INPUT.relative_to(ROOT)).replace("\\", "/"),
        "frozen_active_pointer": str(ACTIVE_REPORT.relative_to(ROOT)).replace("\\", "/"),
        "forbidden_as_customer_sla": True,
    },
    {
        "corpus_id": "public_open_web_v1",
        "label": "public-open-web-v1 masked open bench",
        "source_type": "jsonl",
        "path": "data/compression/stateless_poc_prospect_public-open-web-v1_v1.jsonl",
    },
    {
        "corpus_id": "wtt_premium_cs_customer_v1",
        "label": "wtt-premium-cs-customer-v1 masked CS pilot",
        "source_type": "jsonl",
        "path": "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl",
    },
    {
        "corpus_id": "open_structured_long_v1",
        "label": "open_structured_long internal long-context proxy",
        "source_type": "jsonl",
        "path": "data/compression/stateless_poc_open_structured_long_v1.jsonl",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token_proxy(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _load_corpus_rows(spec: dict[str, Any], workspace: Path, max_cases: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rel = spec["path"]
    path = (workspace / rel).resolve()
    if spec["source_type"] == "eval_json":
        doc = json.loads(path.read_text(encoding="utf-8"))
        for case in doc.get("compression_cases") or []:
            if not isinstance(case, dict):
                continue
            raw = case.get("raw_text")
            if not isinstance(raw, str) or not raw.strip():
                continue
            rows.append({"id": str(case.get("id") or f"case_{len(rows)}"), "text": raw})
            if len(rows) >= max_cases:
                break
        return rows

    if not path.is_file():
        raise FileNotFoundError(path)
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        if not line.strip() or len(rows) >= max_cases:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        text = None
        for key in ("text", "raw_text", "content", "body"):
            v = obj.get(key)
            if isinstance(v, str) and v.strip():
                text = v
                break
        if not text:
            continue
        rows.append({"id": str(obj.get("id") or f"row_{i}"), "text": text})
    return rows


def _row_metrics(text: str, compressed: str, expanded: str) -> dict[str, float]:
    tin = _token_proxy(text)
    tout = _token_proxy(compressed)
    saving = max(0.0, 1.0 - (tout / tin)) if tin > 0 else 0.0
    from scripts.report_multilens_performance_eval import _jaccard

    return {
        "token_in_proxy": float(tin),
        "token_out_proxy": float(tout),
        "token_saving_rate_proxy": saving,
        "jaccard_proxy": float(_jaccard(text, expanded)),
    }


def _run_mkm_economy(
    rows: list[dict[str, str]],
    jaccard_floor: float,
    *,
    routing_profile: str = "track_a_promoted",
    enable_candidate_pool_expansion: bool = False,
    client_request_id_prefix: str = "sota-mkm",
) -> dict[str, Any]:
    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    client = TestClient(app)
    out_rows: list[dict[str, Any]] = []
    failures = 0
    for row in rows:
        text = row["text"]
        row_id = row["id"]
        cr = client.post(
            "/v2/compress",
            json={
                "text": text,
                "loss_profile": "semantic_general",
                "compression_profile": "economy",
                "routing_profile": routing_profile,
                "enable_candidate_pool_expansion": enable_candidate_pool_expansion,
                "client_request_id": f"{client_request_id_prefix}-{row_id}",
                "stateless_packet": True,
            },
        )
        if cr.status_code != 200:
            failures += 1
            out_rows.append({"id": row_id, "ok": False, "error": cr.text[:200]})
            continue
        pkt = cr.json().get("compression_packet") or {}
        stub = (pkt.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
        if "reconstructed_text" in stub:
            failures += 1
            out_rows.append({"id": row_id, "ok": False, "error": "stateless_leak"})
            continue
        er = client.post(
            "/v2/expand",
            json={"compression_packet": pkt, "decode_mode": "codebook_only"},
        )
        if er.status_code != 200:
            failures += 1
            out_rows.append({"id": row_id, "ok": False, "error": er.text[:200]})
            continue
        expanded = er.json().get("text") or ""
        metrics = _row_metrics(text, str(pkt.get("compressed_text") or ""), expanded)
        ok = metrics["jaccard_proxy"] >= jaccard_floor
        if not ok:
            failures += 1
        out_rows.append({"id": row_id, "ok": ok, **metrics})
    raw_savings = [
        float(r["token_saving_rate_proxy"]) for r in out_rows if "token_saving_rate_proxy" in r
    ]
    raw_jaccards = [float(r["jaccard_proxy"]) for r in out_rows if "jaccard_proxy" in r]
    op_savings = [float(r["token_saving_rate_proxy"]) for r in out_rows if r.get("ok")]
    op_jaccards = [float(r["jaccard_proxy"]) for r in out_rows if r.get("ok")]
    return {
        "algorithm": "mkm_v2_economy_stateless",
        "family": "mkm_codebook_router",
        "compression_profile": "economy",
        "routing_profile": routing_profile,
        "enable_candidate_pool_expansion": enable_candidate_pool_expansion,
        "rows": len(out_rows),
        "rows_ok": sum(1 for r in out_rows if r.get("ok")),
        "failures": failures,
        "raw": {
            "mean_token_saving_rate_proxy": _mean(raw_savings),
            "mean_jaccard_proxy": _mean(raw_jaccards),
            "rows": len(raw_savings),
        },
        "operational_post_jaccard_floor": {
            "mean_token_saving_rate_proxy": _mean(op_savings),
            "mean_jaccard_proxy": _mean(op_jaccards),
            "rows": len(op_savings),
            "jaccard_floor": jaccard_floor,
        },
        "mean_token_saving_rate_proxy": _mean(op_savings),
        "mean_jaccard_proxy": _mean(op_jaccards),
        "row_samples": out_rows[:3],
    }


def _init_llmlingua(model_name: str, device_map: str) -> tuple[Any | None, str | None]:
    import os

    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
    try:
        from llmlingua import PromptCompressor
    except ImportError as exc:
        return None, f"llmlingua_import_error:{exc}"
    try:
        import torch

        compressor = PromptCompressor(
            model_name=model_name,
            device_map=device_map,
            use_llmlingua2=True,
            model_config={"torch_dtype": torch.float32},
        )
        return compressor, None
    except TypeError:
        try:
            compressor = PromptCompressor(
                model_name=model_name,
                device_map=device_map,
                use_llmlingua2=True,
            )
            return compressor, None
        except Exception as exc:  # noqa: BLE001
            return None, f"llmlingua_init_error:{type(exc).__name__}:{exc}"
    except Exception as exc:  # noqa: BLE001
        return None, f"llmlingua_init_error:{type(exc).__name__}:{exc}"


def _run_llmlingua(
    rows: list[dict[str, str]],
    compressor: Any,
    rate: float,
) -> dict[str, Any]:
    out_rows: list[dict[str, Any]] = []
    failures = 0
    for row in rows:
        text = row["text"]
        row_id = row["id"]
        try:
            result = compressor.compress_prompt(text, rate=rate)
            compressed = ""
            if isinstance(result, dict):
                compressed = str(result.get("compressed_prompt") or result.get("compressed_context") or "")
            elif isinstance(result, str):
                compressed = result
            if not compressed.strip():
                failures += 1
                out_rows.append({"id": row_id, "ok": False, "error": "empty_compressed"})
                continue
            llm_saving = result.get("saving") if isinstance(result, dict) else None
            llm_ratio = result.get("ratio") if isinstance(result, dict) else None
        except Exception as exc:  # noqa: BLE001
            failures += 1
            out_rows.append({"id": row_id, "ok": False, "error": f"{type(exc).__name__}:{exc}"[:200]})
            continue
        metrics = _row_metrics(text, compressed, compressed)
        if isinstance(llm_saving, (int, float)):
            metrics["llmlingua_reported_saving"] = float(llm_saving)
        if isinstance(llm_ratio, (int, float)):
            metrics["llmlingua_reported_ratio"] = float(llm_ratio)
        out_rows.append({"id": row_id, "ok": True, **metrics})
    savings = [float(r["token_saving_rate_proxy"]) for r in out_rows if r.get("ok")]
    jaccards = [float(r["jaccard_proxy"]) for r in out_rows if r.get("ok")]
    return {
        "algorithm": "llmlingua2",
        "family": "llm_external_sota",
        "target_rate": rate,
        "rows": len(out_rows),
        "rows_ok": sum(1 for r in out_rows if r.get("ok")),
        "failures": failures,
        "raw": {
            "mean_token_saving_rate_proxy": _mean(savings),
            "mean_jaccard_proxy": _mean(jaccards),
            "rows": len(savings),
        },
        "mean_token_saving_rate_proxy": _mean(savings),
        "mean_jaccard_proxy": _mean(jaccards),
        "row_samples": out_rows[:3],
    }


def _compare_corpus(mkm: dict[str, Any], llm: dict[str, Any] | None) -> dict[str, Any]:
    m_s = (mkm.get("raw") or {}).get("mean_token_saving_rate_proxy", mkm.get("mean_token_saving_rate_proxy"))
    l_s = (llm or {}).get("mean_token_saving_rate_proxy")
    m_j = mkm.get("mean_jaccard_proxy")
    l_j = (llm or {}).get("mean_jaccard_proxy")
    delta_saving = None
    winner_saving = None
    if isinstance(m_s, (int, float)) and isinstance(l_s, (int, float)):
        delta_saving = float(m_s) - float(l_s)
        if abs(delta_saving) < 0.01:
            winner_saving = "tie"
        elif delta_saving > 0:
            winner_saving = "mkm"
        else:
            winner_saving = "llmlingua2"
    delta_jaccard = None
    if isinstance(m_j, (int, float)) and isinstance(l_j, (int, float)):
        delta_jaccard = float(m_j) - float(l_j)
    return {
        "delta_mkm_minus_llmlingua_saving_rate": delta_saving,
        "delta_mkm_minus_llmlingua_jaccard": delta_jaccard,
        "winner_token_saving_rate": winner_saving,
    }


def _sku_recommendation(corpus_results: list[dict[str, Any]]) -> dict[str, Any]:
    llm_wins = 0
    mkm_wins = 0
    ties = 0
    comparable = 0
    for item in corpus_results:
        cmp = item.get("comparison") or {}
        w = cmp.get("winner_token_saving_rate")
        if w == "llmlingua2":
            llm_wins += 1
            comparable += 1
        elif w == "mkm":
            mkm_wins += 1
            comparable += 1
        elif w == "tie":
            ties += 1
            comparable += 1
    if comparable == 0:
        decision = "control_plane_only"
        reason = "LLMLingua unavailable or no comparable corpora."
    elif llm_wins >= 3:
        decision = "hybrid_sku"
        reason = f"LLMLingua-2 wins saving-rate on {llm_wins}/{comparable} corpora — hybrid routing worth spike."
    elif mkm_wins >= 3:
        decision = "control_plane_primary"
        reason = f"MKM economy wins saving-rate on {mkm_wins}/{comparable} corpora — sell control plane, not raw codec."
    else:
        decision = "hybrid_sku"
        reason = f"Mixed split (mkm={mkm_wins}, llm={llm_wins}, tie={ties}) — hybrid SKU with corpus router."
    return {
        "decision": decision,
        "reason": reason,
        "mkm_wins_saving_rate": mkm_wins,
        "llmlingua_wins_saving_rate": llm_wins,
        "ties_saving_rate": ties,
        "comparable_corpora": comparable,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="MKM economy vs LLMLingua-2 SOTA ablation [HYPO].")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cases", type=int, default=200)
    ap.add_argument("--jaccard-floor", type=float, default=0.73)
    ap.add_argument("--llmlingua-rate", type=float, default=0.5, help="Target keep ratio for LLMLingua-2.")
    ap.add_argument(
        "--llmlingua-model",
        default="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    )
    ap.add_argument("--llmlingua-device", default="cpu")
    ap.add_argument("--skip-llmlingua", action="store_true")
    ap.add_argument("--corpus-id", action="append", default=[], help="Subset corpus ids (default: all 4).")
    ap.add_argument(
        "--include-candidate-pool-arm",
        action="store_true",
        help="Also run mkm_candidate_pool (routing_profile=candidate_pool_on) per corpus.",
    )
    args = ap.parse_args()

    workspace = args.workspace_root.resolve()
    selected = [c for c in CORPORA if not args.corpus_id or c["corpus_id"] in args.corpus_id]
    if not selected:
        print("error: no corpora matched --corpus-id", file=sys.stderr)
        return 2

    compressor = None
    llm_init_error: str | None = None
    if not args.skip_llmlingua:
        compressor, llm_init_error = _init_llmlingua(args.llmlingua_model, args.llmlingua_device)

    corpus_results: list[dict[str, Any]] = []
    failures = 0
    for spec in selected:
        try:
            rows = _load_corpus_rows(spec, workspace, args.max_cases)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        if not rows:
            failures += 1
            corpus_results.append(
                {
                    "corpus_id": spec["corpus_id"],
                    "label": spec["label"],
                    "path": spec["path"],
                    "error": "empty_corpus",
                }
            )
            continue
        mkm = _run_mkm_economy(rows, args.jaccard_floor)
        pool: dict[str, Any] | None = None
        if args.include_candidate_pool_arm:
            pool = _run_mkm_economy(
                rows,
                args.jaccard_floor,
                routing_profile="candidate_pool_on",
                enable_candidate_pool_expansion=True,
                client_request_id_prefix="sota-pool",
            )
        llm: dict[str, Any] | None = None
        if compressor is not None:
            llm = _run_llmlingua(rows, compressor, args.llmlingua_rate)
        elif not args.skip_llmlingua:
            llm = {
                "algorithm": "llmlingua2",
                "status": "skipped",
                "reason": llm_init_error or "llmlingua_not_available",
            }
        cmp = _compare_corpus(mkm, llm if llm and llm.get("status") != "skipped" else None)
        corpus_results.append(
            {
                "corpus_id": spec["corpus_id"],
                "label": spec["label"],
                "path": spec["path"],
                "row_count": len(rows),
                "mkm_economy": mkm,
                "mkm_candidate_pool": pool,
                "llmlingua2": llm,
                "comparison": cmp,
            }
        )

    recommendation = _sku_recommendation(corpus_results)
    doc: dict[str, Any] = {
        "schema": "compression_sota_ablation_v1",
        "generated_at_utc": _utc(),
        "labels": ["HYPO", "research_only", "B-track"],
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "boundary_ack": (
            "Exploratory apples-to-oranges ablation: MKM uses codebook round-trip Jaccard; "
            "LLMLingua uses prompt retention Jaccard. Not Track A ACTIVE 47% or customer SLA."
        ),
        "config": {
            "mkm": {"compression_profile": "economy", "loss_profile": "semantic_general", "stateless_packet": True},
            "llmlingua2": {
                "model": args.llmlingua_model,
                "target_rate": args.llmlingua_rate,
                "device": args.llmlingua_device,
                "skipped": args.skip_llmlingua or compressor is None,
                "init_error": llm_init_error,
            },
            "max_cases": args.max_cases,
            "jaccard_floor": args.jaccard_floor,
        },
        "corpora": corpus_results,
        "sku_recommendation": recommendation,
        "aggregate": {
            "corpus_count": len(corpus_results),
            "mkm_raw_mean_saving_across_corpora": _mean(
                [
                    float((c.get("mkm_economy") or {}).get("raw", {}).get("mean_token_saving_rate_proxy"))
                    for c in corpus_results
                    if isinstance(
                        (c.get("mkm_economy") or {}).get("raw", {}).get("mean_token_saving_rate_proxy"),
                        (int, float),
                    )
                ]
            ),
            "llmlingua_mean_saving_across_corpora": _mean(
                [
                    float(c["llmlingua2"]["mean_token_saving_rate_proxy"])
                    for c in corpus_results
                    if isinstance((c.get("llmlingua2") or {}).get("mean_token_saving_rate_proxy"), (int, float))
                ]
            ),
        },
        "notes": [
            "golden40_internal uses MULTILENS_PERFORMANCE_EVAL_INPUT_V2 raw_text — frozen ACTIVE 47% is separate artifact.",
            "FAIL-COMP-004: do not merge corpus KPIs into Track A headline.",
        ],
    }

    out_path = args.out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "sku_decision": recommendation["decision"]}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
