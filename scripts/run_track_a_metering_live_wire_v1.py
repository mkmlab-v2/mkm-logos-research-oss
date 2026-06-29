#!/usr/bin/env python3
"""Internal pilot: POST /v1/compress with eval_context.meter_log → track_a_metering_log_v1.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
DEFAULT_INPUT = ROOT / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/track_a_metering_live_wire_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cases(path: Path, *, limit: int) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    cases = doc.get("compression_cases") or []
    if not isinstance(cases, list):
        raise ValueError("compression_cases must be a list")
    out: list[dict[str, Any]] = []
    for row in cases:
        if not isinstance(row, dict):
            continue
        text = str(row.get("raw_text") or "").strip()
        if not text:
            continue
        out.append({"id": row.get("id"), "text": text})
        if len(out) >= max(1, limit):
            break
    if not out:
        raise ValueError(f"no compress cases in {path}")
    return out


def run_live_wire(
    *,
    workspace_root: Path,
    input_json: Path,
    case_limit: int,
    client_prefix: str,
    use_live_eval: bool = False,
) -> dict[str, Any]:
    import os

    from scripts.core.compression_hardening_v1 import _config_doc

    hardening = workspace_root / "data/btrack/track_a_metering_live_wire_hardening_v1.json"
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = str(hardening.resolve())
    _config_doc.cache_clear()

    from fastapi.testclient import TestClient

    from scripts.compression_token_api_stub import app

    cases = _load_cases(input_json, limit=case_limit)
    client = TestClient(app)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for idx, case in enumerate(cases, start=1):
        case_id = str(case.get("id") or f"case_{idx}")
        eval_context: dict[str, Any] = {
            "hydrate_metrics": True,
            "meter_log": True,
        }
        if use_live_eval:
            eval_context["hydrate_live_eval"] = True
        payload = {
            "text": case["text"],
            "client_request_id": f"{client_prefix}-{case_id}",
            "eval_context": eval_context,
        }
        resp = client.post("/v1/compress", json=payload)
        body = resp.json() if resp.content else {}
        flags = body.get("integrity_flags") or {}
        metrics = body.get("compression_metrics") or {}
        ok = (
            resp.status_code == 200
            and bool(flags.get("meter_log_appended"))
            and isinstance(metrics.get("token_in"), int)
            and isinstance(metrics.get("token_out"), int)
            and int(metrics["token_in"]) > 0
            and int(metrics["token_out"]) <= int(metrics["token_in"])
        )
        row = {
            "case_id": case_id,
            "http_status": resp.status_code,
            "meter_log_appended": bool(flags.get("meter_log_appended")),
            "token_in": metrics.get("token_in"),
            "token_out": metrics.get("token_out"),
            "saving_rate": metrics.get("savings_ratio"),
            "band_valid": ok,
        }
        rows.append(row)
        if not ok:
            failures.append({**row, "integrity_flags": flags})

    appended = sum(1 for r in rows if r.get("meter_log_appended"))
    band_valid = sum(1 for r in rows if r.get("band_valid"))

    return {
        "schema": "track_a_metering_live_wire_v1",
        "generated_at_utc": _utc(),
        "status": "pass" if appended == len(rows) and band_valid == len(rows) else "fail",
        "input_json": str(input_json).replace("\\", "/"),
        "case_limit": case_limit,
        "cases_attempted": len(rows),
        "meter_log_appended_count": appended,
        "band_valid_count": band_valid,
        "client_request_prefix": client_prefix,
        "notes": "In-process compress stub dogfood; not billing or external routing.",
        "hardening_config": str(
            (workspace_root / "data/btrack/track_a_metering_live_wire_hardening_v1.json").resolve()
        ).replace("\\", "/"),
        "use_live_eval": use_live_eval,
        "rows": rows,
        "failures": failures,
        "reproducible_command": (
            "py scripts/run_track_a_metering_live_wire_v1.py "
            f"--input-json {input_json.relative_to(workspace_root).as_posix()}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--case-limit", type=int, default=20)
    ap.add_argument("--client-prefix", default="live-wire-pilot-v1")
    ap.add_argument("--use-live-eval", action="store_true", help="Run evaluate_report per case (slower).")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    input_json = args.input_json if args.input_json.is_absolute() else root / args.input_json
    out = args.out if args.out.is_absolute() else root / args.out

    if not input_json.is_file():
        print(f"error: input missing: {input_json}", file=sys.stderr)
        return 2

    try:
        doc = run_live_wire(
            workspace_root=root,
            input_json=input_json.resolve(),
            case_limit=max(1, args.case_limit),
            client_prefix=str(args.client_prefix).strip() or "live-wire-pilot-v1",
            use_live_eval=bool(args.use_live_eval),
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(
        f"meter_log_appended={doc['meter_log_appended_count']}/{doc['cases_attempted']} "
        f"band_valid={doc['band_valid_count']}/{doc['cases_attempted']}"
    )
    return 0 if doc.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
