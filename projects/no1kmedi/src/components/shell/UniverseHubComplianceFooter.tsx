import Link from "next/link";
import { siteCopy } from "@/content/siteCopy";

/** Shell-wide compliance strip — not a substitute for counsel-reviewed biz disclosure on /home. */

export function UniverseHubComplianceFooter() {
  const positioning = siteCopy.positioning_v1?.footer_strip_ko ?? "";

  return (
    <footer className="universe-hub-compliance-footer universe-hub-compliance-footer--shell">
      {positioning ? (
        <p className="universe-hub-compliance-positioning">{positioning}</p>
      ) : null}
      <p>
        [HYPO] research_only · SEND_GATE HOLD · 관측·참고용(투자·의료·실매매 지시 아님) ·{" "}
        <Link href="/home" className="universe-hub-inline-link">
          사업자 정보·면책 전문
        </Link>
      </p>
    </footer>
  );
}
