#!/usr/bin/env python3
"""Triage legacy MKM_CORE_INTELLIGENCE_V1 notebook vs new 3-lane business NL corpus.

Probes Google via `nlm notebook get`, compares against MKM_CORE_FACT keep-set,
writes reports/notebooklm_legacy_core_intelligence_triage_v1_latest.json.

SSOT: docs/final/notebooklm_nl_notebook_uuid_registry_v1.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/final/notebooklm_nl_notebook_uuid_registry_v1.json"
CORE_FACT_PACK_INDEX = ROOT / "reports/notebooklm_core_fact_sync_pack_v1/index.json"
OUT = ROOT / "reports/notebooklm_legacy_core_intelligence_triage_v1_latest.json"

LEGACY_KEY = "MKM_CORE_INTELLIGENCE_V1_LEGACY"
CORE_FACT_KEY = "MKM_CORE_FACT"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _nlm_get(notebook_uuid: str) -> dict:
    proc = subprocess.run(
        ["nlm", "notebook", "get", notebook_uuid, "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
        errors="replace",
    )
    raw = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    if not raw:
        return {"status": "error", "error": "empty nlm output", "exit_code": proc.returncode}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        return {"status": "error", "error": f"json parse: {exc}", "raw_head": raw[:500]}


def _keep_titles() -> list[str]:
    if CORE_FACT_PACK_INDEX.is_file():
        idx = json.loads(CORE_FACT_PACK_INDEX.read_text(encoding="utf-8"))
        files = idx.get("files") or idx.get("pack_files") or []
        return sorted(
            {
                (f.get("dest_name") or f.get("filename") or Path(f.get("source", "")).name)
                for f in files
                if isinstance(f, dict)
            }
        )
    pack_dir = ROOT / "reports/notebooklm_core_fact_sync_pack_v1"
    if pack_dir.is_dir():
        return sorted(p.name for p in pack_dir.iterdir() if p.is_file())
    return []


def _classify_sources(sources: list[dict], keep: set[str]) -> dict:
    on_lane: list[str] = []
    off_lane: list[str] = []
    for s in sources:
        title = (s.get("title") or "").strip()
        if not title:
            continue
        if title in keep or any(title.endswith(k) for k in keep):
            on_lane.append(title)
        else:
            off_lane.append(title)
    return {
        "on_lane_count": len(on_lane),
        "off_lane_count": len(off_lane),
        "on_lane_titles_sample": on_lane[:20],
        "off_lane_titles_sample": off_lane[:40],
        "migrate_hint": {
            "myeongni_logos_sasang": "LENS_MYEONGNI / Fusion Hub 71f55a03",
            "trackc_biz": "TRACKC_BIZ notebook or 00_OPS pack",
            "clinical": "20_CLINICIAN_PHYSICIAN_GOLD f9503fe6",
            "consumer": "21_MKMLIFE_CONSUMER_SURVEY 45cfd207",
            "compression_btrack": "Vault via push_lens_packs_to_vault_v1.py (no NL notebook yet)",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--what-if", action="store_true", help="Probe only; no deletes")
    args = parser.parse_args()

    reg = _load_registry()
    legacy = reg["notebooks"][LEGACY_KEY]
    core = reg["notebooks"][CORE_FACT_KEY]
    legacy_uuid = legacy["uuid"]
    core_uuid = core["uuid"]

    keep_titles = _keep_titles()
    keep_set = set(keep_titles)

    legacy_probe = _nlm_get(legacy_uuid)
    core_probe = _nlm_get(core_uuid)

    legacy_status = "unknown"
    legacy_sources: list[dict] = []
    if legacy_probe.get("status") == "error":
        err = str(legacy_probe.get("error", ""))
        legacy_status = "NOT_FOUND" if "NOT_FOUND" in err else "error"
    else:
        val = legacy_probe.get("value") or legacy_probe
        legacy_status = "exists"
        legacy_sources = val.get("sources") or []

    core_val = (core_probe.get("value") or core_probe) if core_probe.get("status") != "error" else {}
    core_source_count = core_val.get("source_count")
    if core_source_count is None and core_val.get("sources"):
        core_source_count = len(core_val["sources"])

    classification = (
        _classify_sources(legacy_sources, keep_set)
        if legacy_sources
        else {"note": "legacy notebook not reachable; no source list to classify"}
    )

    doc = {
        "schema": "notebooklm_legacy_core_intelligence_triage_v1",
        "generated_at_utc": _utc(),
        "what_if": args.what_if,
        "legacy": {
            "key": LEGACY_KEY,
            "uuid": legacy_uuid,
            "google_status": legacy_status,
            "superseded_by": core["name"],
            "superseded_uuid": core_uuid,
        },
        "mkm_core_fact": {
            "uuid": core_uuid,
            "name": core["name"],
            "source_count": core_source_count,
            "keep_set_count": len(keep_set),
            "push_script": core.get("push_script"),
        },
        "business_lanes_2026q2": {
            "physician_gold": reg["notebooks"]["PHYSICIAN_GOLD"],
            "consumer_survey": reg["notebooks"]["CONSUMER_SURVEY"],
            "mkm_core_fact": {"uuid": core_uuid, "name": core["name"]},
        },
        "compression_btrack_nl": {
            **reg["notebooks"]["COMPRESSION_BTRACK"],
            "note": "Dedicated 23_COMPRESSION_BTRACK lane; do not push to MKM_CORE_FACT.",
        },
        "legacy_source_classification": classification,
        "actions_taken": [],
        "recommended_actions": [],
    }

    if legacy_status == "NOT_FOUND":
        doc["recommended_actions"] = [
            "Update push maps: MKM_CORE_FACT -> 9cd23971 (done in registry + template).",
            "Do not push COMPRESSION_BTRACK to MKM_CORE_FACT; use vault fallback until dedicated notebook.",
            "Point NOTEBOOKLM_LOG_METABOLISM_CORE_BRIDGE_POINTER to 22_ACODEAI MKM_CORE_FACT if still needed.",
            "Refresh notebooklm_archive_migration_plan_v1_latest.json business_lanes block.",
        ]
    elif classification.get("off_lane_count", 0) > 0:
        doc["recommended_actions"] = [
            "Migrate off-lane titles to LENS_MYEONGNI / TRACKC_BIZ / physician / consumer notebooks.",
            "Prune legacy after migration; keep MKM_CORE_FACT slim pack only on 22_ACODEAI notebook.",
        ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT.relative_to(ROOT)), "legacy_status": legacy_status, "core_sources": core_source_count}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
