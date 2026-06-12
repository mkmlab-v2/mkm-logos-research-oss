export type UniverseHubReportLedgerEntryV1 = {
  id: string;
  title_ko: string;
  status: string;
  lane: string;
  updated_utc: string;
  source: string;
};

export type UniverseHubReportLedgerStubV1 = {
  schema: "universe_hub_report_ledger_stub_v1";
  version: string;
  research_only: boolean;
  hypothesis_tag: string;
  last_updated_utc: string;
  disclaimer_ko: string;
  entries: UniverseHubReportLedgerEntryV1[];
};
