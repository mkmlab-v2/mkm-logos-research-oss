#!/usr/bin/env python3
"""Customer corpus PoC: V2 Trust Packet Stateless Profile (stateless_packet + codebook_only).

Reads JSONL rows with `text` or `raw_text`; reports per-row and aggregate token/Jaccard proxies.
Does not claim global 47.5% — customer-specific ROI only. [research_only] for external send.
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
DEFAULT_OUT = ROOT / "reports/customer_compression_stateless_poc_v1_latest.json"
DEFAULT_SKU_SPEC = ROOT / "docs/final/artifacts/compression_b2b_off_the_shelf_shard_sku_v1.json"
V2_JACCARD_FLOOR = 0.73


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token_proxy(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def _row_text(obj: dict[str, Any]) -> str | None:
    for key in ("text", "raw_text", "content", "body"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _resolve_sku_context(
    *,
    workspace_root: Path,
    external_sku: str | None,
    sku_spec_json: Path | None,
) -> dict[str, Any]:
    if not external_sku:
        return {}
    from scripts.compression_b2b_off_the_shelf_shard_sku_v1_lib import build_sku_context

    spec_path = sku_spec_json or DEFAULT_SKU_SPEC
    try:
        ctx = build_sku_context(
            workspace_root=workspace_root,
            spec_path=spec_path,
            external_sku=external_sku,
            shard_json_override=None,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"error: sku resolution failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if ctx.get("forced_shard_id"):
        ctx["routing_wiring"] = "forced_shard_id_v1"
        ctx["routing_note_ko"] = (
            "PoC /v2/compress에 forced_shard_id 전달 — B2B off-the-shelf SKU 샤드 고정."
        )
    return ctx


def _resolve_overlay_terms(
    *,
    workspace_root: Path,
    external_sku: str | None,
    auto_b2b_overlay: bool,
    must_keep_overlay_json: Path | None,
) -> tuple[list[str], dict[str, Any]]:
    overlay_meta: dict[str, Any] = {"applied": False}
    if must_keep_overlay_json is not None:
        path = must_keep_overlay_json.resolve()
        if not path.is_file():
            print(f"error: missing overlay json: {path}", file=sys.stderr)
            raise SystemExit(2)
        from scripts.compression_b2b_must_keep_overlay_v1_lib import load_overlay_terms

        terms = load_overlay_terms(path)
        overlay_meta = {
            "applied": bool(terms),
            "source": str(path.relative_to(workspace_root)).replace("\\", "/"),
        }
        return terms, overlay_meta
    if auto_b2b_overlay and external_sku:
        from scripts.compression_b2b_must_keep_overlay_v1_lib import (
            load_overlay_terms,
            overlay_path_for_external_sku,
        )

        path = overlay_path_for_external_sku(external_sku, workspace_root=workspace_root)
        if path.is_file():
            terms = load_overlay_terms(path)
            overlay_meta = {
                "applied": bool(terms),
                "source": str(path.relative_to(workspace_root)).replace("\\", "/"),
            }
            return terms, overlay_meta
    return [], overlay_meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Customer JSONL stateless V2 compression PoC.")
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument(
        "--input-jsonl",
        type=Path,
        required=True,
        help="JSONL with text/raw_text per line",
    )
    ap.add_argument("--max-cases", type=int, default=200)
    ap.add_argument(
        "--loss-profile",
        default="semantic_general",
        choices=["semantic_general", "lossless_text", "code_equivalent"],
    )
    ap.add_argument(
        "--compression-profile",
        default="economy",
        choices=["economy", "fidelity", "literal"],
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jaccard-floor", type=float, default=V2_JACCARD_FLOOR)
    ap.add_argument("--sku", default=None, help="B2B external SKU (e.g. MKM-SCM-A1).")
    ap.add_argument("--sku-spec-json", type=Path, default=None)
    ap.add_argument("--auto-b2b-overlay", action="store_true")
    ap.add_argument("--must-keep-overlay-json", type=Path, default=None)
    ap.add_argument("--relax-pass-gate", action="store_true")
    ap.add_argument("--graph-wire-selective-bridge", action="store_true")
    ap.add_argument("--short-context-token-threshold", type=int, default=None)
    ap.add_argument("--short-context-max-saving-rate", type=float, default=None)
    args = ap.parse_args()

    workspace_root = args.workspace_root.resolve()
    inp = args.input_jsonl.resolve()
    if not inp.is_file():
        print(f"error: missing input: {inp}", file=sys.stderr)
        return 2

    sku_context = _resolve_sku_context(
        workspace_root=workspace_root,
        external_sku=args.sku,
        sku_spec_json=args.sku_spec_json,
    )
    overlay_terms, overlay_meta = _resolve_overlay_terms(
        workspace_root=workspace_root,
        external_sku=args.sku,
        auto_b2b_overlay=args.auto_b2b_overlay,
        must_keep_overlay_json=args.must_keep_overlay_json,
    )
    forced_shard_id = sku_context.get("forced_shard_id")

    from fastapi.testclient import TestClient
    from scripts.compression_token_api_v2_stub import RESIDUAL_STUB_KEY, app
    from scripts.report_multilens_performance_eval import _jaccard

    client = TestClient(app)
    rows: list[dict[str, Any]] = []
    failures = 0

    for i, line in enumerate(inp.read_text(encoding="utf-8", errors="replace").splitlines()):
        if not line.strip() or len(rows) >= max(0, args.max_cases):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            failures += 1
            continue
        if not isinstance(obj, dict):
            continue
        text = _row_text(obj)
        if not text:
            continue
        row_id = str(obj.get("id") or f"row_{i}")
        compress_body: dict[str, Any] = {
            "text": text,
            "loss_profile": args.loss_profile,
            "compression_profile": args.compression_profile,
            "client_request_id": f"poc-{row_id}",
            "stateless_packet": True,
        }
        if forced_shard_id:
            compress_body["forced_shard_id"] = forced_shard_id
        if overlay_terms:
            compress_body["must_keep_overlay_terms"] = overlay_terms
        if args.graph_wire_selective_bridge:
            compress_body["graph_wire_selective_bridge"] = True
        if args.short_context_token_threshold is not None:
            compress_body["short_context_token_threshold"] = args.short_context_token_threshold
        if args.short_context_max_saving_rate is not None:
            compress_body["short_context_max_saving_rate"] = args.short_context_max_saving_rate

        cr = client.post("/v2/compress", json=compress_body)
        if cr.status_code != 200:
            failures += 1
            rows.append({"id": row_id, "ok": False, "error": cr.text[:200]})
            continue
        pkt = cr.json().get("compression_packet") or {}
        stub = (pkt.get("residual_meta") or {}).get(RESIDUAL_STUB_KEY) or {}
        if "reconstructed_text" in stub:
            failures += 1
            rows.append({"id": row_id, "ok": False, "error": "stateless_packet_leaked_reconstructed_text"})
            continue
        er = client.post(
            "/v2/expand",
            json={"compression_packet": pkt, "decode_mode": "codebook_only"},
        )
        if er.status_code != 200:
            failures += 1
            rows.append({"id": row_id, "ok": False, "error": er.text[:200]})
            continue
        expanded = er.json().get("text") or ""
        tin = _token_proxy(text)
        tout = _token_proxy(str(pkt.get("compressed_text") or ""))
        saving = max(0.0, 1.0 - (tout / tin)) if tin > 0 else 0.0
        jac = float(_jaccard(text, expanded))
        exact_restore = expanded == text
        if args.loss_profile == "lossless_text":
            ok = exact_restore
        else:
            ok = jac >= args.jaccard_floor
        if not ok and not args.relax_pass_gate:
            failures += 1
        router_meta = pkt.get("router_meta") if isinstance(pkt.get("router_meta"), dict) else {}
        rows.append(
            {
                "id": row_id,
                "ok": ok,
                "exact_restore": exact_restore,
                "token_in_proxy": tin,
                "token_out_proxy": tout,
                "token_saving_rate_proxy": round(saving, 6),
                "jaccard_proxy": round(jac, 6),
                "reassembly": (er.json().get("integrity_flags") or {}).get("reassembly"),
                "router_shard_id": router_meta.get("shard_id"),
            }
        )

    n_ok = sum(1 for r in rows if r.get("ok"))
    n = len(rows)
    avg_saving = sum(r.get("token_saving_rate_proxy", 0.0) for r in rows if r.get("ok")) / max(1, n_ok)
    avg_jac = sum(r.get("jaccard_proxy", 0.0) for r in rows if r.get("ok")) / max(1, n_ok)

    doc = {
        "schema": "customer_compression_stateless_poc_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "boundary_ack": "Per-customer JSONL only; not Golden 40 or Track A 47.5% claim.",
        "input_jsonl": str(inp).replace("\\", "/"),
        "loss_profile": args.loss_profile,
        "compression_profile": args.compression_profile,
        "case_count": n,
        "cases_passed": n_ok,
        "cases_passed_jaccard_floor": n_ok,
        "jaccard_floor": args.jaccard_floor,
        "pass_criterion": "exact_restore" if args.loss_profile == "lossless_text" else "jaccard_floor",
        "relax_pass_gate": bool(args.relax_pass_gate),
        "aggregate": {
            "mean_token_saving_rate_proxy": round(avg_saving, 6),
            "mean_jaccard_proxy": round(avg_jac, 6),
        },
        "parse_or_api_failures": failures,
        "cases": rows[:50],
        "cases_truncated": len(rows) > 50,
    }
    if sku_context:
        doc["sku_context"] = sku_context
    if overlay_meta.get("applied") or args.auto_b2b_overlay or args.must_keep_overlay_json:
        doc["must_keep_overlay"] = overlay_meta

    out_path = args.out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"cases={n} passed_jaccard={n_ok} mean_saving_proxy={avg_saving:.4f} mean_jaccard={avg_jac:.4f}")

    if n == 0:
        return 1
    if failures > 0:
        return 1
    if args.relax_pass_gate:
        return 0
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
