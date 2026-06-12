import type { UniverseHubRq025OracleCardV1 } from "@/lib/universeHubRq025OracleCardV1";

type Props = {
  card: UniverseHubRq025OracleCardV1;
};

export function UniverseOracleRq025CardV2({ card }: Props) {
  const updated = card.last_updated_utc.replace("T", " · ").replace("Z", " UTC");

  return (
    <article
      className="universe-hub-rq025-card"
      aria-labelledby="rq025-card-title"
      data-research-only="true"
    >
      <header className="universe-hub-rq025-card-head">
        <p className="universe-hub-plugin-lane">
          {card.hypothesis_tag} {card.gating} · {card.rq_id}
        </p>
        <h2 id="rq025-card-title" className="universe-hub-section-title">
          {card.title_ko}
        </h2>
        <p className="universe-hub-rq025-updated">last_updated: {updated}</p>
      </header>
      <p className="universe-hub-rq025-summary">{card.summary_ko}</p>
      <dl className="universe-hub-rq025-meta">
        <div>
          <dt>arms</dt>
          <dd>{card.arms_label_ko}</dd>
        </div>
        <div>
          <dt>majority beat</dt>
          <dd>{card.verdict.any_beats_majority ? "true" : "false"}</dd>
        </div>
        <div>
          <dt>Track A promotion</dt>
          <dd>{card.verdict.track_a_promotion ? "true" : "false"}</dd>
        </div>
      </dl>
      <p className="universe-hub-rq025-discovery">{card.discovery_note_ko}</p>
      <p className="universe-hub-rq025-ssot">
        SSOT: <code>{card.data_ssot}</code>
      </p>
    </article>
  );
}
