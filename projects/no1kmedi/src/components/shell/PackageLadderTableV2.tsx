import Link from "next/link";
import {
  CUSTOMIZE_PACKAGES,
  type CustomizePackageTier,
} from "@/lib/universeHubCustomizeContentV2";
import { UNIVERSE_HUB_DEEP_LINKS } from "@/lib/universeHubPluginsV2";

function tierLabel(tier: CustomizePackageTier): string {
  if (tier === "core") return "Core";
  if (tier === "proof") return "Proof";
  return "Add-on";
}

function tierClass(tier: CustomizePackageTier): string {
  return `universe-hub-tier universe-hub-tier--${tier}`;
}

export function PackageLadderTableV2() {
  return (
    <div className="universe-hub-package-table-wrap">
      <table className="universe-hub-package-table">
        <thead>
          <tr>
            <th scope="col">티어</th>
            <th scope="col">패키지</th>
            <th scope="col">구매 가치</th>
          </tr>
        </thead>
        <tbody>
          {CUSTOMIZE_PACKAGES.map((row) => (
            <tr key={row.id}>
              <td>
                <span className={tierClass(row.tier)}>{tierLabel(row.tier)}</span>
              </td>
              <td>{row.labelKo}</td>
              <td>{row.buyerValueKo}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="universe-hub-package-cta-row">
        <Link className="universe-hub-cta universe-hub-cta--primary" href={UNIVERSE_HUB_DEEP_LINKS.compressionPilotApply}>
          B2B 상담·사전 감사 신청
        </Link>
        <span className="universe-hub-package-cta-note">가격 미표기 · SEND HOLD · Track A SLA 없음</span>
      </p>
    </div>
  );
}
