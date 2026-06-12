import Link from "next/link";
import { CUSTOMIZE_SPOKES } from "@/lib/universeHubCustomizeContentV2";

const HUB_W = 148;
const HUB_H = 48;
const SPOKE_W = 120;
const SPOKE_H = 40;

export function HubSpokeDiagramV2() {
  const hubX = 24;
  const hubY = 56;
  const spokesY = hubY + (HUB_H - SPOKE_H) / 2;
  const spokeXs = [220, 360, 500];

  return (
    <figure className="universe-hub-spoke-figure" aria-labelledby="hub-spoke-title">
      <figcaption id="hub-spoke-title" className="sr-only">
        WTT Persona OS 허브와 선택 스포크 Compression, Macro, Showroom
      </figcaption>
      <svg
        className="universe-hub-spoke-svg"
        viewBox="0 0 640 160"
        role="img"
        aria-hidden="true"
      >
        {spokeXs.map((x) => (
          <line
            key={x}
            x1={hubX + HUB_W}
            y1={hubY + HUB_H / 2}
            x2={x}
            y2={spokesY + SPOKE_H / 2}
            className="universe-hub-spoke-line"
          />
        ))}
        <rect
          x={hubX}
          y={hubY}
          width={HUB_W}
          height={HUB_H}
          rx={8}
          className="universe-hub-spoke-hub"
        />
        <text x={hubX + HUB_W / 2} y={hubY + 30} textAnchor="middle" className="universe-hub-spoke-hub-text">
          WTT Persona OS
        </text>
        {CUSTOMIZE_SPOKES.map((spoke, i) => (
          <g key={spoke.id}>
            <rect
              x={spokeXs[i]}
              y={spokesY}
              width={SPOKE_W}
              height={SPOKE_H}
              rx={6}
              className="universe-hub-spoke-node"
            />
            <text
              x={spokeXs[i] + SPOKE_W / 2}
              y={spokesY + 24}
              textAnchor="middle"
              className="universe-hub-spoke-node-text"
            >
              {spoke.label}
            </text>
          </g>
        ))}
      </svg>
      <ul className="universe-hub-spoke-links">
        {CUSTOMIZE_SPOKES.map((spoke) => (
          <li key={spoke.id}>
            {spoke.external ? (
              <a href={spoke.href} target="_blank" rel="noopener noreferrer">
                {spoke.label}
                {spoke.tag ? ` · ${spoke.tag}` : ""} ↗
              </a>
            ) : (
              <Link href={spoke.href}>
                {spoke.label}
                {spoke.tag ? ` · ${spoke.tag}` : ""}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </figure>
  );
}
