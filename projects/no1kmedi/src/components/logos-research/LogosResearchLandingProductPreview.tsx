/**
 * Soft-open product anchor — static Ask chrome mock (theme tabs + report spine).
 * No invented KPI / pass-rate numbers. Static mock only; not a live query.
 */
export function LogosResearchLandingProductPreview() {
  return (
    <aside
      className="lr-product-preview"
      aria-label="베타 Q&A 화면 미리보기"
      data-logos-landing-product-preview="1"
    >
      <div className="lr-product-preview-chrome">
        <p className="lr-product-preview-eyebrow">Ask 미리보기</p>
        <p className="lr-product-preview-query">시편 23편 — 목자 비유와 학파별 해석</p>
        <ul className="lr-product-preview-tabs" aria-hidden="true">
          <li className="lr-product-preview-tab lr-product-preview-tab--active">인용</li>
          <li className="lr-product-preview-tab">학파</li>
          <li className="lr-product-preview-tab">통찰</li>
          <li className="lr-product-preview-tab">경로</li>
        </ul>
        <div className="lr-product-preview-body">
          <div className="lr-product-preview-block">
            <span className="lr-product-preview-label">인용 근거</span>
            <p>시편 23:1–4 · 본문 앵커가 리포트 상단에 고정됩니다.</p>
          </div>
          <div className="lr-product-preview-block">
            <span className="lr-product-preview-label">학파 비교</span>
            <p>해석 분기를 나란히 두고, 단정 대신 차이를 보여 줍니다.</p>
          </div>
          <div className="lr-product-preview-block lr-product-preview-block--muted">
            <span className="lr-product-preview-label">연구 통찰</span>
            <p>질문 → 근거 → 분기 → 한 줄 정리. 교리 판결·상담 대체가 아닙니다.</p>
          </div>
        </div>
      </div>
      <p className="lr-product-preview-caption">구조만 미리보기 · 수치는 표시하지 않음</p>
    </aside>
  );
}
