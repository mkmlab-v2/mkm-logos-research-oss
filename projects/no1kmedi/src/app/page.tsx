import { redirect } from "next/navigation";
import { MarketingLegacyHomePage } from "@/components/MarketingLegacyHomePage";

export const dynamic = "force-dynamic";

type RootPageProps = {
  searchParams?: {
    preset?: string;
    legacy_home?: string;
  };
};

/** jema-ai.com HQ: default entry is `/hub`. Classic marketing at `/home` or `/?legacy_home=1`. */
export default function RootPage({ searchParams }: RootPageProps) {
  if (searchParams?.legacy_home !== "1") {
    redirect("/hub");
  }
  return <MarketingLegacyHomePage searchParams={searchParams} />;
}
