import Link from "next/link";

import {
  DocsPageHeader,
  LogosResearchDocsShell,
} from "@/components/logos-research/LogosResearchDocsShell";
import { logosResearchDocsCopy } from "@/content/logosResearchDocsCopy";

export const metadata = {
  title: "Logos Public Docs",
  description:
    "Graph Studio, citation lock, pilot scope, and glossary. HYPO · research_only · NON_GATING · send_gate HOLD.",
};

export default function LogosResearchDocsHubPage() {
  const hub = logosResearchDocsCopy.hub;

  return (
    <LogosResearchDocsShell activeId="hub">
      <DocsPageHeader title={hub.title} lead={hub.lead} />
      <ul className="lr-docs-card-grid">
        {hub.cards.map((card) => (
          <li key={card.id}>
            <Link className="lr-docs-card" href={card.href}>
              <strong>{card.title}</strong>
              <p>{card.summary}</p>
              <span className="lr-docs-card-cta">Read →</span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="lr-docs-hub-demo">
        <a className="lr-btn lr-btn-primary" href={logosResearchDocsCopy.demo_url} rel="noopener noreferrer">
          Open Graph Studio (live demo)
        </a>
      </p>
    </LogosResearchDocsShell>
  );
}
