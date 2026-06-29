#!/usr/bin/env python3
"""Generate mkmlife magic-orb query presets TS from fixture + manifest SSOT."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
MANIFEST = ROOT / "docs/final/fixtures/magic_orb_query_presets_manifest_v1.json"
OUT_TS = ROOT / "projects/mkm/mkm-life/lib/magic-orb-query-presets-v1.ts"
SYNC = ROOT / "scripts/sync_magic_orb_public_queries_from_fixture_v1.py"

TS_HEADER = """/** B-track oracle-sphere query presets — generated; do not hand-edit. */
/* eslint-disable */
/* prettier-ignore */
// SSOT: docs/final/fixtures/magic_orb_query_presets_manifest_v1.json
// regen: py scripts/build_magic_orb_query_presets_from_fixture_v1.py
"""


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _query_by_id(fixture: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in fixture.get("items") or []:
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def build_presets(fixture: dict, manifest: dict) -> tuple[list[dict], list[str]]:
    by_id = _query_by_id(fixture)
    default_shadow = str(
        manifest.get("default_shadow_lane_showroom_url")
        or "https://api.jemaai.cloud/public_showroom_research_shadow_lane_v3.html"
    )
    presets: list[dict] = []
    immersive_ids: list[str] = []
    for row in manifest.get("items") or []:
        if not isinstance(row, dict):
            continue
        qid = str(row.get("query_id") or "").strip()
        if not qid:
            continue
        fq = by_id.get(qid)
        if not fq:
            raise SystemExit(f"manifest query_id not in fixture: {qid}")
        qhash = str(fq.get("query_key_hint") or "").strip()
        if not qhash:
            raise SystemExit(f"fixture missing query_key_hint for {qid}")
        preset = {
            "id": qid,
            "query_ko": str(fq["query_ko"]),
            "query_key_hash": qhash,
            "insight_by_query_url": f"/data/magic_orb_insight_by_query/{qhash}.json",
            "shadow_lane_showroom_url": str(row.get("shadow_lane_showroom_url") or default_shadow),
            "auto_reveal": bool(row.get("auto_reveal", False)),
            "hypothesis_tier": "B",
            "non_gating": True,
        }
        presets.append(preset)
        if row.get("immersive_gold"):
            immersive_ids.append(qid)
    return presets, immersive_ids


def _ts_preset_object(p: dict) -> str:
    lines = [
        "  {",
        f"    id: {json.dumps(p['id'])},",
        f"    query_ko: {json.dumps(p['query_ko'], ensure_ascii=False)},",
        f"    query_key_hash: {json.dumps(p['query_key_hash'])},",
        f"    insight_by_query_url: {json.dumps(p['insight_by_query_url'])},",
        f"    shadow_lane_showroom_url: {json.dumps(p['shadow_lane_showroom_url'])},",
        f"    auto_reveal: {'true' if p['auto_reveal'] else 'false'},",
        "    hypothesis_tier: 'B',",
        "    non_gating: true,",
        "  } satisfies MagicOrbQueryPreset,",
    ]
    return "\n".join(lines)


def render_ts(presets: list[dict], immersive_ids: list[str]) -> str:
    const_lines: list[str] = []
    preset_entries: list[str] = []
    for p in presets:
        const_name = p["id"].upper()
        const_lines.append(f"export const {const_name}_ID = {json.dumps(p['id'])} as const")
        const_lines.append(
            f"export const {const_name}_QUERY_HASH = {json.dumps(p['query_key_hash'])} as const"
        )
        preset_entries.append(f"  [{json.dumps(p['id'])}]: {_ts_preset_object(p)}")

    immersive_json = json.dumps(immersive_ids, ensure_ascii=False)
    body = f"""{TS_HEADER}
{chr(10).join(const_lines)}

export type MagicOrbQueryPreset = {{
  id: string
  query_ko: string
  query_key_hash: string
  insight_by_query_url: string
  shadow_lane_showroom_url: string
  auto_reveal: boolean
  hypothesis_tier: 'B'
  non_gating: true
}}

const PRESETS: Record<string, MagicOrbQueryPreset> = {{
{chr(10).join(preset_entries)}
}}

/** Preset ids flagged immersive_gold in manifest (append to gold showroom ids in UI). */
export const PRESET_IMMERSIVE_QUERY_IDS = {immersive_json} as const

export function resolveMagicOrbQueryPreset(
  raw: string | null | undefined
): MagicOrbQueryPreset | null {{
  const id = (raw ?? '').trim()
  if (!id) return null
  return PRESETS[id] ?? null
}}

export function insightUrlForPreset(preset: MagicOrbQueryPreset | null): string | null {{
  return preset?.insight_by_query_url ?? null
}}

export function listMagicOrbQueryPresets(): MagicOrbQueryPreset[] {{
  return Object.values(PRESETS)
}}
"""
    return body


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=FIXTURE)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--out-ts", type=Path, default=OUT_TS)
    ap.add_argument("--skip-sync-public", action="store_true")
    args = ap.parse_args()

    fixture = _load(args.fixture)
    manifest = _load(args.manifest)
    presets, immersive_ids = build_presets(fixture, manifest)
    if not presets:
        raise SystemExit("manifest produced zero presets")

    args.out_ts.write_text(render_ts(presets, immersive_ids), encoding="utf-8")
    summary = {
        "ok": True,
        "out_ts": str(args.out_ts),
        "preset_count": len(presets),
        "preset_ids": [p["id"] for p in presets],
        "immersive_ids": immersive_ids,
    }
    print(json.dumps(summary, ensure_ascii=False))

    if not args.skip_sync_public:
        import subprocess
        import sys

        rc = subprocess.call([sys.executable, str(SYNC)], cwd=str(ROOT))
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
