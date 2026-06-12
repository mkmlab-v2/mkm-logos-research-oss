import {
  CUSTOMIZE_PACKAGES,
  type CustomizePackageTier,
} from "@/lib/universeHubCustomizeContentV2";

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
    </div>
  );
}
