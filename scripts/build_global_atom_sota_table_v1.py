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


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def metric_row(label: str, ours: Any, base: Any) -> dict[str, Any]:
    delta = None
    if isinstance(ours, (int, float)) and isinstance(base, (int, float)):
        delta = float(ours) - float(base)
    return {"metric": label, "ours": ours, "baseline": base, "delta_ours_minus_baseline": delta}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Table-1 style SOTA comparison from adapter packet.")
    ap.add_argument("--adapter-json", default="docs/final/artifacts/global_atom_sota_benchmark_adapter_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/global_atom_sota_table_latest.json")
    ap.add_argument("--output-md", default="docs/final/artifacts/global_atom_sota_table_latest.md")
    args = ap.parse_args()

    apath = resolve(args.adapter_json)
    if not apath.is_file():
        raise SystemExit(f"missing adapter json: {apath}")
    ad = load(apath)
    ours = (ad.get("ours") or {}).get("metrics") or {}
    baselines = ad.get("baselines") if isinstance(ad.get("baselines"), dict) else {}

    tables = []
    md_lines = ["# Global Atom SOTA Table (Draft)", ""]
    for key, base in baselines.items():
        if not isinstance(base, dict):
            continue
        bname = str(base.get("model_name") or key)
        bmet = base.get("metrics") if isinstance(base.get("metrics"), dict) else {}
        rows = [
            metric_row("oos_f1", ours.get("oos_f1"), bmet.get("oos_f1")),
            metric_row("oos_auc", ours.get("oos_auc"), bmet.get("oos_auc")),
            metric_row("ece", ours.get("ece"), bmet.get("ece")),
            metric_row("runtime_sec", ours.get("runtime_sec"), bmet.get("runtime_sec")),
            metric_row("cost_usd", ours.get("cost_usd"), bmet.get("cost_usd")),
        ]
        tables.append(
            {
                "baseline_key": key,
                "baseline_name": bname,
                "is_placeholder": bool(base.get("is_placeholder", False)),
                "rows": rows,
            }
        )
        md_lines.append(f"## vs {bname}")
        md_lines.append(f"- placeholder: `{bool(base.get('is_placeholder', False))}`")
        md_lines.append("")
        md_lines.append("| metric | ours | baseline | delta |")
        md_lines.append("|---|---:|---:|---:|")
        for r in rows:
            md_lines.append(
                f"| {r['metric']} | {r['ours']} | {r['baseline']} | {r['delta_ours_minus_baseline']} |"
            )
        md_lines.append("")

    out = {
        "schema": "global_atom_sota_table_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "tables": tables,
        "note": "If placeholders remain, Table-1 is draft-only and not submission-claimable.",
    }

    jout = resolve(args.output_json)
    mout = resolve(args.output_md)
    jout.parent.mkdir(parents=True, exist_ok=True)
    jout.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mout.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")
    print(str(jout))
    print(str(mout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

