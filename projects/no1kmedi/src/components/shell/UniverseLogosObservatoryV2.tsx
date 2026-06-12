import type { LogosTopologyHubV1 } from "@/lib/universeHubLogosTopologyV1";

type Props = {
  topology: LogosTopologyHubV1;
};

function slPoint(vec: { S: number; L: number } | undefined, size = 200): { x: number; y: number } | null {
  if (!vec) return null;
  const x = 20 + vec.S * size;
  const y = 20 + (1 - vec.L) * size;
  return { x, y };
}

export function UniverseLogosObservatoryV2({ topology }: Props) {
  const hubs = topology.global_centrality_hubs ?? [];
  const eras = topology.era_centroid_trajectories ?? [];
  const eraPoints = eras
    .map((e) => slPoint(e.centroid_4d))
    .filter((p): p is { x: number; y: number } => p !== null);

  return (
    <div className="universe-hub-logos-observatory">
      <p className="universe-hub-logos-meta">
        코퍼스 {topology.n_verses?.toLocaleString() ?? "—"}절 · 배치 스냅샷 ·{" "}
        <span className="universe-hub-logos-badge">[HYPO] research_only</span>
      </p>
      {topology.disclaimer_ko ? (
        <p className="universe-hub-logos-disclaimer">{topology.disclaimer_ko}</p>
      ) : null}

      <section aria-labelledby="logos-era-phase-heading" className="universe-hub-logos-section">
        <h2 id="logos-era-phase-heading" className="universe-hub-section-title">
          시대 centroid 궤적 (S–L 평면)
        </h2>
        <svg
          className="universe-hub-logos-era-svg"
          viewBox="0 0 240 240"
          role="img"
          aria-label="11-era centroid phase trajectory on S-L plane"
        >
          <rect x="0" y="0" width="240" height="240" className="universe-hub-logos-era-bg" />
          {eraPoints.length > 1 ? (
            <polyline
              points={eraPoints.map((p) => `${p.x},${p.y}`).join(" ")}
              className="universe-hub-logos-era-line"
            />
          ) : null}
          {eraPoints.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={4} className="universe-hub-logos-era-dot" />
          ))}
        </svg>
        <ol className="universe-hub-logos-era-list">
          {eras.map((era) => (
            <li key={era.era_id}>
              <strong>{era.label_ko ?? era.era_id}</strong>
              {typeof era.phase_shift_l2_from_previous === "number" ? (
                <span> · ΔL2 {era.phase_shift_l2_from_previous}</span>
              ) : null}
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="logos-hubs-heading" className="universe-hub-logos-section">
        <h2 id="logos-hubs-heading" className="universe-hub-section-title">
          구조적 hub 후보 (Top {hubs.length})
        </h2>
        <div className="universe-hub-logos-table-wrap">
          <table className="universe-hub-logos-table">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">구절</th>
                <th scope="col">책</th>
                <th scope="col">hub score</th>
                <th scope="col">L2</th>
              </tr>
            </thead>
            <tbody>
              {hubs.map((hub, idx) => (
                <tr key={hub.verse_id}>
                  <td>{idx + 1}</td>
                  <td>{hub.verse_id}</td>
                  <td>{hub.book_id ?? "—"}</td>
                  <td>{hub.hub_score_inverse_l2?.toFixed(4) ?? "—"}</td>
                  <td>{hub.l2_to_global_centroid?.toFixed(4) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {topology.reproduce_command ? (
        <p className="universe-hub-logos-repro">
          <span className="universe-hub-logos-repro-label">재현:</span>{" "}
          <code>{topology.reproduce_command}</code>
        </p>
      ) : null}
    </div>
  );
}
