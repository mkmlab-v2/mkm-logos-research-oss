#!/usr/bin/env python3
"""BEP from INTEGRITY_COST_V4 JSON: inject Gain and Cost_marginal from per-case rows.

Mapping (per case, then mean over cohort):
  Gain_i = bytes_raw_utf8 - bytes_compressed_utf8  (token compression slack vs raw)
  Cost_marginal_i = total_wire_bytes - bytes_compressed_utf8  (diff + varint framing over comp)

Contribution margin per case = Gain_i - Cost_marginal_i = bytes_raw_utf8 - total_wire_bytes
(v4 real_saving_vs_raw * br).

N_BEP = Cost_fixed / (mean(Gain) - mean(Cost_marginal)) for batch-homogeneous approximation.

Cost_fixed scenarios default: 250 (light TLS+BLS assumption), 500 (heavier L4-L7).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.simulate_micro_payload_bep_v1 import compute_bep, sweep_curve  # noqa: E402

DEFAULT_INTEGRITY = ROOT / "docs" / "final" / "artifacts" / "INTEGRITY_COST_V4_ZONE_C_HANGUL_V1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "MICRO_PAYLOAD_BEP_FROM_INTEGRITY_ZONE_C_V1.json"


def extract_per_case(doc: dict) -> tuple[list[dict[str, float]], dict[str, float]]:
    cases = doc.get("cases") or []
    rows: list[dict[str, float]] = []
    for c in cases:
        br = float(c.get("bytes_raw_utf8") or 0)
        bc = float(c.get("bytes_compressed_utf8") or 0)
        tw = float(c.get("total_wire_bytes") or 0)
        gain = br - bc
        marginal = max(0.0, tw - bc)
        net = br - tw
        rows.append(
            {
                "id": str(c.get("id", "")),
                "bytes_raw_utf8": br,
                "bytes_compressed_utf8": bc,
                "total_wire_bytes": tw,
                "gain_compression_bytes": gain,
                "cost_marginal_integrity_bytes": marginal,
                "net_bytes_vs_raw": net,
            }
        )
    n = len(rows)
    if n == 0:
        return rows, {}
    sg = sum(r["gain_compression_bytes"] for r in rows)
    sm = sum(r["cost_marginal_integrity_bytes"] for r in rows)
    sn = sum(r["net_bytes_vs_raw"] for r in rows)
    return rows, {
        "case_count": float(n),
        "mean_gain_compression_bytes": sg / n,
        "mean_cost_marginal_integrity_bytes": sm / n,
        "mean_net_bytes_vs_raw": sn / n,
        "total_gain_compression_bytes": sg,
        "total_cost_marginal_integrity_bytes": sm,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="BEP from integrity_cost_model_v4 JSON (zone_c or any shard cohort).")
    ap.add_argument("--integrity-json", type=Path, default=DEFAULT_INTEGRITY)
    ap.add_argument(
        "--cost-fixed-scenarios",
        default="250,500",
        help="Comma-separated Cost_fixed bytes (e.g. 250,500).",
    )
    ap.add_argument("--sweep-n-max", type=int, default=0, help="Optional curve 0..N for first scenario.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    path = Path(args.integrity_json).resolve()
    if not path.is_file():
        print("FAIL: integrity json not found", path, file=sys.stderr)
        return 1

    doc = json.loads(path.read_text(encoding="utf-8"))
    per_case, agg = extract_per_case(doc)
    if not agg:
        print("FAIL: no cases in document", file=sys.stderr)
        return 1

    gain_m = float(agg["mean_gain_compression_bytes"])
    cm_m = float(agg["mean_cost_marginal_integrity_bytes"])

    scenarios: list[dict[str, object]] = []
    cfs = [float(x.strip()) for x in str(args.cost_fixed_scenarios).split(",") if x.strip()]
    for cf in cfs:
        bep = compute_bep(cf, gain_m, cm_m)
        entry: dict[str, object] = {"cost_fixed_bytes": cf, "bep": bep}
        if scenarios == [] and int(args.sweep_n_max) > 0 and bep.get("n_bep_ceil") is not None:
            ncap = max(int(args.sweep_n_max), int(bep["n_bep_ceil"]) * 2)
            entry["curve_0_to_n"] = sweep_curve(cf, gain_m, cm_m, n_max=ncap)
        scenarios.append(entry)

    payload = {
        "schema": "micro_payload_bep_from_integrity_v4_v1",
        "description": (
            "Gain = mean(raw - compressed); Cost_marginal = mean(wire - compressed) from v4 cases. "
            "N_BEP = Cost_fixed / (Gain - Cost_marginal)."
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_integrity_json": str(path.relative_to(ROOT)).replace("\\", "/"),
        "integrity_schema": doc.get("schema"),
        "v4_config": doc.get("v4_config"),
        "summary_from_integrity": doc.get("summary"),
        "derived_averages": agg,
        "per_case": per_case,
        "cost_fixed_scenarios": scenarios,
    }

    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("OK:", out_path)
    print("mean_gain_compression_bytes", gain_m)
    print("mean_cost_marginal_integrity_bytes", cm_m)
    print("contribution_margin", gain_m - cm_m)
    for s in scenarios:
        b = s["bep"]
        if isinstance(b, dict) and b.get("n_bep_ceil") is not None:
            print(f"Cost_fixed={s['cost_fixed_bytes']} -> N_BEP_ceil={b['n_bep_ceil']} exact={b.get('n_bep')}")
        elif isinstance(b, dict):
            print(f"Cost_fixed={s['cost_fixed_bytes']} -> no finite N_BEP ({b.get('reason')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
