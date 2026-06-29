#!/usr/bin/env python3
"""Seed or update web_ops_regime pointer baselines from gate/CDP probe artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINES = ROOT / "reports/web_ops_regime_pointer_baselines_v1.json"
DEFAULT_GATE = ROOT / "reports/web_ops_regime_gate_v1_latest.json"
DEFAULT_CDP = ROOT / "reports/web_ops_regime_cdp_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _probe_key(probe: dict[str, Any]) -> str:
    portal = str(probe.get("portal") or "unknown")
    probe_id = str(probe.get("probe_id") or "unknown")
    return f"{portal}:{probe_id}"


def _collect_probes(gate_doc: dict[str, Any], cdp_doc: dict[str, Any]) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in gate_doc.get("probes") or []:
        if isinstance(item, dict) and item.get("probe_id"):
            key = _probe_key(item)
            if key not in seen:
                seen.add(key)
                probes.append(item)
    cdp_probe = cdp_doc.get("probe")
    if isinstance(cdp_probe, dict) and cdp_probe.get("probe_id"):
        key = _probe_key(cdp_probe)
        if key not in seen:
            probes.append(cdp_probe)
    return probes


def sync_baselines(
    *,
    probes: list[dict[str, Any]],
    existing: dict[str, Any],
    seed: bool,
    update_if_pass: bool,
) -> tuple[dict[str, Any], list[str]]:
    baselines = dict(existing)
    notes: list[str] = []
    for probe in probes:
        key = _probe_key(probe)
        fp = str(probe.get("page_fingerprint") or "")
        if not fp:
            notes.append(f"skip_no_fingerprint:{key}")
            continue
        final_action = str(probe.get("final_action") or "")
        allow_update = seed or (update_if_pass and final_action in {"ALLOW_READ", "ALLOW_PREFILL"})
        if not allow_update and key not in baselines:
            notes.append(f"skip_no_seed:{key}")
            continue
        if key in baselines and not allow_update:
            notes.append(f"keep_existing:{key}")
            continue
        baselines[key] = {
            "page_fingerprint": fp,
            "probe_id": probe.get("probe_id"),
            "portal": probe.get("portal"),
            "url": (probe.get("raw") or {}).get("url"),
            "final_action": final_action,
            "updated_at_utc": _utc(),
        }
        notes.append(f"updated:{key}")
    return baselines, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--cdp-json", type=Path, default=DEFAULT_CDP)
    ap.add_argument("--out", type=Path, default=DEFAULT_BASELINES)
    ap.add_argument("--seed", action="store_true", help="Overwrite baselines from current probes")
    ap.add_argument("--update-if-pass", action="store_true", default=True)
    ap.add_argument("--no-update-if-pass", dest="update_if_pass", action="store_false")
    args = ap.parse_args()

    existing_doc = _read_json(args.out)
    existing_rows = existing_doc.get("baselines") if isinstance(existing_doc.get("baselines"), dict) else existing_doc
    if not isinstance(existing_rows, dict):
        existing_rows = {}

    probes = _collect_probes(_read_json(args.gate_json), _read_json(args.cdp_json))
    if not probes:
        print(json.dumps({"ok": False, "error": "no_probes"}, ensure_ascii=False))
        return 2

    baselines, notes = sync_baselines(
        probes=probes,
        existing=existing_rows,
        seed=args.seed,
        update_if_pass=args.update_if_pass,
    )
    doc = {
        "schema": "web_ops_regime_pointer_baselines_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "baselines": baselines,
        "sync_notes": notes,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.out), "baseline_count": len(baselines), "notes": notes},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
