import { HubApexDirectoryHome } from "@/components/HubApexDirectoryHome";
import { MarketingLegacyHomePage } from "@/components/MarketingLegacyHomePage";

export const dynamic = "force-dynamic";

type RootPageProps = {
  searchParams?: {
    preset?: string;
    legacy_home?: string;
  };
};

/**
 * jema-ai.com apex: thin brand hub + §1.1b surface directory.
 * Ask chrome: `/hub` only. Classic Ring 0 marketing: `/home` or `/?legacy_home=1`.
 */
export default function RootPage({ searchParams }: RootPageProps) {
  if (searchParams?.legacy_home === "1") {
    return <MarketingLegacyHomePage searchParams={searchParams} />;
  }
  return <HubApexDirectoryHome />;
}
