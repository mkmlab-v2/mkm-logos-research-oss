"use client";



type LifestyleSlot = {

  slot_id?: string;

  title?: string;

  body_markdown?: string;

  human_confirm_required?: boolean;

};



type SuppressionEntry = {

  node_id?: string;

  reason?: string;

  tier_blocked_by?: string;

  triggered_by?: string;

};



type IntegratedWellnessDraft = {

  schema?: string;

  disclaimer?: string;

  human_confirm_required?: boolean;

  suppression_log_count?: number;

  suppression_log?: SuppressionEntry[];

  patient_slots?: LifestyleSlot[];

  error?: string;

};



type IntegratedWellnessLifestyleDraftPreviewProps = {

  draft: IntegratedWellnessDraft | undefined;

  loading?: boolean;

};



function renderMarkdownLite(md: string): string {

  return md

    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")

    .replace(/^#### (.+)$/gm, "<h4>$1</h4>")

    .replace(/^- (.+)$/gm, "<li>$1</li>")

    .replace(/~~([^~]+)~~/g, "<s>$1</s>");

}



export function IntegratedWellnessLifestyleDraftPreview({

  draft,

  loading = false,

}: IntegratedWellnessLifestyleDraftPreviewProps) {

  if (loading) {

    return (

      <article className="card consult-iws-draft">

        <h3>웰니스 생활지도 초안 (IWS v2)</h3>

        <p className="consult-source-chip">Tier 0–3 resolver 실행 중…</p>

      </article>

    );

  }



  if (!draft) return null;



  if (draft.error) {

    return (

      <article className="card consult-iws-draft">

        <h3>웰니스 생활지도 초안 (IWS v2)</h3>

        <p className="consult-notice">IWS v2 미생성: {draft.error}</p>

        <p className="consult-source-chip">MKM_WORKSPACE_ROOT·Python 체인 확인 필요 (B-track 참고용).</p>

      </article>

    );

  }



  const sasangSlot = (draft.patient_slots || []).find((s) => s.slot_id === "sasang");

  const body = sasangSlot?.body_markdown?.trim() || "";

  const suppression = draft.suppression_log || [];

  const suppressionCount =

    typeof draft.suppression_log_count === "number" ? draft.suppression_log_count : suppression.length;



  return (

    <article className="card consult-iws-draft">

      <h3>웰니스 생활지도 초안 (IWS v2)</h3>

      <p className="consult-source-chip">

        B-track · human_confirm 필수

        {suppressionCount > 0 ? ` · suppression ${suppressionCount}건` : ""}

      </p>

      {draft.disclaimer ? <p className="consult-notice">{draft.disclaimer}</p> : null}

      {body ? (

        <div

          className="consult-iws-draft-body"

          dangerouslySetInnerHTML={{ __html: renderMarkdownLite(body) }}

        />

      ) : (

        <p className="consult-notice">생활지도 슬롯이 비어 있습니다.</p>

      )}

      {suppression.length > 0 ? (

        <details className="consult-iws-suppression">

          <summary>제외된 권고 (suppression_log) — {suppression.length}건</summary>

          <table className="consult-iws-suppression-table">

            <thead>

              <tr>

                <th scope="col">node_id</th>

                <th scope="col">tier</th>

                <th scope="col">trigger</th>

                <th scope="col">reason</th>

              </tr>

            </thead>

            <tbody>

              {suppression.map((entry) => (

                <tr key={`${entry.node_id}-${entry.triggered_by}`}>

                  <td>

                    <code>{entry.node_id}</code>

                  </td>

                  <td>{entry.tier_blocked_by || "—"}</td>

                  <td>{entry.triggered_by || "—"}</td>

                  <td>{entry.reason || "—"}</td>

                </tr>

              ))}

            </tbody>

          </table>

        </details>

      ) : null}

      <p className="consult-notice">

        [HYPO] 사상·명리 구간은 임상 확정이 아닙니다. 최종 생활지도는 한의사 human_confirm 후 차트에 반영하세요.

      </p>

    </article>

  );

}


