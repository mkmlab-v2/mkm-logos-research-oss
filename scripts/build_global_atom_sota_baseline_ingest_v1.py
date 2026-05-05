#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        try:
            return float(s)
        except Exception:
            return None
    return None


def load_input(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize external baseline results to SOTA adapter schema.")
    ap.add_argument("--model-name", required=True)
    ap.add_argument("--input-json", default="")
    ap.add_argument("--oos-f1", default="")
    ap.add_argument("--oos-auc", default="")
    ap.add_argument("--ece", default="")
    ap.add_argument("--runtime-sec", default="")
    ap.add_argument("--cost-usd", default="")
    ap.add_argument("--split-id", default="")
    ap.add_argument("--dataset-id", default="")
    ap.add_argument("--notes", default="")
    ap.add_argument("--output-json", required=True)
    args = ap.parse_args()

    src_doc: dict[str, Any] = {}
    src_path = None
    if args.input_json.strip():
        src_path = resolve(args.input_json)
        if not src_path.is_file():
            raise SystemExit(f"missing input json: {src_path}")
        src_doc = load_input(src_path)

    metrics_src = src_doc.get("metrics") if isinstance(src_doc.get("metrics"), dict) else src_doc
    oos_f1 = to_float(args.oos_f1) if args.oos_f1 != "" else to_float(metrics_src.get("oos_f1"))
    oos_auc = to_float(args.oos_auc) if args.oos_auc != "" else to_float(metrics_src.get("oos_auc"))
    ece = to_float(args.ece) if args.ece != "" else to_float(metrics_src.get("ece"))
    runtime_sec = to_float(args.runtime_sec) if args.runtime_sec != "" else to_float(metrics_src.get("runtime_sec"))
    cost_usd = to_float(args.cost_usd) if args.cost_usd != "" else to_float(metrics_src.get("cost_usd"))

    is_placeholder = any(x is None for x in (oos_f1, oos_auc, ece, runtime_sec, cost_usd))
    out = {
        "schema": "global_atom_sota_baseline_result_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "model_name": args.model_name,
        "is_placeholder": is_placeholder,
        "metrics": {
            "oos_f1": oos_f1,
            "oos_auc": oos_auc,
            "ece": ece,
            "runtime_sec": runtime_sec,
            "cost_usd": cost_usd,
        },
        "evaluation_context": {
            "split_id": args.split_id or src_doc.get("split_id"),
            "dataset_id": args.dataset_id or src_doc.get("dataset_id"),
            "input_json": str(src_path) if src_path else "",
        },
        "notes": args.notes or src_doc.get("notes", ""),
    }

    outp = resolve(args.output_json)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

