import {
  DocsPageHeader,
  LogosResearchDocsShell,
} from "@/components/logos-research/LogosResearchDocsShell";
import { logosResearchDocsCopy } from "@/content/logosResearchDocsCopy";

export const metadata = {
  title: "Pilot scope",
  description: "Demo, Pilot, Workspace tiers and PoC boundaries. send_gate HOLD.",
};

export default function LogosResearchPilotScopePage() {
  const page = logosResearchDocsCopy.pilot_scope;

  return (
    <LogosResearchDocsShell activeId="pilot-scope">
      <DocsPageHeader eyebrow={page.eyebrow} title={page.title} />

      <section className="lr-docs-section">
        <h2>Included</h2>
        <ul className="lr-docs-list">
          {page.included.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="lr-docs-section">
        <h2>Excluded</h2>
        <ul className="lr-docs-list lr-docs-list--warn">
          {page.excluded.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="lr-docs-section">
        <h2>Tiers</h2>
        <ul className="lr-tier-list">
          {page.tiers.map((tier) => (
            <li key={tier.id} className="lr-tier-card">
              <strong>{tier.name}</strong>
              <span>{tier.audience}</span>
              <p>{tier.note}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="lr-docs-section">
        <h2>Governance</h2>
        <ul className="lr-docs-list">
          {page.governance.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </LogosResearchDocsShell>
  );
}
