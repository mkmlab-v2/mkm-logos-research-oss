/**
 * K-Startup PMS 표준항목(STEP04) — OpenData 327 · 과제 20460495
 * 로그인된 Chrome에서 F12 → Console → 붙여넣기 → Enter
 * 제출완료 누르지 말 것. 끝나면 화면에서 「임시저장」 한 번 더 확인.
 */
(function () {
  const TSKS_NM =
    "정책자금 융자 신청서 자동 초안 생성(RAG·근거연동·출력보류)";
  const TSKS_CTNT =
    "공고·신청서식·기재요령·사업계획서 예시를 버전관리·인덱싱하고, 기업정보와 RAG로 항목별 초안을 생성한다. 근거 미연결·필수누락 시 출력보류(HOLD) 후 담당자 확인을 거쳐 PDF(hwp 단계적) 산출·감사로그를 제공한다.";

  function setVal(id, v) {
    const el = document.getElementById(id);
    if (!el || el.readOnly) return { id, ok: false };
    el.focus();
    el.value = v;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
    return { id, ok: true, value: el.value };
  }

  function pickCombo(suffix, label) {
    const inp = document.querySelector(
      `[id*="mf_wfm_contents_sbx_${suffix}"][id$="_input"]`
    );
    if (!inp) return { suffix, ok: false, reason: "input_missing" };
    const btn = document.getElementById(inp.id.replace("_input", "_button"));
    if (!btn) return { suffix, ok: false, reason: "button_missing" };
    btn.click();
    const row = [...document.querySelectorAll("tr")].find((r) =>
      (r.innerText || "").includes(label)
    );
    if (!row) return { suffix, ok: false, reason: "row_missing", label };
    row.click();
    return { suffix, ok: true, label };
  }

  const r = [];
  r.push(setVal("mf_wfm_contents_ibx_tsksNm", TSKS_NM));
  r.push(setVal("mf_wfm_contents_ibx_tsksCtnt", TSKS_CTNT));

  const svc =
    document.getElementById("mf_wfm_contents_sbx_suptShpr_input_1") ||
    document.querySelector('[id*="suptShpr"][id$="_input_1"]');
  if (svc) {
    svc.click();
    r.push({ id: "지원분야", ok: true, value: "지식서비스(input_1)" });
  } else {
    r.push({ id: "지원분야", ok: false });
  }

  r.push(pickCombo("entHopeRgnClcd", "경기"));
  r.push(pickCombo("spcTechFldClcd", "정보통신"));
  r.push(pickCombo("ictDtlClcd", "소프트웨어"));

  console.table(r);
  console.log("과제명:", document.getElementById("mf_wfm_contents_ibx_tsksNm")?.value);
  console.log(
    "과제내용 길이:",
    (document.getElementById("mf_wfm_contents_ibx_tsksCtnt")?.value || "").length
  );
  alert(
    "표준항목 채움 완료. 지원분야=지식서비스·경기·정보통신·소프트웨어 확인 후 임시저장을 눌러 주세요."
  );
})();
