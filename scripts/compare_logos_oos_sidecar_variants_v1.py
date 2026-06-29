#!/usr/bin/env python3
"""Compare strict OOS gate JSONs (sidecar A/B table). research_only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/logos_oos_sidecar_variant_compare_v1_latest.json"


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _summarize(label: str, path: Path) -> dict[str, Any]:
    d = _read(path)
    oos = d.get("oos_metrics") or {}
    train = (d.get("best_train_candidate") or {}).get("train_metrics") or {}
    gate = d.get("gate") or {}
    return {
        "label": label,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "oos_hit": oos.get("directional_hit_rate_active"),
        "oos_n_active": oos.get("n_active_days"),
        "oos_return": oos.get("total_return"),
        "train_n_active": train.get("n_active_days"),
        "train_hit": train.get("directional_hit_rate_active"),
        "go": gate.get("go"),
        "status": gate.get("status"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--variant",
        action="append",
        nargs=2,
        metavar=("LABEL", "PATH"),
        help="Repeatable: --variant label path",
    )
    args = ap.parse_args()

    default_variants = [
        ("golden_gate_ssot", "docs/final/artifacts/prophecy_logos_revalidation_oos_gate_latest.json"),
        ("sparse_v1_latest_30y", "reports/logos_oos_30y_sparse_v1_latest_recheck.json"),
        ("manseryeok_session_30y", "reports/logos_oos_30y_manseryeok_session_v1_latest.json"),
        ("ensemble_backfill_30y", "reports/logos_oos_30y_ensemble_sidecar_v1_latest.json"),
        ("calendar_stub_30y", "reports/logos_oos_30y_sidecar_calendar_v1_latest.json"),
    ]
    variants = args.variant if args.variant else default_variants
    rows = []
    for item in variants:
        if len(item) != 2:
            continue
        label, rel = item[0], item[1]
        p = ROOT / rel
        if not p.is_file():
            rows.append({"label": label, "path": rel, "missing": True})
            continue
        if p.name.startswith("prophecy_logos_revalidation"):
            d = _read(p)
            oos = d.get("oos_metrics") or {}
            gate = d.get("gate") or {}
            rows.append(
                {
                    "label": label,
                    "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "oos_hit": oos.get("directional_hit_rate_active"),
                    "oos_n_active": oos.get("n_active_days"),
                    "oos_return": oos.get("total_return"),
                    "go": gate.get("go"),
                    "status": gate.get("status"),
                    "note": "promoted revalidation artifact (not raw router-only)",
                }
            )
        else:
            rows.append(_summarize(label, p))

    scored = [r for r in rows if r.get("oos_hit") is not None and not r.get("missing")]
    best = max(scored, key=lambda r: float(r.get("oos_hit") or 0)) if scored else None
    out = {
        "schema": "logos_oos_sidecar_variant_compare_v1",
        "generated_at_utc": None,
        "variants": rows,
        "best_oos_hit_label": best.get("label") if best else None,
        "note_ko": (
            "30y panel 단일 lb28/nz0.15 재현은 sparse도 go=false일 수 있음(활성일·수익). "
            "성숙도 D SSOT는 prophecy_logos_revalidation_oos_gate_latest.json 유지."
        ),
    }
    from datetime import datetime, timezone

    out["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
