#!/usr/bin/env python3
"""B2B short-context cap + fidelity/literal profile A/B on industry SKUs. [HYPO]"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/compression_b2b_short_context_cap_chain_v1_latest.json"

SKU_CORPUS: dict[str, tuple[str, str]] = {
    "MKM-SCM-A1": ("data/compression/stateless_poc_scm_public_safe_v1.jsonl", "scm_a1"),
    "MKM-CHAT-D1": ("data/compression/stateless_poc_chat_public_safe_v1.jsonl", "chat_d1"),
    "MKM-FIN-E1": ("data/compression/stateless_poc_finance_public_safe_v1.jsonl", "fin_e1"),
    "MKM-MED-G1": ("data/compression/stateless_poc_health_public_safe_v1.jsonl", "med_g1"),
}

ARMS: list[dict[str, Any]] = [
    {
        "arm": "fidelity_overlay",
        "suffix": "fidelity_overlay",
        "compression_profile": "fidelity",
        "short_threshold": None,
        "short_max_saving": None,
    },
    {
        "arm": "short_cap_overlay",
        "suffix": "shortcap_overlay",
        "compression_profile": "economy",
        "short_threshold": 40,
        "short_max_saving": 0.35,
    },
    {
        "arm": "literal_overlay",
        "suffix": "literal_overlay",
        "compression_profile": "literal",
        "short_threshold": None,
        "short_max_saving": None,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], label: str) -> int:
    print(f"RUN [{label}]", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip()[-500:])
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip()[-500:], file=sys.stderr)
    return proc.returncode


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") or {}
    cc = doc.get("case_count") or 0
    cp = doc.get("cases_passed") or 0
    return {
        "cases_passed": cp,
        "case_count": cc,
        "pass_rate": round(cp / cc, 4) if cc else 0.0,
        "mean_jaccard_all": agg.get("mean_jaccard_proxy_all_cases"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--short-threshold", type=int, default=40)
    ap.add_argument("--short-max-saving", type=float, default=0.35)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    chain_ok = True

    for sku, (corpus_rel, slug) in SKU_CORPUS.items():
        for arm in ARMS:
            threshold = arm["short_threshold"]
            max_saving = arm["short_max_saving"]
            if arm["arm"] == "short_cap_overlay":
                threshold = args.short_threshold
                max_saving = args.short_max_saving
            report_rel = f"reports/customer_compression_stateless_poc_{slug}_{arm['suffix']}_v1_latest.json"
            cmd = [
                PY,
                "scripts/run_customer_compression_stateless_poc_v1.py",
                "--input-jsonl",
                corpus_rel,
                "--sku",
                sku,
                "--auto-b2b-overlay",
                "--compression-profile",
                arm["compression_profile"],
                "--max-cases",
                str(args.max_cases),
                "--out-json",
                report_rel,
                "--relax-pass-gate",
            ]
            if threshold is not None and max_saving is not None:
                cmd.extend(
                    [
                        "--short-context-token-threshold",
                        str(threshold),
                        "--short-context-max-saving-rate",
                        str(max_saving),
                    ]
                )
            rc = _run(cmd, label=f"{arm['arm']}_{slug}")
            report = ROOT / report_rel
            steps.append(
                {
                    "arm": arm["arm"],
                    "external_sku": sku,
                    "exit_code": rc,
                    "report_path": report_rel,
                    **_read(report),
                }
            )
            if rc != 0:
                chain_ok = False

    rc = _run([PY, "scripts/build_compression_b2b_short_context_cap_compare_v1.py"], label="compare")
    if rc != 0:
        chain_ok = False

    compare_path = ROOT / "reports/compression_b2b_short_context_cap_compare_v1_latest.json"
    compare = json.loads(compare_path.read_text(encoding="utf-8-sig")) if compare_path.is_file() else {}

    doc = {
        "schema": "compression_b2b_short_context_cap_chain_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ad_headline_ready": False,
        "chain_ok": chain_ok,
        "short_context_defaults": {
            "token_threshold": args.short_threshold,
            "max_saving_rate": args.short_max_saving,
            "disable_min_saving_floor": True,
        },
        "steps": steps,
        "compare_path": compare_path.as_posix() if compare_path.is_file() else None,
        "winners": compare.get("winners"),
    }
    out = args.out_json.resolve()
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
