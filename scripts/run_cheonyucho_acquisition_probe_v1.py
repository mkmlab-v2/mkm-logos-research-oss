#!/usr/bin/env python3
"""Run cheonyucho P1 acquisition probes (disk + optional NL via nlm)."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_run_v1.json"
NL_OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_park1985_nl_probe_v1.json"
P344_MANIFEST = ROOT / "data/corpus/ijeoma/_inventory/cheonyucho_p344_partial_ingest_v1.json"
NB = "e6c1f050-40ef-49f0-8b2c-c509b8570cf4"

SEARCH_ROOTS = [
    ROOT / "data/corpus/ijeoma",
    ROOT / "docs/research",
    Path("G:/공유 드라이브/MKM_DATA_VAULT/notebooklm_sources/이제마_B_Track"),
    Path("G:/공유 드라이브/MKM_DATA_VAULT/data/corpus/ijeoma"),
    Path("F:/BACKUP/MKM_ARCHIVE_FROM_F/workspace_sync_from_C/ijeoma_2026-06-24"),
    Path("E:/mkm-data-workspace/ijeoma_original_text"),
]
NAME_TERMS = ("동무격치고", "박석언", "格致藁", "闡幽", "천유초", "geukchigo")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def disk_scan() -> list[dict]:
    hits: list[dict] = []
    for base in SEARCH_ROOTS:
        if not base.is_dir():
            continue
        try:
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                if len(p.relative_to(base).parts) > 8:
                    continue
                if any(t in p.name for t in NAME_TERMS):
                    hits.append({"path": str(p), "size": p.stat().st_size})
                    if len(hits) >= 40:
                        return hits
        except OSError:
            continue
    return hits


def nl_probe() -> dict | None:
    if not NL_OUT.is_file():
        q = (
            "박석언 역주 동무격치고 1985 태양사판에 천유초(闡幽抄) 또는 유고초(遺稿抄)가 "
            "수록·색인되는지 — 업로드 소스만 근거로 yes/no/unknown."
        )
        cmd = ["nlm", "notebook", "query", NB, q]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            return {"ok": False, "error": (proc.stderr or proc.stdout)[-400:]}
        NL_OUT.write_text(proc.stdout, encoding="utf-8")
    try:
        raw = NL_OUT.read_text(encoding="utf-8-sig")
        payload = json.loads(raw)
        val = payload.get("value", payload)
        return {
            "ok": True,
            "answer": val.get("answer", "")[:1200],
            "sources_used": val.get("sources_used", [])[:8],
        }
    except (json.JSONDecodeError, OSError) as e:
        return {"ok": False, "error": str(e)}


def main() -> int:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    disk = disk_scan()
    nl = nl_probe()

    # update checklist statuses from automation
    for item in probe.get("checklist", []):
        if item["id"] == "P1-01":
            if disk:
                item["status"] = "partial_disk_hit"
                item["artifact"] = disk[0]["path"]
                item["note"] = f"{len(disk)} filename hits; not 1985 book scan"
            elif nl and nl.get("ok"):
                item["status"] = "nl_briefing_only"
                item["artifact"] = str(NL_OUT)
            else:
                item["status"] = "pending_physical_book"
        if item["id"] == "P1-02":
            item["status"] = "pending_reading_room"
            item["urls"] = [
                "https://jsg.aks.ac.kr/dir/view?dataId=JSG_K3-328",
                "https://jsg.aks.ac.kr/",
            ]
            item["grep_terms"] = ["格致藁", "闡幽抄", "遺稿抄", "격치고", "천유초"]
        if item["id"] == "P1-03":
            item["status"] = "pending_nlk_opac"
            item["urls"] = [
                "https://www.nl.go.kr/",
                "https://www.nl.go.kr/NL/contents/search.do",
            ]
            item["grep_terms"] = ["闡幽抄", "천유초", "格致藁", "이제마"]
            item["note"] = "openApi requires key; use OPAC UI"
        if item["id"] == "P1-06" and P344_MANIFEST.is_file():
            item["status"] = "partial_p344_user_paste"
            item["artifact"] = str(P344_MANIFEST.relative_to(ROOT)).replace("\\", "/")
            item["note"] = "PARTIAL_INGEST; 抄 in paste — physical_verified false until scan"

    probe["updated_at_utc"] = _utc()
    probe["last_run"] = {
        "script": "scripts/run_cheonyucho_acquisition_probe_v1.py",
        "disk_hits": disk,
        "nl_probe": nl,
        "park1985_biblio": {
            "title": "동무격치고",
            "editor": "박석언 역주",
            "publisher": "태양사",
            "year": 1985,
            "workspace_copy": "not_found",
            "encykorea_lists_edition": True,
            "cheonyucho_in_edition": "unverified_until_physical_index",
        },
    }
    PROBE.write_text(json.dumps(probe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    out = {
        "schema": "cheonyucho_acquisition_probe_run_v1",
        "generated_at_utc": _utc(),
        "disk_hit_count": len(disk),
        "disk_hits": disk[:15],
        "nl_probe": nl,
        "probe_ssot": str(PROBE.relative_to(ROOT)).replace("\\", "/"),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"disk_hits": len(disk), "nl_ok": bool(nl and nl.get("ok"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
