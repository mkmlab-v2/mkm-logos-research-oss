/**
 * Hyper-local POI delight lines (preview · [HYPO] curation, not maps API).
 */
import catalog from "../../public/data/personadiary_hyper_local_poi_catalog_v1.json";

export type HyperLocalPoiEntry = {
  poi_id: string;
  city_key: string;
  area_ko: string;
  menu_ko: string;
  venue_ko: string;
  one_liner_ko: string;
  weather_tags?: string[];
  meal_tags?: string[];
  evidence_tier?: string;
};

type PoiCatalog = {
  schema: string;
  entries: HyperLocalPoiEntry[];
};

const POI_CATALOG = catalog as PoiCatalog;

function weatherBand(weatherLine: string): string {
  const w = weatherLine.toLowerCase();
  if (/비|rain|우산/.test(w)) return "rain";
  if (/무더|hot|29|30|31|32|33/.test(w)) return "hot";
  if (/선선|cool|20|21|22/.test(w)) return "cool";
  return "mild";
}

function scorePoi(
  entry: HyperLocalPoiEntry,
  opts: { city: string; weatherLine: string; mealHint: string }
): number {
  let score = 0;
  if (entry.city_key.toLowerCase() === opts.city.toLowerCase()) score += 10;
  const band = weatherBand(opts.weatherLine);
  const tags = (entry.weather_tags || []).join(" ").toLowerCase();
  if (band === "hot" && /hot|warm|무더|29|30/.test(tags)) score += 8;
  if (band === "rain" && /비|rain/.test(tags)) score += 8;
  if (band === "cool" && /cool|선선|20|21|22/.test(tags)) score += 6;
  const meal = opts.mealHint.toLowerCase();
  for (const tag of entry.meal_tags || []) {
    if (meal.includes(tag.toLowerCase())) score += 5;
  }
  if (/삼계|닭/.test(meal) && /삼계|닭/.test(entry.menu_ko)) score += 6;
  if (/국밥|곰탕/.test(meal) && /국밥|곰탕|국물/.test(entry.menu_ko)) score += 4;
  return score;
}

export function pickHyperLocalPoi(opts: {
  city?: string;
  weatherLine?: string;
  mealHint?: string;
}): HyperLocalPoiEntry | null {
  const entries = POI_CATALOG.entries || [];
  if (!entries.length) return null;
  const city = opts.city || "Seoul";
  const weatherLine = opts.weatherLine || "";
  const mealHint = opts.mealHint || "";
  const ranked = [...entries]
    .map((e) => ({ e, score: scorePoi(e, { city, weatherLine, mealHint }) }))
    .sort((a, b) => b.score - a.score);
  const best = ranked[0];
  if (!best || best.score < 8) {
    return entries.find((e) => e.poi_id === "seoul_samgyetang_chain") || entries[0];
  }
  return best.e;
}

export function formatPoiDelightLine(poi: HyperLocalPoiEntry | null): string {
  if (!poi) return "";
  return poi.one_liner_ko;
}
