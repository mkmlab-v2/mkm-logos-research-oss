#!/usr/bin/env python3
"""Bridge WTT session JSONL -> compression stateless PoC corpus rows [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data/wtt/intake/wtt-customer-live-v1.jsonl"
DEFAULT_OUT = ROOT / "data/compression/examples/wtt_premium_cs_compression_bridge_v1.jsonl"
DEFAULT_META = ROOT / "reports/wtt_compression_bridge_export_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def export_sessions(jsonl_path: Path, *, tenant_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        session = json.loads(line)
        parts: list[str] = []
        for turn in session.get("turns") or []:
            role = str(turn.get("role", "user"))
            parts.append(f"[{role}] {turn.get('text', '')}")
        rows.append(
            {
                "id": str(session.get("session_id")),
                "text": " ".join(parts),
                "domain_tag": session.get("domain_tag") or "customer-support-chat",
                "labels": list(session.get("labels") or []) + ["wtt_bridge_export"],
                "customer_provided": bool(session.get("customer_provided")),
                "wtt_session_id": session.get("session_id"),
                "tenant_id": tenant_id,
                "source": "export_wtt_sessions_to_compression_corpus_v1",
                "send_gate": "HOLD",
                "ready_for_external_send": False,
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-out", type=Path, default=DEFAULT_META)
    ap.add_argument("--tenant-id", default="wtt-customer-live-v1")
    args = ap.parse_args()

    src = args.jsonl.resolve()
    if not src.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {src}"}))
        return 1

    rows = export_sessions(src, tenant_id=args.tenant_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    meta = {
        "schema": "wtt_compression_bridge_export_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "wtt_jsonl": _rel(src),
        "compression_jsonl": _rel(args.out),
        "row_count": len(rows),
        "tenant_id": args.tenant_id,
        "note_ko": "WTT≠compression 격벽 브리지 — ROI proxy만; SEND·대외 SLA 주장 금지",
    }
    args.meta_out.parent.mkdir(parents=True, exist_ok=True)
    args.meta_out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
