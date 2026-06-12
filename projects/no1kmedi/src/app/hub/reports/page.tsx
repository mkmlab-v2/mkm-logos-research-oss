import { readFile } from "node:fs/promises";

import path from "node:path";



import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";
import { UniverseHubDisclaimerCollapsible } from "@/components/shell/UniverseHubDisclaimerCollapsible";
import { UniverseHubPluginPanel } from "@/components/shell/UniverseHubPluginPanel";
import { UniverseReportsEmptyV2 } from "@/components/shell/UniverseReportsEmptyV2";
import { UniverseReportsLedgerStubV2 } from "@/components/shell/UniverseReportsLedgerStubV2";

import type { UniverseHubReportLedgerStubV1 } from "@/lib/universeHubReportLedgerStubV1";

import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";



export const metadata = {

  title: "내 리포트 — JEMA AI Hub",

};



async function loadReportLedgerStub(): Promise<UniverseHubReportLedgerStubV1 | null> {

  try {

    const filePath = path.join(

      process.cwd(),

      "public/data/universe_hub_report_ledger_stub_v1.json",

    );

    const raw = await readFile(filePath, "utf8");

    const data = JSON.parse(raw) as UniverseHubReportLedgerStubV1;

    if (data.schema !== "universe_hub_report_ledger_stub_v1") return null;

    return data;

  } catch {

    return null;

  }

}



type Props = {

  searchParams?: { prefill?: string };

};



export default async function HubReportsPage({ searchParams }: Props) {

  const prefill = searchParams?.prefill;

  const ledgerStub = await loadReportLedgerStub();

  return (

    <div className="universe-hub-plugin-stack universe-hub-plugin-stack--spoke">
      <HubPrefillBannerV2 prefill={prefill} />

      <UniverseHubPluginPanel

        pluginId="my_reports"

        title="내 리포트"

        body="오픈 베타는 회원가입 없이 mkmlife.com에서 생성한 리포트를 이 브라우저 기준으로 확인합니다. (계정 연동은 이후 단계)"

        primaryCta={{

          href: UNIVERSE_HUB_DEEP_LINKS.mkmlifeReports,

          label: "MKM LIFE 내 리포트",

          external: true,

        }}

        phaseNote="P2 · stub ledger + empty state"

      />

      {ledgerStub ? <UniverseReportsLedgerStubV2 ledger={ledgerStub} /> : null}

      <UniverseReportsEmptyV2 />

      <UniverseHubDisclaimerCollapsible defaultOpen={false} />
    </div>

  );

}

