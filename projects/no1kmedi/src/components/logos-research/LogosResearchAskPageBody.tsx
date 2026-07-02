"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { LogosResearchAskClient } from "@/components/logos-research/LogosResearchAskClient";
import { logosResearchCopy } from "@/content/logosResearchCopy";

type AskCopy = {
  placeholder?: string;
  run_label?: string;
  running_label?: string;
  governance?: string;
  handoff_label?: string;
  handoff_url?: string;
  export_json?: string;
  sample_questions?: string[];
};

function AskBodyInner() {
  const sp = useSearchParams();
  const initialQuestion = (sp.get("q") || "").trim();
  const autorun = sp.get("autorun") === "1";
  const ask = ("ask" in logosResearchCopy ? logosResearchCopy.ask : null) as AskCopy | null;

  return (
    <LogosResearchAskClient
        initialQuestion={initialQuestion}
        autorun={autorun}
        outputFormat="inquiry_report_v1"
        sampleQuestions={ask?.sample_questions ?? []}
        placeholder={ask?.placeholder ?? "질문을 입력하세요"}
        runLabel={ask?.run_label ?? "질문하기"}
        runningLabel={ask?.running_label ?? "분석 중…"}
        governance={ask?.governance ?? "Track B [HYPO] · research_only"}
        handoffLabel={ask?.handoff_label ?? "mkmlife /oracle-sphere"}
        handoffUrl={ask?.handoff_url ?? "https://mkmlife.com/oracle-sphere"}
        exportLabel={ask?.export_json ?? "리포트 JSON 내보내기"}
    />
  );
}

export function LogosResearchAskPageBody() {
  return (
    <Suspense fallback={<p className="lr-section-lead">Q&A 로딩 중…</p>}>
      <AskBodyInner />
    </Suspense>
  );
}
