import Link from "next/link";

/** Sticky site-header for /hub routes — brand only (nav lives in sidebar; contract max_primary_nav: 0). */
export function UniverseHubSiteHeader() {
  return (
    <header className="site-header universe-hub-site-header">
      <div className="header-inner universe-hub-site-header-inner">
        <Link className="brand" href="/hub">
          JEMA AI <span>Hub</span>
        </Link>
      </div>
    </header>
  );
}
