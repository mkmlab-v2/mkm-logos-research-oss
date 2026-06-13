#!/usr/bin/env python3
"""tp01 ops measurement snapshot — resume pack latency, inject tokens, A2A compress pilot.

[HYPO] / research_only / B-track. Append `--append-log` for longitudinal ops tracking.

  py scripts/build_a2a_tp01_ops_measurement_v1.py
  py scripts/build_a2a_tp01_ops_measurement_v1.py --append-log
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_tp01_ops_measurement_v1_latest.json"
DEFAULT_LOG = ROOT / "docs/final/artifacts/a2a_tp01_ops_measurement_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _time_resume_pack_build(root: Path, *, lane: str | None) -> dict[str, Any]:
    cmd = [sys.executable, "scripts/build_mkm_chat_resume_pack_v1.py"]
    if lane:
        cmd.extend(["--lane", lane])
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return {
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "elapsed_ms": elapsed_ms,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-400:],
    }


def _token_bench_snapshot(root: Path, *, top_n: int) -> dict[str, Any]:
    from bench_mkm_ops_memory_index_token_savings_v1 import (  # noqa: E402
        _count_tokens,
        _full_top_n_slice_text,
        _inject_pins_text,
    )
    from mkm_ops_memory_index_lib_v1 import DEFAULT_INDEX_PATH  # noqa: E402

    if not DEFAULT_INDEX_PATH.is_file():
        return {"ok": False, "error": f"missing index: {DEFAULT_INDEX_PATH}"}

    inject_off = _inject_pins_text(root, top_n=top_n, include_slice=False)
    inject_off_count = _count_tokens(inject_off)
    try:
        full_text = _full_top_n_slice_text(root, top_n=top_n)
        full_count = _count_tokens(full_text)
    except (FileNotFoundError, ValueError) as exc:
        full_count = {"tokens": 0, "method": "skipped", "error": str(exc)}

    full_t = int(full_count.get("tokens") or 0)
    inject_t = int(inject_off_count.get("tokens") or 0)
    saved = max(0, full_t - inject_t)
    ratio = round(saved / full_t, 4) if full_t else 0.0
    return {
        "ok": True,
        "top_n": top_n,
        "inject_off_tokens": inject_t,
        "full_anchor_tokens": full_t,
        "tokens_saved_vs_full_anchor": saved,
        "reduction_ratio_vs_full_anchor": ratio,
        "token_count_method": inject_off_count.get("method"),
    }


def _tp01_pilot_snapshot(root: Path, *, top_n: int, routing_profile: str) -> dict[str, Any]:
    from scripts.build_mkm_chat_resume_a2a_pilot_v1 import build_pilot_document  # noqa: E402

    doc = build_pilot_document(
        root,
        top_n=top_n,
        include_slice=False,
        slice_max_chars=1200,
        lane=None,
        routing_profile=routing_profile,
    )
    compress = doc.get("compress_result") or {}
    inject = doc.get("inject_payload") or {}
    return {
        "pilot_ok": compress.get("skipped") is not True and compress.get("http_status") == 200,
        "inject_tokens": inject.get("tokens"),
        "compress_skipped": compress.get("skipped"),
        "savings_ratio": (compress.get("compression_metrics") or {}).get("savings_ratio"),
        "routing_profile": routing_profile,
    }


def _load_log_rows(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _longitudinal_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"run_count": 0}
    build_ms = [float(r["resume_pack_build_ms"]) for r in rows if r.get("resume_pack_build_ms") is not None]
    inject_t = [int(r["inject_off_tokens"]) for r in rows if r.get("inject_off_tokens") is not None]
    savings = [float(r["tp01_savings_ratio"]) for r in rows if r.get("tp01_savings_ratio") is not None]
    first = rows[0].get("measured_at_utc")
    last = rows[-1].get("measured_at_utc")
    out: dict[str, Any] = {
        "run_count": len(rows),
        "first_measured_at_utc": first,
        "last_measured_at_utc": last,
    }
    if build_ms:
        out["resume_pack_build_ms"] = {
            "min": min(build_ms),
            "max": max(build_ms),
            "mean": round(sum(build_ms) / len(build_ms), 2),
        }
    if inject_t:
        out["inject_off_tokens"] = {
            "min": min(inject_t),
            "max": max(inject_t),
            "mean": round(sum(inject_t) / len(inject_t), 2),
        }
    if savings:
        out["tp01_savings_ratio"] = {
            "min": min(savings),
            "max": max(savings),
            "mean": round(sum(savings) / len(savings), 6),
        }
    return out


def _log_path_display(root: Path, log_path: Path) -> str:
    try:
        return str(log_path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(log_path)


def build_measurement_document(
    root: Path,
    *,
    top_n: int = 3,
    routing_profile: str = "track_a_promoted",
    log_path: Path = DEFAULT_LOG,
) -> dict[str, Any]:
    build_row = _time_resume_pack_build(root, lane=None)
    token_row = _token_bench_snapshot(root, top_n=top_n)
    pilot_row = _tp01_pilot_snapshot(root, top_n=top_n, routing_profile=routing_profile)
    log_rows = _load_log_rows(log_path)
    ok = bool(build_row.get("ok") and token_row.get("ok") and pilot_row.get("pilot_ok"))
    return {
        "schema": "a2a_tp01_ops_measurement_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "classification": "INTERNAL_ONLY",
        "target_point_id": "tp01_cursor_ops_resume_handoff",
        "measurement_ok": ok,
        "boundary_ack": (
            "[HYPO] tp01 ops measurement — resume pack build latency + inject token footprint + "
            "A2A compress pilot. Not Track A SLA. Human resume MD unchanged."
        ),
        "a2a_target_points_ssot": "docs/final/artifacts/a2a_target_points_v1_latest.json",
        "resume_pack_build": build_row,
        "token_bench": token_row,
        "tp01_pilot": pilot_row,
        "longitudinal_log": {
            "path": _log_path_display(root, log_path),
            "summary": _longitudinal_summary(log_rows),
        },
        "raw_vs_operational": {
            "raw": {
                "inject_off_tokens": token_row.get("inject_off_tokens"),
                "label": "essence+must_keep_tags (no repair guard)",
            },
            "operational_note": "tp01 compress uses v2 stub only; repair_v2 not applied on wire handoff",
        },
        "evidence_paths": [
            "scripts/build_a2a_tp01_ops_measurement_v1.py",
            "scripts/build_mkm_chat_resume_pack_v1.py",
            "scripts/bench_mkm_ops_memory_index_token_savings_v1.py",
            "scripts/build_mkm_chat_resume_a2a_pilot_v1.py",
        ],
    }


def _append_log_row(log_path: Path, doc: dict[str, Any]) -> None:
    row = {
        "schema": "a2a_tp01_ops_measurement_log_v1",
        "measured_at_utc": doc.get("generated_at_utc"),
        "resume_pack_build_ms": (doc.get("resume_pack_build") or {}).get("elapsed_ms"),
        "inject_off_tokens": (doc.get("token_bench") or {}).get("inject_off_tokens"),
        "tp01_savings_ratio": (doc.get("tp01_pilot") or {}).get("savings_ratio"),
        "measurement_ok": doc.get("measurement_ok"),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument("--routing-profile", default="track_a_promoted")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    doc = build_measurement_document(
        root,
        top_n=max(1, args.top_n),
        routing_profile=args.routing_profile,
        log_path=args.log,
    )
    if args.append_log:
        _append_log_row(args.log, doc)
        doc["longitudinal_log"]["summary"] = _longitudinal_summary(_load_log_rows(args.log))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"measurement_ok={doc.get('measurement_ok')} "
        f"build_ms={(doc.get('resume_pack_build') or {}).get('elapsed_ms')} "
        f"inject_tokens={(doc.get('token_bench') or {}).get('inject_off_tokens')} "
        f"tp01_savings={(doc.get('tp01_pilot') or {}).get('savings_ratio')}"
    )
    if args.strict_exit and not doc.get("measurement_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
