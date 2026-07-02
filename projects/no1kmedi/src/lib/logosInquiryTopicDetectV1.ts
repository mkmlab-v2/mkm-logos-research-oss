/** Client-safe query topic detectors (no Node/fs imports). */

function norm(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

export function detectPsalm23Topic(query: string): boolean {
  const q = norm(query);
  if (/시편\s*23|psalm\s*23|ps\.?\s*23|psalm\s*xxiii/.test(q)) return true;
  if (/(시편|psalm)/.test(q) && /(목자|shepherd)/.test(q)) return true;
  if (/23\s*편/.test(q) && /(목자|shepherd|green pasture|풍광)/.test(q)) return true;
  return false;
}

export function detectSchoolComparisonIntent(query: string): boolean {
  const q = (query || "").trim();
  if (!q) return false;
  return /학파|school|interpretation|해석\s*차|병렬|tradition/i.test(q);
}
