/**
 * Stage-① ledger LOOKUP pack (non-AI) for tabernacle noun-domain Ask.
 * research_only · SEND HOLD · ≠ product DONE · inject = prevention only.
 */
import lookupPack from "@/data/logos_ask_ledger_lookup_pack_tabernacle_v1.json";

export type LedgerLookupPackItemV1 = {
  label_ko: string;
  ref: string;
  text_ko: string;
  domain?: boolean;
};

export type LedgerLookupPackV1 = {
  schema: string;
  external_label_ko?: string;
  panel_copy_ko?: string;
  items: LedgerLookupPackItemV1[];
  domain_anchor_count?: number;
  ai_used?: boolean;
};

export function getTabernacleLedgerLookupPackV1(): LedgerLookupPackV1 {
  return lookupPack as LedgerLookupPackV1;
}

/** Prompt/body inject block — disk SSOT texts, not LLM classification. */
export function buildTabernacleLedgerLookupInjectBlockKo(): string {
  const pack = getTabernacleLedgerLookupPackV1();
  const label = pack.external_label_ko || "MKM 원장 대조";
  const lines = [
    `### ${label} · 조회 팩 (비AI · 주입)`,
    "아래 원문은 디스크 SSOT에서 규칙으로 꺼낸 후보입니다. 공인 번역본 일치 주장이 아닙니다.",
    pack.panel_copy_ko || "대조된 구절만 표시합니다",
    "",
  ];
  for (const it of pack.items || []) {
    if (!it?.ref || !it?.text_ko) continue;
    lines.push(`- **(${it.ref} · ${it.label_ko || ""})** ${it.text_ko}`);
  }
  lines.push(
    "",
    "- [HYPO][NON_GATING] · send_gate: HOLD · ai_used=false · 사후 배지(③)는 별도 보험",
  );
  return lines.join("\n");
}

export function tabernacleLedgerLookupDomainCount(): number {
  const pack = getTabernacleLedgerLookupPackV1();
  if (typeof pack.domain_anchor_count === "number") return pack.domain_anchor_count;
  return (pack.items || []).filter((i) => i.domain !== false).length;
}
