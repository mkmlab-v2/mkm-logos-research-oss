/** Consumer-safe labels for daily-guide UI blocks (internal section ids unchanged). */

const EXACT_TITLE_MAP: Record<string, string> = {
  "오늘의 팔자 (명리)": "오늘의 흐름",
  "마음 에너지 (MKM 4AI)": "마음 리듬",
  "오늘의 성경 앵커": "앵커 한 줄",
  "찰나의 나라 (세상×나)": "세상 속의 나",
  "오늘 초론 스트림": "오늘의 초론",
};

export function toConsumerGuideTitle(title: string): string {
  const t = title.trim();
  if (EXACT_TITLE_MAP[t]) return EXACT_TITLE_MAP[t];
  if (/명리/.test(t)) return "오늘의 흐름";
  if (/4AI|MKM 4AI/i.test(t)) return "마음 리듬";
  if (/성경/.test(t)) return "앵커 한 줄";
  return t;
}
