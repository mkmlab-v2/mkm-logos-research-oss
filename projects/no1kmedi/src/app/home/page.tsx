import { MarketingLegacyHomePage } from "@/components/MarketingLegacyHomePage";

export const dynamic = "force-dynamic";

type ClassicHomePageProps = {
  searchParams?: {
    preset?: string;
  };
};

/** Classic marketing landing (pre-hub HQ). */
export default function ClassicHomePage({ searchParams }: ClassicHomePageProps) {
  return <MarketingLegacyHomePage searchParams={searchParams} />;
}
