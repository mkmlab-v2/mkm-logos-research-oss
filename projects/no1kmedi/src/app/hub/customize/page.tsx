import { HubPrefillBannerV2 } from "@/components/shell/HubPrefillBannerV2";

import { UniverseCustomizePanelV2 } from "@/components/shell/UniverseCustomizePanelV2";



export const metadata = {

  title: "AI 맞춤·가드 (B2B) — JEMA AI Hub",

  description: "Governed AI Customization · WTT Persona OS · Track C [DRAFT]",

};



type Props = {

  searchParams?: { prefill?: string };

};



export default function HubCustomizePage({ searchParams }: Props) {

  const prefill = searchParams?.prefill;

  return (

    <>

      <HubPrefillBannerV2 prefill={prefill} />

      <UniverseCustomizePanelV2 />

    </>

  );

}

