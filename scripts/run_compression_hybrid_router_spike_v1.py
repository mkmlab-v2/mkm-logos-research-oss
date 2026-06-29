#!/usr/bin/env python3
"""[HYPO] Hybrid compression router spike — corpus-level MKM vs LLMLingua-2 routing.

Derives routes from compression_sota_ablation_v1_latest.json; WTT uses economy short-cap
from wtt_cs_pilot_compression_ablation. Writes reports/compression_hybrid_router_spike_v1_latest.json.
research_only · SEND_GATE HOLD.
"""

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

from scripts.run_compression_sota_ablation_v1 import (  # noqa: E402
    CORPORA,
    _init_llmlingua,
    _load_corpus_rows,
    _mean,
    _run_llmlingua,
    _row_metrics,
)

DEFAULT_ABLATION = ROOT / "reports/compression_sota_ablation_v1_latest.json"
DEFAULT_WTT_ABLATION = ROOT / "reports/wtt_cs_pilot_compression_ablation_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/compression_hybrid_router_spike_v1_latest.json"
WTT_OVERLAY = ROOT / "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"

# Corpus overrides after ablation-derived policy (B-track tuning evidence).
CORPUS_ROUTE_OVERRIDES: dict[str, dict[str, Any]] = {
    "public_open_web_v1": {
        "backend": "mkm_candidate_pool",
        "routing_profile": "candidate_pool_on",
        "enable_candidate_pool_expansion": True,
        "reason": "41k grid best arm field pass 96.7% vs ACTIVE 90% (Tier A gate corpus)",
    },
    "wtt_premium_cs_customer_v1": {
        "backend": "mkm_economy_shortcap",
        "compression_profile": "economy",
        "short_context_token_threshold": 30,
        "short_context_max_saving_rate": 0.30,
        "must_keep_overlay_json": str(WTT_OVERLAY.relative_to(ROOT)).replace("\\", "/"),
        "reason": "wtt_cs_pilot best_arm economy_shortcap_30_030 (pass_rate leader)",
    },
}

TIER_A_GATE_CORPORA = frozenset({"public_open_web_v1", "wtt_premium_cs_customer_v1"})
TIER_A_EXCLUDE_CORPUS = "open_structured_long_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _derive_route(
    corpus_id: str,
    ablation: dict[str, Any],
    *,
    saving_delta_threshold: float,
    jaccard_guard: float,
) -> dict[str, Any]:
    if corpus_id in CORPUS_ROUTE_OVERRIDES:
        ov = CORPUS_ROUTE_OVERRIDES[corpus_id]
        return {
            "corpus_id": corpus_id,
            "backend": ov["backend"],
            "reason": ov["reason"],
            "override": True,
            **{k: v for k, v in ov.items() if k not in ("backend", "reason")},
        }
    for corp in ablation.get("corpora") or []:
        if corp.get("corpus_id") != corpus_id:
            continue
        mkm = (corp.get("mkm_economy") or {}).get("raw") or {}
        llm = (corp.get("llmlingua2") or {}).get("raw") or {}
        m_s = mkm.get("mean_token_saving_rate_proxy")
        l_s = llm.get("mean_token_saving_rate_proxy")
        m_j = mkm.get("mean_jaccard_proxy")
        l_j = llm.get("mean_jaccard_proxy")
        if not all(isinstance(x, (int, float)) for x in (m_s, l_s, m_j, l_j)):
            return {
                "corpus_id": corpus_id,
                "backend": "mkm_economy",
                "reason": "missing_ablation_metrics_default_mkm",
                "override": False,
            }
        d_save = float(m_s) - float(l_s)
        d_jac = float(m_j) - float(l_j)
        if d_jac >= jaccard_guard:
            return {
                "corpus_id": corpus_id,
                "backend": "mkm_economy",
                "reason": f"jaccard_guard delta={d_jac:.3f}>={jaccard_guard}",
                "override": False,
                "delta_mkm_minus_llmlingua_saving": d_save,
                "delta_mkm_minus_llmlingua_jaccard": d_jac,
            }
        if d_save <= -saving_delta_threshold:
            return {
                "corpus_id": corpus_id,
                "backend": "llmlingua2",
                "reason": f"saving_delta={d_save:.3f}<=-{saving_delta_threshold}",
                "override": False,
                "delta_mkm_minus_llmlingua_saving": d_save,
                "delta_mkm_minus_llmlingua_jaccard": d_jac,
            }
        return {
            "corpus_id": corpus_id,
            "backend": "mkm_economy",
            "reason": "default_mkm_no_strong_llm_saving_edge",
            "override": False,
            "delta_mkm_minus_llmlingua_saving": d_save,
            "delta_mkm_minus_llmlingua_jaccard": d_jac,
        }
    return {
        "corpus_id": corpus_id,
        "backend": "mkm_economy",
        "reason": "corpus_not_in_ablation_default_mkm",
        "override": False,
    }


