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
    ap.add_argument("--loss-profile", default="semantic_general", choices=["semantic_general", "lossless_text", "code_equivalent"])
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jaccard-floor", type=float, default=V2_JACCARD_FLOOR)
    args = ap.parse_args()

    inp = args.input_jsonl.resolve()
    if not inp.is_file():
        print(f"error: missing input: {inp}", file=sys.stderr)
        return 2

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
        cr = client.post(
            "/v2/compress",
            json={
                "text": text,
                "loss_profile": args.loss_profile,
                "client_request_id": f"poc-{row_id}",
                "stateless_packet": True,
            },
        )
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
        if not ok:
            failures += 1
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
        "case_count": n,
        "cases_passed": n_ok,
        "cases_passed_jaccard_floor": n_ok,
        "jaccard_floor": args.jaccard_floor,
        "pass_criterion": "exact_restore" if args.loss_profile == "lossless_text" else "jaccard_floor",
        "aggregate": {
            "mean_token_saving_rate_proxy": round(avg_saving, 6),
            "mean_jaccard_proxy": round(avg_jac, 6),
        },
        "parse_or_api_failures": failures,
        "cases": rows[:50],
        "cases_truncated": len(rows) > 50,
    }
    out_path = args.out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"cases={n} passed_jaccard={n_ok} mean_saving_proxy={avg_saving:.4f} mean_jaccard={avg_jac:.4f}")
    return 0 if n > 0 and failures == 0 and n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
