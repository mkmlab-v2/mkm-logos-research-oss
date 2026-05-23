import type { SiteCopy } from "@/content/siteCopy";

type GovernanceFlowCopy = SiteCopy["governance_flow"];

export function FieldLensGovernanceFlow({ copy }: { copy: GovernanceFlowCopy }) {
  return (
    <section
      id="governance-flow"
      className="field-lens-flow mkm-section"
      aria-labelledby="governance-flow-title"
    >
      <h2 id="governance-flow-title">{copy.title}</h2>
      <p className="section-lead">{copy.section_lead}</p>

      <div className="field-lens-flow-grid" role="group" aria-label="Field-Lens-Resolver 흐름">
        <div className="field-lens-column field-lens-column-primary">
          <p className="field-lens-column-label">{copy.field_label}</p>
          <ul className="field-lens-stack">
            {copy.field_items.map((item) => (
              <li key={item.title}>
                <article className="card card-lift field-lens-node">
                  <h3>{item.title}</h3>
                  <p>{item.body}</p>
                </article>
              </li>
            ))}
          </ul>
        </div>

        <div className="field-lens-arrow" aria-hidden="true">
          →
        </div>

        <div className="field-lens-column field-lens-column-aux">
          <p className="field-lens-column-label">{copy.lens_label}</p>
          <ul className="field-lens-stack">
            {copy.lens_items.map((item) => (
              <li key={item.title}>
                <article className="card card-lift field-lens-node">
                  <h3>
                    {item.title}
                    {item.non_gating ? <span className="field-lens-tag">NON_GATING</span> : null}
                  </h3>
                  <p>{item.body}</p>
                </article>
              </li>
            ))}
          </ul>
        </div>

        <div className="field-lens-arrow" aria-hidden="true">
          →
        </div>

        <div className="field-lens-column field-lens-column-resolve">
          <p className="field-lens-column-label">{copy.resolve_label}</p>
          <article className="card card-lift field-lens-resolver" aria-label="Conflict Resolver">
            <h3>{copy.resolver.title}</h3>
            <p>{copy.resolver.body}</p>
          </article>
          <div className="field-lens-final" aria-label="Final Action observational labels">
            <p className="field-lens-final-label">{copy.final_action_label}</p>
            <div className="field-lens-chips">
              {copy.final_actions.map((action) => (
                <span key={action} className="field-lens-chip">
                  {action}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      <p className="trust-note" role="note">
        {copy.footnote_prefix}{" "}
        <a href={copy.figjam_url} rel="noopener noreferrer" target="_blank">
          {copy.figjam_label}
        </a>
        · {copy.svg_preview_note}
      </p>
    </section>
  );
}
