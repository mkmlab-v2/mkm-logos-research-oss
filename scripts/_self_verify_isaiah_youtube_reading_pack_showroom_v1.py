#!/usr/bin/env python3
"""Self-verify Isaiah YouTube reading pack showroom chain (exit 0 = pass)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"


def main() -> int:
    checks: list[tuple[str, bool]] = []

    subprocess.run(
        [sys.executable, "scripts/build_showroom_logos_isaiah_youtube_reading_pack_slice_v1.py"],
        cwd=str(ROOT),
        check=True,
    )
    subprocess.run(
        [sys.executable, "scripts/build_public_showroom_logos_isaiah_youtube_reading_pack_html_v1.py"],
        cwd=str(ROOT),
        check=True,
    )

    slice_path = ROOT / "docs/final/artifacts/showroom_logos_isaiah_youtube_reading_pack_slice_v1_latest.json"
    mvp_slice = MVP / "showroom_logos_isaiah_youtube_reading_pack_slice_v1.json"
    html_path = MVP / "public_showroom_logos_isaiah_youtube_reading_pack_v1.html"

    checks.append(("artifact_slice", slice_path.is_file()))
    checks.append(("mvp_slice", mvp_slice.is_file()))
    checks.append(("mvp_html", html_path.is_file()))

    doc = json.loads(slice_path.read_text(encoding="utf-8"))
    checks.append(("stages_16", len(doc.get("narrative_route_public") or []) == 16))
    checks.append(("packs_3", len(doc.get("reading_packs") or []) == 3))
    checks.append(("bridge_ok", doc.get("export_gate", {}).get("bridge_map_ok") is True))

    html = html_path.read_text(encoding="utf-8")
    checks.append(("html_slice_url", "showroom_logos_isaiah_youtube_reading_pack_slice_v1.json" in html))
    checks.append(("html_studio_link", "isaiah_youtube_spine_v1" in html))

    presets_path = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
    if presets_path.is_file():
        presets = json.loads(presets_path.read_text(encoding="utf-8-sig"))
        ids = {p.get("id") for p in presets.get("presets") or []}
        checks.append(("preset_spine", "isaiah_youtube_spine_v1" in ids))
        checks.append(("preset_ch09", "isaiah_yt_ch09" in ids))

    failed = [name for name, ok in checks if not ok]
    report = {
        "schema": "isaiah_youtube_reading_pack_self_verify_v1",
        "ok": len(failed) == 0,
        "checks": [{"name": n, "ok": ok} for n, ok in checks],
        "failed": failed,
        "reproduce": "py scripts/_self_verify_isaiah_youtube_reading_pack_showroom_v1.py",
    }
    out = ROOT / "reports/isaiah_youtube_reading_pack_self_verify_v1_latest.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
