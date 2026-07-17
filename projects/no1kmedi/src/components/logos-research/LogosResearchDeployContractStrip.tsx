import { logosResearchCopy } from "@/content/logosResearchCopy";

/**
 * Soft public status line — no internal ops jargon in visible chrome.
 * FAIL-COMP-004: no Cosmic Meta / 4-force mash on Logos scripture surfaces.
 */
export function LogosResearchDeployContractStrip() {
  const pilot = logosResearchCopy.pilot_status;

  return (
    <section
      className="lr-deploy-contract lr-section lr-section--compact"
      aria-label="LOGOS research workspace status"
    >
      <p className="lr-deploy-contract-lead">
        <span>{pilot?.badge ?? "Public Beta"}</span>
        {" · "}
        <span>텍스트 Q&A 우선</span>
        {" · "}
        <span>Graph Studio는 베타 후</span>
      </p>
      <div
        className="lr-deploy-contract-embed"
        data-logos-graph-studio-embed="1"
        aria-hidden
        hidden
      />
    </section>
  );
}
