import Link from "next/link";
import { HubAccountEntryV1 } from "@/components/shell/HubAccountEntryV1";

/** Sticky site-header for /hub routes — brand only (nav lives in sidebar; contract max_primary_nav: 0). */
export function UniverseHubSiteHeader() {
  return (
    <header className="site-header universe-hub-site-header">
      <div className="header-inner universe-hub-site-header-inner">
        <Link className="brand" href="/hub">
          JEMA AI <span>Hub</span>
        </Link>
        <HubAccountEntryV1 />
      </div>
    </header>
  );
}
