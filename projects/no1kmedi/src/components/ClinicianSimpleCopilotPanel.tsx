"use client";

import { useCallback, useState, type ReactNode } from "react";
import {
  buildChartSummaryCopy,
  buildFullCopilotCopy,
  buildPatientEducationCopy,
  HAN_MEDICINE_LORA_PACK_V0,
  type SimpleCopilotMedicalCalcV1,
  type SimpleCopilotCardsV1,
  type SimpleCopilotSajuCalcV1,
} from "@/lib/clinician-simple-copilot-v1";

type CopilotCardProps = {
  title: string;
  badge?: string;
  variant?: "primary" | "muted";
  children: ReactNode;
};

function CopilotCard({ title, badge, variant = "muted", children }: CopilotCardProps) {
  return (
    <section className={`copilot-card copilot-card--${variant}`}>
      <header className="copilot-card-head">
        <h3 className="copilot-card-title">{title}</h3>
        {badge ? <span className="copilot-card-badge">{badge}</span> : null}
      </header>
      <div className="copilot-card-body">{children}</div>
    </section>
  );
}

export function ClinicianSimpleCopilotPanel() {
  const [chiefComplaint, setChiefComplaint] = useState("");
  const [onset, setOnset] = useState("");
  const [birthdate, setBirthdate] = useState("");
  const [birthTime, setBirthTime] = useState("");
  const [sasang, setSasang] = useState("unknown");
  const [painScale, setPainScale] = useState(5);
  const [redFlagChestPain, setRedFlagChestPain] = useState(false);
  const [redFlagNeuro, setRedFlagNeuro] = useState(false);
  const [redFlagDyspnea, setRedFlagDyspnea] = useState(false);
  const [redFlagFeverBleeding, setRedFlagFeverBleeding] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [cards, setCards] = useState<SimpleCopilotCardsV1 | null>(null);
  const [medicalCalc, setMedicalCalc] = useState<SimpleCopilotMedicalCalcV1 | null>(null);
  const [sajuCalc, setSajuCalc] = useState<SimpleCopilotSajuCalcV1 | null>(null);
  const [actionNotice, setActionNotice] = useState("");

  const runAnalysis = useCallback(async () => {
    setError("");
    setCards(null);
    setMedicalCalc(null);
    setSajuCalc(null);
    if (!chiefComplaint.trim()) {
      setError("주호소·증상을 입력해 주세요.");
      return;
    }
    if (!birthdate.trim()) {
      setError("생년월일을 입력해 주세요.");
      return;
    }

    setBusy(true);
    try {
      const request_id = `copilot_${Date.now()}`;
      const res = await fetch("/api/clinician/simple-copilot-v1", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema: "simple_copilot_request_v1",
          request_id,
          chief_complaint: chiefComplaint.trim(),
          onset: onset.trim() || undefined,
          birthdate: birthdate.trim(),
          birth_time: birthTime.trim() || undefined,
          birth_time_known: Boolean(birthTime.trim()),
          sasang_candidate: sasang,
          pain_scale_0_10: painScale,
          red_flags: {
            chest_pain: redFlagChestPain,
            neuro_deficit: redFlagNeuro,
            dyspnea: redFlagDyspnea,
            bleeding_or_high_fever: redFlagFeverBleeding,
          },
        }),
      });
      const json = (await res.json()) as {
        success: boolean;
        error?: string;
        cards?: SimpleCopilotCardsV1;
        medical_calc?: SimpleCopilotMedicalCalcV1;
        saju_calc?: SimpleCopilotSajuCalcV1;
      };
      if (!json.success || !json.cards) {
        setError(json.error || "분석에 실패했습니다.");
        return;
      }
      setCards(json.cards);
      setMedicalCalc(json.medical_calc || null);
      setSajuCalc(json.saju_calc || null);
    } catch {
      setError("네트워크 오류로 분석을 완료하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  }, [
    birthTime,
    birthdate,
    chiefComplaint,
    onset,
    painScale,
    redFlagChestPain,
    redFlagDyspnea,
    redFlagFeverBleeding,
    redFlagNeuro,
    sasang,
  ]);

  const copyContext = useCallback(() => {
    if (!cards) return null;
    return {
      chief_complaint: chiefComplaint,
      cards,
      medical: medicalCalc,
      saju: sajuCalc,
    };
  }, [cards, chiefComplaint, medicalCalc, sajuCalc]);

  const copyText = useCallback(
    async (text: string, notice: string) => {
      setActionNotice("");
      try {
        await navigator.clipboard.writeText(text);
        setActionNotice(notice);
      } catch {
        setActionNotice("클립보드 복사에 실패했습니다. 브라우저 권한을 확인해 주세요.");
      }
    },
    [],
  );

  const copyChartSummary = useCallback(async () => {
    const ctx = copyContext();
    if (!ctx) return;
    await copyText(buildChartSummaryCopy(ctx), "차트 요약본을 복사했습니다.");
  }, [copyContext, copyText]);

  const copyPatientEducation = useCallback(async () => {
    const ctx = copyContext();
    if (!ctx) return;
    await copyText(buildPatientEducationCopy(ctx), "환자 안내문을 복사했습니다.");
  }, [copyContext, copyText]);

  const copyFullResult = useCallback(async () => {
    const ctx = copyContext();
    if (!ctx) return;
    await copyText(buildFullCopilotCopy(ctx), "전체 결과를 복사했습니다.");
  }, [copyContext, copyText]);

  const savePdf = useCallback(() => {
    if (!cards) return;
    setActionNotice("브라우저 인쇄 창에서 PDF로 저장해 주세요.");
    window.print();
  }, [cards]);

  return (
    <div className="copilot-panel">
      <div className="copilot-panel-intro">
        <p className="copilot-pack-label">
          {HAN_MEDICINE_LORA_PACK_V0.product_name_ko} · v{HAN_MEDICINE_LORA_PACK_V0.version}
        </p>
        <p className="copilot-panel-lead">
          메뉴는 진료 분석(기본) → 대화 → 환자설정 순서로 쓰세요. 입력 즉시 사주 계산과 의학 리스크 계산을
          함께 반영해 4카드로 정리합니다.
        </p>
      </div>

      <form
        className="copilot-form"
        onSubmit={(e) => {
          e.preventDefault();
          void runAnalysis();
        }}
      >
        <label className="copilot-field copilot-field--full">
          <span>주호소 / 증상 *</span>
          <textarea
            value={chiefComplaint}
            onChange={(e) => setChiefComplaint(e.target.value)}
            rows={4}
            placeholder="예: 복통 2주, 식후 더부룩함, 설사 간헐적"
            disabled={busy}
          />
        </label>

        <label className="copilot-field copilot-field--full">
          <span>증상 경과 (선택)</span>
          <input
            type="text"
            value={onset}
            onChange={(e) => setOnset(e.target.value)}
            placeholder="예: 2주, 어제부터 급성"
            disabled={busy}
          />
        </label>

        <div className="copilot-form-row">
          <label className="copilot-field">
            <span>생년월일 *</span>
            <input
              type="text"
              value={birthdate}
              onChange={(e) => setBirthdate(e.target.value)}
              placeholder="1990-03-15"
              disabled={busy}
            />
          </label>
          <label className="copilot-field">
            <span>출생시간 (선택)</span>
            <input
              type="text"
              value={birthTime}
              onChange={(e) => setBirthTime(e.target.value)}
              placeholder="14:30"
              disabled={busy}
            />
          </label>
          <label className="copilot-field">
            <span>사상 체질 (선택)</span>
            <select value={sasang} onChange={(e) => setSasang(e.target.value)} disabled={busy}>
              <option value="unknown">미지정</option>
              <option value="taeyang">태양</option>
              <option value="soyag">소양</option>
              <option value="taeum">태음</option>
              <option value="soeum">소음</option>
            </select>
          </label>
        </div>

        <div className="copilot-form-row">
          <label className="copilot-field">
            <span>통증 척도 (0~10)</span>
            <input
              type="number"
              min={0}
              max={10}
              value={painScale}
              onChange={(e) => setPainScale(Number(e.target.value))}
              disabled={busy}
            />
          </label>
          <label className="copilot-flag-toggle">
            <input type="checkbox" checked={redFlagChestPain} onChange={(e) => setRedFlagChestPain(e.target.checked)} disabled={busy} />
            흉통
          </label>
          <label className="copilot-flag-toggle">
            <input type="checkbox" checked={redFlagNeuro} onChange={(e) => setRedFlagNeuro(e.target.checked)} disabled={busy} />
            신경학적 이상
          </label>
          <label className="copilot-flag-toggle">
            <input type="checkbox" checked={redFlagDyspnea} onChange={(e) => setRedFlagDyspnea(e.target.checked)} disabled={busy} />
            호흡곤란
          </label>
          <label className="copilot-flag-toggle">
            <input
              type="checkbox"
              checked={redFlagFeverBleeding}
              onChange={(e) => setRedFlagFeverBleeding(e.target.checked)}
              disabled={busy}
            />
            고열/출혈
          </label>
        </div>

        <button type="submit" className="copilot-submit" disabled={busy}>
          {busy ? "분석 중…" : "진료 보조 분석"}
        </button>
      </form>

      {error ? (
        <p className="copilot-error" role="alert">
          {error}
        </p>
      ) : null}

      {cards ? (
        <div className="copilot-results">
          {medicalCalc ? (
            <div className="copilot-meta-block">
              <div className="copilot-meta-strip">
                <span className={`copilot-meta-chip is-${medicalCalc.triage_level}`}>
                  {medicalCalc.triage_label_ko}
                </span>
                <span className="copilot-meta-chip">통증 NRS {medicalCalc.pain_scale_0_10}</span>
                <span className="copilot-meta-chip">레드플래그 {medicalCalc.red_flag_count}개</span>
                {medicalCalc.acute_onset_suspected ? (
                  <span className="copilot-meta-chip">급성 경과 의심</span>
                ) : null}
              </div>
              <p className="copilot-meta-action">{medicalCalc.recommended_action}</p>
              {medicalCalc.rationale.length ? (
                <ul className="copilot-rationale">
                  {medicalCalc.rationale.map((line, i) => (
                    <li key={`rat-${i}`}>{line}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
          {sajuCalc ? (
            <div className="copilot-meta-strip">
              <span className="copilot-meta-chip">사주 계산: {sajuCalc.saju_source === "live" ? "완료" : "대기"}</span>
              <span className="copilot-meta-chip">{sajuCalc.saju_label || "사주 라벨 계산 중"}</span>
              <span className="copilot-meta-chip">{sajuCalc.birth_time_known ? "출생시간 입력" : "출생시간 기본값(12:00)"}</span>
            </div>
          ) : null}

          <div className="copilot-action-row">
            <button type="button" className="copilot-action-btn copilot-action-btn--primary" onClick={() => void copyChartSummary()}>
              차트 요약 복사
            </button>
            <button type="button" className="copilot-action-btn copilot-action-btn--primary" onClick={() => void copyPatientEducation()}>
              환자 안내문 복사
            </button>
            <button type="button" className="copilot-action-btn" onClick={() => void copyFullResult()}>
              전체 복사
            </button>
            <button type="button" className="copilot-action-btn" onClick={savePdf}>
              PDF 저장
            </button>
            {actionNotice ? <span className="copilot-action-notice">{actionNotice}</span> : null}
          </div>

          <CopilotCard title={cards.tcm_primary.title} variant="primary">
            {cards.tcm_primary.items.length ? (
              <ul className="copilot-item-list">
                {cards.tcm_primary.items.map((item, i) => (
                  <li key={`tcm-${i}`}>
                    <strong>{item.title}</strong>
                    <p>{item.body}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="copilot-empty">해당 항목이 없습니다.</p>
            )}
          </CopilotCard>

          <CopilotCard title={cards.modern_explain.title} badge="비결정">
            {cards.modern_explain.items.length ? (
              <ul className="copilot-item-list">
                {cards.modern_explain.items.map((item, i) => (
                  <li key={`mod-${i}`}>
                    <strong>{item.title}</strong>
                    <p>{item.body}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="copilot-empty">근거 설명 슬롯이 비어 있습니다.</p>
            )}
          </CopilotCard>

          <CopilotCard title={cards.saju_aux.title} badge="보조/비결정">
            {cards.saju_aux.items.length ? (
              <ul className="copilot-item-list">
                {cards.saju_aux.items.map((item, i) => (
                  <li key={`saju-${i}`}>
                    <strong>{item.title}</strong>
                    <p>{item.body}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="copilot-empty">사주·시간축 보조 항목이 없습니다.</p>
            )}
          </CopilotCard>

          <CopilotCard title={cards.physician_checklist.title}>
            <ul className="copilot-checklist">
              {cards.physician_checklist.items.map((line, i) => (
                <li key={`chk-${i}`}>{line}</li>
              ))}
            </ul>
          </CopilotCard>

          <p className="copilot-disclaimer">{cards.disclaimer}</p>
        </div>
      ) : null}
    </div>
  );
}
