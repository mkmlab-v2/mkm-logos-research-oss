#!/usr/bin/env python3
"""Defense hybrid bench: deterministic critical-field wire + Track B literal semantic lane.

Default output: docs/final/artifacts/defense_hybrid_compression_bench_v0.json .
With --append-stress, appends stress records and defaults output to
defense_hybrid_compression_bench_merged_v0.json (override with --out).
Does not modify B-track trading code. research_only — not a MoD compliance seal.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.l1_side_channel_wire_codec import (  # noqa: E402
    codec_availability,
    decode_adaptive_msgpack,
    encode_adaptive_msgpack,
)
from scripts.report_multilens_performance_eval import evaluate_report  # noqa: E402

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_INPUT = ART / "defense_uav_bench_input_v0.json"
DEFAULT_STRESS = ART / "defense_uav_bench_stress_v0.json"
DEFAULT_OUT = ART / "defense_hybrid_compression_bench_v0.json"
DEFAULT_OUT_MERGED = ART / "defense_hybrid_compression_bench_merged_v0.json"
BASELINE_V2 = ART / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
DECISION = ART / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"

# Track B literal caps — align with scripts/run_ultra_compression_default.py
LITERAL_STRATEGY = "C"
LITERAL_INTENSITY = "high"
LITERAL_GENERAL_MAX_SAVING = 0.28
LITERAL_SENSITIVE_MAX_SAVING = 0.26
LITERAL_HANGUL_MAX_SAVING = 0.30

TARGET_TYPES = ("personnel", "vehicle", "structure", "unknown", "none")
SIT_TEMPLATES_KO = [
    "전방 {a}m 고도에서 {tgt} 신호 약함, 구름 영향 가능.",
    "서쪽 이격 중 배터리 {b}%대, 귀환 권고 검토.",
    "시야 불량 구간 통과, 표적 재확인 요청.",
    "바람 {w}m/s 추정, 고도 유지하며 재촬영.",
    "전자간섭 흔적 없음, 좌표 고정 완료.",
]


def _canonical_json_bytes(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _critical_dict(rec: dict[str, Any]) -> dict[str, Any]:
    loc = rec.get("location") or {}
    return {
        "lat": float(loc["lat"]),
        "lon": float(loc["lon"]),
        "altitude_m": float(rec["altitude_m"]),
        "battery_pct": int(rec["battery_pct"]),
        "target_type": str(rec["target_type"]),
        "confidence": float(rec["confidence"]),
        "timestamp_utc": str(rec["timestamp_utc"]),
    }


def _critical_equal(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if set(a) != set(b):
        return False
    for k in a:
        va, vb = a[k], b[k]
        if k in ("lat", "lon", "altitude_m", "confidence"):
            if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
                return False
            if not math.isclose(float(va), float(vb), rel_tol=0.0, abs_tol=1e-9):
                return False
        elif va != vb:
            return False
    return True


def generate_records(n: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    base = datetime(2026, 4, 1, tzinfo=timezone.utc)
    out: list[dict[str, Any]] = []
    for i in range(n):
        lat = round(rng.uniform(33.0, 38.5), 6)
        lon = round(rng.uniform(124.0, 132.0), 6)
        alt = round(rng.uniform(30.0, 500.0), 1)
        bat = rng.randint(5, 99)
        tgt = rng.choice(TARGET_TYPES)
        conf = round(rng.uniform(0.15, 0.99), 4)
        ts = (base + timedelta(minutes=i * 17 + rng.randint(0, 9))).strftime("%Y-%m-%dT%H:%M:%SZ")
        tpl = rng.choice(SIT_TEMPLATES_KO)
        situ = tpl.format(a=int(alt), tgt=tgt, b=bat, w=rng.randint(2, 15))
        if rng.random() < 0.35:
            situ += " EN: maintain orbit; no IFF change."
        out.append(
            {
                "id": f"uav_{i:03d}",
                "location": {"lat": lat, "lon": lon},
                "altitude_m": alt,
                "battery_pct": bat,
                "target_type": tgt,
                "confidence": conf,
                "timestamp_utc": ts,
                "situational_text": situ,
            }
        )
    return out


def build_input_doc(records: list[dict[str, Any]]) -> dict[str, Any]:
    cases = []
    for rec in records:
        raw = str(rec["situational_text"])
        cases.append(
            {
                "id": rec["id"],
                "raw_text": raw,
                "compressed_text": raw,
                "reconstructed_text": raw,
            }
        )
    return {"schema": "multilens_performance_eval_input_v1", "compression_cases": cases}


def write_input(path: Path, n: int, seed: int) -> None:
    records = generate_records(n, seed)
    doc = {
        "schema": "defense_uav_bench_input_v0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": seed,
        "record_count": len(records),
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {path}")


def load_records(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return list(doc.get("records") or [])


def main() -> int:
    ap = argparse.ArgumentParser(description="Defense UAV hybrid compression bench (critical wire + literal semantic).")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="defense_uav_bench_input_v0.json")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output bench artifact JSON")
    ap.add_argument(
        "--append-stress",
        type=Path,
        nargs="?",
        const=DEFAULT_STRESS,
        default=None,
        help="Append stress records from this file (default: defense_uav_bench_stress_v0.json); ids must not overlap --input.",
    )
    ap.add_argument("--write-input", action="store_true", help=f"Generate {DEFAULT_INPUT.name} and exit")
    ap.add_argument("--n", type=int, default=100, help="Record count when using --write-input")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for --write-input")
    args = ap.parse_args()

    if args.append_stress is not None and args.out.resolve() == DEFAULT_OUT.resolve():
        args.out = DEFAULT_OUT_MERGED

    if args.write_input:
        write_input(args.input, args.n, args.seed)
        return 0

    if not args.input.is_file():
        print(f"Missing input {args.input}; run with --write-input first.", file=sys.stderr)
        return 2

    avail = codec_availability()
    if not avail.msgpack:
        print("msgpack required: pip install msgpack", file=sys.stderr)
        return 2

    records = load_records(args.input)
    if not records:
        print("No records in input.", file=sys.stderr)
        return 2

    stress_rel: str | None = None
    if args.append_stress is not None:
        if not args.append_stress.is_file():
            print(f"Missing --append-stress file {args.append_stress}", file=sys.stderr)
            return 2
        extra = load_records(args.append_stress)
        if not extra:
            print("No records in --append-stress file.", file=sys.stderr)
            return 2
        ids_a = {str(r.get("id")) for r in records}
        ids_b = {str(r.get("id")) for r in extra}
        dup = ids_a & ids_b
        if dup:
            print(f"Duplicate record ids between --input and --append-stress: {sorted(dup)[:20]}", file=sys.stderr)
            return 2
        records = records + extra
        stress_rel = str(args.append_stress.relative_to(ROOT)).replace("\\", "/")

    baseline_doc = json.loads(BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(DECISION.read_text(encoding="utf-8"))
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    src_doc = build_input_doc(records)
    source_input = str(args.input.as_posix())
    if stress_rel:
        source_input = f"{source_input}|{stress_rel}"

    report = evaluate_report(
        src_doc,
        source_input=source_input,
        mode="experimental",
        strategy=LITERAL_STRATEGY,
        intensity=LITERAL_INTENSITY,
        must_keep=set(),
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=LITERAL_GENERAL_MAX_SAVING,
        sensitive_max_saving_rate=LITERAL_SENSITIVE_MAX_SAVING,
        hangul_max_saving_rate=LITERAL_HANGUL_MAX_SAVING,
        use_domain_router=False,
        use_master_codebook_lexicon_v1=False,
        include_gematria_metadata=False,
        include_gematria_4d_bridge=False,
        include_cee_core=False,
        apply_gematria_4d_bridge_policy=False,
    )

    cases_out = (report.get("compression_metrics") or {}).get("cases") or []
    by_id = {str(r.get("id")): r for r in cases_out}

    critical_ok = 0
    ratios: list[float] = []
    per_record: list[dict[str, Any]] = []

    for rec in records:
        cid = rec["id"]
        crit = _critical_dict(rec)
        wire, _variant = encode_adaptive_msgpack(crit)
        decoded = decode_adaptive_msgpack(wire)
        ok = _critical_equal(crit, decoded)
        if ok:
            critical_ok += 1

        row = by_id.get(str(cid), {})
        comp_sem = str(row.get("compressed_text_effective") or "")
        hybrid_bytes = len(wire) + len(comp_sem.encode("utf-8"))
        full_obj = {k: v for k, v in rec.items() if k != "id"}
        original_bytes = len(_canonical_json_bytes(full_obj))
        ratio = 1.0 - (hybrid_bytes / original_bytes) if original_bytes else 0.0
        ratios.append(ratio)

        per_record.append(
            {
                "id": cid,
                "critical_wire_bytes": len(wire),
                "semantic_compressed_utf8_bytes": len(comp_sem.encode("utf-8")),
                "original_full_json_bytes": original_bytes,
                "payload_compression_ratio": ratio,
                "critical_round_trip_ok": ok,
                "semantic_jaccard": row.get("reconstruction_fidelity_jaccard"),
                "semantic_token_saving_rate": row.get("token_saving_rate"),
            }
        )

    n = len(records)
    out_doc: dict[str, Any] = {
        "schema": "defense_hybrid_compression_bench_v0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_pack_ssot": "docs/final/artifacts/defense_code_pack_v1.json",
        "research_only": True,
        "note": (
            "Hybrid = encode_adaptive_msgpack(critical fields) + UTF-8 bytes of experimental compressed_text "
            "for situational_text only. Not MoD/USMTF compliance. literal caps match run_ultra_compression_default "
            "Track B; router/codebook/gematria disabled for isolated defense bench."
        ),
        "input_path": str(args.input.relative_to(ROOT)).replace("\\", "/"),
        **({"stress_input_appended": stress_rel} if stress_rel else {}),
        "record_count": n,
        "literal_profile": {
            "strategy": LITERAL_STRATEGY,
            "intensity": LITERAL_INTENSITY,
            "general_max_saving_rate": LITERAL_GENERAL_MAX_SAVING,
            "sensitive_max_saving_rate": LITERAL_SENSITIVE_MAX_SAVING,
            "hangul_max_saving_rate": LITERAL_HANGUL_MAX_SAVING,
        },
        "aggregate": {
            "critical_field_integrity": critical_ok / n if n else 0.0,
            "mean_payload_compression_ratio": sum(ratios) / len(ratios) if ratios else 0.0,
            "mean_semantic_jaccard": float(
                report.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
            ),
            "global_token_saving_rate": float(
                report.get("compression_metrics", {}).get("global_token_saving_rate", 0.0)
            ),
            "avg_sensitive_integrity": float(
                report.get("compression_metrics", {}).get("avg_sensitive_integrity", 0.0)
            ),
        },
        "multilens_report_excerpt": {
            "quality_gate": report.get("quality_gate"),
            "compression_metrics_headline": {
                k: report.get("compression_metrics", {}).get(k)
                for k in (
                    "avg_reconstruction_fidelity_jaccard",
                    "global_token_saving_rate",
                    "avg_sensitive_integrity",
                )
                if k in (report.get("compression_metrics") or {})
            },
        },
        "per_record": per_record,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"critical_field_integrity={out_doc['aggregate']['critical_field_integrity']:.6f} "
        f"mean_payload_compression_ratio={out_doc['aggregate']['mean_payload_compression_ratio']:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
