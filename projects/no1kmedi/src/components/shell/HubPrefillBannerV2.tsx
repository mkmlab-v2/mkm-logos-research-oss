type Props = {
  prefill?: string;
};

export function HubPrefillBannerV2({ prefill }: Props) {
  if (!prefill?.trim()) {
    return null;
  }
  return (
    <p className="universe-hub-prefill-banner" role="note">
      질문 컨텍스트(허브 라우팅): <q>{prefill.trim()}</q>
    </p>
  );
}
