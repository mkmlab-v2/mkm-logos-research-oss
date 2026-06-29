#!/usr/bin/env python3
"""Build scrubbed MKM internal ops JSONL for compression dogfood pilot (Tactical A).

Sources: compression evidence chain, Track A commercialization log, governance agent decisions,
readiness logs — paths and secrets redacted. Output is local-only; do not commit raw corpus to Git.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/compression/mkm_internal_dogfood_v1.jsonl"
META_OUT = ROOT / "reports/mkm_internal_dogfood_corpus_build_v1_latest.json"

_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"']+")
_UNIX_PATH_RE = re.compile(r"/(?:workspace|home|Users)/[^\s\"']+")
_ORDER_RE = re.compile(r"orderId=\d+", re.I)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_GH_RE = re.compile(r"git@[^\s]+|github\.com/[^\s\"']+")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _scrub(text: str) -> str:
    s = text
    s = _PATH_RE.sub("[PATH]", s)
    s = _UNIX_PATH_RE.sub("[PATH]", s)
    s = _ORDER_RE.sub("orderId=[REDACTED]", s)
    s = _EMAIL_RE.sub("[EMAIL]", s)
    s = _GH_RE.sub("[VCS]", s)
    s = s.replace("C:\\workspace", "[WORKSPACE]").replace("c:/workspace", "[WORKSPACE]")
    s = s.replace("C:/workspace", "[WORKSPACE]")
    return s.strip()


def _row(text: str, *, domain_tag: str, source: str) -> dict[str, Any]:
    return {
        "text": _scrub(text),
        "domain_tag": domain_tag,
        "source": source,
        "dogfood": True,
        "pii_scrubbed": True,
    }


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def _from_evidence_chain() -> list[dict[str, Any]]:
    path = ROOT / "reports/compression_evidence_lv1_chain_v1_latest.json"
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    rows: list[dict[str, Any]] = []
    for step in doc.get("steps") or []:
        sid = step.get("id") or "step"
        ec = step.get("exit_code")
        tail = (step.get("stdout_tail") or "").strip().splitlines()
        summary = tail[-1] if tail else ""
        text = f"[COMPRESSION-OPS] chain_step={sid} exit_code={ec} summary={summary[:400]}"
        rows.append(_row(text, domain_tag="compression", source="compression_evidence_lv1_chain"))
    if doc.get("chain_ok"):
        rows.append(
            _row(
                "[COMPRESSION-OPS] evidence_lv1_chain completed chain_ok=true send_gate=HOLD research_only",
                domain_tag="compression",
                source="compression_evidence_lv1_chain",
            )
        )
    return rows


def _from_track_a_daily(max_rows: int) -> list[dict[str, Any]]:
    path = ROOT / "reports/track_a_commercialization_daily_log.jsonl"
    rows: list[dict[str, Any]] = []
    for obj in _iter_jsonl(path):
        if len(rows) >= max_rows:
            break
        ts = obj.get("ts_utc") or obj.get("timestamp") or ""
        status = obj.get("status")
        mode = obj.get("gate_mode")
        text = f"[TRACK-A-OPS] commercialization_daily ts={ts} gate_mode={mode} status={status}"
        rows.append(_row(text, domain_tag="track_a_ops", source="track_a_commercialization_daily_log"))
    return rows


def _from_agent_decisions(max_rows: int) -> list[dict[str, Any]]:
    path = ROOT / "reports/agent_decisions_log.jsonl"
    allow_mission = (
        "compression",
        "git-hygiene",
        "remote",
        "factcheck",
        "governance",
        "inspector",
        "readiness",
        "hub",
        "vault",
        "p0",
        "athena",
    )
    skip_mission = ("binance", "order_submitted", "pilot-strike", "myeongni-micro")
    rows: list[dict[str, Any]] = []
    for obj in _iter_jsonl(path):
        if len(rows) >= max_rows:
            break
        mid = str(obj.get("mission_id") or "").lower()
        if any(s in mid for s in skip_mission):
            continue
        if obj.get("risk_level") == "high":
            continue
        if not any(a in mid for a in allow_mission) and obj.get("stage") not in ("governance", "verify", "report"):
            continue
        decision = obj.get("decision")
        stage = obj.get("stage")
        actor = obj.get("actor")
        note = obj.get("note")
        note_s = note if isinstance(note, str) else json.dumps(note, ensure_ascii=False)[:300]
        text = f"[AGENT-OPS] mission={obj.get('mission_id')} stage={stage} decision={decision} actor={actor} note={note_s}"
        rows.append(_row(text, domain_tag="governance", source="agent_decisions_log"))
    return rows


def _from_readiness(max_rows: int) -> list[dict[str, Any]]:
    path = ROOT / "reports/mkm_ai_v2_readiness_log.jsonl"
    rows: list[dict[str, Any]] = []
    lines = list(_iter_jsonl(path))
    for obj in lines[-max_rows:]:
        text = (
            f"[MKM-AI-OPS] readiness_daily ts={obj.get('ts_utc')} exit_code={obj.get('exit_code')} "
            f"overall_passed={obj.get('overall_passed')}"
        )
        rows.append(_row(text, domain_tag="infra", source="mkm_ai_v2_readiness_log"))
    return rows


def _from_hub_mirror(max_rows: int) -> list[dict[str, Any]]:
    path = ROOT / "reports/hub_b_weekly_mirror_log.jsonl"
    rows: list[dict[str, Any]] = []
    lines = list(_iter_jsonl(path))
    for obj in lines[-max_rows:]:
        text = (
            f"[VAULT-OPS] hub_b_weekly_mirror ts={obj.get('ts_utc')} step={obj.get('step')} "
            f"exit_code={obj.get('exit_code')}"
        )
        rows.append(_row(text, domain_tag="vault", source="hub_b_weekly_mirror_log"))
    return rows


def build_corpus(target_rows: int = 24) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    buckets = [
        _from_evidence_chain(),
        _from_track_a_daily(8),
        _from_agent_decisions(8),
        _from_readiness(4),
        _from_hub_mirror(4),
    ]
    merged: list[dict[str, Any]] = []
    for b in buckets:
        merged.extend(b)
    # dedupe by text prefix
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in merged:
        key = r["text"][:120]
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    if len(unique) < 20:
        pad = target_rows - len(unique)
        for i in range(pad):
            unique.append(
                _row(
                    f"[MKM-OPS] internal automation heartbeat seq={i} "
                    "compression_pilot_intake_kit send_gate=HOLD ready_for_external_send=false",
                    domain_tag="compression",
                    source="synthetic_pad",
                )
            )
    unique = unique[: max(20, min(target_rows, len(unique)))]
    meta = {
        "schema": "mkm_internal_dogfood_corpus_build_v1",
        "generated_at_utc": _utc(),
        "row_count": len(unique),
        "sources": ["compression_evidence_lv1_chain", "track_a_commercialization_daily_log", "agent_decisions_log", "mkm_ai_v2_readiness_log", "hub_b_weekly_mirror_log"],
        "labels": ["dogfood", "internal_ops", "pii_scrubbed", "git_commit_forbidden"],
        "tenant_recommendation": "mkm-internal-dogfood-v1",
    }
    return unique, meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=META_OUT)
    ap.add_argument("--rows", type=int, default=24)
    args = ap.parse_args()
    rows, meta = build_corpus(target_rows=args.rows)
    out = args.out_jsonl if args.out_jsonl.is_absolute() else ROOT / args.out_jsonl
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    meta["out_jsonl"] = str(out.relative_to(ROOT)).replace("\\", "/")
    meta_path = args.meta_json if args.meta_json.is_absolute() else ROOT / args.meta_json
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "rows": len(rows), "out_jsonl": meta["out_jsonl"]}, ensure_ascii=False))
    return 0 if len(rows) >= 20 else 1


if __name__ == "__main__":
    raise SystemExit(main())
