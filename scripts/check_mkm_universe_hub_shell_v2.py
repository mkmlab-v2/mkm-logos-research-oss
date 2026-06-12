#!/usr/bin/env python3
"""universe_hub_v2 gate: jema-ai.com /hub shell (P1–P4 local scaffold).

Draft contract: docs/final/artifacts/mkm_universe_hub_shell_contract_v2_draft.json
Does not supersede mkm_ui_shell_contract_v1.json (mkmlife consumer_portal_v1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "docs/final/artifacts/mkm_universe_hub_shell_contract_v2_draft.json"
DEFAULT_OUT = ROOT / "reports/mkm_universe_hub_shell_gate_v2_latest.json"

REQUIRED_COMPONENTS = (
    "projects/no1kmedi/src/components/shell/UnifiedUniverseShellV2.tsx",
    "projects/no1kmedi/src/components/shell/UniverseHubSiteHeader.tsx",
    "projects/no1kmedi/src/components/shell/UniverseSidebarV2.tsx",
    "projects/no1kmedi/src/components/shell/UniverseCenterAskV2.tsx",
    "projects/no1kmedi/src/components/shell/IntentChipRowV2.tsx",
    "projects/no1kmedi/src/components/shell/PackageLadderTableV2.tsx",
    "projects/no1kmedi/src/components/shell/UniverseCustomizePanelV2.tsx",
    "projects/no1kmedi/src/components/shell/HubSpokeDiagramV2.tsx",
    "projects/no1kmedi/src/lib/universeHubPluginsV2.ts",
    "projects/no1kmedi/src/lib/universeHubIntentRouterV2.ts",
    "projects/no1kmedi/src/lib/universeHubCustomizeContentV2.ts",
    "projects/no1kmedi/src/lib/universeHubPathActivePlugin.ts",
    "projects/no1kmedi/src/components/shell/HubShellClient.tsx",
    "projects/no1kmedi/src/components/shell/UniverseOperatorPanelV2.tsx",
    "projects/no1kmedi/src/components/shell/UniverseReportsEmptyV2.tsx",
    "projects/no1kmedi/src/components/shell/UniverseMkmlifeEmbedV2.tsx",
    "projects/no1kmedi/src/lib/universeHubMkmlifeEmbedV2.ts",
    "projects/no1kmedi/src/lib/universeHubDiscoverCopyV2.ts",
    "projects/no1kmedi/src/components/shell/UniverseOracleRq025CardV2.tsx",
    "projects/no1kmedi/src/lib/universeHubRq025OracleCardV1.ts",
    "projects/no1kmedi/src/components/shell/UniverseReportsLedgerStubV2.tsx",
    "projects/no1kmedi/src/lib/universeHubReportLedgerStubV1.ts",
    "projects/no1kmedi/src/lib/no1kmedi-portal-host.ts",
    "projects/no1kmedi/src/components/shell/UniverseLogosObservatoryV2.tsx",
    "projects/no1kmedi/src/lib/universeHubLogosTopologyV1.ts",
    "projects/no1kmedi/src/components/shell/HubEvidenceInspectorV3.tsx",
    "projects/no1kmedi/src/lib/universeHubInspectorV3.ts",
    "projects/no1kmedi/src/components/shell/UniverseCompressionSandboxV2.tsx",
)

REQUIRED_ROUTES = (
    "projects/no1kmedi/src/app/hub/page.tsx",
    "projects/no1kmedi/src/app/hub/layout.tsx",
    "projects/no1kmedi/src/app/hub/customize/page.tsx",
    "projects/no1kmedi/src/app/hub/oracle/page.tsx",
    "projects/no1kmedi/src/app/hub/logos/page.tsx",
    "projects/no1kmedi/src/app/hub/life/page.tsx",
    "projects/no1kmedi/src/app/hub/developer/page.tsx",
    "projects/no1kmedi/src/app/hub/reports/page.tsx",
    "projects/no1kmedi/src/app/hub/operator/page.tsx",
    "projects/no1kmedi/src/app/hub/compression/page.tsx",
)

FORBIDDEN_IN_HUB = frozenset(
    {
        "47.5%",
        "0.890",
        "56.5%",
        "무한 채팅",
        "실매매 ON",
    }
)

DEEP_LINK_MARKERS = (
    "mkmlife.com",
    "jemaai.cloud",
    "a-codeai.com",
)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _scan_hub_tree() -> list[str]:
    hits: list[str] = []
    hub_root = ROOT / "projects/no1kmedi/src/app/hub"
    shell_root = ROOT / "projects/no1kmedi/src/components/shell"
    lib_root = ROOT / "projects/no1kmedi/src/lib"
    lib_files = list(lib_root.glob("universeHub*.ts"))
    for path in list(hub_root.rglob("*")) + list(shell_root.rglob("*.tsx")) + lib_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for needle in FORBIDDEN_IN_HUB:
            if needle in text and needle != "무한 채팅":
                hits.append(f"{_rel(path)}: {needle}")
            elif needle == "무한 채팅" and "무한 채팅" in text:
                if "아님" not in text and "아닌" not in text:
                    hits.append(f"{_rel(path)}: 무한 채팅 (non-negated)")
    return hits


def run_check(*, write_report: bool = True, out_path: Path | None = None) -> tuple[int, dict[str, Any]]:
    issues: list[str] = []
    if not DRAFT.is_file():
        issues.append(f"missing draft contract: {DRAFT}")

    doc: dict[str, Any] = {}
    if DRAFT.is_file():
        doc = json.loads(DRAFT.read_text(encoding="utf-8"))
        if doc.get("schema") != "mkm_universe_hub_shell_contract_v2_draft":
            issues.append("bad draft schema")
        shell = (doc.get("shells") or {}).get("universe_hub_v2") or {}
        plugins = shell.get("sidebar_plugins") or []
        max_plugins = int((shell.get("layout") or {}).get("max_sidebar_plugins") or 8)
        if len(plugins) > max_plugins:
            issues.append(f"plugin count {len(plugins)} > {max_plugins}")

    for rel in REQUIRED_COMPONENTS:
        if not (ROOT / rel).is_file():
            issues.append(f"missing component: {rel}")

    for rel in REQUIRED_ROUTES:
        if not (ROOT / rel).is_file():
            issues.append(f"missing route: {rel}")

    shell_tsx = ROOT / "projects/no1kmedi/src/components/shell/UnifiedUniverseShellV2.tsx"
    if shell_tsx.is_file():
        text = shell_tsx.read_text(encoding="utf-8")
        has_shell_id = (
            "universe_hub_v2" in text
            or "UNIVERSE_HUB_SHELL_ID" in text
            or "data-shell-id" in text
        )
        if not has_shell_id:
            issues.append("UnifiedUniverseShellV2 missing shell id")
        if "UniverseHubSiteHeader" not in text:
            issues.append("UnifiedUniverseShellV2 missing sticky site header")
        if "HubEvidenceInspectorV3" not in text:
            issues.append("UnifiedUniverseShellV2 missing HubEvidenceInspectorV3 chassis v3")

    plugins_ts = ROOT / "projects/no1kmedi/src/lib/universeHubPluginsV2.ts"
    if plugins_ts.is_file():
        text = plugins_ts.read_text(encoding="utf-8")
        missing_links = [m for m in DEEP_LINK_MARKERS if m not in text]
        if missing_links:
            issues.append(f"universeHubPluginsV2 missing deep links: {missing_links}")

    forbidden_hits = _scan_hub_tree()
    if forbidden_hits:
        issues.extend(forbidden_hits)

    dev_page = ROOT / "projects/no1kmedi/src/app/hub/developer/page.tsx"
    if dev_page.is_file():
        dev_text = dev_page.read_text(encoding="utf-8")
        if "a-codeai-compression-reproduce" not in dev_text:
            issues.append("hub/developer missing open-bench reproduce GitHub link")

    middleware = ROOT / "projects/no1kmedi/src/middleware.ts"
    if middleware.is_file():
        mw_text = middleware.read_text(encoding="utf-8")
        if "isHubOperatorPath" not in mw_text or "403" not in mw_text:
            issues.append("middleware missing /hub/operator 403 gate")

    router_ts = ROOT / "projects/no1kmedi/src/lib/universeHubIntentRouterV2.ts"
    if router_ts.is_file():
        router_text = router_ts.read_text(encoding="utf-8")
        for sym in ("validateHubAskSubmit", "customize", "clinician", "reports"):
            if sym not in router_text:
                issues.append(f"universeHubIntentRouterV2 missing {sym}")

    rq025_card = ROOT / "projects/no1kmedi/public/data/universe_hub_rq025_oracle_card_v1.json"
    if not rq025_card.is_file():
        issues.append("missing rq025 oracle card fixture: public/data/universe_hub_rq025_oracle_card_v1.json")
    elif rq025_card.is_file():
        card_doc = json.loads(rq025_card.read_text(encoding="utf-8"))
        if card_doc.get("schema") != "universe_hub_rq025_oracle_card_v1":
            issues.append("bad rq025 oracle card schema")
        if not card_doc.get("last_updated_utc"):
            issues.append("rq025 oracle card missing last_updated_utc")
        card_raw = rq025_card.read_text(encoding="utf-8")
        for banned in ("56.5%", "47.5%"):
            if banned in card_raw and banned not in str(card_doc.get("forbidden_on_surface") or []):
                issues.append(f"rq025 card exposes forbidden metric {banned}")

    oracle_page = ROOT / "projects/no1kmedi/src/app/hub/oracle/page.tsx"
    if oracle_page.is_file() and "UniverseOracleRq025CardV2" not in oracle_page.read_text(encoding="utf-8"):
        issues.append("hub/oracle missing UniverseOracleRq025CardV2")

    portal_host = ROOT / "projects/no1kmedi/src/lib/no1kmedi-portal-host.ts"
    if portal_host.is_file():
        ph_text = portal_host.read_text(encoding="utf-8")
        if "app.jema-ai.com" not in ph_text or "shouldRedirectRootToHubHome" not in ph_text:
            issues.append("no1kmedi-portal-host missing app.jema-ai.com hub root redirect")

    reports_ledger = ROOT / "projects/no1kmedi/public/data/universe_hub_report_ledger_stub_v1.json"
    if not reports_ledger.is_file():
        issues.append("missing report ledger stub: public/data/universe_hub_report_ledger_stub_v1.json")
    else:
        ledger_doc = json.loads(reports_ledger.read_text(encoding="utf-8"))
        if ledger_doc.get("schema") != "universe_hub_report_ledger_stub_v1":
            issues.append("bad report ledger stub schema")
        if not ledger_doc.get("entries"):
            issues.append("report ledger stub missing entries")

    reports_page = ROOT / "projects/no1kmedi/src/app/hub/reports/page.tsx"
    if reports_page.is_file() and "UniverseReportsLedgerStubV2" not in reports_page.read_text(encoding="utf-8"):
        issues.append("hub/reports missing UniverseReportsLedgerStubV2")

    compression_page = ROOT / "projects/no1kmedi/src/app/hub/compression/page.tsx"
    if compression_page.is_file():
        comp_text = compression_page.read_text(encoding="utf-8")
        if "UniverseCompressionSandboxV2" not in comp_text:
            issues.append("hub/compression missing UniverseCompressionSandboxV2")
        if "47.5%" in comp_text:
            issues.append("hub/compression exposes forbidden 47.5% metric")
    elif compression_page not in [ROOT / r for r in REQUIRED_ROUTES]:
        pass
    else:
        issues.append("hub/compression page missing")

    plugins_ts_compression = ROOT / "projects/no1kmedi/src/lib/universeHubPluginsV2.ts"
    if plugins_ts_compression.is_file():
        pt = plugins_ts_compression.read_text(encoding="utf-8")
        if "compression_sandbox" not in pt or "/hub/compression" not in pt:
            issues.append("universeHubPluginsV2 missing compression_sandbox spoke")

    customize_page = ROOT / "projects/no1kmedi/src/app/hub/customize/page.tsx"
    if customize_page.is_file():
        cust_text = customize_page.read_text(encoding="utf-8")
        if "HubSpokeDiagramV2" not in cust_text and "UniverseCustomizePanelV2" not in cust_text:
            issues.append("hub/customize missing customize panel wiring")
        if "HubPrefillBannerV2" not in cust_text:
            issues.append("hub/customize missing HubPrefillBannerV2")

    overall_ok = not issues
    report = {
        "schema": "mkm_universe_hub_shell_gate_v2",
        "draft_contract": _rel(DRAFT),
        "overall_ok": overall_ok,
        "phase": "P4_embed_scaffold_complete_local",
        "issues": issues,
        "track_wall": "draft_research_only_not_track_a_not_live",
    }
    if write_report:
        path = out_path or DEFAULT_OUT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"overall_ok": overall_ok, "issues": issues}, ensure_ascii=False))
    return (0 if overall_ok else 1), report


def main() -> int:
    code, _ = run_check()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
