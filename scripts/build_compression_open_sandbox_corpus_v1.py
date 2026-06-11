#!/usr/bin/env python3
"""Build virtual open-sandbox tenant JSONL from public-safe golden40 stub (1-person R&D)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
FALLBACK_SOURCE = (
    ROOT / "exports/a-codeai-public-reproduce-v2/data/compression/stateless_poc_golden40_public_safe_v1.jsonl"
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_source(explicit: Path | None) -> Path:
    if explicit is not None:
        p = (ROOT / explicit).resolve() if not explicit.is_absolute() else explicit.resolve()
        if not p.is_file():
            raise FileNotFoundError(f"missing source corpus: {p}")
        return p
    if DEFAULT_SOURCE.is_file():
        return DEFAULT_SOURCE
    if FALLBACK_SOURCE.is_file():
        return FALLBACK_SOURCE
    raise FileNotFoundError("no golden40 public-safe corpus; copy or build golden40 first")


def build_corpus(
    tenant_id: str,
    *,
    source: Path,
    max_cases: int,
    out_path: Path | None = None,
) -> Path:
    out = out_path or (ROOT / f"data/compression/stateless_poc_open_sandbox_{tenant_id}_v1.jsonl")
    if not out.is_absolute():
        out = (ROOT / out).resolve()
    lines: list[str] = []
    for i, line in enumerate(source.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or i >= max_cases:
            break
        obj = json.loads(line)
        obj["id"] = f"sandbox-{tenant_id}-{i:03d}"
        obj["tenant_id"] = tenant_id
        obj["source"] = f"open_sandbox_stub_from_{source.stem}"
        obj["virtual_tenant"] = True
        obj["public_safe"] = True
        obj["forbidden_as_customer_sla"] = True
        obj["research_only"] = True
        obj["solo_self_audit_only"] = True
        lines.append(json.dumps(obj, ensure_ascii=False))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", default="open-sandbox-01")
    ap.add_argument("--source-jsonl", type=Path, default=None)
    ap.add_argument("--max-cases", type=int, default=40)
    ap.add_argument("--out-jsonl", type=Path, default=None)
    args = ap.parse_args()
    source = _resolve_source(args.source_jsonl)
    out = build_corpus(
        args.tenant_id,
        source=source,
        max_cases=args.max_cases,
        out_path=args.out_jsonl,
    )
    meta = {
        "ok": True,
        "tenant_id": args.tenant_id,
        "source": source.relative_to(ROOT).as_posix(),
        "output": out.relative_to(ROOT).as_posix(),
        "case_count": len(out.read_text(encoding="utf-8").splitlines()),
        "generated_at_utc": _utc(),
        "labels": ["virtual_sandbox_stub", "solo_self_audit_only", "research_only"],
    }
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
