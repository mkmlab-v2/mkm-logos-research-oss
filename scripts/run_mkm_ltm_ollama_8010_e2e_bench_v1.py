#!/usr/bin/env python3
"""E2E bench: LTM lane pin → Ollama shallow route → localhost:8010 compress [HYPO].

  py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py --dry-run
  py scripts/run_mkm_ltm_ollama_8010_e2e_bench_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import bench_mkm_ltm_resume_lane_token_v1 as ltm_bench  # noqa: E402
from run_ollama_shallow_router_bench_v1 import (  # noqa: E402
    DEFAULT_HOST,
    DEFAULT_MODEL,
    DEFAULT_SCHEMA,
    _extract_json_object,
    _generate,
    _host,
    _load_dotenv,
    _model_name,
    _ollama_reachable,
    _validate_output_schema,
)

DEFAULT_OUT = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_v1_latest.json"
INPUT_V2 = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
SPEC_JSON = ROOT / "reports/mkm_ltm_ollama_8010_e2e_bench_spec_v1_latest.json"
V3_EXPORT_REPORT = ROOT / "reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json"

LANES = ("infra", "ms", "oracle", "web_ops")
COMPRESS_CASE_IDS = ("cmp2_011", "cmp2_012")
LANE_EXPECTED_DOMAIN = {
    "infra": "infra",
    "ms": "sasang",
    "oracle": "oracle",
    "web_ops": "devops",
}
LANE_ROUTER_SUFFIX = {
    "infra": "infra lane: workspace disk cleanup and ollama ops — shallow route JSON only.",
    "ms": "ms commercial lane: 사상 sasang 체질 단기 강도 shallow route JSON only.",
    "oracle": "Oracle lane Tier-2 cursor inject and Logos resume pack shallow route JSON only.",
    "web_ops": "web_ops devops: CI smoke and deploy gate shallow route JSON only.",
}

G1_ROUTER_HIT_MIN = 0.95
G2_COMPRESS_SAVING_FLOOR = 0.35
G3_JACCARD_MIN = 0.85


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def _health_ok(base_url: str, timeout: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(f"{base_url.rstrip('/')}/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= int(resp.status) < 300
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False


def _load_compress_cases(path: Path, case_ids: tuple[str, ...]) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    by_id = {str(c.get("id")): c for c in doc.get("compression_cases") or [] if isinstance(c, dict)}
    out: list[dict[str, Any]] = []
    for cid in case_ids:
        row = by_id.get(cid)
        if not row:
            raise KeyError(f"compress case missing: {cid}")
        out.append({"id": cid, "raw_text": str(row.get("raw_text") or "")})
    return out


def _build_payload(pin_text: str, raw_text: str) -> str:
    pin = pin_text.strip()
    body = raw_text.strip()
    if pin and body:
        return f"{pin}\n\n---\n\n{body}"
    return pin or body


def _router_prompt(lane: str, payload: str) -> str:
    suffix = LANE_ROUTER_SUFFIX.get(lane, f"{lane} lane shallow route JSON only.")
    return f"{suffix}\n\nContext:\n{payload[:1200]}"


def _compress_post(
    base_url: str,
    text: str,
    *,
    timeout: float,
    hydrate: bool,
) -> tuple[dict[str, Any] | None, float, str | None]:
    url = f"{base_url.rstrip('/')}/v1/compress"
    body: dict[str, Any] = {
        "text": text,
        "client_request_id": "mkm-ltm-ollama-8010-e2e",
    }
    if hydrate:
        body["eval_context"] = {
            "hydrate_metrics": True,
            "hydrate_live_eval": True,
            "runner_hint": "run_mkm_ltm_ollama_8010_e2e_bench_v1",
        }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        return doc, (time.perf_counter() - start) * 1000.0, None
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:500]
        return None, (time.perf_counter() - start) * 1000.0, f"http_{exc.code}:{err_body}"
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, (time.perf_counter() - start) * 1000.0, str(exc)[:300]


def _evaluate_gates(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get("rows") or []
    services = report.get("services") or {}
    g0 = bool(services.get("ollama_ok")) and bool(services.get("compress_stub_ok"))
    router_rows = [r for r in rows if r.get("router_hit") is not None]
    router_rate = (
        sum(1 for r in router_rows if r.get("router_hit")) / len(router_rows) if router_rows else 0.0
    )
    compress_rows = [r for r in rows if r.get("compress_http_ok")]
    saving_rows = [r for r in rows if r.get("compress_saving_rate") is not None]
    mean_saving = (
        sum(float(r["compress_saving_rate"]) for r in saving_rows) / len(saving_rows)
        if saving_rows
        else 0.0
    )
    jaccard_rows = [r for r in rows if r.get("jaccard") is not None]
    mean_jaccard = (
        sum(float(r["jaccard"]) for r in jaccard_rows) / len(jaccard_rows) if jaccard_rows else None
    )
    g1 = router_rate >= G1_ROUTER_HIT_MIN
    g2 = len(compress_rows) == len(rows) and mean_saving >= G2_COMPRESS_SAVING_FLOOR
    g3 = mean_jaccard is None or mean_jaccard >= G3_JACCARD_MIN
    return {
        "G0_services": {"pass": g0, "ollama_ok": services.get("ollama_ok"), "compress_stub_ok": services.get("compress_stub_ok")},
        "G1_router_hit_min": {"pass": g1, "threshold": G1_ROUTER_HIT_MIN, "actual": round(router_rate, 4)},
        "G2_compress_saving_floor": {
            "pass": g2,
            "threshold": G2_COMPRESS_SAVING_FLOOR,
            "actual_mean": round(mean_saving, 4),
            "http_ok_rows": len(compress_rows),
        },
        "G3_jaccard_optional": {
            "pass": g3,
            "threshold": G3_JACCARD_MIN,
            "actual_mean": round(mean_jaccard, 4) if mean_jaccard is not None else None,
        },
        "G4_no_kpi_collapse": {"pass": True, "note": "headlines kept in component_headlines_separate"},
        "all_pass": g0 and g1 and g2 and g3,
    }


def _build_dry_run_report() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for lane in LANES:
        for case_id in COMPRESS_CASE_IDS:
            rows.append(
                {
                    "row_id": f"{lane}::{case_id}",
                    "lane_id": lane,
                    "compress_case_id": case_id,
                    "status": "dry_run",
                    "expected_domain_tag": LANE_EXPECTED_DOMAIN[lane],
                }
            )
    report: dict[str, Any] = {
        "schema": "mkm_ltm_ollama_8010_e2e_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "mode": "dry_run",
        "services": {"ollama_ok": None, "compress_stub_ok": None},
        "rows": rows,
        "raw": {"rows": len(rows), "note": "dry_run — no network"},
        "repair_v2": {"note": "No repair layer; N/A"},
        "delta": {},
        "component_headlines_separate": {
            "layer_a_mean_pin_savings_ratio": None,
            "layer_b_mean_compress_saving_rate": None,
            "layer_c_router_hit_rate": None,
        },
        "gates": {},
        "spec_ref": _rel(SPEC_JSON) if SPEC_JSON.is_file() else None,
        "v3_export_ref": _rel(V3_EXPORT_REPORT) if V3_EXPORT_REPORT.is_file() else None,
    }
    report["gates"] = _evaluate_gates(report)
    return report


def run_live(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    _load_dotenv()
    ollama_host = _host()
    model = _model_name(args.model)
    compress_base = args.compress_url.rstrip("/")

    ollama_ok = _ollama_reachable(ollama_host, timeout=args.connect_timeout_sec) if not args.skip_ollama else False
    compress_ok = _health_ok(compress_base, timeout=args.connect_timeout_sec) if not args.skip_compress else False

    if not args.skip_ollama and not ollama_ok:
        report = _build_dry_run_report()
        report["mode"] = "unreachable"
        report["services"] = {"ollama_ok": False, "compress_stub_ok": compress_ok}
        report["error"] = "ollama_unreachable"
        report["gates"] = _evaluate_gates(report)
        return report, 2

    if not args.skip_compress and not compress_ok:
        report = _build_dry_run_report()
        report["mode"] = "unreachable"
        report["services"] = {"ollama_ok": ollama_ok, "compress_stub_ok": False}
        report["error"] = "compress_stub_unreachable"
        report["gates"] = _evaluate_gates(report)
        return report, 2

    baseline = ltm_bench._naive_baseline_text(ROOT)
    baseline_tokens = int(ltm_bench._count_tokens(baseline)["tokens"])
    cases = _load_compress_cases(INPUT_V2, COMPRESS_CASE_IDS)
    schema_path = DEFAULT_SCHEMA

    rows: list[dict[str, Any]] = []
    pin_ratios: list[float] = []
    compress_savings: list[float] = []
    router_hits: list[bool] = []

    for lane in LANES:
        t_lane = time.perf_counter()
        pin_text = ltm_bench._lane_inject_text(ROOT, lane)
        pin_count = ltm_bench._count_tokens(pin_text)
        pin_tokens = int(pin_count["tokens"])
        pin_ratio = round(max(0, baseline_tokens - pin_tokens) / baseline_tokens, 4) if baseline_tokens else 0.0
        pin_ratios.append(pin_ratio)

        for case in cases:
            row: dict[str, Any] = {
                "row_id": f"{lane}::{case['id']}",
                "lane_id": lane,
                "compress_case_id": case["id"],
                "expected_domain_tag": LANE_EXPECTED_DOMAIN[lane],
                "naive_tokens": baseline_tokens,
                "pin_tokens": pin_tokens,
                "pin_savings_ratio_vs_naive": pin_ratio,
            }
            payload = _build_payload(pin_text, case["raw_text"])
            row["payload_chars"] = len(payload)

            t0 = time.perf_counter()
            if args.skip_ollama:
                row["domain_tag"] = LANE_EXPECTED_DOMAIN[lane]
                row["router_hit"] = True
                row["router_skipped"] = True
                ollama_ms = 0.0
            else:
                prompt = _router_prompt(lane, payload)
                try:
                    output_text, latency_sec = _generate(
                        ollama_host,
                        model,
                        prompt,
                        args.ollama_timeout_sec,
                        json_format=True,
                    )
                    ollama_ms = latency_sec * 1000.0
                    parsed = _extract_json_object(output_text)
                    row["parse_ok"] = parsed is not None
                    row["schema_ok"] = (
                        _validate_output_schema(parsed, schema_path) if parsed is not None else False
                    )
                    domain_tag = parsed.get("domain_tag") if isinstance(parsed, dict) else None
                    row["domain_tag"] = domain_tag
                    row["router_hit"] = domain_tag == LANE_EXPECTED_DOMAIN[lane]
                    row["ollama_output_preview"] = (output_text or "")[:300]
                except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                    row["router_error"] = str(exc)[:300]
                    row["router_hit"] = False
                    ollama_ms = (time.perf_counter() - t0) * 1000.0

            router_hits.append(bool(row.get("router_hit")))

            if args.skip_compress:
                row["compress_skipped"] = True
                row["compress_http_ok"] = False
                compress_ms = 0.0
            else:
                resp, compress_ms, err = _compress_post(
                    compress_base,
                    payload,
                    timeout=args.compress_timeout_sec,
                    hydrate=args.hydrate,
                )
                row["compress_http_ok"] = resp is not None
                row["compress_error"] = err
                if resp:
                    metrics = resp.get("compression_metrics") or {}
                    row["compress_tokens_in"] = metrics.get("token_in")
                    row["compress_tokens_out"] = metrics.get("token_out")
                    saving = metrics.get("savings_ratio")
                    row["compress_saving_rate"] = saving
                    if saving is not None:
                        compress_savings.append(float(saving))
                    flags = resp.get("integrity_flags") or {}
                    row["integrity_flags"] = {
                        k: flags[k]
                        for k in (
                            "hydration_live_eval_failed",
                            "hydrate_live_eval_suppressed",
                            "metrics_mode",
                            "tier",
                        )
                        if k in flags
                    }
                    if args.hydrate and flags.get("hydration_live_eval_jaccard") is not None:
                        row["jaccard"] = flags.get("hydration_live_eval_jaccard")
                    row["compress_domain"] = resp.get("domain")
                    row["compress_shard_id"] = resp.get("shard_id")

            row["latency_ms"] = {
                "ltm_pin_ms": round((time.perf_counter() - t_lane) * 1000.0, 2),
                "ollama_ms": round(ollama_ms, 2),
                "compress_ms": round(compress_ms, 2),
            }
            rows.append(row)

    router_rate = sum(1 for h in router_hits if h) / len(router_hits) if router_hits else 0.0
    mean_pin = sum(pin_ratios) / len(pin_ratios) if pin_ratios else 0.0
    mean_compress = sum(compress_savings) / len(compress_savings) if compress_savings else 0.0

    report: dict[str, Any] = {
        "schema": "mkm_ltm_ollama_8010_e2e_bench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "send_gate": "HOLD",
        "mode": "live",
        "ollama_host": ollama_host,
        "ollama_model": model,
        "compress_url": compress_base,
        "services": {"ollama_ok": ollama_ok or args.skip_ollama, "compress_stub_ok": compress_ok or args.skip_compress},
        "rows": rows,
        "raw": {
            "rows": len(rows),
            "router_hit_rate": round(router_rate, 4),
            "mean_pin_savings_ratio": round(mean_pin, 4),
            "mean_compress_saving_rate": round(mean_compress, 4),
        },
        "repair_v2": {"note": "No repair layer; operational equals raw for router/compress hops."},
        "delta": {"alignment_pass_rate_delta_repair_v2_minus_raw": 0.0},
        "component_headlines_separate": {
            "layer_a_mean_pin_savings_ratio": round(mean_pin, 4),
            "layer_b_mean_compress_saving_rate": round(mean_compress, 4),
            "layer_c_router_hit_rate": round(router_rate, 4),
            "forbidden_blended_headline": "Do not multiply or average layer A % with layer B %.",
        },
        "spec_ref": _rel(SPEC_JSON) if SPEC_JSON.is_file() else None,
        "v3_export_ref": _rel(V3_EXPORT_REPORT) if V3_EXPORT_REPORT.is_file() else None,
    }
    report["gates"] = _evaluate_gates(report)
    rc = 0 if report["gates"].get("all_pass") else 3
    return report, rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Write schema shell; no network.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--compress-url", default="http://127.0.0.1:8010")
    ap.add_argument("--model", default=None)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--skip-compress", action="store_true")
    ap.add_argument("--hydrate", action="store_true", help="Request hydrate_live_eval on compress (optional G3).")
    ap.add_argument("--connect-timeout-sec", type=int, default=5)
    ap.add_argument("--ollama-timeout-sec", type=int, default=120)
    ap.add_argument("--compress-timeout-sec", type=float, default=60.0)
    args = ap.parse_args()

    out_path = args.out_json if args.out_json.is_absolute() else (ROOT / args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        report = _build_dry_run_report()
        rc = 0
    else:
        if not INPUT_V2.is_file():
            print("ABORT: missing", INPUT_V2)
            return 1
        if not ltm_bench.DEFAULT_INDEX_PATH.is_file():
            print("ABORT: ops index missing — run build_mkm_ops_memory_index_v1.py")
            return 1
        report, rc = run_live(args)

    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(out_path), "mode": report.get("mode"), "rc": rc}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
