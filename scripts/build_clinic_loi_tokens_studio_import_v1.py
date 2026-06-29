#!/usr/bin/env python3
"""Build Tokens Studio plugin-ready JSON (value/type) for paste-import."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DTCG = ROOT / "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json"
MAP = ROOT / "docs/final/artifacts/clinic_loi_figma_token_map_v1.json"
OUT_DIR = ROOT / "reports/clinic_loi_tokens_studio_import_v1"
MANIFEST = OUT_DIR / "clinic_loi_tokens_studio_import_manifest_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dtcg_to_studio(node: Any, set_prefix: str) -> Any:
    if isinstance(node, dict):
        if "$value" in node and "$type" in node:
            val = node["$value"]
            if isinstance(val, str) and val.startswith("{") and val.endswith("}"):
                inner = val[1:-1]
                val = "{" + f"{set_prefix}.{inner}" + "}"
            out: dict[str, Any] = {"value": val, "type": node["$type"]}
            if "$description" in node:
                out["description"] = node["$description"]
            return out
        return {k: _dtcg_to_studio(v, set_prefix) for k, v in node.items()}
    return node


def _flat_from_map(map_doc: dict) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for row in map_doc.get("variables") or []:
        name = str(row.get("figma_name", ""))
        value = row.get("value")
        if not name or value is None:
            continue
        parts = name.split("/")
        cur = tree
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        leaf_type = "color" if str(value).startswith("#") else "dimension"
        cur[parts[-1]] = {"value": value, "type": leaf_type}
    return tree


def main() -> int:
    dtcg = json.loads(DTCG.read_text(encoding="utf-8-sig"))
    map_doc = json.loads(MAP.read_text(encoding="utf-8-sig"))
    preset = dtcg.get("preset") or "clinic-loi-trust-light"
    layers = (dtcg.get(preset) or {}) if isinstance(dtcg.get(preset), dict) else {}

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sets = {
        "clinic-loi-primitive": _dtcg_to_studio(layers.get("primitive") or {}, "clinic-loi-primitive"),
        "clinic-loi-semantic": _dtcg_to_studio(layers.get("semantic") or {}, "clinic-loi-semantic"),
        "clinic-loi-component": _dtcg_to_studio(layers.get("component") or {}, "clinic-loi-component"),
        "clinic-loi-flat": _flat_from_map(map_doc),
    }

    written: list[str] = []
    for name, body in sets.items():
        path = OUT_DIR / f"{name}.json"
        path.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    paste_path = OUT_DIR / "PASTE_FIRST_clinic-loi-flat.json"
    paste_path.write_text(
        json.dumps(sets["clinic-loi-flat"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    steps_ko = [
        "Figma에서 mkm-20260624 + Tokens Studio 플러그인 열기",
        "왼쪽 하단 + New Set → 이름: clinic-loi-flat",
        "오른쪽 상단 {} 아이콘(JSON view) 클릭",
        "reports/clinic_loi_tokens_studio_import_v1/PASTE_FIRST_clinic-loi-flat.json 전체 복사 후 붙여넣기",
        "플러그인 하단 Save(저장) 클릭 후 List view로 전환해 토큰 확인",
        "(선택) primitive/semantic/component 3세트도 동일 방식으로 각각 New Set 후 붙여넣기",
    ]

    manifest = {
        "schema": "clinic_loi_tokens_studio_import_manifest_v1",
        "generated_at_utc": _utc(),
        "paste_first": str(paste_path.relative_to(ROOT)).replace("\\", "/"),
        "files": written + [str(paste_path.relative_to(ROOT)).replace("\\", "/")],
        "import_method": "json_view_paste",
        "import_not_found_reason": "Tokens Studio 2.x has no file Import button; use {} JSON view per token set.",
        "steps_ko": steps_ko,
        "docs": "https://docs.tokens.studio/manage-tokens/token-sets/json-view",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_dir": str(OUT_DIR), "paste_first": str(paste_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
