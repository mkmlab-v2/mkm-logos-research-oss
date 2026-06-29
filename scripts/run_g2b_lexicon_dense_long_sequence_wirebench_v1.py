#!/usr/bin/env python3
"""G2-b lexicon_dense long-sequence wirebench using stitched 31k mesh refs (B-track)."""

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

from scripts.compression_token_api_v2_stub import app  # noqa: E402
from scripts.mkm_inter_agent_wire_envelope_v1 import (  # noqa: E402
    build_turn_envelope,
    envelope_utf8_byte_len,
    new_session_id,
)

from fastapi.testclient import TestClient  # noqa: E402

DEFAULT_JSONL = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
DEFAULT_BASE = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_vs_packet_bench_extended_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/g2b_lexicon_dense_long_sequence_wirebench_v1_latest.json"

# Match lexicon_dense extended bench char lengths (~962–1808).
DEFAULT_TARGETS = (1800, 1800, 1000, 1000)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mesh_ref_line(row: dict[str, Any]) -> str:
    hints = row.get("sasang_routing_hints") or {}
    ref = row.get("gematria_path_ref") or {}
    return " ".join(
        [
            f"VID:{row.get('verse_id')}",
            f"PID:{row.get('path_id')}",
            f"S16:{ref.get('state16')}",
            f"P:{hints.get('posture_hint')}",
            f"E:{hints.get('entropy_leg')}",
        ]
    )


def _iter_mesh_ref_lines(path: Path, *, stride: int = 500) -> list[str]:
    out: list[str] = []
    with path.open(encoding="utf-8-sig") as f:
        for i, raw in enumerate(f):
            if i % stride != 0:
                continue
            row = json.loads(raw)
            if isinstance(row, dict):
                out.append(_mesh_ref_line(row))
    return out


def _stitch_long_sequences(short_lines: list[str], targets: tuple[int, ...]) -> list[str]:
    if not short_lines:
        return []
    sequences: list[str] = []
    cursor = 0
    n = len(short_lines)
    for target in targets:
        parts: list[str] = []
        guard = 0
        while guard < n * 50:
            parts.append(short_lines[cursor % n])
            cursor += 1
            guard += 1
            joined = " | ".join(parts)
            if len(joined) >= target:
                sequences.append(joined)
                break
    return sequences


def _bench(lines: list[str], *, session_prefix: str) -> tuple[float | None, list[dict[str, Any]]]:
    client = TestClient(app)
    session = new_session_id(session_prefix)
    rows: list[dict[str, Any]] = []
    vals: list[float] = []
    for i, text in enumerate(lines, start=1):
        enc = client.post("/v1/research/mkm_lexicon_wire/encode", json={"text": text, "zstd_min_raw_bytes": 0})
        enc_body = enc.json() if enc.status_code == 200 else {}
        env = build_turn_envelope(
            encode_response=enc_body,
            session_id=session,
            turn_id=i,
            from_agent="g2b_candidate",
            to_agent="g2b_receiver",
        )
        env_b = envelope_utf8_byte_len(env)
        cr = client.post("/v2/compress", json={"text": text, "loss_profile": "semantic_general"})
        pkt_b = 0
        if cr.status_code == 200:
            pkt = cr.json().get("compression_packet")
            if isinstance(pkt, dict):
                pkt_b = len(json.dumps(pkt, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        saving = round(1.0 - env_b / pkt_b, 6) if pkt_b else None
        if saving is not None:
            vals.append(saving)
        rows.append(
            {
                "line_index": i,
                "char_len": len(text),
                "envelope_bytes": env_b,
                "packet_json_bytes": pkt_b,
                "byte_saving": saving,
            }
        )
    avg = round(sum(vals) / len(vals), 6) if vals else None
    return avg, rows


def build_report(
    *,
    jsonl_path: Path,
    baseline_path: Path,
    targets: tuple[int, ...],
    stride: int,
) -> dict[str, Any]:
    short_lines = _iter_mesh_ref_lines(jsonl_path, stride=stride)
    long_lines = _stitch_long_sequences(short_lines, targets)
    cand_avg, cand_rows = _bench(long_lines, session_prefix="g2b-wire")
    base = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    summary = base.get("summary") or {}
    lexicon_dense = (base.get("corpora") or {}).get("lexicon_dense") or {}
    lexicon_avg = summary.get("lexicon_dense_avg_byte_savings")
    g2a_short_avg = None
    g2a_path = ROOT / "reports/g2a_candidate_wire_payload_bench_v1_latest.json"
    if g2a_path.is_file():
        g2a_short_avg = json.loads(g2a_path.read_text(encoding="utf-8-sig")).get("candidate_avg_byte_saving_vs_packet")

    return {
        "schema": "g2b_lexicon_dense_long_sequence_wirebench_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "candidate_corpus": "31k_mesh_ref_long_sequence_stitch",
        "candidate_line_count": len(long_lines),
        "candidate_avg_byte_saving_vs_packet": cand_avg,
        "target_char_lengths": list(targets),
        "stitch_stride": stride,
        "baseline_lexicon_dense": {
            "avg_byte_savings_vs_packet": lexicon_avg,
            "line_count": lexicon_dense.get("line_count"),
            "char_lens": [row.get("char_len") for row in lexicon_dense.get("lines") or [] if isinstance(row, dict)],
        },
        "delta_vs_baseline": {
            "vs_lexicon_dense": (
                round(cand_avg - lexicon_avg, 6)
                if cand_avg is not None and lexicon_avg is not None
                else None
            ),
            "vs_g2a_short_mesh_sample": (
                round(cand_avg - g2a_short_avg, 6)
                if cand_avg is not None and g2a_short_avg is not None
                else None
            ),
        },
        "rows": cand_rows,
        "boundary_ack": "Long-sequence mesh_ref stitch probe; compares against lexicon_dense extended bench lengths only.",
        "reproduce": "py scripts/run_g2b_lexicon_dense_long_sequence_wirebench_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stride", type=int, default=500)
    ap.add_argument("--targets", type=int, nargs="+", default=list(DEFAULT_TARGETS))
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {args.jsonl}"}))
        return 1
    if not args.baseline.is_file():
        print(json.dumps({"ok": False, "error": f"missing baseline bench: {args.baseline}"}))
        return 1

    doc = build_report(
        jsonl_path=args.jsonl,
        baseline_path=args.baseline,
        targets=tuple(args.targets),
        stride=args.stride,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "candidate_avg": doc["candidate_avg_byte_saving_vs_packet"],
                "delta_vs_lexicon_dense": doc["delta_vs_baseline"]["vs_lexicon_dense"],
                "out": str(args.out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