def _load_overlay_terms(path: Path | None) -> list[str]:
    if not path or not path.is_file():
        return []
    from scripts.compression_b2b_must_keep_overlay_v1_lib import load_overlay_terms

    return load_overlay_terms(path)


def _run_mkm(
    rows: list[dict[str, str]],
    *,
    compression_profile: str = "economy",
    jaccard_floor: float = 0.73,
    overlay_terms: list[str] | None = None,
    short_threshold: int | None = None,
    short_max_saving: float | None = None,
    routing_profile: str = "track_a_promoted",
    enable_candidate_pool_expansion: bool = False,
) -> dict[str, Any]:
    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app

    client = TestClient(app)
    out_rows: list[dict[str, Any]] = []
    failures = 0
    for row in rows:
        text = row["text"]
        row_id = row["id"]
        body: dict[str, Any] = {
            "text": text,
            "loss_profile": "semantic_general",
            "compression_profile": compression_profile,
            "routing_profile": routing_profile,
            "enable_candidate_pool_expansion": enable_candidate_pool_expansion,
            "client_request_id": f"hybrid-mkm-{row_id}",
            "stateless_packet": True,
        }
        if overlay_terms:
            body["must_keep_overlay_terms"] = overlay_terms
        if short_threshold is not None:
            body["short_context_token_threshold"] = short_threshold
        if short_max_saving is not None:
            body["short_context_max_saving_rate"] = short_max_saving
        cr = client.post("/v2/compress", json=body)
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
    raw_savings = [float(r["token_saving_rate_proxy"]) for r in out_rows if "token_saving_rate_proxy" in r]
    raw_jaccards = [float(r["jaccard_proxy"]) for r in out_rows if "jaccard_proxy" in r]
    op_savings = [float(r["token_saving_rate_proxy"]) for r in out_rows if r.get("ok")]
    op_jaccards = [float(r["jaccard_proxy"]) for r in out_rows if r.get("ok")]
    return {
        "backend": "mkm_v2_stateless",
        "compression_profile": compression_profile,
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
        "row_samples": out_rows[:2],
    }


