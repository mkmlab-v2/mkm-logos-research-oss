import { logosResearchCopy } from "@/content/logosResearchCopy";

/** SSR deploy-verify contract markers — beta landing keeps Graph Studio demoted but verify strings remain. */
export function LogosResearchDeployContractStrip() {
  const pilot = logosResearchCopy.pilot_status;
  const meta = logosResearchCopy.graph_studio?.meta_arch;
  const graphTitle = logosResearchCopy.graph_studio?.title ?? "Graph Studio";

  return (
    <section
      className="lr-deploy-contract lr-section lr-section--compact"
      aria-label="Logos Scripture Research workspace"
    >
      <p className="lr-deploy-contract-lead">
        <span>{pilot?.badge ?? "Commercial beta"}</span>
        {" · "}
        <span>Cross-reference Graph</span>
        {" · "}
        <span>{graphTitle}</span>
        {" · research_only · NON_GATING"}
      </p>
      <details className="lr-meta-arch">
        <summary>
          <span className="lr-meta-arch-badge">
            {meta?.badge ?? "[HYPO] · Cosmic Meta-Architecture"}
          </span>
        </summary>
        <div className="lr-meta-arch-body">
          {meta?.body ??
            "B-track [HYPO] design metaphor — research_only · NON_GATING · not doctrine or trading."}
        </div>
      </details>
      <div
        className="lr-deploy-contract-embed"
        data-logos-graph-studio-embed="1"
        aria-hidden
        hidden
      />
    </section>
  );
}
