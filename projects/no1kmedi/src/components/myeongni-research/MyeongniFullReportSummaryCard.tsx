"use client";

type PillarMap = Record<string, string | undefined>;

function asPillars(value: unknown): PillarMap | null {
  if (!value || typeof value !== "object") return null;
  const p = value as PillarMap;
  if (!p.year && !p.month && !p.day && !p.hour) return null;
  return p;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function formatYongsinHeadline(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") return value;
  const rec = asRecord(value);
  if (!rec) return String(value);
  const primary = rec.primary_hypothesis ?? rec.headline ?? rec.label;
  return primary != null ? String(primary) : JSON.stringify(rec);
}

function strengthLabel(structure: Record<string, unknown> | null): string | null {
  if (!structure) return null;
  const profile = asRecord(structure.element_profile);
  const strength = asRecord(structure.strength_assessment ?? structure.strength);
  if (strength?.label) return String(strength.label);
  if (strength?.strength_label) return String(strength.strength_label);
  if (profile?.dominant_element_visible && profile?.weakest_element_visible) {
    return `강 ${String(profile.dominant_element_visible)} · 약 ${String(profile.weakest_element_visible)}`;
  }
  return null;
}

type AnnualRow = {
  year?: number;
  sewoon_pillar?: string;
  sewoon_stem_ten_god?: string;
  daewoon_pillar?: string;
};

function asAnnualRows(value: unknown): AnnualRow[] {
  if (Array.isArray(value)) return value as AnnualRow[];
  const rec = asRecord(value);
  if (!rec) return [];
  const rows = rec.rows;
  return Array.isArray(rows) ? (rows as AnnualRow[]) : [];
}

type Props = {
  summary: Record<string, unknown>;
};

export function MyeongniFullReportSummaryCard({ summary }: Props) {
  const pillars = asPillars(summary.pillars_native);
  const structure = asRecord(summary.structure_analysis);
  const yongsin = formatYongsinHeadline(summary.yongsin_hypothesis_headline);
  const strength = strengthLabel(structure);
  const daewoon = asRecord(summary.daewoon_headline);
  const annualRows = asAnnualRows(summary.annual_rows);

  const currentCycle =
    daewoon && Array.isArray(daewoon.cycles) && daewoon.cycles.length
      ? (daewoon.cycles[0] as Record<string, unknown>)
      : null;

  return (
    <div className="mn-studio-full-report-card" role="region" aria-label="풀 리포트 요약">
      <div className="mn-studio-full-report-card-head">
        <span className="mn-studio-full-report-tag">B-track · NON_GATING</span>
        <span className="mn-studio-full-report-tag is-hold">send_gate HOLD</span>
      </div>

      {pillars ? (
        <dl className="mn-studio-full-report-grid">
          <div>
            <dt>년주</dt>
            <dd>{pillars.year ?? "—"}</dd>
          </div>
          <div>
            <dt>월주</dt>
            <dd>{pillars.month ?? "—"}</dd>
          </div>
          <div>
            <dt>일주</dt>
            <dd>{pillars.day ?? "—"}</dd>
          </div>
          <div>
            <dt>시주</dt>
            <dd>{pillars.hour ?? "—"}</dd>
          </div>
        </dl>
      ) : null}

      {strength ? (
        <p className="mn-studio-full-report-line">
          <strong>체질·오행</strong> {strength}
        </p>
      ) : null}

      {yongsin ? (
        <p className="mn-studio-full-report-line">
          <strong>용신 가설</strong> {yongsin}
        </p>
      ) : null}

      {currentCycle ? (
        <p className="mn-studio-full-report-line">
          <strong>대운(1주기)</strong>{" "}
          {String(currentCycle.pillar ?? currentCycle.daewoon_pillar ?? "—")}
          {currentCycle.age_start != null ? ` · ${String(currentCycle.age_start)}세~` : ""}
        </p>
      ) : null}

      {annualRows.length ? (
        <div className="mn-studio-full-report-annual">
          <strong>세운 미리보기</strong>
          <ul>
            {annualRows.map((row) => (
              <li key={String(row.year)}>
                {row.year}년 · {row.sewoon_pillar ?? "—"}
                {row.sewoon_stem_ten_god ? ` (${row.sewoon_stem_ten_god})` : ""}
                {row.daewoon_pillar ? ` · 대운 ${row.daewoon_pillar}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <p className="mn-studio-full-report-foot">
        연구·참고용 요약입니다. 임상·매매·Track A 게이트와 무관합니다.
      </p>
    </div>
  );
}