def _baseline_from_ablation(ablation: dict[str, Any]) -> dict[str, Any]:
    mkm_s: list[float] = []
    mkm_j: list[float] = []
    llm_s: list[float] = []
    llm_j: list[float] = []
    for corp in ablation.get("corpora") or []:
        mr = (corp.get("mkm_economy") or {}).get("raw") or {}
        lr = (corp.get("llmlingua2") or {}).get("raw") or {}
        if isinstance(mr.get("mean_token_saving_rate_proxy"), (int, float)):
            mkm_s.append(float(mr["mean_token_saving_rate_proxy"]))
        if isinstance(mr.get("mean_jaccard_proxy"), (int, float)):
            mkm_j.append(float(mr["mean_jaccard_proxy"]))
        if isinstance(lr.get("mean_token_saving_rate_proxy"), (int, float)):
            llm_s.append(float(lr["mean_token_saving_rate_proxy"]))
        if isinstance(lr.get("mean_jaccard_proxy"), (int, float)):
            llm_j.append(float(lr["mean_jaccard_proxy"]))
    return {
        "all_mkm_economy_from_ablation": {
            "mean_token_saving_rate_proxy": _mean(mkm_s),
            "mean_jaccard_proxy": _mean(mkm_j),
            "corpus_count": len(mkm_s),
            "artifact": str(DEFAULT_ABLATION.relative_to(ROOT)).replace("\\", "/"),
        },
        "all_llmlingua2_from_ablation": {
            "mean_token_saving_rate_proxy": _mean(llm_s),
            "mean_jaccard_proxy": _mean(llm_j),
            "corpus_count": len(llm_s),
            "artifact": str(DEFAULT_ABLATION.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Hybrid MKM/LLMLingua router spike [HYPO].")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--ablation-json", type=Path, default=DEFAULT_ABLATION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-cases", type=int, default=200)
    ap.add_argument("--jaccard-floor", type=float, default=0.73)
    ap.add_argument("--saving-delta-threshold", type=float, default=0.10)
    ap.add_argument("--jaccard-guard", type=float, default=0.20)
    ap.add_argument("--llmlingua-rate", type=float, default=0.5)
    ap.add_argument(
        "--llmlingua-model",
        default="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
    )
    ap.add_argument("--skip-llmlingua", action="store_true")
    args = ap.parse_args()

    workspace = args.workspace_root.resolve()
    ablation_path = args.ablation_json.resolve()
    if not ablation_path.is_file():
        print(f"error: missing ablation artifact: {ablation_path}", file=sys.stderr)
        return 2
    ablation = json.loads(ablation_path.read_text(encoding="utf-8"))

    routes = [
        _derive_route(
            spec["corpus_id"],
            ablation,
            saving_delta_threshold=args.saving_delta_threshold,
            jaccard_guard=args.jaccard_guard,
        )
        for spec in CORPORA
    ]

    compressor = None
    llm_init_error: str | None = None
    needs_llm = any(r["backend"] == "llmlingua2" for r in routes)
    if needs_llm and not args.skip_llmlingua:
        compressor, llm_init_error = _init_llmlingua(args.llmlingua_model, "cpu")
        if compressor is None:
            for r in routes:
                if r["backend"] == "llmlingua2":
                    r["backend"] = "mkm_economy"
                    r["fallback_reason"] = llm_init_error or "llmlingua_unavailable"

    corpus_results: list[dict[str, Any]] = []
    hybrid_savings: list[float] = []
    hybrid_jaccards: list[float] = []
    hybrid_op_savings: list[float] = []
    hybrid_op_jaccards: list[float] = []

    for spec, route in zip(CORPORA, routes):
        rows = _load_corpus_rows(spec, workspace, args.max_cases)
        backend = route["backend"]
        if backend == "llmlingua2":
            if compressor is None:
                result = {"status": "skipped", "reason": llm_init_error}
            else:
                result = _run_llmlingua(rows, compressor, args.llmlingua_rate)
        elif backend == "mkm_economy_shortcap":
            overlay_path = workspace / str(route.get("must_keep_overlay_json", ""))
            overlay_terms = _load_overlay_terms(overlay_path if overlay_path.is_file() else None)
            result = _run_mkm(
                rows,
                compression_profile=str(route.get("compression_profile", "economy")),
                jaccard_floor=args.jaccard_floor,
                overlay_terms=overlay_terms or None,
                short_threshold=int(route["short_context_token_threshold"]),
                short_max_saving=float(route["short_context_max_saving_rate"]),
                routing_profile=str(route.get("routing_profile", "track_a_promoted")),
                enable_candidate_pool_expansion=bool(route.get("enable_candidate_pool_expansion", False)),
            )
        elif backend == "mkm_candidate_pool":
            result = _run_mkm(
                rows,
                jaccard_floor=args.jaccard_floor,
                routing_profile=str(route.get("routing_profile", "candidate_pool_on")),
                enable_candidate_pool_expansion=bool(route.get("enable_candidate_pool_expansion", True)),
            )
        else:
            result = _run_mkm(rows, jaccard_floor=args.jaccard_floor)

        raw = result.get("raw") or {}
        op = result.get("operational_post_jaccard_floor") or {}
        if isinstance(raw.get("mean_token_saving_rate_proxy"), (int, float)):
            hybrid_savings.append(float(raw["mean_token_saving_rate_proxy"]))
        if isinstance(raw.get("mean_jaccard_proxy"), (int, float)):
            hybrid_jaccards.append(float(raw["mean_jaccard_proxy"]))
        if isinstance(op.get("mean_token_saving_rate_proxy"), (int, float)):
            hybrid_op_savings.append(float(op["mean_token_saving_rate_proxy"]))
        if isinstance(op.get("mean_jaccard_proxy"), (int, float)):
            hybrid_op_jaccards.append(float(op["mean_jaccard_proxy"]))

        corpus_results.append(
            {
                "corpus_id": spec["corpus_id"],
                "label": spec["label"],
                "row_count": len(rows),
                "route": route,
                "result": result,
            }
        )

    baselines = _baseline_from_ablation(ablation)
    tier_a_pass_rates: list[float] = []
    for cr in corpus_results:
        cid = cr.get("corpus_id")
        if cid not in TIER_A_GATE_CORPORA:
            continue
        op = ((cr.get("result") or {}).get("operational_post_jaccard_floor") or {})
        rows_ok = op.get("rows")
        total = (cr.get("result") or {}).get("rows")
        if isinstance(rows_ok, int) and isinstance(total, int) and total > 0:
            tier_a_pass_rates.append(rows_ok / total)
    hybrid_raw_s = _mean(hybrid_savings)
    hybrid_raw_j = _mean(hybrid_jaccards)
    all_mkm_s = baselines["all_mkm_economy_from_ablation"]["mean_token_saving_rate_proxy"]
    all_llm_s = baselines["all_llmlingua2_from_ablation"]["mean_token_saving_rate_proxy"]
    all_mkm_j = baselines["all_mkm_economy_from_ablation"]["mean_jaccard_proxy"]
    all_llm_j = baselines["all_llmlingua2_from_ablation"]["mean_jaccard_proxy"]

    doc: dict[str, Any] = {
        "schema": "compression_hybrid_router_spike_v1",
        "generated_at_utc": _utc(),
        "labels": ["HYPO", "research_only", "B-track"],
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "boundary_ack": (
            "Corpus-level router spike from SOTA ablation; not production SKU or Track A promotion."
        ),
        "source_artifacts": {
            "sota_ablation": str(ablation_path.relative_to(workspace)).replace("\\", "/"),
            "wtt_ablation": str(DEFAULT_WTT_ABLATION.relative_to(ROOT)).replace("\\", "/"),
        },
        "routing_policy": {
            "saving_delta_threshold": args.saving_delta_threshold,
            "jaccard_guard": args.jaccard_guard,
            "corpus_overrides": list(CORPUS_ROUTE_OVERRIDES.keys()),
            "tier_a_gate_corpora": sorted(TIER_A_GATE_CORPORA),
            "tier_a_exclude_corpus": TIER_A_EXCLUDE_CORPUS,
            "routes": routes,
        },
        "tier_a_gate": {
            "corpus_ids": sorted(TIER_A_GATE_CORPORA),
            "excluded_artifact_corpus": TIER_A_EXCLUDE_CORPUS,
            "mean_operational_pass_rate": _mean(tier_a_pass_rates),
            "jaccard_floor": args.jaccard_floor,
        },
        "corpora": corpus_results,
        "comparison": {
            "baselines_from_ablation": baselines,
            "hybrid_routed": {
                "raw": {
                    "mean_token_saving_rate_proxy": hybrid_raw_s,
                    "mean_jaccard_proxy": hybrid_raw_j,
                    "corpus_count": len(hybrid_savings),
                },
                "operational_post_jaccard_floor": {
                    "mean_token_saving_rate_proxy": _mean(hybrid_op_savings),
                    "mean_jaccard_proxy": _mean(hybrid_op_jaccards),
                    "corpus_count": len(hybrid_op_savings),
                },
            },
            "delta_hybrid_minus_all_mkm_raw_saving": (
                hybrid_raw_s - all_mkm_s
                if isinstance(hybrid_raw_s, (int, float)) and isinstance(all_mkm_s, (int, float))
                else None
            ),
            "delta_hybrid_minus_all_llm_raw_saving": (
                hybrid_raw_s - all_llm_s
                if isinstance(hybrid_raw_s, (int, float)) and isinstance(all_llm_s, (int, float))
                else None
            ),
            "delta_hybrid_minus_all_mkm_raw_jaccard": (
                hybrid_raw_j - all_mkm_j
                if isinstance(hybrid_raw_j, (int, float)) and isinstance(all_mkm_j, (int, float))
                else None
            ),
        },
        "sku_note": (
            "Hybrid beats all-MKM on saving when LLMLingua corpora included; "
            "beats all-LLMLingua on Jaccard when MKM fidelity corpora dominate."
        ),
    }

    out_path = args.out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "hybrid_raw_saving": hybrid_raw_s,
                "hybrid_raw_jaccard": hybrid_raw_j,
                "routes": {r["corpus_id"]: r["backend"] for r in routes},
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
