"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { MyeongniFullReportSummaryCard } from "@/components/myeongni-research/MyeongniFullReportSummaryCard";
import { MyeongniPathMindmapPanel } from "@/components/myeongni-research/MyeongniPathMindmapPanel";
import type { MyeongniLiteMindmapInput } from "@/lib/myeongniPathMindmapV1";
import { MYEONGNI_FULL_REPORT_SSOT } from "@/lib/myeongniLiteToMindmapInputV1";

const DEMO_URL = "/data/myeongni_studio/demo_lite_v1.json";
const ENGINE_URL = "/api/myeongni/studio-mindmap-v1";
const FULL_REPORT_URL = "/api/myeongni/studio-full-report-v1";

type DemoDoc = MyeongniLiteMindmapInput & {
  demo_query?: string;
  disclaimer_ko?: string;
};

type SourceMode = "demo" | "engine";

type BirthForm = {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
  tz: string;
  is_male: boolean;
};

const DEFAULT_BIRTH: BirthForm = {
  year: 1991,
  month: 3,
  day: 10,
  hour: 11,
  minute: 10,
  tz: "Asia/Seoul",
  is_male: true,
};

export function MyeongniResearchStudioClient() {
  const [mode, setMode] = useState<SourceMode>("demo");
  const [demo, setDemo] = useState<DemoDoc | null>(null);
  const [engineInput, setEngineInput] = useState<MyeongniLiteMindmapInput | null>(null);
  const [gateStatus, setGateStatus] = useState<string | null>(null);
  const [gateReasons, setGateReasons] = useState<string[]>([]);
  const [boundaryWarning, setBoundaryWarning] = useState(false);
  const [policyInterpretation, setPolicyInterpretation] = useState<string | null>(null);
  const [fullReportSummary, setFullReportSummary] = useState<Record<string, unknown> | null>(null);
  const [fullReportMarkdown, setFullReportMarkdown] = useState<string | null>(null);
  const [fullReportLoading, setFullReportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("올해 커리어 전환 타이밍과 에너지 흐름은?");
  const [birth, setBirth] = useState<BirthForm>(DEFAULT_BIRTH);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(DEMO_URL, { cache: "no-store" });
        if (!res.ok) throw new Error(`demo_fetch_${res.status}`);
        const doc = (await res.json()) as DemoDoc;
        if (!cancelled) {
          setDemo(doc);
          if (doc.demo_query) setQuery(doc.demo_query);
          setDisclaimer(doc.disclaimer_ko ?? null);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "demo_load_failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const demoInput = useMemo((): MyeongniLiteMindmapInput | null => {
    if (!demo) return null;
    return {
      query,
      pillars: demo.pillars,
      daewoon_current: demo.daewoon_current,
      sewoon_current: demo.sewoon_current,
      ten_god_lite: demo.ten_god_lite,
      oheng_visible: demo.oheng_visible,
      strength_hint: demo.strength_hint,
    };
  }, [demo, query]);

  const mindmapInput = mode === "engine" ? engineInput : demoInput;

  const runEngine = useCallback(async () => {
    setLoading(true);
    setError(null);
    setGateStatus(null);
    try {
      const res = await fetch(ENGINE_URL, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          query,
          year: birth.year,
          month: birth.month,
          day: birth.day,
          hour: birth.hour,
          minute: birth.minute,
          tz: birth.tz,
          is_male: birth.is_male,
          is_solar: true,
        }),
      });
      const json = (await res.json()) as {
        success?: boolean;
        error?: string;
        message?: string;
        mindmap_input?: MyeongniLiteMindmapInput;
        gate_status?: string;
        policy_interpretation?: string;
        reasons?: string[];
        boundary_warning?: boolean;
        disclaimer_ko?: string;
      };
      if (!res.ok || !json.success || !json.mindmap_input) {
        throw new Error(json.message || json.error || `engine_${res.status}`);
      }
      setEngineInput({ ...json.mindmap_input, query });
      setGateStatus(json.gate_status ?? null);
      setPolicyInterpretation(json.policy_interpretation ?? null);
      setGateReasons(Array.isArray(json.reasons) ? json.reasons.map(String) : []);
      setBoundaryWarning(Boolean(json.boundary_warning));
      setFullReportSummary(null);
      setFullReportMarkdown(null);
      setDisclaimer(json.disclaimer_ko ?? MYEONGNI_FULL_REPORT_SSOT.note_ko);
      setMode("engine");
    } catch (e) {
      setError(e instanceof Error ? e.message : "engine_failed");
    } finally {
      setLoading(false);
    }
  }, [birth, query]);

  const runFullReport = useCallback(async () => {
    setFullReportLoading(true);
    setError(null);
    try {
      const res = await fetch(FULL_REPORT_URL, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          year: birth.year,
          month: birth.month,
          day: birth.day,
          hour: birth.hour,
          minute: birth.minute,
          tz: birth.tz,
          is_male: birth.is_male,
          is_solar: true,
          include_markdown: true,
        }),
      });
      const json = (await res.json()) as {
        success?: boolean;
        error?: string;
        message?: string;
        summary?: Record<string, unknown>;
        markdown_preview?: string;
      };
      if (!res.ok || !json.success || !json.summary) {
        throw new Error(json.message || json.error || `full_report_${res.status}`);
      }
      setFullReportSummary(json.summary);
      setFullReportMarkdown(json.markdown_preview ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "full_report_failed");
    } finally {
      setFullReportLoading(false);
    }
  }, [birth]);

  const patchBirth = (key: keyof BirthForm, raw: string | boolean) => {
    setBirth((prev) => {
      if (key === "is_male") return { ...prev, is_male: Boolean(raw) };
      if (key === "tz") return { ...prev, tz: String(raw) };
      const n = Number(raw);
      return { ...prev, [key]: Number.isFinite(n) ? n : prev[key] };
    });
  };

  return (
    <section className="mn-studio-panel" aria-labelledby="mn-studio-title">
      <div className="mn-studio-mode-row" role="tablist" aria-label="데이터 소스">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "demo"}
          className={`mn-studio-mode-btn${mode === "demo" ? " is-active" : ""}`}
          onClick={() => setMode("demo")}
        >
          데모 팩
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "engine"}
          className={`mn-studio-mode-btn${mode === "engine" ? " is-active" : ""}`}
          onClick={() => setMode("engine")}
        >
          엔진 (verify-lite)
        </button>
      </div>

      <div className="mn-studio-form">
        <label className="mn-studio-label" htmlFor="mn-studio-query">
          질의
        </label>
        <input
          id="mn-studio-query"
          className="mn-studio-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="중기 방향·타이밍 질문"
        />
      </div>

      <fieldset className="mn-studio-birth-grid">
        <legend className="mn-studio-label">생년월일시 (엔진 조회)</legend>
        <label>
          년
          <input
            type="number"
            className="mn-studio-input mn-studio-input--compact"
            value={birth.year}
            onChange={(e) => patchBirth("year", e.target.value)}
          />
        </label>
        <label>
          월
          <input
            type="number"
            className="mn-studio-input mn-studio-input--compact"
            value={birth.month}
            onChange={(e) => patchBirth("month", e.target.value)}
          />
        </label>
        <label>
          일
          <input
            type="number"
            className="mn-studio-input mn-studio-input--compact"
            value={birth.day}
            onChange={(e) => patchBirth("day", e.target.value)}
          />
        </label>
        <label>
          시
          <input
            type="number"
            className="mn-studio-input mn-studio-input--compact"
            value={birth.hour}
            onChange={(e) => patchBirth("hour", e.target.value)}
          />
        </label>
        <label>
          분
          <input
            type="number"
            className="mn-studio-input mn-studio-input--compact"
            value={birth.minute}
            onChange={(e) => patchBirth("minute", e.target.value)}
          />
        </label>
        <label>
          성별
          <select
            className="mn-studio-input mn-studio-input--compact"
            value={birth.is_male ? "male" : "female"}
            onChange={(e) => patchBirth("is_male", e.target.value === "male")}
          >
            <option value="male">남</option>
            <option value="female">여</option>
          </select>
        </label>
        <button
          type="button"
          className="mn-studio-engine-btn"
          onClick={() => void runEngine()}
          disabled={loading}
        >
          {loading ? "엔진 조회 중…" : "엔진 조회 → 마인드맵"}
        </button>
      </fieldset>

      <p className="mn-studio-hint" role="note">
        B-track · NON_GATING · send_gate HOLD · 매매·임상 확정 아님
        {gateStatus ? ` · gate_status=${gateStatus}` : ""}
        {policyInterpretation ? ` · ${policyInterpretation}` : ""}
      </p>

      {boundaryWarning ? (
        <div className="mn-studio-boundary-badge" role="status">
          <strong>REVIEW · 경계 시각</strong>
          {gateReasons.length ? (
            <ul>
              {gateReasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : (
            <p>시주·절기 경계 근접 — 해석 단정 금지</p>
          )}
        </div>
      ) : null}

      {error ? <p className="mn-studio-error">{error}</p> : null}

      {mindmapInput ? (
        <MyeongniPathMindmapPanel
          input={mindmapInput}
          presetId={mode === "engine" ? "myeongni_engine_v1" : "myeongni_demo_v1"}
          autoDemo={mode === "demo"}
        />
      ) : (
        <p className="mn-studio-loading" role="status">
          {mode === "demo" ? "데모 명리 팩 로딩 중…" : "엔진 조회 후 마인드맵이 표시됩니다."}
        </p>
      )}

      <aside className="mn-studio-full-report" role="note">
        <strong>풀 리포트 SSOT</strong> — <code>{MYEONGNI_FULL_REPORT_SSOT.script}</code>
        <p>{disclaimer ?? MYEONGNI_FULL_REPORT_SSOT.note_ko}</p>
        <button
          type="button"
          className="mn-studio-full-report-btn"
          onClick={() => void runFullReport()}
          disabled={fullReportLoading}
        >
          {fullReportLoading ? "풀 리포트 생성 중…" : "풀 리포트 요약 미리보기"}
        </button>
        {fullReportSummary ? (
          <MyeongniFullReportSummaryCard summary={fullReportSummary} />
        ) : null}
        {fullReportMarkdown ? (
          <details className="mn-studio-full-report-md">
            <summary>풀 리포트 Markdown 미리보기</summary>
            <pre className="mn-studio-full-report-md-pre">{fullReportMarkdown}</pre>
          </details>
        ) : null}
      </aside>
    </section>
  );
}
